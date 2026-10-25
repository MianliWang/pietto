"""Authored aggregate inputs and their current completed relational inspection."""

from pathlib import Path

from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_inspection import (
    ProjectIRQueryBlockInspectionProduct,
    build_project_query_block_ir_inspection,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)


def _source() -> str:
    return """shape CustomerRow:
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
query windowed:
    from orders
    select:
        id
        ranking = row_number() window(order by id)
relationship customer_orders_raw(customer: CustomerRow, orders: OrderRow):
    customer.id == orders.customer_id
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
query joined_aggregate_text:
    from customers
    inner join orders on customer_orders_raw(customers, orders)
    select:
        total = count()
query aggregate_left_outputs:
    from orders
    let customer = customers
    left join customer on customer_orders_raw(customer, orders)
    select:
        order_id = orders.id
        matched_customer_id = customer.id
relationship customer_copy(first: CustomerRow, second: CustomerRow):
    first.id == second.id
relationship customer_returns_raw(customer: CustomerRow, returned: ReturnRow):
    customer.id == returned.customer_id
query aggregate_pair_outputs:
    from customers
    let dimension = customers
    inner join dimension on customer_copy(customers, dimension)
    inner join orders on customer_orders_raw(customers, orders)
    let returned = returns
    inner join returned on customer_returns_raw(dimension, returned)
    select:
        orders_total = sum(orders.amount)
        returns_total = sum(returned.amount)
query aggregate_pair_same_input:
    from orders
    let returned = returns
    inner join returned on orders.customer_id == returned.customer_id
    select:
        orders_total = sum(orders.amount)
        orders_count = count(orders.amount)
relationship order_return_key(order: OrderRow, returned: ReturnRow):
    order.id == returned.id
query aggregate_pair_keyed:
    from orders
    let returned = returns
    inner join returned on order_return_key(orders, returned)
    select:
        orders_total = sum(orders.amount)
        returns_total = sum(returned.amount)
query aggregate_pair_shared_inputs:
    from customers
    let dimension = customers
    inner join dimension on customer_copy(customers, dimension)
    inner join orders on customer_orders_raw(customers, orders)
    let returned = returns
    inner join returned on customer_returns_raw(dimension, returned)
    select:
        orders_total = sum(orders.amount + customers.id)
        returns_total = sum(returned.amount + dimension.id)
"""


def _build(
    root: Path,
) -> tuple[
    ProjectSemanticResult,
    ProjectConcreteCompletedSemanticResult,
    ProjectIRQueryBlockAnalysisBundle,
    ProjectIRQueryBlockInspectionProduct,
]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(_source(), encoding="utf-8")
    parsed = check_project_parse_only(root)
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
