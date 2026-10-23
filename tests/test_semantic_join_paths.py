from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from _pietto_semantic_join_facts import JoinScript, join_mode, join_script, located
from pietto._project import check as project_check
from pietto._project import project_grain
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_relationship_conditions as conditions
from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project import project_relationship_paths as paths
from pietto._project import project_relationships
from pietto._project import project_row_keys
from pietto._project import project_value_fds
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
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
from pietto.ast_nodes import (
    AuthoredJoinKind,
    JoinClause,
    JoinOnClause,
    JoinTraversalStep,
    LiteralExpr,
    QueryDef,
    SourceDef,
)
from pietto.errors import Diagnostic, Severity
from pietto.semantic.join_relationships import (
    ResolvedJoinRelationship,
    resolve_join_relationship,
)


def _source() -> str:
    return """shape ARow:
    b_id: Int not null
source a_rows: ARow is postgres.table("a")
shape BRow:
    a_id: Int nullable
    c_id: Int not null
    unique a_key on a_id
source b_rows: BRow is postgres.table("b")
shape CRow:
    id: Int not null
    unique id_key on id
source c_rows: CRow is postgres.table("c")
shape DRow:
    id: Int not null
source d_rows: DRow is postgres.table("d")
relationship ab_one:
    endpoint a: a_rows
    endpoint b: b_rows
    on a.b_id == b.a_id
relationship ab_two:
    endpoint a: a_rows
    endpoint b: b_rows
    on a.b_id == b.a_id
relationship bc:
    endpoint b: b_rows
    endpoint c: c_rows
    on b.c_id == c.id
relationship bd_many:
    endpoint b: b_rows
    endpoint d: d_rows
    on b.c_id == d.id
relationship self_b:
    endpoint child: b_rows
    endpoint parent: b_rows
    on child.a_id == parent.a_id
relationship absent_condition:
    endpoint c: c_rows
    endpoint d: d_rows
"""


