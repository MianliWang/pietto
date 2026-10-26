from __future__ import annotations

from pathlib import Path

import pytest

from _pietto_semantic_join_facts import located
from pietto._project import check as project_check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze


# A single-file JOIN without `on` (other than CROSS): a declared relationship
# never joins by itself, so the JOIN names its FROM input and the relation of
# its target, also when either is a table or query.

_RESOLUTION_SOURCE = """shape Order:
    id: Int
    customer_id: Int
    order_key = unique(id)
shape Customer:
    id: Int
    name: Text
    region_id: Int | None
    customer_key = unique(id)
shape Region:
    id: Int
    region_key = unique(id)
shape Site:
    id: Int
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
source regions: Region = postgres.table("shop.regions")
source sites: Site = postgres.table("shop.sites")
relationship OrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id
query per_customer:
    from orders
    group by customer_id
    select:
        customer_id
        total = count()
table named:
    from customers
    select:
        id
        name
query zero:
    from orders
    let s = sites
    inner join s
    select:
        id = orders.id
query declared_relationship:
    from orders
    let c = customers
    inner join c
    select:
        id = orders.id
query two_sources:
    from customers
    let peer = customers
    inner join peer on peer.id == customers.id
    let r = regions
    inner join r
    select:
        id = customers.id
query hidden_candidate:
    from orders
    where not any(c.id == orders.customer_id for c in customers)
    let r = regions
    inner join r
    select:
        id = orders.id
query derived_source:
    from per_customer
    let c = customers
    inner join c
    select:
        id = c.id
query derived_target:
    from customers
    let p = per_customer
    left join p
    select:
        id = customers.id
query derived_table:
    from regions
    let n = named
    inner join n
    select:
        id = regions.id
query derived_listed:
    from per_customer
    let o = orders
    inner join o on o.customer_id == per_customer.customer_id
    let c = customers
    full join c
    select:
        id = c.id
"""


def _owners(source: str) -> list[tuple[int, str]]:
    """The first line and name of each table and query of `source`."""

    return [
        (number, line.split()[1].rstrip(":"))
        for number, line in enumerate(source.split("\n"), 1)
        if line.startswith(("query ", "table "))
    ]


def _errors_by_relation(
    source: str, diagnostics: tuple[Diagnostic, ...]
) -> dict[str, tuple[Diagnostic, ...]]:
    """The ERROR diagnostics of `source`, by the table or query holding them."""

    owners = _owners(source)
    found: dict[str, tuple[Diagnostic, ...]] = {}
    for item in diagnostics:
        if item.severity is Severity.ERROR:
            name = next(
                name
                for number, name in reversed(owners)
                if number <= item.location.line
            )
            found[name] = (*found.get(name, ()), item)
    return found


def _single_file_errors(source: str) -> dict[str, tuple[Diagnostic, ...]]:
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None, parsed.diagnostics
    return _errors_by_relation(source, analyze(parsed.ast).diagnostics)


@pytest.fixture(scope="module")
def resolution() -> dict[str, tuple[Diagnostic, ...]]:
    return _single_file_errors(_RESOLUTION_SOURCE)


def _at(source: str, query: str, needle: str) -> tuple[int, int]:
    """The 1-based line and column of the first `needle` inside a query."""

    lines = source.split("\n")
    start = lines.index(f"query {query}:")
    for number, line in enumerate(lines[start:], start + 1):
        if needle in line:
            return number, line.index(needle) + 1
    raise AssertionError(f"{needle!r} is not in query {query}")


def _expected(
    source: str, query: str, items: tuple[tuple[str, str, str], ...]
) -> list[tuple[str, str, int, int]]:
    return [
        (code, message, *_at(source, query, needle)) for code, message, needle in items
    ]


_S2335 = "PIE-S2335"


def _write_on(
    binding: str, inputs: str, relation: str, needle: str
) -> tuple[str, str, str]:
    return (
        _S2335,
        f"JOIN {binding}: write `on` with the condition that matches {inputs} "
        f"to {relation}",
        needle,
    )


