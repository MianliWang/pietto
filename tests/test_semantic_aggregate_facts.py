from __future__ import annotations

from dataclasses import replace
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
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectGrainDependencyFact,
    ProjectGrainDomainFactor,
    ProjectJoinGrainFactorIdentity,
)
from pietto._project.project_ir import ProjectIRSnapshotScope, ProjectIRUseRef
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRProvidedIntrinsicGrain,
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


def test_slice12_owner_is_private_and_fact_catalog_is_occurrence_complete(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    assert multifact.__all__ == ()
    assert len(built.facts) == 8
    assert tuple(
        (
            fact.context.semantic_facts.owner.definition.name,
            fact.aggregate_result_position,
        )
        for fact in built.facts
    ) == (
        ("orders_by_customer", 0),
        ("orders_by_customer", 1),
        ("orders_by_customer_copy", 0),
        ("orders_by_customer_product", 0),
        ("returns_by_customer", 0),
        ("returns_by_customer_reason", 0),
        ("global_orders", 0),
        ("global_returns", 0),
    )
    assert all(
        fact.identity.aggregate_node == fact.context.operator.node.ref
        for fact in built.facts
    )
    assert not any(
        fact.context.semantic_facts.owner.definition.name
        in {"windowed", "joined_aggregate_text"}
        for fact in built.facts
    )
    assert len(built.home_localities) == len(built.facts)


def test_fact_retains_exact_stage_home_value_and_distinct_same_name_authority(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    orders = _fact(built, "orders_by_customer", "total")
    returns = _fact(built, "returns_by_customer", "total")
    assert orders.aggregate_result is orders.select_fact.aggregate_result_fact
    assert orders.stage_scalar_output.output is orders.context.result_row_output
    assert orders.home_field.output is orders.context.fragment.root_relation_output
    assert orders.stage_scalar_output.output is not orders.home_field.output
    assert orders.final_scalar_output.field.evidence is orders.home_field.evidence
    assert orders.home_value_class.members == (orders.home_field,)
    assert orders.aggregate_result.output_name == returns.aggregate_result.output_name
    assert orders.identity != returns.identity
    assert orders.aggregate_result is not returns.aggregate_result


def test_same_context_facts_remain_distinct_and_exactly_aligned(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    total = _fact(built, "orders_by_customer", "total")
    count = _fact(built, "orders_by_customer", "order_count")
    matches = tuple(
        item
        for item in built.home_alignments
        if {id(item.left.fact), id(item.right.fact)} == {id(total), id(count)}
    )
    assert len(matches) == 1
    assert (
        matches[0].structural
        is multifact.ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED
    )
    assert matches[0].multiplicity_risks == ()
    assert matches[0].requirements == ()


def test_join_localities_preserve_use_field_path_and_contextual_factor_identity(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    total = _fact(built, "orders_by_customer", "total")
    reused = _localities(_region(built, "reused_join"), total)
    assert len(reused) == 2
    assert reused[0].introduction_use is not reused[1].introduction_use
    assert reused[0].contextual_grain.factors != reused[1].contextual_grain.factors
    assert all(
        locality.relationship_entry_path is locality.introduction_join.path_step
        and locality.final_field.introduction_use is locality.introduction_use
        for locality in reused
    )
    assert all(
        type(factor) is ProjectJoinGrainFactorIdentity
        and factor.base == total.result_intrinsic_grain.active[0]
        and factor.introduction_use == locality.introduction_use.ref
        for locality in reused
        for factor in locality.contextual_grain.factors
    )
    queried = multifact.analyze_project_fact_locality_pair(built, reused[1], reused[0])
    assert (
        queried.structural
        is multifact.ProjectMultiFactStructuralAlignment.STRUCTURALLY_ALIGNABLE
    )


def test_intermediate_path_and_self_role_fact_uses_remain_distinct(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    orders = _fact(built, "orders_by_customer", "total")
    returns = _fact(built, "returns_by_customer", "total")
    multihop = _region(built, "multihop_join")
    order_locality = _localities(multihop, orders)[0]
    return_locality = _localities(multihop, returns)[0]
    assert order_locality.introduction_join.identity.path_step_position == 0
    assert return_locality.introduction_join.identity.path_step_position == 1
    assert order_locality.relationship_entry_path is multihop.region.joins[0].path_step
    assert return_locality.relationship_entry_path is multihop.region.joins[1].path_step

    self_region = _region(built, "self_fact_join")
    same_fact = _localities(self_region, orders)
    assert len(same_fact) == 2
    assert same_fact[0].side is multifact.ProjectFactJoinInputSide.LEFT
    assert same_fact[0].relationship_entry_path is None
    assert same_fact[1].side is multifact.ProjectFactJoinInputSide.RIGHT
    assert same_fact[0].introduction_use is not same_fact[1].introduction_use
    assert same_fact[1].final_field.nulling_joins == (
        same_fact[1].introduction_join.node.ref,
    )


def test_exact_mutual_dependency_and_strict_grain_order_classifications(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    orders = _fact(built, "orders_by_customer", "total")
    copy = _fact(built, "orders_by_customer_copy", "total")
    aligned = _alignment(_region(built, "aligned_join"), orders, copy)
    assert (
        aligned.structural
        is multifact.ProjectMultiFactStructuralAlignment.STRUCTURALLY_ALIGNABLE
    )
    assert aligned.grain_comparison is not None
    assert (
        aligned.grain_comparison.status
        is relational.ProjectIRGrainComparisonStatus.EQUAL
    )
    assert (
        aligned.left.contextual_grain.factors != aligned.right.contextual_grain.factors
    )

    fine = _fact(built, "orders_by_customer_product", "total")
    comparable_region = _region(built, "comparable_join")
    comparable = _alignment(comparable_region, orders, fine)
    assert (
        comparable.structural
        is multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
    )
    assert comparable.finer is not None and comparable.finer.fact is fine
    assert comparable.common_grain.status is multifact.ProjectCommonGrainStatus.UNIQUE
    assert comparable.requirements == (
        multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,
    )
    assert comparable_region.chasms == ()


def test_independent_fact_branches_form_exact_chasm_and_multiplication_risk(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    orders = _fact(built, "orders_by_customer_product", "total")
    returns = _fact(built, "returns_by_customer_reason", "return_count")
    region = _region(built, "chasm_join")
    assert len(region.localities) == 2
    assert len(region.chasms) == 1
    chasm = region.chasms[0]
    assert chasm.localities == region.localities
    assert len(chasm.introduction_joins) == 2
    assert all(
        item.status is relational.ProjectIRGrainComparisonStatus.INCOMPARABLE
        for item in chasm.pairwise_comparisons
    )
    alignment = _alignment(region, orders, returns)
    assert (
        alignment.structural
        is multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
    )
    assert alignment.common_grain.status is multifact.ProjectCommonGrainStatus.UNIQUE
    assert alignment.multiplicity_risks == (
        multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,
        multifact.ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION,
    )
    assert alignment.requirements == (
        multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,
    )
    assert all(locality.multiplicity_exposures for locality in region.localities)
    assert {orders.aggregate_result.function, returns.aggregate_result.function} == {
        "sum",
        "count",
    }


def test_incomparable_facts_without_actual_common_candidate_are_incompatible(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    orders = _fact(built, "orders_by_customer_product", "total")
    returns = _fact(built, "returns_by_customer_reason", "return_count")
    region = _region(built, "incompatible_join")
    alignment = _alignment(region, orders, returns)
    assert alignment.grain_comparison is not None
    assert alignment.grain_comparison.status is (
        relational.ProjectIRGrainComparisonStatus.INCOMPARABLE
    )
    assert alignment.common_grain.status is multifact.ProjectCommonGrainStatus.NONE
    assert (
        alignment.structural
        is multifact.ProjectMultiFactStructuralAlignment.INCOMPATIBLE
    )
    assert alignment.multiplicity_risks == (
        multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,
    )
    assert region.chasms == ()


def test_global_facts_keep_zero_factors_without_fabricated_grain(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    orders = _fact(built, "global_orders", "total")
    returns = _fact(built, "global_returns", "total")
    assert orders.result_intrinsic_grain.state is ProjectGrainBasisState.GLOBAL
    assert orders.result_intrinsic_grain.active == ()
    region = _region(built, "global_join")
    assert len(region.localities) == 2
    assert all(
        locality.contextual_grain.state is ProjectGrainBasisState.GLOBAL
        and locality.contextual_grain.factors == ()
        for locality in region.localities
    )
    assert _alignment(region, orders, returns).structural is (
        multifact.ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED
    )


def test_non_concrete_regions_preserve_ambiguous_path_or_missing_evidence(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    ambiguous = _subject(built, "ambiguous_fact_join")
    assert ambiguous.identifiable_facts
    assert (
        ambiguous.structural
        is multifact.ProjectMultiFactStructuralAlignment.AMBIGUOUS_PATH
    )
    assert ambiguous.region.ending_allocation is ambiguous.region.starting_allocation
    missing = _subject(built, "missing_fact_join")
    assert missing.identifiable_facts
    assert (
        missing.structural
        is multifact.ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE
    )
    assert missing.region.ending_allocation is missing.region.starting_allocation


def test_unrelated_locality_query_is_incompatible_without_global_pair_table(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    left = _region(built, "aligned_join").localities[0]
    right = _region(built, "chasm_join").localities[0]
    result = multifact.analyze_project_fact_locality_pair(built, left, right)
    assert (
        result.structural is multifact.ProjectMultiFactStructuralAlignment.INCOMPATIBLE
    )
    assert result.grain_comparison is None
    assert result.common_grain.status is multifact.ProjectCommonGrainStatus.NONE
    assert result.multiplicity_risks == ()


def test_common_grain_masks_are_arbitrary_width_and_keep_every_finest_candidate(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    locality = _region(built, "chasm_join").localities[0]
    retained = locality.contextual_grain.factors[0]
    assert type(retained) is ProjectJoinGrainFactorIdentity
    identities = tuple(
        ProjectJoinGrainFactorIdentity(
            base=retained.base,
            introduction_use=ProjectIRUseRef(
                scope=retained.introduction_use.scope,
                position=10_000 + position,
            ),
            nulling_joins=(),
        )
        for position in range(72)
    )
    dependencies = (
        ProjectGrainDependencyFact(
            determinants=(identities[70],),
            dependents=(identities[0], identities[1]),
        ),
        ProjectGrainDependencyFact(
            determinants=(identities[71],),
            dependents=(identities[0], identities[1]),
        ),
    )
    original = locality.final_region_properties.relational.grain
    authority = ProjectIRProvidedIntrinsicGrain(
        output=original.output,
        state=ProjectGrainBasisState.FACTORIZED,
        factors=tuple(ProjectGrainDomainFactor(identity=item) for item in identities),
        active=identities,
        dependencies=dependencies,
        origin_set=original.origin_set,
        witness=original,
    )
    index = multifact._grain_index(authority)
    left = multifact.ProjectFactContextualGrain(
        authority=authority,
        state=ProjectGrainBasisState.FACTORIZED,
        factors=(identities[70],),
        evidence=identities[70],
    )
    right = multifact.ProjectFactContextualGrain(
        authority=authority,
        state=ProjectGrainBasisState.FACTORIZED,
        factors=(identities[71],),
        evidence=identities[71],
    )
    candidates: list[multifact.ProjectActualGrainCandidate] = []
    for identity in identities[:2]:
        multifact._add_actual_candidate(
            candidates,
            index=index,
            kind=multifact.ProjectActualGrainAuthorityKind.JOIN_SOURCE_SLICE,
            evidence=(identity,),
            factors=(identity,),
            allow_empty=False,
        )
    result = multifact._common_grain(
        index=index,
        left=left,
        right=right,
        actual_candidates=tuple(candidates),
    )
    assert result.status is multifact.ProjectCommonGrainStatus.AMBIGUOUS
    assert tuple(item.candidate.factors.factors for item in result.candidates) == (
        (identities[0],),
        (identities[1],),
    )
    assert result.candidates[-1].candidate.factors.mask > 1
    reversed_result = multifact._common_grain(
        index=index,
        left=left,
        right=right,
        actual_candidates=tuple(reversed(candidates)),
    )
    assert tuple(
        item.candidate.factors.factors for item in reversed_result.candidates
    ) == ((identities[1],), (identities[0],))


def test_carriers_reject_detached_fact_and_locality_authority(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    fact = _fact(built, "orders_by_customer", "total")
    with pytest.raises(ValueError, match="selected output"):
        replace(fact, selected_output_ordinal=fact.selected_output_ordinal + 1)
    reused = _localities(_region(built, "reused_join"), fact)
    with pytest.raises(ValueError, match="side"):
        replace(reused[0], introduction_use=reused[1].introduction_use)
    with pytest.raises(ValueError, match="context facts index"):
        replace(built, facts_by_context={})
    region = _region(built, "chasm_join")
    assert region.fact_buckets[region.chasms[0].common_grain] == region.localities
    with pytest.raises(ValueError, match="i < j"):
        replace(region, alignments=())


def test_contract_records_boundaries_and_exact_pass_title() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "aggregate result occurrence != aggregate relation declaration",
        "fact occurrence != fact locality",
        "AUTHORED_JOIN_DEFERRED",
        "AGGREGATE_ALGEBRA_REQUIRED",
        "no reaggregation",
        "MULTIFACT_ANALYSIS_RESCANS_RETAINED_AUTHORITY_INSTEAD_OF_REUSING_TYPED_INDEXES",
        "Slice 12 repair batches: 1/1",
        "Slice 13 = NEXT / NOT IMPLEMENTED",
        "A3/M5/D0",
        "PASS — PHASE62_SLICE12_PER_AGGREGATE_FACT_LOCALITY_CHASM_DETECTION_MULTI_FACT_ALIGNMENT_END_TO_END",
    ):
        assert evidence in document