def _build(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(_source(), encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    semantic = build_empty_project_semantic_result(parsed)
    keys = project_row_keys.build_project_row_keys(semantic)
    fds = project_value_fds.build_project_value_fds(keys)
    facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = project_grain.build_project_grain_origins(fds, evaluation)
    analyses = build_project_ir_analysis_bundle(verify_project_ir_stage(evaluation))
    properties = relational.build_project_ir_relational_property_stage(
        origins, analyses
    )
    relationship_set = project_relationships.build_project_relationships(semantic)
    condition_set = conditions.build_project_relationship_conditions(relationship_set)
    guarantee_set = guarantees.build_project_relationship_match_guarantees(
        condition_set, properties
    )
    return guarantee_set, paths.build_project_relationship_join_shape_index(
        guarantee_set
    )


def _direction(result, name: str, source_role: str):
    identity = next(
        subject.occurrence.identity
        for subject in result.conditions.relationships.subjects
        if subject.occurrence.name == name
    )
    matches = tuple(
        item
        for item in result.subjects
        if type(item) is guarantees.ProjectDirectionalRelationshipMatchGuarantee
        and item.direction.declaration == identity
        and item.direction.source.authored_role == source_role
    )
    assert len(matches) == 1
    return matches[0]


def _positive(result, direction, name: str):
    condition = next(
        item
        for item in result.conditions.conditions
        if item.relationship.occurrence.name == name
    )
    assert type(condition) is conditions.ProjectConcreteRelationshipCondition
    source_position = direction.direction.source.identity.endpoint_position
    target_position = direction.direction.target.identity.endpoint_position
    source_ref = (
        condition.correspondences[0].endpoint_zero
        if source_position == 0
        else condition.correspondences[0].endpoint_one
    )
    target_ref = (
        condition.correspondences[0].endpoint_zero
        if target_position == 0
        else condition.correspondences[0].endpoint_one
    )
    coverage = guarantees.ProjectReferentialCoverageEvidence(
        direction=direction.direction,
        correspondences=condition.correspondences,
        source_scope=source_ref.constraint_scope,
        target_scope=target_ref.constraint_scope,
        policy=guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE,
        origin=guarantees.ProjectReferentialCoverageOrigin.EXPLICIT_RULE_BOUNDARY,
        trust=guarantees.ProjectReferentialCoverageTrust.TRUSTED,
        authority=guarantees.ProjectExplicitCoverageAuthority(),
    )
    return guarantees.derive_directional_match_guarantee(
        direction.direction,
        condition,
        direction.source_output,
        direction.target_output,
        coverage,
    )


def _index_with(result, replacements):
    subjects = tuple(
        replacements.get(id(subject), subject) for subject in result.subjects
    )
    updated = replace(result, subjects=subjects)
    return paths.build_project_relationship_join_shape_index(updated)


def test_direct_index_absent_unique_ambiguous_parallel_and_self(tmp_path: Path) -> None:
    result, index = _build(tmp_path)
    ab = _direction(result, "ab_one", "a")
    bc = _direction(result, "bc", "b")
    assert index.resolve_direct(ab.source_output, ab.target_output).status is (
        paths.ProjectDirectRelationshipCandidateStatus.AMBIGUOUS
    )
    assert index.resolve_direct(bc.source_output, bc.target_output).status is (
        paths.ProjectDirectRelationshipCandidateStatus.CONCRETE
    )
    assert index.resolve_direct(bc.target_output, ab.source_output).status is (
        paths.ProjectDirectRelationshipCandidateStatus.ABSENT
    )
    self_b = _direction(result, "self_b", "child")
    assert index.resolve_direct(self_b.source_output, self_b.target_output).status is (
        paths.ProjectDirectRelationshipCandidateStatus.AMBIGUOUS
    )
    assert index.non_concrete


def test_explicit_paths_are_ordered_contiguous_and_never_auto_selected(
    tmp_path: Path,
) -> None:
    result, index = _build(tmp_path)
    ab = _direction(result, "ab_one", "a")
    bc = _direction(result, "bc", "b")
    explicit = paths.build_explicit_relationship_path(index, (ab, bc))
    assert tuple(step.position for step in explicit.steps) == (0, 1)
    assert explicit.steps[0].guarantee is ab and explicit.steps[1].guarantee is bc
    with pytest.raises(ValueError, match="contiguous"):
        paths.build_explicit_relationship_path(index, (bc, ab))
    self_b = _direction(result, "self_b", "child")
    repeated = paths.build_explicit_relationship_path(index, (self_b, self_b))
    assert tuple(step.position for step in repeated.steps) == (0, 1)
    assert not hasattr(index, "find_path")


def test_zero_minimum_effects_are_independent_and_nulling_propagates(
    tmp_path: Path,
) -> None:
    result, index = _build(tmp_path)
    ab = _direction(result, "ab_one", "a")
    bd = _direction(result, "bd_many", "b")
    analysis = paths.analyze_relationship_path(
        paths.build_explicit_relationship_path(index, (ab, bd))
    )
    assert analysis.fanout is paths.ProjectRelationshipFanoutEffect.MAY_MULTIPLY
    assert analysis.multiplying_hops == (analysis.path.steps[1],)
    assert analysis.inner_survival is (
        paths.ProjectRelationshipInnerSurvivalEffect.MAY_DROP_SOURCE_ROWS
    )
    assert analysis.survival_risk_hops == analysis.path.steps
    assert (
        analysis.left_nulling
        is paths.ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
    )
    assert analysis.local_nulling_roots == analysis.path.steps
    assert analysis.propagated_null_positions == (0, 1)
    assert analysis.hops[0].fanout is (
        paths.ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY
    )
    with pytest.raises(ValueError, match="complete exact evidence"):
        replace(analysis, multiplying_hops=())
    with pytest.raises(ValueError, match="complete exact evidence"):
        replace(analysis, propagated_null_positions=(0,))
    with pytest.raises(ValueError, match="complete exact evidence"):
        replace(
            analysis,
            fanout=paths.ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY,
        )


def test_positive_minimum_variants_and_early_late_null_propagation(
    tmp_path: Path,
) -> None:
    result, _index = _build(tmp_path)
    ab = _direction(result, "ab_one", "a")
    bd = _direction(result, "bd_many", "b")
    positive_ab = _positive(result, ab, "ab_one")
    positive_bd = _positive(result, bd, "bd_many")

    early_index = _index_with(result, {id(bd): positive_bd})
    early = paths.analyze_relationship_path(
        paths.build_explicit_relationship_path(early_index, (ab, positive_bd))
    )
    assert early.local_nulling_roots == (early.path.steps[0],)
    assert early.propagated_null_positions == (0, 1)

    late_index = _index_with(result, {id(ab): positive_ab})
    late = paths.analyze_relationship_path(
        paths.build_explicit_relationship_path(late_index, (positive_ab, bd))
    )
    assert late.local_nulling_roots == (late.path.steps[1],)
    assert late.propagated_null_positions == (1,)

    all_positive_index = _index_with(result, {id(ab): positive_ab, id(bd): positive_bd})
    all_positive = paths.analyze_relationship_path(
        paths.build_explicit_relationship_path(
            all_positive_index, (positive_ab, positive_bd)
        )
    )
    assert all_positive.inner_survival is (
        paths.ProjectRelationshipInnerSurvivalEffect.GUARANTEES_SOURCE_SURVIVAL
    )
    assert all_positive.left_nulling is (
        paths.ProjectRelationshipLeftNullingEffect.NO_MISSING_MATCH_NULLING
    )
    assert all_positive.fanout is paths.ProjectRelationshipFanoutEffect.MAY_MULTIPLY


def test_closed_vocabulary_private_boundaries_and_contract() -> None:
    assert tuple(paths.ProjectRelationshipFanoutEffect) == (
        paths.ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY,
        paths.ProjectRelationshipFanoutEffect.MAY_MULTIPLY,
        paths.ProjectRelationshipFanoutEffect.UNKNOWN,
        paths.ProjectRelationshipFanoutEffect.CONFLICT,
    )
    assert paths.__all__ == ()


# Single-file JOIN relationship resolution: one M1, M2 or M4 JOIN against the
# relationships of its file, as the analyzer's JOIN phase calls it with the
# JOIN's visible earlier bindings and written `from`.

_RESOLUTION_SOURCE = """type CustomerKey = Int not null
shape Order:
    id: Int not null
    customer_id: CustomerKey not null
    amount: Int not null
    unique order_key on id
shape Customer:
    id: Int not null
    name: Text not null
    region_id: Int nullable
    ref: Int nullable
    unique customer_key on id
shape Region:
    id: Int not null
    label: Text not null
    unique region_key on id
shape Site:
    id: Int not null
shape Line:
    ord_id: Int not null
    line_no: Int not null
    unique line_k on ord_id, line_no
shape Ship:
    id: Int not null
    ord_id: Int nullable
    line_no: Int nullable
source orders: Order is postgres.table("shop.orders")
source customers: Customer is postgres.table("shop.customers")
source regions: Region is postgres.table("shop.regions")
source sites: Site is postgres.table("shop.sites")
source lines: Line is postgres.table("shop.lines")
source ships: Ship is postgres.table("shop.ships")
relationship order_customer: orders.customer_id == customers.id
relationship customer_region: customers.region_id == regions.id
relationship referral:
    endpoint referrer: customers
    endpoint referee: customers
    on referee.ref == referrer.id
relationship ship_line: ships.ord_id == lines.ord_id and ships.line_no == lines.line_no
relationship ship_order: ships.ord_id == lines.ord_id
query per_customer:
    from orders
    group by: customer_id
    select:
        customer_id
        total = count()
table named:
    from customers
    select:
        id
        name
relationship per_customer_customer: per_customer.customer_id == customers.id
relationship per_customer_dup:
    endpoint x: per_customer
    endpoint x: customers
query m1_inferred:
    from orders
    inner join customers as c
    select:
        id = orders.id
query m1_written:
    from orders
    inner join customers as c
    left join regions as r: from c
    select:
        id = orders.id
query m2_roles:
    from customers
    right join orders as o: via order_customer: customers -> orders
    select:
        id = customers.id
query m2_omitted_roles:
    from customers
    inner join orders as o: via order_customer
    select:
        id = customers.id
query m4:
    from orders
    left join customers as c:
        from orders
        via order_customer
        on c.name != "x"
    select:
        id = orders.id
query self_roles:
    from customers
    inner join customers as peer: via referral: referee -> referrer
    select:
        id = customers.id
query self_roles_back:
    from customers
    semi join customers as peer:
        from customers
        via referral: referrer -> referee
    select:
        id = customers.id
query via_later_source:
    from orders
    inner join customers as c
    full join regions as r: via customer_region
    select:
        id = orders.id
query composite:
    from lines
    inner join ships as s: via ship_line
    select:
        id = s.id
query zero:
    from orders
    inner join sites as s
    select:
        id = orders.id
query no_relationship:
    from orders
    inner join sites as s: from orders
    select:
        id = orders.id
query self_no_roles:
    from customers
    inner join customers as peer
    select:
        id = customers.id
query parallel:
    from ships
    inner join lines as l
    select:
        id = ships.id
query two_sources:
    from customers
    inner join customers as peer:
        from customers
        on peer.id == customers.id
    inner join regions as r
    select:
        id = customers.id
query two_sources_via:
    from orders
    inner join customers as c
    inner join customers as d
    select:
        id = orders.id
query start_unread:
    from sites
    inner join regions as r: via customer_region
    select:
        id = sites.id
query start_twice:
    from customers
    inner join customers as peer:
        from customers
        on peer.id == customers.id
    inner join regions as r: via customer_region
    select:
        id = customers.id
query self_omitted:
    from customers
    inner join customers as peer: via referral
    select:
        id = customers.id
query end_unreached:
    from customers
    inner join sites as s: via customer_region
    select:
        id = customers.id
query self_unreached:
    from customers
    inner join regions as r: via referral
    select:
        id = customers.id
query unknown_via:
    from customers
    inner join regions as r: via nowhere
    select:
        id = customers.id
query unknown_via_roles:
    from customers
    inner join regions as r: via nowhere: customers -> regions
    select:
        id = customers.id
query unknown_role:
    from customers
    inner join regions as r: via customer_region: customers -> nope
    select:
        id = customers.id
query unknown_roles:
    from customers
    inner join regions as r: via customer_region: x -> y
    select:
        id = customers.id
query one_role:
    from customers
    inner join regions as r: via customer_region: customers -> customers
    select:
        id = customers.id
query path_start:
    from orders
    inner join regions as r:
        from orders
        via customer_region: customers -> regions
    select:
        id = orders.id
query path_end:
    from customers
    inner join sites as s:
        from customers
        via customer_region: customers -> regions
    select:
        id = customers.id
query path_both:
    from orders
    inner join sites as s:
        from orders
        via customer_region: customers -> regions
    select:
        id = orders.id
query path_start_omitted:
    from orders
    inner join regions as r:
        from orders
        via customer_region
    select:
        id = orders.id
query hidden_reader:
    from orders
    semi join customers as c
    inner join regions as r: via customer_region
    select:
        id = orders.id
query hidden_candidate:
    from orders
    anti join customers as c
    inner join regions as r
    select:
        id = orders.id
query derived_via:
    from customers
    inner join per_customer as p: via per_customer_customer
    select:
        id = customers.id
query derived_via_roles:
    from customers
    inner join per_customer as p:
        from customers
        via per_customer_customer: customers -> per_customer
    select:
        id = customers.id
query derived_source:
    from per_customer
    inner join customers as c: from per_customer
    select:
        id = c.id
query derived_target:
    from customers
    left join per_customer as p: from customers
    select:
        id = customers.id
query derived_inferred:
    from per_customer
    inner join customers as c
    select:
        id = c.id
query derived_table:
    from regions
    inner join named as n: from regions
    select:
        id = regions.id
query derived_listed:
    from per_customer
    inner join orders as o:
        from per_customer
        on o.customer_id == per_customer.customer_id
    inner join customers as c
    select:
        id = c.id
query unknown_via_written:
    from customers
    inner join regions as r:
        from customers
        via nowhere: customers -> regions
    select:
        id = customers.id
query unknown_role_written:
    from customers
    inner join regions as r:
        from customers
        via customer_region: customers -> nope
    select:
        id = customers.id
query unknown_roles_written:
    from customers
    inner join regions as r:
        from customers
        via customer_region: x -> y
    select:
        id = customers.id
query one_role_written:
    from customers
    inner join regions as r:
        from customers
        via customer_region: customers -> customers
    select:
        id = customers.id
query path_end_inferred:
    from customers
    inner join sites as s: via customer_region: customers -> regions
    select:
        id = customers.id
query derived_via_bad_role:
    from customers
    inner join per_customer as p:
        from customers
        via per_customer_customer: customers -> nope
    select:
        id = customers.id
query derived_via_path:
    from orders
    inner join per_customer as p:
        from orders
        via per_customer_customer: customers -> per_customer
    select:
        id = orders.id
query derived_via_unreached:
    from customers
    inner join regions as r: via per_customer_customer
    select:
        id = customers.id
"""


@pytest.fixture(scope="module")
def resolution() -> JoinScript:
    return join_script(_RESOLUTION_SOURCE)


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


def _parts(pair: tuple) -> tuple:
    source, target, comparison, source_operand, target_operand = pair
    return (
        source,
        target,
        (comparison.left.parts, comparison.right.parts),
        source_operand.parts,
        target_operand.parts,
    )


_ORDER_CUSTOMER = ((("orders", "customer_id"), ("customers", "id")),)


_RESOLVED = (
    # M1 without `from`: the one binding with a relationship to the target.
    (
        "m1_inferred",
        1,
        (0, "orders", True, "order_customer", "orders", "customers")
        + (
            (
                (
                    "customer_id",
                    "id",
                    *_ORDER_CUSTOMER,
                    ("orders", "customer_id"),
                    ("customers", "id"),
                ),
            ),
        ),
    ),
    # M1 with `from` an earlier JOIN binding.
    (
        "m1_written",
        2,
        (1, "c", False, "customer_region", "customers", "regions")
        + (
            (
                (
                    "region_id",
                    "id",
                    (("customers", "region_id"), ("regions", "id")),
                    ("customers", "region_id"),
                    ("regions", "id"),
                ),
            ),
        ),
    ),
    # Roles against the declaration order flip the operands, not the
    # conjunct; any kind takes a relationship.
    (
        "m2_roles",
        1,
        (0, "customers", True, "order_customer", "customers", "orders")
        + (
            (
                (
                    "id",
                    "customer_id",
                    *_ORDER_CUSTOMER,
                    ("customers", "id"),
                    ("orders", "customer_id"),
                ),
            ),
        ),
    ),
    (
        "m2_omitted_roles",
        1,
        (0, "customers", True, "order_customer", "customers", "orders")
        + (
            (
                (
                    "id",
                    "customer_id",
                    *_ORDER_CUSTOMER,
                    ("customers", "id"),
                    ("orders", "customer_id"),
                ),
            ),
        ),
    ),
    (
        "m4",
        1,
        (0, "orders", False, "order_customer", "orders", "customers")
        + (
            (
                (
                    "customer_id",
                    "id",
                    *_ORDER_CUSTOMER,
                    ("orders", "customer_id"),
                    ("customers", "id"),
                ),
            ),
        ),
    ),
    # A relationship of a relation to itself is oriented by its roles.
    (
        "self_roles",
        1,
        (0, "customers", True, "referral", "referee", "referrer")
        + (
            (
                (
                    "ref",
                    "id",
                    (("referee", "ref"), ("referrer", "id")),
                    ("referee", "ref"),
                    ("referrer", "id"),
                ),
            ),
        ),
    ),
    (
        "self_roles_back",
        1,
        (0, "customers", False, "referral", "referrer", "referee")
        + (
            (
                (
                    "id",
                    "ref",
                    (("referee", "ref"), ("referrer", "id")),
                    ("referrer", "id"),
                    ("referee", "ref"),
                ),
            ),
        ),
    ),
    # Without `from`, a VIA step starts at the one earlier binding of its
    # source relation, an earlier JOIN binding included.
    (
        "via_later_source",
        2,
        (1, "c", True, "customer_region", "customers", "regions")
        + (
            (
                (
                    "region_id",
                    "id",
                    (("customers", "region_id"), ("regions", "id")),
                    ("customers", "region_id"),
                    ("regions", "id"),
                ),
            ),
        ),
    ),
    # Every equality pair, in declared conjunct order.
    (
        "composite",
        1,
        (0, "lines", True, "ship_line", "lines", "ships")
        + (
            (
                (
                    "ord_id",
                    "ord_id",
                    (("ships", "ord_id"), ("lines", "ord_id")),
                    ("lines", "ord_id"),
                    ("ships", "ord_id"),
                ),
                (
                    "line_no",
                    "line_no",
                    (("ships", "line_no"), ("lines", "line_no")),
                    ("lines", "line_no"),
                    ("ships", "line_no"),
                ),
            ),
        ),
    ),
)


@pytest.mark.parametrize(
    ("query", "ordinal", "expected"), _RESOLVED, ids=[case[0] for case in _RESOLVED]
)
def test_single_file_relationship_joins_resolve_to_oriented_equality_pairs(
    resolution: JoinScript, query: str, ordinal: int, expected: tuple
) -> None:
    resolved = resolution.resolve(query, ordinal)
    assert isinstance(resolved, ResolvedJoinRelationship)
    clause = resolution.relation(query).join_clauses[ordinal - 1]
    assert resolved.step is (
        clause.traversal_steps[0] if clause.traversal_steps else None
    )
    assert resolved.source in resolution.visible(query, ordinal)
    assert (
        resolved.source.ordinal,
        resolved.source.name,
        resolved.source_inferred,
        resolved.relationship,
        resolved.source_role,
        resolved.target_role,
        tuple(_parts(pair) for pair in resolved.pairs),
    ) == expected
    # Each pair keeps the relationship's own conjunct and its two operands.
    (metadata,) = (
        item
        for item in resolution.script.relationships
        if item.name == resolved.relationship
    )
    assert metadata.base_match is not None
    for _, _, comparison, source_operand, target_operand in resolved.pairs:
        assert {id(source_operand), id(target_operand)} == {
            id(comparison.left),
            id(comparison.right),
        }
        assert _is_conjunct(comparison, metadata.base_match.expression)


def _is_conjunct(comparison: object, expression: object) -> bool:
    pending = [expression]
    while pending:
        current = pending.pop()
        if current is comparison:
            return True
        if getattr(current, "operator", None) == "and":
            pending.extend((getattr(current, "left"), getattr(current, "right")))
    return False


_S2335 = "PIE-S2335"
_L3 = (
    "PIE-S2334",
    "A relationship JOIN through a table or query is not available in single "
    "files yet: JOIN {binding} reads {relation}; write `from` and `on` instead.",
)


def _derived(binding: str, relation: str, needle: str) -> tuple[str, str, str]:
    return (_L3[0], _L3[1].format(binding=binding, relation=relation), needle)


_FAILURES = (
    # No earlier binding has a relationship to the target, and a written
    # `from` has none.
    (
        "zero",
        1,
        (
            (
                _S2335,
                "JOIN s: no relationship joins orders to sites; declare one, or "
                "write `from` and `on`",
                "inner join sites as s",
            ),
        ),
    ),
    (
        "no_relationship",
        1,
        (
            (
                _S2335,
                "JOIN s: no relationship joins orders to sites; declare one, or "
                "write `on`",
                "inner join sites as s",
            ),
        ),
    ),
    # Several usable directions from one binding.
    (
        "self_no_roles",
        1,
        (
            (
                _S2335,
                "JOIN peer matches 2 relationship directions from customers: "
                "`via referral: referrer -> referee` and `via referral: referee "
                "-> referrer`; write one of them",
                "inner join customers as peer",
            ),
        ),
    ),
    (
        "parallel",
        1,
        (
            (
                _S2335,
                "JOIN l matches 2 relationship directions from ships: `via "
                "ship_line: ships -> lines` and `via ship_order: ships -> "
                "lines`; write one of them",
                "inner join lines as l",
            ),
        ),
    ),
    # Several candidate bindings; ` and `via`` when one has several
    # directions.
    (
        "two_sources",
        2,
        (
            (
                _S2335,
                "JOIN r matches relationships from 2 earlier bindings: customers "
                "`via customer_region: customers -> regions` and peer `via "
                "customer_region: customers -> regions`; write `from <binding>`",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "two_sources_via",
        2,
        (
            (
                _S2335,
                "JOIN d matches relationships from 2 earlier bindings: orders "
                "`via order_customer: orders -> customers`, c `via referral: "
                "referrer -> referee` and c `via referral: referee -> referrer`; "
                "write `from <binding>` and `via`",
                "inner join customers as d",
            ),
        ),
    ),
    # A VIA step without `from` starts at one earlier binding of its
    # relation; SEMI and ANTI targets are not visible.
    (
        "start_unread",
        1,
        (
            (
                _S2335,
                "JOIN r: `via customer_region` starts at customers, which no "
                "earlier binding reads",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "start_twice",
        2,
        (
            (
                _S2335,
                "JOIN r: `via customer_region` starts at customers, which 2 "
                "earlier bindings read: customers and peer; write `from "
                "<binding>`",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "hidden_reader",
        2,
        (
            (
                _S2335,
                "JOIN r: `via customer_region` starts at customers, which no "
                "earlier binding reads",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "hidden_candidate",
        2,
        (
            (
                _S2335,
                "JOIN r: no relationship joins orders to regions; declare one, "
                "or write `from` and `on`",
                "inner join regions as r",
            ),
        ),
    ),
    # A VIA step without roles takes the one direction ending at the target.
    (
        "self_omitted",
        1,
        (
            (
                _S2335,
                "JOIN peer: relationship referral joins customers to itself; "
                "write `via referral: referrer -> referee` or `via referral: "
                "referee -> referrer`",
                "inner join customers as peer",
            ),
        ),
    ),
    (
        "end_unreached",
        1,
        (
            (
                _S2335,
                "JOIN s: `via customer_region` joins customers and regions, not sites",
                "inner join sites as s",
            ),
        ),
    ),
    (
        "self_unreached",
        1,
        (
            (
                _S2335,
                "JOIN r: `via referral` joins customers to itself, not regions",
                "inner join regions as r",
            ),
        ),
    ),
    # A JOIN without `from` or without roles names a failing step or path at
    # the JOIN, as a project names it.
    (
        "path_start_omitted",
        1,
        (
            (
                _S2335,
                "JOIN r: its VIA path starts at customers, not at its source "
                "binding orders (orders)",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "path_end_inferred",
        1,
        (
            (
                _S2335,
                "JOIN s: its VIA path ends at regions, not at the JOIN target sites",
                "inner join sites as s",
            ),
        ),
    ),
    (
        "unknown_via",
        1,
        (
            (
                _S2335,
                "JOIN r: `via nowhere` names no relationship of this module",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "unknown_via_roles",
        1,
        (
            (
                _S2335,
                "JOIN r: `via nowhere` names no relationship of this module",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "unknown_role",
        1,
        (
            (
                _S2335,
                "JOIN r: relationship customer_region has no endpoint role nope; "
                "its roles are customers and regions",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "unknown_roles",
        1,
        (
            (
                _S2335,
                "JOIN r: relationship customer_region has no endpoint roles x and "
                "y; its roles are customers and regions",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "one_role",
        1,
        (
            (
                _S2335,
                "JOIN r: `via customer_region: customers -> customers` names one "
                "role as both source and target",
                "inner join regions as r",
            ),
        ),
    ),
    # A JOIN that writes `from` and both roles keeps the single-file step
    # checks at the step and its path checks at the JOIN.
    (
        "unknown_via_written",
        1,
        ((_S2335, "Unknown relationship in JOIN VIA: nowhere", "via nowhere"),),
    ),
    (
        "unknown_role_written",
        1,
        (
            (
                _S2335,
                "Unknown endpoint role in JOIN VIA customer_region: nope",
                "via customer_region",
            ),
        ),
    ),
    (
        "unknown_roles_written",
        1,
        (
            (
                _S2335,
                "Unknown endpoint role in JOIN VIA customer_region: x",
                "via customer_region",
            ),
            (
                _S2335,
                "Unknown endpoint role in JOIN VIA customer_region: y",
                "via customer_region",
            ),
        ),
    ),
    (
        "one_role_written",
        1,
        (
            (
                _S2335,
                "JOIN VIA customer_region uses one endpoint role as both source "
                "and target: customers",
                "via customer_region",
            ),
        ),
    ),
    (
        "path_start",
        1,
        (
            (
                _S2335,
                "JOIN VIA path starts at customers, not at source binding orders "
                "(orders)",
                "inner join regions as r",
            ),
        ),
    ),
    (
        "path_end",
        1,
        (
            (
                _S2335,
                "JOIN VIA path ends at regions, not at the JOIN target sites",
                "inner join sites as s",
            ),
        ),
    ),
    (
        "path_both",
        1,
        (
            (
                _S2335,
                "JOIN VIA path starts at customers, not at source binding orders "
                "(orders)",
                "inner join sites as s",
            ),
            (
                _S2335,
                "JOIN VIA path ends at regions, not at the JOIN target sites",
                "inner join sites as s",
            ),
        ),
    ),
    # Relationship JOINs read only sources; a candidate list names a
    # relationship with a table or query endpoint for that reason, also when
    # its declaration has errors (per_customer_dup).
    ("derived_via", 1, (_derived("p", "per_customer", "inner join"),)),
    ("derived_via_roles", 1, (_derived("p", "per_customer", "inner join"),)),
    ("derived_source", 1, (_derived("c", "per_customer", "inner join"),)),
    ("derived_target", 1, (_derived("p", "per_customer", "left join"),)),
    ("derived_inferred", 1, (_derived("c", "per_customer", "inner join"),)),
    ("derived_table", 1, (_derived("n", "named", "inner join"),)),
    (
        "derived_listed",
        2,
        (
            (
                _S2335,
                "JOIN c matches relationships from 2 earlier bindings: "
                "per_customer relationship per_customer_customer (cannot be "
                "used: a relationship JOIN cannot read per_customer), "
                "per_customer relationship per_customer_dup (cannot be used: a "
                "relationship JOIN cannot read per_customer) and o `via "
                "order_customer: orders -> customers`; write `from <binding>`",
                "inner join customers as c",
            ),
        ),
    ),
    # The step and its path are checked before that limit.
    (
        "derived_via_bad_role",
        1,
        (
            (
                _S2335,
                "Unknown endpoint role in JOIN VIA per_customer_customer: nope",
                "via per_customer_customer",
            ),
        ),
    ),
    (
        "derived_via_path",
        1,
        (
            (
                _S2335,
                "JOIN VIA path starts at customers, not at source binding orders "
                "(orders)",
                "inner join per_customer as p",
            ),
        ),
    ),
    (
        "derived_via_unreached",
        1,
        (
            (
                _S2335,
                "JOIN r: `via per_customer_customer` joins per_customer and "
                "customers, not regions",
                "inner join regions as r",
            ),
        ),
    ),
)


@pytest.mark.parametrize(
    ("query", "ordinal", "items"), _FAILURES, ids=[case[0] for case in _FAILURES]
)
def test_single_file_relationship_join_failures_name_their_cause(
    resolution: JoinScript,
    query: str,
    ordinal: int,
    items: tuple[tuple[str, str, str], ...],
) -> None:
    diagnostics = resolution.resolve(query, ordinal)
    assert isinstance(diagnostics, tuple)
    assert all(item.severity is Severity.ERROR for item in diagnostics)
    assert located(diagnostics) == _expected(_RESOLUTION_SOURCE, query, items)


_USABILITY_SOURCE = """type Money = Decimal(10, 2) not null
shape Note:
    id: Int not null
    tag_id: Int nullable
    label: Text not null
    doc: Json nullable
    amount: Money not null
    blob: Bytes nullable
    payload: Any nullable
shape Tag:
    id: Int not null
    doc: Json nullable
    amount: Money not null
    blob: Bytes nullable
    payload: Any nullable
shape Box:
    id: Int not null
shape Addr:
    city: Text not null
shape Person:
    id: Int not null
    home: Addr not null
    tag: Nope not null
shape Place:
    id: Int not null
    home: Addr not null
    tag: Nope not null
source notes: Note is postgres.table("app.notes")
source tags: Tag is postgres.table("app.tags")
source boxes: Box is postgres.table("app.boxes")
source people: Person is postgres.table("app.people")
source places: Place is postgres.table("app.places")
relationship no_on:
    endpoint n: notes
    endpoint t: tags
relationship less:
    endpoint n: notes
    endpoint t: tags
    on n.tag_id < t.id
relationship either:
    endpoint n: notes
    endpoint t: tags
    on n.tag_id == t.id or n.id == t.id
relationship one_side:
    endpoint n: notes
    endpoint t: tags
    on n.tag_id == t.id and n.tag_id == n.id
relationship literal:
    endpoint n: notes
    endpoint t: tags
    on n.tag_id == t.id and n.id == 1
relationship json:
    endpoint n: notes
    endpoint t: tags
    on n.doc == t.doc
relationship money:
    endpoint n: notes
    endpoint t: tags
    on n.amount == t.amount
relationship bytes:
    endpoint n: notes
    endpoint t: tags
    on n.blob == t.blob
relationship anything:
    endpoint n: notes
    endpoint t: tags
    on n.payload == t.payload
relationship bad_field:
    endpoint n: notes
    endpoint t: tags
    on n.nope == t.id
relationship bad_role:
    endpoint n: notes
    endpoint t: tags
    on x.tag_id == t.id
relationship bad_types:
    endpoint n: notes
    endpoint t: tags
    on n.label == t.id
relationship twice:
    endpoint n: notes
    endpoint t: tags
relationship twice:
    endpoint n: notes
    endpoint t: tags
    on n.tag_id == t.id
relationship dangling:
    endpoint n: notes
    endpoint t: nowhere
    on n.tag_id == t.id
relationship same_role:
    endpoint n: notes
    endpoint n: tags
    on n.tag_id == n.id
relationship box_note:
    endpoint b: boxes
    endpoint n: notes
    on b.id == n.nope
relationship home_id:
    endpoint p: people
    endpoint q: places
    on p.home == q.id
relationship same_home:
    endpoint p: people
    endpoint q: places
    on p.home == q.home
relationship same_tag:
    endpoint p: people
    endpoint q: places
    on p.tag == q.tag
relationship box_tag: boxes.id == tags.id
relationship box_tag_bad:
    endpoint b: boxes
    endpoint t: tags
    on b.nope == t.id
query all_reasons:
    from notes
    inner join tags as t
    select:
        id = notes.id
query via_no_on:
    from notes
    inner join tags as t: via no_on
    select:
        id = notes.id
query via_less:
    from notes
    inner join tags as t: via less: n -> t
    select:
        id = notes.id
query via_either:
    from notes
    inner join tags as t: via either
    select:
        id = notes.id
query via_one_side:
    from notes
    inner join tags as t: via one_side
    select:
        id = notes.id
query via_literal:
    from notes
    inner join tags as t: via literal
    select:
        id = notes.id
query via_json:
    from notes
    inner join tags as t: via json
    select:
        id = notes.id
query via_money:
    from notes
    inner join tags as t: via money
    select:
        id = notes.id
query via_bytes:
    from notes
    inner join tags as t: via bytes
    select:
        id = notes.id
query via_anything:
    from notes
    inner join tags as t: via anything
    select:
        id = notes.id
query via_bad_field:
    from notes
    inner join tags as t: via bad_field
    select:
        id = notes.id
query via_bad_role:
    from notes
    inner join tags as t:
        from notes
        via bad_role: n -> t
    select:
        id = notes.id
query via_bad_types:
    from notes
    inner join tags as t: via bad_types
    select:
        id = notes.id
query via_twice:
    from notes
    inner join tags as t: via twice: n -> t
    select:
        id = notes.id
query via_dangling:
    from notes
    inner join tags as t: via dangling: n -> t
    select:
        id = notes.id
query via_same_role:
    from notes
    inner join tags as t: via same_role
    select:
        id = notes.id
query only_declaration_errors:
    from notes
    inner join boxes as b
    select:
        id = notes.id
query only_declaration_errors_written:
    from boxes
    inner join notes as n: from boxes
    select:
        id = boxes.id
query bad_field_unknown_role:
    from notes
    inner join tags as t: via bad_field: n -> x
    select:
        id = notes.id
query bad_field_path_end:
    from notes
    inner join boxes as b:
        from notes
        via bad_field: n -> t
    select:
        id = notes.id
query bad_field_unreached:
    from notes
    inner join boxes as b: via bad_field
    select:
        id = notes.id
query dangling_unreached:
    from notes
    inner join boxes as b: via dangling
    select:
        id = notes.id
query same_role_unreached:
    from notes
    inner join boxes as b: via same_role
    select:
        id = notes.id
query shape_inferred:
    from people
    inner join places as pl
    select:
        id = people.id
query shape_written:
    from people
    inner join places as pl: from people
    select:
        id = people.id
query via_home_id:
    from people
    inner join places as pl: via home_id
    select:
        id = people.id
query via_same_home:
    from people
    inner join places as pl: via same_home
    select:
        id = people.id
query via_same_tag:
    from people
    inner join places as pl: via same_tag
    select:
        id = people.id
query beside_error:
    from boxes
    inner join tags as t
    select:
        id = boxes.id
"""


@pytest.fixture(scope="module")
def usability() -> JoinScript:
    return join_script(_USABILITY_SOURCE)


_NOT_EQUALITIES = "its `on` is not only field equalities that a JOIN can use"
_DECLARATION_ERRORS = "its declaration has errors"


def test_every_relationship_a_join_cannot_use_is_named_with_its_reason(
    usability: JoinScript,
) -> None:
    """In declaration order, each with the first reason that applies: a
    declaration error, no `on`, then any conjunct that is not a field equality
    of the two endpoints, or one of a Decimal (also through an alias), Json,
    Bytes or Any type."""

    reasons = (
        ("no_on", "it has no `on`"),
        ("less", _NOT_EQUALITIES),
        ("either", _NOT_EQUALITIES),
        ("one_side", _NOT_EQUALITIES),
        ("literal", _NOT_EQUALITIES),
        ("json", _NOT_EQUALITIES),
        ("money", _NOT_EQUALITIES),
        ("bytes", _NOT_EQUALITIES),
        ("anything", _NOT_EQUALITIES),
        ("bad_field", _DECLARATION_ERRORS),
        ("bad_role", _DECLARATION_ERRORS),
        ("bad_types", _DECLARATION_ERRORS),
        ("twice", "it has no `on`"),
        ("twice", _DECLARATION_ERRORS),
        ("same_role", _DECLARATION_ERRORS),
    )
    listed = ", ".join(f"{name} ({reason})" for name, reason in reasons[:-1])
    message = (
        f"JOIN t: no relationship from notes to tags can be used: {listed} and "
        f"{reasons[-1][0]} ({reasons[-1][1]})"
    )
    assert located(_diagnostics(usability.resolve("all_reasons", 1))) == _expected(
        _USABILITY_SOURCE,
        "all_reasons",
        ((_S2335, message, "inner join tags as t"),),
    )
    for name, reason in reasons[:9]:
        query = f"via_{name}"
        assert located(_diagnostics(usability.resolve(query, 1))) == _expected(
            _USABILITY_SOURCE,
            query,
            (
                (
                    _S2335,
                    f"JOIN t: relationship {name} cannot be used: {reason}",
                    "inner join tags as t",
                ),
            ),
        )


def test_an_equality_of_fields_without_an_exact_type_cannot_be_used(
    usability: JoinScript,
) -> None:
    """A field of a shape type or of an unknown type has no exact type to
    compare, so a JOIN cannot use the equality, as in a project."""

    names = ("home_id", "same_home", "same_tag")
    listed = (
        f"{names[0]} ({_NOT_EQUALITIES}), {names[1]} ({_NOT_EQUALITIES}) and "
        f"{names[2]} ({_NOT_EQUALITIES})"
    )
    for query in ("shape_inferred", "shape_written"):
        assert located(_diagnostics(usability.resolve(query, 1))) == _expected(
            _USABILITY_SOURCE,
            query,
            (
                (
                    _S2335,
                    f"JOIN pl: no relationship from people to places can be used: "
                    f"{listed}",
                    "inner join places as pl",
                ),
            ),
        )
    for name in names:
        query = f"via_{name}"
        assert located(_diagnostics(usability.resolve(query, 1))) == _expected(
            _USABILITY_SOURCE,
            query,
            (
                (
                    _S2335,
                    f"JOIN pl: relationship {name} cannot be used: {_NOT_EQUALITIES}",
                    "inner join places as pl",
                ),
            ),
        )


def test_a_relationship_beside_one_with_a_declaration_error_is_used(
    usability: JoinScript,
) -> None:
    resolved = usability.resolve("beside_error", 1)
    assert isinstance(resolved, ResolvedJoinRelationship)
    assert (
        resolved.source.name,
        resolved.source_inferred,
        resolved.relationship,
        resolved.source_role,
        resolved.target_role,
        tuple(_parts(pair) for pair in resolved.pairs),
    ) == (
        "boxes",
        True,
        "box_tag",
        "boxes",
        "tags",
        (
            (
                "id",
                "id",
                (("boxes", "id"), ("tags", "id")),
                ("boxes", "id"),
                ("tags", "id"),
            ),
        ),
    )


@pytest.mark.parametrize(
    "query",
    (
        "via_bad_field",
        "via_bad_role",
        "via_bad_types",
        "via_twice",
        "via_dangling",
        "via_same_role",
        "only_declaration_errors",
        "only_declaration_errors_written",
    ),
)
def test_a_relationship_with_its_own_declaration_error_stops_a_join_silently(
    usability: JoinScript, query: str
) -> None:
    """Its PIE-S2601..PIE-S2604 already fails the file; no JOIN diagnostic
    is caused by declaration errors alone."""

    assert usability.resolve(query, 1) == ()


_BEFORE_SILENT = (
    (
        "bad_field_unknown_role",
        (
            _S2335,
            "JOIN t: relationship bad_field has no endpoint role x; its roles are n "
            "and t",
            "inner join tags as t",
        ),
    ),
    (
        "bad_field_path_end",
        (
            _S2335,
            "JOIN VIA path ends at tags, not at the JOIN target boxes",
            "inner join boxes as b",
        ),
    ),
    (
        "bad_field_unreached",
        (
            _S2335,
            "JOIN b: `via bad_field` joins notes and tags, not boxes",
            "inner join boxes as b",
        ),
    ),
    # Without roles, also before an admission error decides the JOIN.
    (
        "dangling_unreached",
        (
            _S2335,
            "JOIN b: `via dangling` joins notes and nowhere, not boxes",
            "inner join boxes as b",
        ),
    ),
    (
        "same_role_unreached",
        (
            _S2335,
            "JOIN b: `via same_role` joins notes and tags, not boxes",
            "inner join boxes as b",
        ),
    ),
)


@pytest.mark.parametrize(
    ("query", "item"), _BEFORE_SILENT, ids=[case[0] for case in _BEFORE_SILENT]
)
def test_step_and_path_errors_come_before_a_declaration_error_stops_a_join(
    usability: JoinScript, query: str, item: tuple[str, str, str]
) -> None:
    assert located(_diagnostics(usability.resolve(query, 1))) == _expected(
        _USABILITY_SOURCE, query, (item,)
    )


def test_relationship_resolution_takes_one_relationship_join_and_its_bindings(
    resolution: JoinScript,
) -> None:
    clause = resolution.relation("m1_inferred").join_clauses[0]
    target = resolution.model.relation_symbols["customers"]
    assert isinstance(target, SourceDef)
    visible = resolution.visible("m1_inferred", 1)
    step = JoinTraversalStep(
        span=clause.span,
        relationship_name="order_customer",
        source_endpoint_role=None,
        target_endpoint_role=None,
    )
    on = JoinOnClause(
        span=clause.span, expression=LiteralExpr(span=clause.span, value=True)
    )
    for misuse, views in (
        (replace(clause, kind=AuthoredJoinKind.CROSS), visible),
        (replace(clause, on_clause=on), visible),
        (replace(clause, traversal_steps=(step, step)), visible),
        (clause, ()),
    ):
        assert isinstance(misuse, JoinClause)
        with pytest.raises(ValueError, match="needs an M1, M2 or M4 JOIN"):
            resolve_join_relationship(
                misuse,
                target=target,
                visible=views,
                written_source=None,
                context=resolution.context,
            )


# Where a project names the cause of a JOIN without `from` or without roles,
# a single file reports the same text at the same JOIN, with PIE-S2335
# instead of the project's PIE-S2333 prefix.
_AGREEMENT_SOURCE = """shape Order:
    id: Int not null
    customer_id: Int nullable
    amount: Int not null
    unique order_key on id
shape Customer:
    id: Int not null
    name: Text not null
    region_id: Int nullable
    ref: Int nullable
    unique customer_key on id
shape Region:
    id: Int not null
    label: Text not null
    unique region_key on id
shape Site:
    id: Int not null
    region_id: Int not null
shape Addr:
    city: Text not null
shape Person:
    id: Int not null
    home: Addr not null
shape Place:
    id: Int not null
    home: Addr not null
source orders: Order is postgres.table("shop.orders")
source customers: Customer is postgres.table("shop.customers")
source regions: Region is postgres.table("shop.regions")
source sites: Site is postgres.table("shop.sites")
source people: Person is postgres.table("app.people")
source places: Place is postgres.table("app.places")
relationship order_customer: orders.customer_id == customers.id
relationship customer_region: customers.region_id == regions.id
relationship near_region:
    endpoint c: customers
    endpoint r: regions
    on c.region_id < r.id
relationship referral:
    endpoint referrer: customers
    endpoint referee: customers
    on referee.ref == referrer.id
relationship region_only_lt:
    endpoint r: regions
    endpoint o: orders
    on r.id < o.amount
relationship site_region:
    endpoint s: sites
    endpoint r: regions
relationship site_order:
    endpoint s: sites
    endpoint o: orders
    on s.nope == o.id
relationship home_id:
    endpoint p: people
    endpoint q: places
    on p.home == q.id
relationship same_home:
    endpoint p: people
    endpoint q: places
    on p.home == q.home
query per_customer:
    from orders
    group by: customer_id
    select:
        customer_id
        total = count()
query q_zero_candidates:
    from regions
    inner join regions as other
    select:
        x = regions.id
query q_unusable_only:
    from regions
    inner join orders as o
    select:
        x = regions.id
query q_self_no_roles:
    from customers
    inner join customers as peer
    select:
        x = customers.id
query q_derived_rel:
    from per_customer
    inner join customers as c
    select:
        x = c.name
query q_two_sources:
    from customers
    inner join customers as peer:
        from customers
        on peer.id == customers.id
    inner join regions as r
    select:
        x = customers.id
query q_two_sources_via:
    from orders
    inner join customers as c
    inner join customers as d
    select:
        x = orders.id
query q_unusable_listed:
    from sites
    inner join regions as r:
        from sites
        on r.id == sites.region_id
    inner join orders as o
    select:
        x = sites.id
query q_start_unread:
    from sites
    inner join orders as o: via order_customer
    select:
        x = sites.id
query q_start_twice:
    from customers
    inner join customers as peer:
        from customers
        on peer.id == customers.id
    inner join regions as r: via customer_region
    select:
        x = customers.id
query q_self_omitted:
    from customers
    inner join customers as peer: via referral
    select:
        x = customers.id
query q_end_unreached:
    from customers
    inner join sites as s: via customer_region
    select:
        x = customers.id
query q_self_unreached:
    from customers
    inner join regions as r: via referral
    select:
        x = customers.id
query q_via_unusable:
    from customers
    inner join regions as r: via near_region
    select:
        x = customers.id
query q_via_no_on:
    from sites
    inner join regions as r: via site_region: s -> r
    select:
        x = sites.id
query q_via_unknown:
    from customers
    inner join regions as r: via nowhere
    select:
        x = customers.id
query q_via_unknown_roles:
    from customers
    inner join regions as r: via nowhere: customers -> regions
    select:
        x = customers.id
query q_unknown_role:
    from customers
    inner join regions as r: via customer_region: customers -> nope
    select:
        x = customers.id
query q_unknown_roles:
    from customers
    inner join regions as r: via customer_region: x -> y
    select:
        x = customers.id
query q_one_role:
    from customers
    inner join regions as r: via customer_region: customers -> customers
    select:
        x = customers.id
query q_path_end:
    from customers
    inner join sites as s: via customer_region: customers -> regions
    select:
        x = customers.id
query q_path_start_omitted:
    from orders
    inner join regions as r:
        from orders
        via customer_region
    select:
        x = orders.id
query q_shape_inferred:
    from people
    inner join places as pl
    select:
        x = people.id
query q_shape_via:
    from people
    inner join places as pl: via same_home
    select:
        x = people.id
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
    single = join_script(_AGREEMENT_SOURCE, path="main.pietto")
    reported = []
    for definition in single.script.definitions:
        if isinstance(definition, QueryDef) and definition.name.startswith("q_"):
            for ordinal, clause in enumerate(definition.join_clauses, 1):
                if join_mode(clause) not in ("M1", "M2", "M4"):
                    continue
                result = single.resolve(definition.name, ordinal)
                if isinstance(result, tuple):
                    (item,) = result
                    assert item.code == _S2335
                    reported.append(
                        (
                            f"{prefix}{definition.name} ({item.message})",
                            item.location.line,
                            item.location.column,
                        )
                    )
    assert len(reported) == 23
    assert reported == causes


def test_the_probe_programs_report_the_project_cause_texts() -> None:
    """The cause texts the released project reports for these programs."""

    single = join_script(_AGREEMENT_SOURCE, path="main.pietto")
    assert [
        item.message
        for name in (
            "q_zero_candidates",
            "q_unusable_only",
            "q_self_no_roles",
            "q_derived_rel",
        )
        for item in _diagnostics(single.resolve(name, 1))
    ] == [
        "JOIN other: no relationship joins regions to regions; declare one, or "
        "write `from` and `on`",
        "JOIN o: no relationship from regions to orders can be used: "
        "region_only_lt (its `on` is not only field equalities that a JOIN can "
        "use)",
        "JOIN peer matches 2 relationship directions from customers: `via "
        "referral: referrer -> referee` and `via referral: referee -> referrer`; "
        "write one of them",
        "JOIN c: no relationship joins per_customer to customers; declare one, or "
        "write `from` and `on`",
    ]


def _diagnostics(result: object) -> tuple[Diagnostic, ...]:
    assert isinstance(result, tuple)
    return result
