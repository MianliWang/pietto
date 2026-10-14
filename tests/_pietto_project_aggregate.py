from __future__ import annotations

from pathlib import Path

import pytest

from pietto._project import check as project_check
from pietto._project import project_grain
from pietto._project import project_ir_joins as joins
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_multifact as multifact
from pietto._project import project_relationship_conditions as conditions
from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project import project_relationship_paths as paths
from pietto._project import project_relationship_uses as relationship_uses
from pietto._project import project_relationships, project_row_keys, project_value_fds
from pietto._project.model import build_empty_project_semantic_result
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

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice12-per-aggregate-fact-locality-chasm-detection-multi-fact-alignment-v1.md"
)


def _source() -> str:
    return """shape CustomerRow:
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
query windowed:
    from orders
    select:
        id
        ranking = row_number() window:
            order by:
                id
relationship customer_orders_coarse:
    endpoint customer: customers
    endpoint orders: orders_by_customer
    on customer.id == orders.customer_id
relationship customer_orders_fine:
    endpoint customer: customers
    endpoint orders: orders_by_customer_product
    on customer.id == orders.customer_id
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
query joined_aggregate_text:
    from customers
    inner join orders as orders:
        from customers
        via customer_orders_raw: customer -> orders
    select:
        total = count()
"""


def _build(root: Path) -> multifact.ProjectMultiFactAnalysis:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(_source(), encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    semantic = build_empty_project_semantic_result(parsed)
    keys = project_row_keys.build_project_row_keys(semantic)
    value_fds = project_value_fds.build_project_value_fds(keys)
    semantic_facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert semantic_facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = project_grain.build_project_grain_origins(value_fds, evaluation)
    verified = verify_project_ir_stage(evaluation)
    base_properties = relational.build_project_ir_relational_property_stage(
        origins, build_project_ir_analysis_bundle(verified)
    )
    relationships = project_relationships.build_project_relationships(semantic)
    condition_set = conditions.build_project_relationship_conditions(relationships)
    guarantee_set = guarantees.build_project_relationship_match_guarantees(
        condition_set, base_properties
    )
    use_set = relationship_uses.build_project_relationship_uses(
        relationships,
        paths.build_project_relationship_join_shape_index(guarantee_set),
    )
    join_stage = joins.build_project_ir_join_region(
        base_plan=plan,
        base_relational=base_properties,
        uses=use_set,
        allocation=plan.ending_allocation,
    )
    return multifact.build_project_multifact_analysis(
        evaluation=evaluation,
        base_relational=base_properties,
        join_regions=join_stage,
    )


@pytest.fixture(scope="module")
def built(
    tmp_path_factory: pytest.TempPathFactory,
) -> multifact.ProjectMultiFactAnalysis:
    return _build(tmp_path_factory.mktemp("p62s12"))


def _fact(
    built: multifact.ProjectMultiFactAnalysis, owner: str, output: str
) -> multifact.ProjectAggregateFactOccurrence:
    matches = tuple(
        fact
        for fact in built.facts
        if fact.context.semantic_facts.owner.definition.name == owner
        and fact.aggregate_result.output_name == output
    )
    assert len(matches) == 1
    return matches[0]


def _region(
    built: multifact.ProjectMultiFactAnalysis, owner: str
) -> multifact.ProjectMultiFactConcreteRegion:
    matches = tuple(
        region
        for region in built.concrete_regions
        if region.region.ledger.owner.definition.name == owner
    )
    assert len(matches) == 1
    return matches[0]


def _subject(
    built: multifact.ProjectMultiFactAnalysis, owner: str
) -> multifact.ProjectMultiFactNonConcreteRegionSubject:
    matches = tuple(
        subject
        for subject in built.non_concrete_regions
        if subject.region.ledger.owner.definition.name == owner
    )
    assert len(matches) == 1
    return matches[0]


def _localities(
    region: multifact.ProjectMultiFactConcreteRegion,
    fact: multifact.ProjectAggregateFactOccurrence,
) -> tuple[multifact.ProjectAggregateFactJoinLocality, ...]:
    return tuple(locality for locality in region.localities if locality.fact is fact)


def _alignment(
    region: multifact.ProjectMultiFactConcreteRegion,
    left: multifact.ProjectAggregateFactOccurrence,
    right: multifact.ProjectAggregateFactOccurrence,
) -> multifact.ProjectMultiFactAlignment:
    matches = tuple(
        item
        for item in region.alignments
        if {id(item.left.fact), id(item.right.fact)} == {id(left), id(right)}
    )
    assert len(matches) == 1
    return matches[0]