_FAILURES = (
    # No relationship joins the FROM input to the target.
    ("zero", (_write_on("s", "orders", "sites", "inner join s"),)),
    # A declared relationship of the two inputs does not join them by itself.
    (
        "declared_relationship",
        (_write_on("c", "orders", "customers", "inner join c"),),
    ),
    # A later JOIN also names the FROM input.
    (
        "two_sources",
        (_write_on("r", "customers", "regions", "inner join r"),),
    ),
    # The input of an existence filter is not an input of a later JOIN.
    (
        "hidden_candidate",
        (_write_on("r", "orders", "regions", "inner join r"),),
    ),
    # A table or query input or target is named as a source is.
    (
        "derived_source",
        (_write_on("c", "per_customer", "customers", "inner join c"),),
    ),
    (
        "derived_target",
        (_write_on("p", "customers", "per_customer", "left join p"),),
    ),
    ("derived_table", (_write_on("n", "regions", "named", "inner join n"),)),
    (
        "derived_listed",
        (_write_on("c", "per_customer", "customers", "full join c"),),
    ),
)


@pytest.mark.parametrize(
    ("query", "items"), _FAILURES, ids=[case[0] for case in _FAILURES]
)
def test_single_file_relationship_join_failures_name_their_cause(
    resolution: dict[str, tuple[Diagnostic, ...]],
    query: str,
    items: tuple[tuple[str, str, str], ...],
) -> None:
    # Only the JOINs without `on` fail; their inputs and the ON JOINs do not.
    assert set(resolution) == {name for name, _ in _FAILURES}
    assert located(resolution[query]) == _expected(_RESOLUTION_SOURCE, query, items)


# Where a project names the cause of a JOIN without `on` whose one earlier
# input is the FROM input, a single file reports the same text at the same
# JOIN, with PIE-S2335 instead of the project's PIE-S2333 prefix.
_AGREEMENT_SOURCE = """shape Order:
    id: Int
    customer_id: Int | None
    amount: Int
    order_key = unique(id)
shape Customer:
    id: Int
    name: Text
    region_id: Int | None
    ref: Int | None
    customer_key = unique(id)
shape Region:
    id: Int
    label: Text
    region_key = unique(id)
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
source regions: Region = postgres.table("shop.regions")
relationship OrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id
relationship CustomerRegion(customer: Customer, region: Region):
    customer.region_id == region.id
relationship Referral(referrer: Customer, referee: Customer):
    referee.ref == referrer.id
relationship RegionOnlyLt(region: Region, order: Order):
    region.id < order.amount
query per_customer:
    from orders
    group by customer_id
    select:
        customer_id
        total = count()
query q_zero_candidates:
    from regions
    let other = regions
    inner join other
    select:
        x = regions.id
query q_unusable_only:
    from regions
    let o = orders
    inner join o
    select:
        x = regions.id
query q_self_no_roles:
    from customers
    let peer = customers
    inner join peer
    select:
        x = customers.id
query q_derived_rel:
    from per_customer
    let c = customers
    inner join c
    select:
        x = c.name
query q_derived_target:
    from customers
    let p = per_customer
    left join p
    select:
        x = customers.id
query q_hidden:
    from orders
    where any(c.id == orders.customer_id for c in customers)
    let r = regions
    inner join r
    select:
        x = orders.id
"""


def test_inferred_join_causes_are_the_project_cause_texts_at_the_same_join(
    tmp_path: Path,
) -> None:
    root = tmp_path / "agreement"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(_AGREEMENT_SOURCE, encoding="utf-8")
    project = build_project_completed_semantic_result(
        build_empty_project_semantic_result(
            project_check.check_project_parse_only(root)
        )
    )
    prefix = "Project relation semantic completion is unavailable: "
    causes = [
        (item.message, item.location.line, item.location.column)
        for item in project.diagnostics
        if item.code == "PIE-S2333"
    ]
    reported = [
        (f"{prefix}{name} ({item.message})", item.location.line, item.location.column)
        for name, items in _single_file_errors(_AGREEMENT_SOURCE).items()
        for item in items
        if item.code == _S2335
    ]
    assert len(reported) == 6
    assert reported == causes


def test_the_probe_programs_report_the_project_cause_texts() -> None:
    """The cause texts the project reports for these programs."""

    single = _single_file_errors(_AGREEMENT_SOURCE)
    assert [
        item.message
        for name in (
            "q_zero_candidates",
            "q_unusable_only",
            "q_self_no_roles",
            "q_derived_rel",
        )
        for item in single[name]
    ] == [
        "JOIN other: write `on` with the condition that matches regions to regions",
        "JOIN o: write `on` with the condition that matches regions to orders",
        "JOIN peer: write `on` with the condition that matches customers to customers",
        "JOIN c: write `on` with the condition that matches per_customer to customers",
    ]
