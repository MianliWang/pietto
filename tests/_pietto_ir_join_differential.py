from __future__ import annotations

import argparse
from dataclasses import replace
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
from typing import cast

from pietto._project import check as project_check
from pietto._project import project_grain
from pietto._project import project_ir_construction as construction
from pietto._project import project_ir_joins as joins
from pietto._project import project_ir_properties as ir_properties
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_multifact as multifact
from pietto._project import project_phase62_inspection as inspection
from pietto._project import project_phase62_pure_boundary as pure
from pietto._project import project_phase62_verification as phase62
from pietto._project import project_relationship_conditions as conditions
from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project import project_relationship_paths as paths
from pietto._project import project_relationship_uses as relationship_uses
from pietto._project import project_relationships, project_row_keys, project_value_fds
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_verification import (
    build_project_ir_analysis_bundle,
    verify_project_ir_stage,
)


OBSERVATION_FORMAT = "pietto.phase62-join-differential.v1"
SEED_ENVIRONMENT = "PIETTO_SLICE15_IRRELEVANT"

PRIMARY_MAIN_SOURCE = """shape CustomerRow:
    id: Int not null
    unique customer_key on id
shape OrderRow:
    id: Int not null
    customer_id: Int not null
    product_id: Int not null
    amount: Int nullable
    unique order_key on id
shape ReturnRow:
    id: Int not null
    customer_id: Int not null
    reason_id: Int not null
    amount: Int nullable
    unique return_key on id
source customers: CustomerRow is postgres.table("customers")
source orders: OrderRow is postgres.table("orders")
source returns: ReturnRow is postgres.table("returns")
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
relationship customer_orders_coarse:
    endpoint customer: customers
    endpoint orders: orders_by_customer
    on customer.id == orders.customer_id
relationship customer_orders_fine:
    endpoint customer: customers
    endpoint orders: orders_by_customer_product
    on customer.id == orders.customer_id
relationship customer_returns_coarse:
    endpoint customer: customers
    endpoint returns: returns_by_customer
    on customer.id == returns.customer_id
relationship customer_returns_fine:
    endpoint customer: customers
    endpoint returns: returns_by_customer_reason
    on customer.id == returns.customer_id
relationship independent_facts:
    endpoint orders: orders_by_customer_product
    endpoint returns: returns_by_customer_reason
    on orders.customer_id == returns.customer_id
relationship coarse_copy:
    endpoint original: orders_by_customer
    endpoint copy: orders_by_customer_copy
    on original.customer_id == copy.customer_id
relationship coarse_fine:
    endpoint coarse: orders_by_customer
    endpoint fine: orders_by_customer_product
    on coarse.customer_id == fine.customer_id
relationship orders_returns_aligned:
    endpoint orders: orders_by_customer
    endpoint returns: returns_by_customer
    on orders.customer_id == returns.customer_id
relationship parallel_one:
    endpoint orders: orders_by_customer
    endpoint returns: returns_by_customer
    on orders.customer_id == returns.customer_id
relationship parallel_two:
    endpoint orders: orders_by_customer
    endpoint returns: returns_by_customer
    on orders.customer_id == returns.customer_id
relationship self_fact:
    endpoint child: orders_by_customer
    endpoint parent: orders_by_customer
    on child.customer_id == parent.customer_id
relationship globals:
    endpoint orders: global_orders
    endpoint returns: global_returns
    on orders.total == returns.total
relationship customer_orders_raw:
    endpoint customer: customers
    endpoint orders: orders
    on customer.id == orders.customer_id
relationship orders_customer_unique_target:
    endpoint orders: orders
    endpoint customer: customers
    on orders.customer_id == customer.id
relationship nullable_amounts:
    endpoint orders: orders
    endpoint returns: returns
    on orders.amount == returns.amount
relationship composite_raw:
    endpoint orders: orders
    endpoint returns: returns
    on orders.customer_id == returns.customer_id and orders.product_id == returns.reason_id
query direct_unique_join:
    from customers
    inner join orders_by_customer as orders:
        from customers
    select:
        id
query explicit_one_join:
    from customers
    inner join orders_by_customer as orders:
        from customers
        via customer_orders_coarse: customer -> orders
    select:
        id
query left_one_join:
    from customers
    left join orders_by_customer as orders:
        from customers
        via customer_orders_coarse: customer -> orders
    select:
        id
query variant_direct:
    from customers
    inner join returns_by_customer as returns:
        from customers
    select:
        id
query variant_explicit:
    from customers
    inner join returns_by_customer as returns:
        from customers
        via customer_returns_coarse: customer -> returns
    select:
        id
query unique_target_inner:
    from orders
    inner join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    select:
        id
query unique_target_left:
    from orders
    left join customers as customer:
        from orders
        via orders_customer_unique_target: orders -> customer
    select:
        id
query fanout_join:
    from customers
    inner join orders as orders:
        from customers
        via customer_orders_raw: customer -> orders
    select:
        id
query aligned_join:
    from orders_by_customer
    inner join orders_by_customer_copy as copy:
        from orders_by_customer
        via coarse_copy: original -> copy
    select:
        customer_id
query comparable_join:
    from orders_by_customer
    inner join orders_by_customer_product as fine:
        from orders_by_customer
        via coarse_fine: coarse -> fine
    select:
        customer_id
query chasm_join:
    from customers
    inner join orders_by_customer_product as orders:
        from customers
        via customer_orders_fine: customer -> orders
    inner join returns_by_customer_reason as returns:
        from customers
        via customer_returns_fine: customer -> returns
    select:
        id
query incompatible_join:
    from orders_by_customer_product
    inner join returns_by_customer_reason as returns:
        from orders_by_customer_product
        via independent_facts: orders -> returns
    select:
        customer_id
query reused_join:
    from customers
    inner join orders_by_customer as first_orders:
        from customers
        via customer_orders_coarse: customer -> orders
    inner join orders_by_customer as second_orders:
        from customers
        via customer_orders_coarse: customer -> orders
    select:
        id
query multihop_join:
    from customers
    inner join returns_by_customer as returns:
        from customers
        via customer_orders_coarse: customer -> orders
        via orders_returns_aligned: orders -> returns
    select:
        id
query self_fact_join:
    from orders_by_customer
    left join orders_by_customer as parent:
        from orders_by_customer
        via self_fact: child -> parent
    select:
        customer_id
query global_join:
    from global_orders
    inner join global_returns as returns:
        from global_orders
        via globals: orders -> returns
    select:
        total
query ambiguous_fact_join:
    from orders_by_customer
    inner join returns_by_customer as returns:
        from orders_by_customer
    select:
        customer_id
query missing_fact_join:
    from orders_by_customer
    inner join returns_by_customer_reason as returns:
        from orders_by_customer
    select:
        customer_id
query bad_relationship_join:
    from customers
    inner join returns_by_customer as returns:
        from customers
        via absent_relationship: customer -> returns
    select:
        id
query bad_role_join:
    from customers
    inner join returns_by_customer as returns:
        from customers
        via customer_returns_coarse: missing -> returns
    select:
        id
"""

