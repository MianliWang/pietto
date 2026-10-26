from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from pietto._project import check as project_check
from pietto._project import project_grain
from pietto._project import project_ir_joins as joins
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_multifact as multifact
from pietto._project import project_relationship_uses as relationship_uses
from pietto._project import project_row_keys, project_value_fds
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectGrainDependencyFact,
    ProjectGrainDomainFactor,
    ProjectGroupedGrainFactorIdentity,
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
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice12-per-aggregate-fact-locality-chasm-detection-multi-fact-alignment-v1.md"
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
relationship customer_orders_raw(customer: CustomerRow, order: OrderRow):
    customer.id == order.customer_id
query missing_fact_join:
    from orders_by_customer
    let reasons = returns_by_customer_reason
    inner join reasons on orders_by_customer.customer_id == reasons.customer_id
    select:
        customer_id = orders_by_customer.customer_id
query joined_aggregate_text:
    from customers
    let raw_orders = orders
    inner join raw_orders on customer_orders_raw(customers, raw_orders)
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
    use_set = relationship_uses.build_project_relationship_uses(
        semantic, base_properties
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


def test_windows_selected_before_aggregates_keep_pre_window_stage_fields(
    tmp_path: Path,
) -> None:
    # The aggregate stage row is (region, total, c); the final row interleaves
    # r and rn, so each final ordinal differs from its stage field position.
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (tmp_path / "main.pietto").write_text(
        """shape Order:
    region: Text
    amount: Int
source orders: Order = postgres.table("orders")
query ranked:
    from orders
    group by:
        region
    select:
        r = rank() window(order by total desc)
        region
        total = max(amount)
        rn = row_number() window(order by region)
        c = count()
""",
        encoding="utf-8",
    )
    parsed = project_check.check_project_parse_only(tmp_path)
    assert parsed.ok, parsed.diagnostics
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.diagnostics == ()
    assert completed.verification.status is ProjectPhase62VerificationStatus.VERIFIED
    facts = completed.verification.root.facts
    assert tuple(
        (
            fact.aggregate_result.output_name,
            fact.selected_output_ordinal,
            fact.stage_scalar_output.field_position,
            fact.home_field.field_position,
        )
        for fact in facts
    ) == (("total", 2, 1, 2), ("c", 4, 2, 4))
    for fact in facts:
        assert fact.stage_scalar_output.evidence is fact.select_fact.field
        assert fact.home_field.evidence is fact.select_fact.field
        assert (
            fact.stage_scalar_output
            is fact.result_row_properties.fields[
                fact.stage_scalar_output.field_position
            ]
        )


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


def test_global_facts_keep_zero_factors_without_fabricated_grain(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    orders = _fact(built, "global_orders", "total")
    returns = _fact(built, "global_returns", "total")
    for fact in (orders, returns):
        assert fact.result_intrinsic_grain.state is ProjectGrainBasisState.GLOBAL
        assert fact.result_intrinsic_grain.active == ()


def test_non_concrete_regions_preserve_missing_evidence(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    missing = _subject(built, "missing_fact_join")
    assert missing.identifiable_facts
    assert (
        missing.structural
        is multifact.ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE
    )
    assert missing.region.ending_allocation is missing.region.starting_allocation


def test_common_grain_masks_are_arbitrary_width_and_keep_every_finest_candidate(
    built: multifact.ProjectMultiFactAnalysis,
) -> None:
    fact = _fact(built, "orders_by_customer_product", "total")
    original = fact.result_intrinsic_grain
    base = original.active[0]
    assert type(base) is ProjectGroupedGrainFactorIdentity
    scope = ProjectIRSnapshotScope()
    identities = tuple(
        ProjectJoinGrainFactorIdentity(
            base=base,
            introduction_use=ProjectIRUseRef(scope=scope, position=10_000 + position),
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
    (home,) = (item for item in built.home_localities if item.fact is fact)
    other = _fact(built, "orders_by_customer", "order_count")
    with pytest.raises(ValueError, match="exact fact result authority"):
        replace(home, home_field=other.home_field)
    with pytest.raises(ValueError, match="context facts index"):
        replace(built, facts_by_context={})


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