DISCONNECTED_SOURCE = """shape AuditRow:
    id: Int not null
source audit_rows: AuditRow is postgres.table("audit_rows")
query audit_result:
    from audit_rows
    select:
        id
"""

PARALLEL_RELATIONSHIP = """relationship customer_returns_coarse_parallel:
    endpoint customer: customers
    endpoint returns: returns_by_customer
    on customer.id == returns.customer_id
"""

VARIANT_SOURCES = {
    "primary": PRIMARY_MAIN_SOURCE,
    "parallel": PRIMARY_MAIN_SOURCE.replace(
        "query variant_direct:\n",
        PARALLEL_RELATIONSHIP + "query variant_direct:\n",
        1,
    ),
    "no_unique": PRIMARY_MAIN_SOURCE.replace(
        "    unique customer_key on id\n",
        "",
        1,
    ),
}


def _write_project(
    root: Path,
    source: str,
    *,
    reverse_creation: bool,
) -> Path:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    file_items = (
        ("main.pietto", source),
        ("z_disconnected.pietto", DISCONNECTED_SOURCE),
    )
    for name, text in file_items[::-1] if reverse_creation else file_items:
        (root / name).write_text(text, encoding="utf-8")
    return root


def _semantic_project(root: Path) -> ProjectSemanticResult:
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _allocation(
    coordinates: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> ProjectIRAllocationState:
    node, output, slot, use = coordinates
    return ProjectIRAllocationState(
        scope=ProjectIRSnapshotScope(),
        next_plan_node_position=node,
        next_output_value_position=output,
        next_input_slot_position=slot,
        next_use_position=use,
    )


def _build(
    root: Path,
    source: str,
    *,
    reverse_creation: bool,
    coordinates: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> tuple[
    ProjectSemanticResult,
    multifact.ProjectMultiFactAnalysis,
    phase62.ProjectPhase62AnalysisBundle,
    inspection.ProjectPhase62InspectionProduct,
]:
    semantic = _semantic_project(
        _write_project(root, source, reverse_creation=reverse_creation)
    )
    key_set = project_row_keys.build_project_row_keys(semantic)
    fd_set = project_value_fds.build_project_value_fds(key_set)
    semantic_facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert semantic_facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=_allocation(coordinates),
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = project_grain.build_project_grain_origins(fd_set, evaluation)
    base_verification = verify_project_ir_stage(evaluation)
    base_properties = relational.build_project_ir_relational_property_stage(
        origins,
        build_project_ir_analysis_bundle(base_verification),
    )
    relationship_set = project_relationships.build_project_relationships(semantic)
    condition_set = conditions.build_project_relationship_conditions(relationship_set)
    guarantee_set = guarantees.build_project_relationship_match_guarantees(
        condition_set,
        base_properties,
    )
    use_set = relationship_uses.build_project_relationship_uses(
        relationship_set,
        paths.build_project_relationship_join_shape_index(guarantee_set),
    )
    join_stage = joins.build_project_ir_join_region(
        base_plan=plan,
        base_relational=base_properties,
        uses=use_set,
        allocation=plan.ending_allocation,
    )
    analysis = multifact.build_project_multifact_analysis(
        evaluation=evaluation,
        base_relational=base_properties,
        join_regions=join_stage,
    )
    verified = phase62.verify_project_phase62(analysis)
    bundle = phase62.build_project_phase62_analysis_bundle(verified)
    product = inspection.build_project_phase62_inspection(bundle)
    assert key_set.semantic_result is semantic
    assert fd_set.row_keys is key_set
    assert plan.semantic_facts is semantic_facts
    assert evaluation.project_plan is plan
    assert origins.value_fds is fd_set and origins.evaluation is evaluation
    assert base_properties.origins is origins
    assert base_properties.analyses.stage is evaluation
    assert relationship_set.semantic_result is semantic
    assert condition_set.relationships is relationship_set
    assert guarantee_set.conditions is condition_set
    assert guarantee_set.relational is base_properties
    assert use_set.relationships is relationship_set
    assert use_set.index.guarantees is guarantee_set
    assert join_stage.base_plan is plan
    assert join_stage.base_relational is base_properties
    assert join_stage.uses is use_set
    assert analysis.evaluation is evaluation
    assert analysis.base_relational is base_properties
    assert analysis.join_regions is join_stage
    assert verified.root is analysis
    assert bundle.verification is verified and bundle.root is analysis
    assert product.inspection.analysis_bundle is bundle
    assert product.inspection.root is analysis
    return semantic, analysis, bundle, product


def _identity_value(identity) -> list[object]:
    nominal = identity.identity
    return [
        nominal.module_path,
        identity.module_position,
        identity.declaration_position,
        nominal.namespace.value,
        nominal.declaration_kind.value,
        nominal.declared_name,
    ]


def _relationship_identity_value(identity, name: str) -> list[object]:
    return [
        identity.module.path,
        identity.module_position,
        identity.relationship_position,
        name,
    ]


def _row_field_identity_value(field) -> list[object]:
    if type(field) is ir_properties.ProjectIRRowField:
        identity = field.anchor.identity
        return [
            *_identity_value(identity.owner),
            identity.kind.value,
            identity.field_position,
            identity.name,
        ]
    assert type(field) is ir_properties.ProjectIRStageRowField
    return [
        *_identity_value(field.checkpoint.relation.identity),
        field.checkpoint.kind.value,
        field.field_position,
        field.evidence.name,
    ]


def _ledger(
    analysis: multifact.ProjectMultiFactAnalysis,
    owner: str,
):
    matches = tuple(
        item
        for item in analysis.join_regions.uses.ledgers
        if item.owner.definition.name == owner
    )
    assert len(matches) == 1
    return matches[0]


def _join_region(
    analysis: multifact.ProjectMultiFactAnalysis,
    owner: str,
):
    matches = tuple(
        item
        for item in analysis.join_regions.regions
        if item.ledger.owner.definition.name == owner
    )
    assert len(matches) == 1
    return matches[0]


def _multifact_region(
    analysis: multifact.ProjectMultiFactAnalysis,
    owner: str,
) -> multifact.ProjectMultiFactConcreteRegion:
    matches = tuple(
        item
        for item in analysis.concrete_regions
        if item.region.ledger.owner.definition.name == owner
    )
    assert len(matches) == 1
    return matches[0]


def _relationship_name(
    analysis: multifact.ProjectMultiFactAnalysis,
    declaration,
) -> str:
    matches = tuple(
        item.occurrence.name
        for item in analysis.join_regions.uses.relationships.subjects
        if item.occurrence.identity is declaration
    )
    assert len(matches) == 1
    return matches[0]


def _join_use_value(
    analysis: multifact.ProjectMultiFactAnalysis,
    use,
) -> list[object]:
    concrete = type(use) is relationship_uses.ProjectConcreteJoinUse
    return [
        [*_identity_value(use.identity.owner), use.identity.join_position],
        use.kind.value,
        "concrete" if concrete else use.state.value,
        [] if concrete else [item.kind.value for item in use.issues],
        []
        if use.path is None
        else [
            [
                step.position,
                _relationship_name(analysis, step.guarantee.direction.declaration),
                step.guarantee.direction.source.identity.endpoint_position,
                step.guarantee.direction.target.identity.endpoint_position,
                step.guarantee.minimum.value,
                step.guarantee.maximum.value,
            ]
            for step in use.path.steps
        ],
        (
            None
            if type(use) is not relationship_uses.ProjectNonConcreteJoinUse
            or use.direct_result is None
            else [
                use.direct_result.status.value,
                [
                    _relationship_name(
                        analysis,
                        candidate.direction.declaration,
                    )
                    for candidate in use.direct_result.candidates
                ],
            ]
        ),
    ]


def _factor_value(identity) -> list[object]:
    if type(identity) is project_grain.ProjectJoinGrainFactorIdentity:
        base = identity.base
        introduction = identity.introduction_use.position
        nulling = [item.position for item in identity.nulling_joins]
    else:
        base = identity
        introduction = None
        nulling = []
    operator = (
        base.operator.position
        if type(base) is project_grain.ProjectGroupedGrainFactorIdentity
        else None
    )
    return [
        base.kind.value,
        _identity_value(base.owner),
        operator,
        introduction,
        nulling,
    ]


def _relational_value(output) -> list[object]:
    return [
        output.output.occurrence.ref.position,
        [
            [item.field_position, item.evidence.name, item.effective_nullability.value]
            for item in output.fields
        ],
        [
            [
                [
                    member.field_position
                    for value_class in item.determinants
                    for member in value_class.members
                ],
                item.strength.value,
            ]
            for item in output.keys
        ],
        [
            [
                [
                    member.field_position
                    for value_class in item.determinants
                    for member in value_class.members
                ],
                [
                    member.field_position
                    for value_class in item.dependents
                    for member in value_class.members
                ],
                item.strength.value,
            ]
            for item in output.fds
        ],
        output.grain.state.value,
        [_factor_value(item.identity) for item in output.grain.factors],
        [_factor_value(item) for item in output.grain.active],
        [
            [
                [_factor_value(item) for item in dependency.determinants],
                [_factor_value(item) for item in dependency.dependents],
            ]
            for dependency in output.grain.dependencies
        ],
    ]


def _portable_ref_value(ref) -> list[object]:
    return [ref.domain.value, ref.position]


def _portable_value(value: pure.ProjectPhase62PureValue) -> list[object]:
    payload: object
    if value.tag is pure.ProjectPhase62PureTag.TEXT:
        payload = value.text
    elif value.tag is pure.ProjectPhase62PureTag.INTEGER:
        payload = value.integer
    elif value.tag is pure.ProjectPhase62PureTag.BOOLEAN:
        payload = value.boolean
    elif value.tag is pure.ProjectPhase62PureTag.ENUMERATION:
        payload = value.enumeration
    elif value.tag is pure.ProjectPhase62PureTag.REF:
        assert value.ref is not None
        payload = _portable_ref_value(value.ref)
    elif value.tag is pure.ProjectPhase62PureTag.REFS:
        payload = [_portable_ref_value(item) for item in value.refs]
    elif value.tag is pure.ProjectPhase62PureTag.TEXTS:
        payload = list(value.texts)
    elif value.tag is pure.ProjectPhase62PureTag.INTEGERS:
        payload = list(value.integers)
    elif value.tag is pure.ProjectPhase62PureTag.ENUMERATIONS:
        payload = list(value.enumerations)
    else:
        assert value.tag is pure.ProjectPhase62PureTag.ABSENT
        payload = None
    return [value.tag.value, payload]


def _portable_records(
    document: pure.ProjectPhase62PureDocument,
) -> list[list[object]]:
    return [
        [
            record.kind.value,
            [[field.key, _portable_value(field.value)] for field in record.fields],
        ]
        for record in document.records
    ]


def _fact_value(fact: multifact.ProjectAggregateFactOccurrence) -> list[object]:
    return [
        _identity_value(fact.context.operator.node.anchor.identity),
        fact.identity.aggregate_node.position,
        fact.identity.aggregate_result_position,
        fact.aggregate_result.function,
        fact.aggregate_result.output_name,
    ]


def _locality_value(locality: multifact.ProjectAggregateFactLocality) -> list[object]:
    if type(locality) is multifact.ProjectAggregateFactHomeLocality:
        kind = "home"
        introduction = None
        owner = None
        exposures: list[object] = []
    else:
        assert type(locality) is multifact.ProjectAggregateFactJoinLocality
        kind = locality.side.value
        introduction = locality.introduction_use.ref.position
        owner = _identity_value(locality.region.ledger.bindings[0].identity.owner)
        exposures = [
            [
                item.join.node.ref.position,
                [_factor_value(factor) for factor in item.factor_additions],
            ]
            for item in locality.multiplicity_exposures
        ]
    return [
        _fact_value(locality.fact),
        kind,
        introduction,
        owner,
        [_factor_value(item) for item in locality.contextual_grain.factors],
        exposures,
    ]


def _binary_value(analysis: multifact.ProjectMultiFactAnalysis, join) -> list[object]:
    properties = next(
        item for item in analysis.join_regions.properties.outputs if item.join is join
    )
    return [
        [
            *_identity_value(join.identity.use.owner),
            join.identity.use.join_position,
            join.identity.path_step_position,
        ],
        join.node.ref.position,
        [item.ref.position for item in join.input_slots],
        [item.ref.position for item in join.input_uses],
        join.left_input.output.occurrence.ref.position,
        join.right_input.output.occurrence.ref.position,
        join.output.occurrence.ref.position,
        join.kind.value,
        join.fanout.value,
        join.survival.value,
        join.null_extension.value,
        join.outer_join_barrier.value,
        [
            [
                item.field_position,
                item.evidence.name,
                item.introduction_use.ref.position,
                [ref.position for ref in item.nulling_joins],
                item.effective_nullability.value,
            ]
            for item in join.output.row_shape.fields
        ],
        [
            [
                item.correspondence.identity.conjunct_position,
                item.left.field_position,
                item.right.field_position,
            ]
            for item in join.matches
        ],
        type(properties.null_extension).__name__,
        _relational_value(properties.relational),
    ]


def _analysis_observation(
    analysis: multifact.ProjectMultiFactAnalysis,
    bundle: phase62.ProjectPhase62AnalysisBundle,
    product: inspection.ProjectPhase62InspectionProduct,
    *,
    query_reverse: bool,
) -> dict[str, object]:
    inspected = product.inspection
    relationship_names = {
        item.occurrence.identity: item.occurrence.name
        for item in inspected.relationship_subjects
    }
    relationships = [
        [
            _relationship_identity_value(
                item.occurrence.identity,
                item.occurrence.name,
            ),
            item.state.value,
            [
                [
                    endpoint.identity.endpoint_position,
                    endpoint.authored_role,
                    endpoint.authored_relation_spelling,
                ]
                for endpoint in item.occurrence.endpoints
            ],
        ]
        for item in inspected.relationship_subjects
    ]
    directions = [
        [
            _relationship_identity_value(
                item.direction.declaration,
                relationship_names[item.direction.declaration],
            ),
            item.direction.source.identity.endpoint_position,
            item.direction.target.identity.endpoint_position,
            item.direction.source.authored_role,
            item.direction.target.authored_role,
            item.source_output.output.occurrence.ref.position,
            item.target_output.output.occurrence.ref.position,
            item.minimum.value,
            item.maximum.value,
        ]
        for item in inspected.relationship_directions
    ]
    conditions_ = [
        [
            relationship_names[item.relationship.occurrence.identity],
            [
                [
                    correspondence.identity.conjunct_position,
                    correspondence.endpoint_zero.authored_endpoint_role,
                    correspondence.endpoint_zero.authored_field_spelling,
                    correspondence.endpoint_one.authored_endpoint_role,
                    correspondence.endpoint_one.authored_field_spelling,
                    correspondence.semantics.value,
                ]
                for correspondence in item.correspondences
            ],
        ]
        for item in inspected.relationship_conditions
    ]
    ledgers = [
        [
            _identity_value(ledger.bindings[0].identity.owner),
            [
                [
                    binding.identity.binding_position,
                    binding.name,
                    binding.relation_name,
                    binding.state.value,
                    None
                    if binding.output is None
                    else binding.output.output.occurrence.ref.position,
                ]
                for binding in ledger.bindings
            ],
            [_join_use_value(analysis, use) for use in ledger.uses],
        ]
        for ledger in inspected.join_use_ledgers
    ]
    join_regions = [
        [
            _identity_value(region.ledger.bindings[0].identity.owner),
            (
                "concrete"
                if type(region) is joins.ProjectIRConcreteJoinRegion
                else cast(joins.ProjectIRNonConcreteJoinRegion, region).state.value
            ),
            [
                _binary_value(analysis, item)
                for item in (
                    region.joins
                    if type(region) is joins.ProjectIRConcreteJoinRegion
                    else ()
                )
            ],
            [
                blocker.identity.join_position
                for blocker in (
                    region.blockers
                    if type(region) is joins.ProjectIRNonConcreteJoinRegion
                    else ()
                )
            ],
            [
                region.starting_allocation.next_plan_node_position,
                region.ending_allocation.next_plan_node_position,
            ],
        ]
        for region in analysis.join_regions.regions
    ]
    relational_outputs = (
        *analysis.base_relational.outputs,
        *(item.relational for item in analysis.join_regions.properties.outputs),
    )
    alignments = [
        [
            _locality_value(item.left),
            _locality_value(item.right),
            item.structural.value,
            item.common_grain.status.value,
            [risk.value for risk in item.multiplicity_risks],
            [requirement.value for requirement in item.requirements],
            len(item.chasms),
        ]
        for item in inspected.alignments
    ]
    chasms = [
        [
            _identity_value(item.region.ledger.bindings[0].identity.owner),
            [_locality_value(locality) for locality in item.localities],
            [join.node.ref.position for join in item.introduction_joins],
        ]
        for item in inspected.chasms
    ]
    query_keys = (
        ("direct_unique_join", "join_use"),
        ("variant_direct", "join_use"),
        ("ambiguous_fact_join", "join_use"),
        ("bad_relationship_join", "join_use"),
        ("bad_role_join", "join_use"),
    )
    query_order = query_keys[::-1] if query_reverse else query_keys
    query_values: dict[str, list[object]] = {}
    for owner, _kind in query_order:
        ledger = _ledger(analysis, owner)
        use = ledger.uses[0]
        query_values[owner] = [
            len(inspection.query_project_phase62_join_uses(inspected, use.identity)),
            _join_use_value(analysis, use),
        ]
    for item in inspected.relationship_subjects:
        assert inspection.query_project_phase62_relationships(
            inspected,
            item.occurrence.identity,
        ) == (item,)
    for item in inspected.relationship_directions:
        assert inspection.query_project_phase62_directions(
            inspected,
            item.direction,
        ) == (item,)
    for item in inspected.binary_joins:
        assert inspection.query_project_phase62_binary_joins(
            inspected,
            item.identity,
        ) == (item,)
    for item in inspected.aggregate_facts:
        queried = inspection.query_project_phase62_fact_localities(
            inspected,
            item.identity,
        )
        expected = next(
            entry.localities
            for entry in inspected.fact_locality_index
            if entry.fact is item
        )
        assert queried == expected
    for item in inspected.alignments:
        assert inspection.query_project_phase62_alignment_bucket(
            inspected,
            item.left,
            item.right,
        ) == (item,)
        assert inspection.query_project_phase62_common_grains(inspected, item) == (
            item.common_grain,
        )
    locality_alignment_counts = [
        len(inspection.query_project_phase62_alignments_involving(inspected, item))
        for item in inspected.fact_localities
    ]
    chasm_query_counts = [
        [
            len(inspection.query_project_phase62_chasms_containing(inspected, locality))
            for locality in item.localities
        ]
        for item in inspected.chasms
    ]
    nulling_query_counts = []
    for item in inspected.nulling_provenance:
        queried = inspection.query_project_phase62_nulling(
            inspected,
            item.coordinate.output,
            item.coordinate.field_position,
        )
        assert queried == (item,)
        nulling_query_counts.append(len(queried))
    non_concrete_multifact = [
        [
            _identity_value(item.region.ledger.bindings[0].identity.owner),
            item.structural.value,
            [
                [
                    blocker.identity.join_position,
                    blocker.state.value,
                    [issue.kind.value for issue in blocker.issues],
                ]
                for blocker in item.blockers
            ],
            [_fact_value(fact) for fact in item.identifiable_facts],
            [
                item.region.starting_allocation.next_plan_node_position,
                item.region.ending_allocation.next_plan_node_position,
            ],
        ]
        for item in inspected.non_concrete_multifact_regions
    ]
    summary = inspected.summary
    return {
        "semantic": _semantic_projection(analysis),
        "relations": [
            [
                _identity_value(fragment.subject.anchor.identity),
                fragment.subject.state.value,
                (
                    [
                        _row_field_identity_value(field)
                        for field in fragment.root_relation_output.row_shape.fields
                    ]
                    if type(fragment)
                    is construction.ProjectIRConcreteSingleRelationFragment
                    else []
                ),
            ]
            for fragment in analysis.evaluation.project_plan.fragments
        ],
        "relationships": relationships,
        "directions": directions,
        "conditions": conditions_,
        "direct_candidate_buckets": [
            [
                item[0].source_output.output.occurrence.ref.position,
                item[0].target_output.output.occurrence.ref.position,
                [
                    relationship_names[candidate.direction.declaration]
                    for candidate in item
                ],
            ]
            for item in inspected.direct_candidate_buckets
        ],
        "ledgers": ledgers,
        "join_regions": join_regions,
        "relational_outputs": [_relational_value(item) for item in relational_outputs],
        "facts": [_fact_value(item) for item in inspected.aggregate_facts],
        "fact_localities": [
            [
                _fact_value(entry.fact),
                [_locality_value(item) for item in entry.localities],
            ]
            for entry in inspected.fact_locality_index
        ],
        "alignments": alignments,
        "chasms": chasms,
        "verification": [
            bundle.verification.status.value,
            [item.kind.value for item in bundle.verification.issues],
            bundle.verification.base_verification.status.value,
        ],
        "analysis_products": [
            len(bundle.combined_reverse_uses),
            [item.ref.position for item in bundle.combined_topological_order],
            len(bundle.nulling_provenance),
            len(bundle.fact_localities),
            len(bundle.multifact_alignments.alignments),
            len(bundle.multifact_alignments.chasms),
        ],
        "inspection_counts": [
            summary.relationship_count,
            summary.direction_count,
            summary.condition_count,
            summary.correspondence_count,
            summary.guarantee_count,
            summary.ledger_count,
            summary.join_use_count,
            summary.path_step_count,
            summary.binary_join_count,
            summary.joined_output_count,
            summary.joined_field_count,
            summary.base_relational_output_count,
            summary.candidate_key_count,
            summary.value_fd_count,
            summary.grain_factor_count,
            summary.grain_dependency_count,
            summary.aggregate_fact_count,
            summary.fact_locality_count,
            summary.common_grain_count,
            summary.alignment_count,
            summary.chasm_count,
            summary.non_concrete_region_count,
            summary.combined_analysis_entry_count,
        ],
        "queries": [[owner, query_values[owner]] for owner, _kind in query_keys],
        "non_concrete": [
            len(inspection.query_project_phase62_non_concrete_join_uses(inspected)),
            len(inspection.query_project_phase62_non_concrete_join_regions(inspected)),
            len(
                inspection.query_project_phase62_non_concrete_multifact_regions(
                    inspected
                )
            ),
        ],
        "non_concrete_multifact": non_concrete_multifact,
        "query_closure": [
            locality_alignment_counts,
            chasm_query_counts,
            nulling_query_counts,
        ],
        "portable_records": _portable_records(product.document),
        "canonical_bytes": product.canonical_bytes.decode("utf-8"),
    }


def _join_effect_observation(
    analysis: multifact.ProjectMultiFactAnalysis,
    owner: str,
) -> list[object]:
    use = _ledger(analysis, owner).uses[0]
    assert type(use) is relationship_uses.ProjectConcreteJoinUse
    region = _join_region(analysis, owner)
    assert type(region) is joins.ProjectIRConcreteJoinRegion
    join = region.joins[-1]
    properties = next(
        item for item in analysis.join_regions.properties.outputs if item.join is join
    )
    right_start = len(join.left_input.fields)
    return [
        _join_use_value(analysis, use),
        join.guarantee.minimum.value,
        join.guarantee.maximum.value,
        join.kind.value,
        join.fanout.value,
        join.survival.value,
        join.null_extension.value,
        join.outer_join_barrier.value,
        [
            item.effective_nullability.value
            for item in join.output.row_shape.fields[right_start:]
        ],
        type(properties.null_extension).__name__,
        [item.strength.value for item in properties.relational.keys],
        len(properties.relational.fds),
        [_factor_value(item) for item in properties.relational.grain.active],
    ]


def _semantic_projection(
    analysis: multifact.ProjectMultiFactAnalysis,
) -> dict[str, object]:
    relationship_names = {
        item.occurrence.identity: item.occurrence.name
        for item in analysis.join_regions.uses.relationships.subjects
    }
    return {
        "relationships": [
            [item.occurrence.name, item.state.value]
            for item in analysis.join_regions.uses.relationships.subjects
        ],
        "directions": [
            [
                relationship_names[item.direction.declaration],
                item.direction.source.authored_role,
                item.direction.target.authored_role,
                item.minimum.value,
                item.maximum.value,
            ]
            for item in analysis.join_regions.uses.index.directions
        ],
        "join_uses": [
            [
                ledger.owner.definition.name,
                [
                    [
                        use.kind.value,
                        (
                            "concrete"
                            if type(use) is relationship_uses.ProjectConcreteJoinUse
                            else cast(
                                relationship_uses.ProjectNonConcreteJoinUse,
                                use,
                            ).state.value
                        ),
                        []
                        if use.path is None
                        else [
                            relationship_names[step.guarantee.direction.declaration]
                            for step in use.path.steps
                        ],
                    ]
                    for use in ledger.uses
                ],
            ]
            for ledger in analysis.join_regions.uses.ledgers
        ],
        "binary": [
            [
                region.ledger.owner.definition.name,
                [
                    [
                        item.identity.path_step_position,
                        item.kind.value,
                        item.fanout.value,
                        item.survival.value,
                        item.null_extension.value,
                        item.outer_join_barrier.value,
                    ]
                    for item in (
                        region.joins
                        if type(region) is joins.ProjectIRConcreteJoinRegion
                        else ()
                    )
                ],
            ]
            for region in analysis.join_regions.regions
        ],
        "facts": [
            [
                item.context.semantic_facts.owner.definition.name,
                item.identity.aggregate_result_position,
                item.aggregate_result.function,
                item.aggregate_result.output_name,
            ]
            for item in analysis.facts
        ],
        "alignments": [
            [
                item.left.fact.context.semantic_facts.owner.definition.name,
                item.left.fact.identity.aggregate_result_position,
                item.right.fact.context.semantic_facts.owner.definition.name,
                item.right.fact.identity.aggregate_result_position,
                item.structural.value,
                item.common_grain.status.value,
                [risk.value for risk in item.multiplicity_risks],
                [requirement.value for requirement in item.requirements],
            ]
            for item in analysis.alignments
        ],
    }


def _metamorphic_observation(
    primary: multifact.ProjectMultiFactAnalysis,
    parallel: multifact.ProjectMultiFactAnalysis,
    no_unique: multifact.ProjectMultiFactAnalysis,
) -> dict[str, object]:
    direct = cast(
        relationship_uses.ProjectConcreteJoinUse,
        _ledger(primary, "direct_unique_join").uses[0],
    )
    explicit = cast(
        relationship_uses.ProjectConcreteJoinUse,
        _ledger(primary, "explicit_one_join").uses[0],
    )
    assert direct.path.steps[0].guarantee is explicit.path.steps[0].guarantee
    direct_region = _join_region(primary, "direct_unique_join")
    explicit_region = _join_region(primary, "explicit_one_join")
    assert type(direct_region) is joins.ProjectIRConcreteJoinRegion
    assert type(explicit_region) is joins.ProjectIRConcreteJoinRegion
    primary_parallel_direct = _ledger(primary, "variant_direct").uses[0]
    transformed_direct = _ledger(parallel, "variant_direct").uses[0]
    transformed_explicit = _ledger(parallel, "variant_explicit").uses[0]
    assert type(primary_parallel_direct) is relationship_uses.ProjectConcreteJoinUse
    assert type(transformed_direct) is relationship_uses.ProjectNonConcreteJoinUse
    assert type(transformed_explicit) is relationship_uses.ProjectConcreteJoinUse
    assert transformed_direct.direct_result is not None
    multihop = _join_region(primary, "multihop_join")
    assert type(multihop) is joins.ProjectIRConcreteJoinRegion
    reused = _join_region(primary, "reused_join")
    assert type(reused) is joins.ProjectIRConcreteJoinRegion
    reused_multifact = _multifact_region(primary, "reused_join")
    self_multifact = _multifact_region(primary, "self_fact_join")
    chasm_ledger = _ledger(primary, "chasm_join")
    reused_ledger = _ledger(primary, "reused_join")
    chasm_branch = chasm_ledger.uses[1]
    reused_branch = reused_ledger.uses[1]
    assert type(chasm_branch) is relationship_uses.ProjectConcreteJoinUse
    assert type(reused_branch) is relationship_uses.ProjectConcreteJoinUse
    assert chasm_branch.source_binding is not None
    assert reused_branch.source_binding is not None
    return {
        "direct_vs_explicit": [
            _join_effect_observation(primary, "direct_unique_join"),
            _join_effect_observation(primary, "explicit_one_join"),
            direct.identity != explicit.identity,
            direct_region.joins[0].identity != explicit_region.joins[0].identity,
            direct.path.steps[0].guarantee is explicit.path.steps[0].guarantee,
        ],
        "parallel": [
            _join_use_value(primary, primary_parallel_direct),
            _join_use_value(parallel, transformed_direct),
            _join_use_value(parallel, transformed_explicit),
            len(transformed_direct.direct_result.candidates),
            [
                _relationship_name(parallel, item.direction.declaration)
                for item in transformed_direct.direct_result.candidates
            ],
        ],
        "unique_transition": [
            _join_effect_observation(primary, "unique_target_inner"),
            _join_effect_observation(no_unique, "unique_target_inner"),
        ],
        "inner_vs_left": [
            _join_effect_observation(primary, "explicit_one_join"),
            _join_effect_observation(primary, "left_one_join"),
        ],
        "multi_hop": [
            len(multihop.joins),
            [item.identity.path_step_position for item in multihop.joins],
            all(
                item.left_input.output is multihop.joins[position - 1].output
                for position, item in enumerate(multihop.joins)
                if position > 0
            ),
        ],
        "branching": [
            chasm_branch.source_binding is chasm_ledger.bindings[0],
            reused_branch.source_binding is reused_ledger.bindings[0],
            [
                chasm_branch.source_binding.identity.binding_position,
                reused_branch.source_binding.identity.binding_position,
            ],
        ],
        "role_playing": [
            [item.identity.use.join_position for item in reused.joins],
            [item.input_uses[1].ref.position for item in reused.joins],
            [
                locality.introduction_use.ref.position
                for locality in reused_multifact.localities
            ],
            [
                [_factor_value(item) for item in locality.contextual_grain.factors]
                for locality in reused_multifact.localities
            ],
            [
                locality.introduction_use.ref.position
                for locality in self_multifact.localities
            ],
        ],
        "fanout": _join_effect_observation(primary, "fanout_join"),
        "chasm": [
            len(_multifact_region(primary, "chasm_join").chasms),
            [
                [
                    item.structural.value,
                    [risk.value for risk in item.multiplicity_risks],
                    [requirement.value for requirement in item.requirements],
                ]
                for item in _multifact_region(primary, "chasm_join").alignments
            ],
        ],
        "comparable": [
            [
                item.structural.value,
                item.common_grain.status.value,
                [requirement.value for requirement in item.requirements],
            ]
            for item in _multifact_region(primary, "comparable_join").alignments
        ],
    }


def _pure_rejections(
    product: inspection.ProjectPhase62InspectionProduct,
) -> list[list[object]]:
    document = product.document
    unknown = replace(document, format_marker="unknown.phase62.format")
    reordered = replace(
        document,
        records=(
            document.records[0],
            document.records[2],
            document.records[1],
            *document.records[3:],
        ),
    )
    use_position = next(
        position
        for position, record in enumerate(document.records)
        if record.kind is pure.ProjectPhase62RecordKind.PROJECT_USE
    )
    use_record = document.records[use_position]
    output_position = next(
        position
        for position, field in enumerate(use_record.fields)
        if field.key == "output"
    )
    output_field = use_record.fields[output_position]
    dangling_record = replace(
        use_record,
        fields=(
            *use_record.fields[:output_position],
            replace(
                output_field,
                value=pure.project_phase62_pure_ref(
                    pure.ProjectPhase62PortableRef(
                        domain=pure.ProjectPhase62PortableRefDomain.OUTPUT_VALUE,
                        position=1 << 40,
                    )
                ),
            ),
            *use_record.fields[output_position + 1 :],
        ),
    )
    dangling = replace(
        document,
        records=(
            *document.records[:use_position],
            dangling_record,
            *document.records[use_position + 1 :],
        ),
    )

    def outcome(value: pure.ProjectPhase62PureDocument) -> list[object]:
        result = pure.evaluate_project_phase62_document(value)
        return [
            result.status.value,
            result.record_position,
            result.field_position,
        ]

    return [
        ["unknown_format", *outcome(unknown)],
        ["section_order", *outcome(reordered)],
        ["dangling_ref", *outcome(dangling)],
    ]


def _variant_observation(
    analysis: multifact.ProjectMultiFactAnalysis,
    bundle: phase62.ProjectPhase62AnalysisBundle,
    product: inspection.ProjectPhase62InspectionProduct,
) -> dict[str, object]:
    return {
        "semantic": _semantic_projection(analysis),
        "verification": bundle.verification.status.value,
        "portable_records": _portable_records(product.document),
        "canonical_bytes": product.canonical_bytes.decode("utf-8"),
    }


def _construction(
    root: Path,
    *,
    reverse_operation_order: bool,
) -> tuple[dict[str, object], tuple[object, ...]]:
    specifications = (
        (
            "primary-normal",
            VARIANT_SOURCES["primary"],
            False,
            (0, 0, 0, 0),
        ),
        (
            "primary-reverse",
            VARIANT_SOURCES["primary"],
            True,
            (0, 0, 0, 0),
        ),
        (
            "parallel",
            VARIANT_SOURCES["parallel"],
            False,
            (0, 0, 0, 0),
        ),
        (
            "no-unique",
            VARIANT_SOURCES["no_unique"],
            True,
            (0, 0, 0, 0),
        ),
        (
            "shifted",
            VARIANT_SOURCES["primary"],
            False,
            (7, 11, 5, 5),
        ),
    )
    order = specifications[::-1] if reverse_operation_order else specifications
    built: dict[
        str,
        tuple[
            ProjectSemanticResult,
            multifact.ProjectMultiFactAnalysis,
            phase62.ProjectPhase62AnalysisBundle,
            inspection.ProjectPhase62InspectionProduct,
        ],
    ] = {}
    for name, source, reverse_creation, coordinates in order:
        built[name] = _build(
            root / name,
            source,
            reverse_creation=reverse_creation,
            coordinates=coordinates,
        )
    _normal_semantic, normal, normal_bundle, normal_product = built["primary-normal"]
    _reverse_semantic, reverse, reverse_bundle, reverse_product = built[
        "primary-reverse"
    ]
    normal_value = _analysis_observation(
        normal,
        normal_bundle,
        normal_product,
        query_reverse=reverse_operation_order,
    )
    reverse_value = _analysis_observation(
        reverse,
        reverse_bundle,
        reverse_product,
        query_reverse=not reverse_operation_order,
    )
    assert normal_value == reverse_value
    assert normal.evaluation.project_plan.structural_stage.scope is not (
        reverse.evaluation.project_plan.structural_stage.scope
    )
    assert normal.evaluation.project_plan.structural_stage.nodes[0].ref != (
        reverse.evaluation.project_plan.structural_stage.nodes[0].ref
    )
    assert normal_product.document == reverse_product.document
    assert normal_product.canonical_bytes == reverse_product.canonical_bytes
    _parallel_semantic, parallel, parallel_bundle, parallel_product = built["parallel"]
    _no_unique_semantic, no_unique, no_unique_bundle, no_unique_product = built[
        "no-unique"
    ]
    _shifted_semantic, shifted, shifted_bundle, shifted_product = built["shifted"]
    assert _semantic_projection(normal) == _semantic_projection(shifted)
    assert normal.evaluation.project_plan.structural_stage.nodes[0].ref.position != (
        shifted.evaluation.project_plan.structural_stage.nodes[0].ref.position
    )
    assert normal_product.canonical_bytes != shifted_product.canonical_bytes
    value = {
        "primary": normal_value,
        "parallel": _variant_observation(
            parallel,
            parallel_bundle,
            parallel_product,
        ),
        "no_unique": _variant_observation(
            no_unique,
            no_unique_bundle,
            no_unique_product,
        ),
        "metamorphic": _metamorphic_observation(normal, parallel, no_unique),
        "shifted": {
            "starting_coordinates": [7, 11, 5, 5],
            "first_coordinates": [
                shifted.evaluation.project_plan.structural_stage.nodes[0].ref.position,
                shifted.evaluation.project_plan.structural_stage.outputs[
                    0
                ].ref.position,
                shifted.evaluation.project_plan.structural_stage.input_slots[
                    0
                ].ref.position,
                shifted.evaluation.project_plan.structural_stage.uses[0].ref.position,
            ],
            "semantic": _semantic_projection(shifted),
            "verification": shifted_bundle.verification.status.value,
            "portable_records": _portable_records(shifted_product.document),
            "canonical_bytes": shifted_product.canonical_bytes.decode("utf-8"),
        },
        "pure_rejections": _pure_rejections(normal_product),
    }
    roots = (
        normal.evaluation.project_plan.structural_stage.scope,
        reverse.evaluation.project_plan.structural_stage.scope,
        parallel.evaluation.project_plan.structural_stage.scope,
        no_unique.evaluation.project_plan.structural_stage.scope,
        shifted.evaluation.project_plan.structural_stage.scope,
    )
    assert all(
        left is not right
        for position, left in enumerate(roots)
        for right in roots[position + 1 :]
    )
    return value, roots


def observation(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    first, first_scopes = _construction(
        workspace / "forward",
        reverse_operation_order=False,
    )
    second, second_scopes = _construction(
        workspace / "reverse",
        reverse_operation_order=True,
    )
    assert first == second
    assert all(
        left is not right
        for left, right in zip(first_scopes, second_scopes, strict=True)
    )
    return {
        "observation_format": OBSERVATION_FORMAT,
        "package_version": version("pietto"),
        "runtime_identities_distinct": True,
        **first,
    }


def render(value: object, workspace: Path) -> bytes:
    """Encode one observation exactly as the standalone probe emits it."""

    document = (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=False,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert str(workspace).encode() not in document
    assert os.getcwd().encode() not in document
    irrelevant = os.environ.get(SEED_ENVIRONMENT)
    if irrelevant is not None:
        assert irrelevant.encode() not in document
    assert b"0x" not in document
    assert b".venv" not in document
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    namespace = parser.parse_args(argv)
    sys.stdout.buffer.write(
        render(observation(namespace.workspace), namespace.workspace)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
