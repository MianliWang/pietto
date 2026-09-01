from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, cast

import pytest

from pietto._project import check as project_check
from pietto._project import project_grain
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_relationship_conditions as conditions
from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project import project_relationship_paths as paths
from pietto._project import project_relationship_uses as uses
from pietto._project import project_relationships, project_row_keys, project_value_fds
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    build_empty_project_semantic_result,
)
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import (
    ProjectIRAllocationState,
    ProjectIRNonConcreteSingleRelationFragment,
    build_project_ir_single_relation_fragment,
)
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_pipeline import build_project_ir_pipeline
from pietto._project.project_ir_verification import (
    ProjectIRVerificationStatus,
    build_project_ir_analysis_bundle,
    verify_project_ir_stage,
)
from pietto.ast_nodes import (
    AuthoredJoinKind,
    JoinClause,
    JoinTraversalStep,
    QueryDef,
    Script,
    TableDef,
)
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice10-authored-join-traversal-syntax-semantic-uses-v1.md"
)


def _source() -> str:
    return """shape ARow:
    id: Int not null
    b_id: Int not null
    c_id: Int not null
shape BRow:
    id: Int not null
    c_id: Int not null
    unique b_key on id
shape CRow:
    id: Int not null
    unique c_key on id
shape DRow:
    id: Int not null
source a_rows: ARow is postgres.table("a")
source b_rows: BRow is postgres.table("b")
source c_rows: CRow is postgres.table("c")
source d_rows: DRow is postgres.table("d")
relationship ab:
    endpoint a: a_rows
    endpoint b: b_rows
    on a.b_id == b.id
relationship bc:
    endpoint b: b_rows
    endpoint c: c_rows
    on b.c_id == c.id
relationship ac_one:
    endpoint a: a_rows
    endpoint c: c_rows
    on a.c_id == c.id
relationship ac_two:
    endpoint a: a_rows
    endpoint c: c_rows
    on a.c_id == c.id
query direct_unique:
    from a_rows
    inner join b_rows as b:
        from a_rows
    select:
        id
query direct_absent:
    from a_rows
    inner join d_rows as d:
        from a_rows
    select:
        id
query direct_ambiguous:
    from a_rows
    inner join c_rows as c:
        from a_rows
    select:
        id
query explicit_one:
    from a_rows
    inner join b_rows as b:
        from a_rows
        via ab: a -> b
    select:
        id
query explicit_multi:
    from a_rows
    left join c_rows as c:
        from a_rows
        via ab: a -> b
        via bc: b -> c
    select:
        id
query branching:
    from a_rows
    inner join b_rows as b:
        from a_rows
        via ab: a -> b
    left join c_rows as c:
        from a_rows
        via ac_one: a -> c
    select:
        id
query repeated_path:
    from a_rows
    inner join b_rows as first_b:
        from a_rows
        via ab: a -> b
    inner join b_rows as second_b:
        from a_rows
        via ab: a -> b
    select:
        id
query wrong_role:
    from a_rows
    inner join b_rows as b:
        from a_rows
        via ab: missing -> b
    select:
        id
query noncontiguous:
    from a_rows
    inner join b_rows as b:
        from a_rows
        via ab: a -> b
        via ab: a -> b
    select:
        id
query start_mismatch:
    from a_rows
    inner join c_rows as c:
        from a_rows
        via bc: b -> c
    select:
        id
query end_mismatch:
    from a_rows
    inner join c_rows as c:
        from a_rows
        via ab: a -> b
    select:
        id
query duplicate_binding:
    from a_rows
    inner join b_rows as a_rows:
        from a_rows
        via ab: a -> b
    select:
        id
query forward_binding:
    from a_rows
    inner join b_rows as b:
        from c
        via ab: a -> b
    inner join c_rows as c:
        from a_rows
        via ac_one: a -> c
    select:
        id
query poisoned_binding:
    from a_rows
    inner join d_rows as d:
        from a_rows
    inner join c_rows as c:
        from d
        via ac_one: a -> c
    select:
        id
query joined_target:
    from a_rows
    inner join explicit_one as joined:
        from a_rows
    select:
        id
query downstream:
    from explicit_one
    select:
        id
query unrelated:
    from d_rows
    select:
        id
"""


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: Any
    plan: Any
    pipeline: Any
    use_set: uses.ProjectRelationshipUseSet


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    root = tmp_path_factory.mktemp("p62s10")
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
    allocation = ProjectIRAllocationState(scope=ProjectIRSnapshotScope())
    plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=allocation,
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = project_grain.build_project_grain_origins(value_fds, evaluation)
    analysis = build_project_ir_analysis_bundle(verify_project_ir_stage(evaluation))
    properties = relational.build_project_ir_relational_property_stage(
        origins, analysis
    )
    relationship_set = project_relationships.build_project_relationships(semantic)
    condition_set = conditions.build_project_relationship_conditions(relationship_set)
    guarantee_set = guarantees.build_project_relationship_match_guarantees(
        condition_set, properties
    )
    index = paths.build_project_relationship_join_shape_index(guarantee_set)
    use_set = uses.build_project_relationship_uses(relationship_set, index)
    pipeline = build_project_ir_pipeline(
        semantic_result=semantic,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    return _Built(semantic=semantic, plan=plan, pipeline=pipeline, use_set=use_set)


def _ledger(built: _Built, name: str) -> uses.ProjectRelationJoinUseLedger:
    matches = tuple(
        ledger
        for ledger in built.use_set.ledgers
        if ledger.owner.definition.name == name
    )
    assert len(matches) == 1
    return matches[0]


def _fact(built: _Built, name: str) -> Any:
    facts = built.semantic.module_semantic_facts
    assert facts is not None
    matches = tuple(
        fact
        for environment in facts.environments
        for fact in environment.relation_facts
        if fact.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _parse(source: str, *, path: str = "slice10.pietto") -> Script:
    result = parse_source(source, path=path)
    assert result.ast is not None, result.diagnostics
    assert result.diagnostics == ()
    return result.ast


def test_join_grammar_ast_occurrences_spans_order_and_compatibility() -> None:
    script = _parse(
        "query result:\n"
        "    from orders\n\n"
        "    inner join customers as customer:\n"
        "        from orders\n\n"
        "    left join regions as region:\n"
        "        from customer\n"
        "        via customer_region: customer -> region\n\n"
        "    select:\n"
        "        id\n",
        path="ordered-joins.pietto",
    )
    relation = cast(QueryDef, script.definitions[0])
    assert tuple(item.kind for item in relation.join_clauses) == (
        AuthoredJoinKind.INNER,
        AuthoredJoinKind.LEFT,
    )
    assert tuple(
        (
            item.target_relation_name,
            item.target_binding_name,
            item.source_binding_name,
        )
        for item in relation.join_clauses
    ) == (
        ("customers", "customer", "orders"),
        ("regions", "region", "customer"),
    )
    first, second = relation.join_clauses
    assert (
        first is not second
        and first.span.path == second.span.path == "ordered-joins.pietto"
    )
    assert (first.span.line, first.span.column, first.span.end_line) == (4, 5, 5)
    assert (second.span.line, second.span.column, second.span.end_line) == (7, 5, 9)
    assert second.traversal_steps == (
        JoinTraversalStep(
            span=second.traversal_steps[0].span,
            relationship_name="customer_region",
            source_endpoint_role="customer",
            target_endpoint_role="region",
        ),
    )
    assert second.traversal_steps[0].span.line == 9
    join_free = cast(
        TableDef,
        _parse("table plain:\n    from orders\n    select:\n        id\n").definitions[
            0
        ],
    )
    assert join_free.join_clauses == ()
    assert tuple(field.name for field in fields(JoinClause)) == (
        "span",
        "kind",
        "target_relation_name",
        "target_binding_name",
        "source_binding_name",
        "traversal_steps",
    )
    for identifier in ("inner", "left", "join", "via"):
        assert _parse(f"type {identifier} = Int\n").definitions[0].name == identifier


@pytest.mark.parametrize("kind", ("right", "full", "semi", "anti", "mark", "single"))
def test_unsupported_join_kinds_and_join_local_on_fail_closed(kind: str) -> None:
    source = (
        "query result:\n"
        "    from orders\n"
        f"    {kind} join customers as customer:\n"
        "        from orders\n"
        "    select:\n"
        "        id\n"
    )
    result = parse_source(source, path=f"{kind}.pietto")
    assert result.ast is None and result.diagnostics
    on_result = parse_source(
        source.replace(f"{kind} join", "inner join").replace(
            "        from orders\n", "        from orders\n        on id == id\n"
        ),
        path="join-on.pietto",
    )
    assert on_result.ast is None and on_result.diagnostics


def test_join_bearing_semantics_and_project_ir_are_deferred_without_global_failure(
    built: _Built,
) -> None:
    joined = _fact(built, "explicit_one")
    downstream = _fact(built, "downstream")
    unrelated = _fact(built, "unrelated")
    assert (joined.state.status, joined.state.reason, joined.state.schema) == (
        ProjectRelationRowSchemaStatus.DEFERRED,
        ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED,
        None,
    )
    assert joined.input_state is None
    assert joined.base_result_state is joined.state
    assert all(fact.field is None for fact in joined.select_facts)
    assert all(fact.project_fact is None for fact in joined.window_outputs)
    assert downstream.state.reason is ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED
    assert unrelated.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    with pytest.raises(ValueError, match="cannot publish a concrete state"):
        replace(
            joined,
            state=unrelated.state,
            base_result_state=unrelated.state,
        )

    for plan in (built.plan, built.pipeline.project_plan):
        fragments = tuple(
            fragment
            for fragment in plan.non_concrete_fragments
            if fragment.semantic_facts.owner.definition.name == "explicit_one"
        )
        assert len(fragments) == 1
        fragment = fragments[0]
        assert type(fragment) is ProjectIRNonConcreteSingleRelationFragment
        assert fragment.subject.state.value == "deferred"
        assert fragment.ending_allocation is fragment.starting_allocation
        assert fragment.structural_stage.nodes == ()
        assert fragment.structural_stage.outputs == ()
        assert fragment.structural_stage.input_slots == ()
        assert fragment.structural_stage.uses == ()
        assert fragment.logical_stage.operators == ()
        assert fragment.property_stage.provided == ()
        assert fragment.property_stage.required == ()
        assert fragment.property_stage.effects == ()
        assert fragment.root is fragment.root_relation_output is None
        assert any(
            concrete.semantic_facts.owner.definition.name == "unrelated"
            for concrete in plan.concrete_fragments
        )
    assert built.pipeline.verification.status is ProjectIRVerificationStatus.VERIFIED


def test_concrete_join_uses_bind_direct_explicit_branching_and_repeated_paths(
    built: _Built,
) -> None:
    direct = _ledger(built, "direct_unique").uses[0]
    one = _ledger(built, "explicit_one").uses[0]
    multi = _ledger(built, "explicit_multi").uses[0]
    assert type(direct) is uses.ProjectConcreteJoinUse
    assert type(one) is uses.ProjectConcreteJoinUse
    assert type(multi) is uses.ProjectConcreteJoinUse
    assert direct.step_uses == () and len(direct.path.steps) == 1
    assert len(one.step_uses) == len(one.path.steps) == 1
    assert len(multi.step_uses) == len(multi.path.steps) == 2
    assert multi.kind is AuthoredJoinKind.LEFT
    assert multi.left_source_preserved
    assert multi.left_potential_null_target is multi.target_binding
    assert multi.inner_survival_readiness is None
    assert multi.left_null_readiness is multi.analysis.left_nulling
    assert one.kind is AuthoredJoinKind.INNER
    assert one.inner_survival_readiness is one.analysis.inner_survival
    assert one.left_null_readiness is None
    assert one.left_potential_null_target is None
    assert _fact(built, "explicit_one").state.reason is (
        ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED
    )

    branching = _ledger(built, "branching")
    assert all(type(item) is uses.ProjectConcreteJoinUse for item in branching.uses)
    assert branching.uses[0].source_binding is branching.bindings[0]
    assert branching.uses[1].source_binding is branching.bindings[0]
    repeated = _ledger(built, "repeated_path").uses
    assert all(type(item) is uses.ProjectConcreteJoinUse for item in repeated)
    repeated_first = cast(uses.ProjectConcreteJoinUse, repeated[0])
    repeated_second = cast(uses.ProjectConcreteJoinUse, repeated[1])
    assert repeated_first.identity != repeated_second.identity
    assert (
        repeated_first.path.steps[0].guarantee
        is repeated_second.path.steps[0].guarantee
    )
    with pytest.raises(ValueError, match="Concrete JOIN path"):
        replace(one, path=multi.path, analysis=multi.analysis)
    repeated_ledger = _ledger(built, "repeated_path")
    with pytest.raises(ValueError, match="exact binding and path roots"):
        replace(
            repeated_ledger,
            uses=(
                replace(
                    repeated_first,
                    target_binding=repeated_ledger.bindings[2],
                ),
                repeated_second,
            ),
        )
    with pytest.raises(ValueError, match="output must match"):
        replace(one.source_binding, output=one.target_binding.output)
    with pytest.raises(ValueError, match="endpoint roles"):
        replace(
            one.step_uses[0],
            directions=(multi.step_uses[-1].directions[0],),
        )


def test_direct_absent_ambiguous_binding_and_failed_binding_states_are_complete(
    built: _Built,
) -> None:
    absent = _ledger(built, "direct_absent").uses[0]
    ambiguous = _ledger(built, "direct_ambiguous").uses[0]
    assert type(absent) is uses.ProjectNonConcreteJoinUse
    assert absent.state is uses.ProjectJoinUseState.UNKNOWN
    assert absent.direct_result is not None
    assert (
        absent.direct_result.status
        is paths.ProjectDirectRelationshipCandidateStatus.ABSENT
    )
    concrete = cast(uses.ProjectConcreteJoinUse, _ledger(built, "explicit_one").uses[0])
    with pytest.raises(ValueError, match="direct JOIN evidence"):
        replace(absent, path=concrete.path)
    assert type(ambiguous) is uses.ProjectNonConcreteJoinUse
    assert ambiguous.state is uses.ProjectJoinUseState.AMBIGUOUS
    assert ambiguous.direct_result is not None
    assert len(ambiguous.direct_result.candidates) == 2

    duplicate = _ledger(built, "duplicate_binding")
    assert tuple(binding.state for binding in duplicate.bindings) == (
        uses.ProjectJoinUseState.AMBIGUOUS,
        uses.ProjectJoinUseState.AMBIGUOUS,
    )
    assert cast(uses.ProjectNonConcreteJoinUse, duplicate.uses[0]).state is (
        uses.ProjectJoinUseState.AMBIGUOUS
    )
    forward = cast(
        uses.ProjectNonConcreteJoinUse, _ledger(built, "forward_binding").uses[0]
    )
    assert forward.issues[0].kind is uses.ProjectJoinUseIssueKind.FORWARD_SOURCE_BINDING
    poisoned = _ledger(built, "poisoned_binding").uses
    assert cast(uses.ProjectNonConcreteJoinUse, poisoned[0]).state is (
        uses.ProjectJoinUseState.UNKNOWN
    )
    dependent = cast(uses.ProjectNonConcreteJoinUse, poisoned[1])
    assert dependent.state is uses.ProjectJoinUseState.BLOCKED
    assert (
        dependent.issues[0].kind is uses.ProjectJoinUseIssueKind.BLOCKED_SOURCE_BINDING
    )
    unavailable = cast(
        uses.ProjectNonConcreteJoinUse, _ledger(built, "joined_target").uses[0]
    )
    assert unavailable.state is uses.ProjectJoinUseState.BLOCKED
    assert (
        unavailable.issues[0].kind
        is uses.ProjectJoinUseIssueKind.BLOCKED_TARGET_RELATION
    )


def test_explicit_role_continuity_start_and_end_failures_never_choose_paths(
    built: _Built,
) -> None:
    expected = {
        "wrong_role": uses.ProjectJoinUseIssueKind.UNKNOWN_ENDPOINT_DIRECTION,
        "noncontiguous": uses.ProjectJoinUseIssueKind.NON_CONTIGUOUS_PATH,
        "start_mismatch": uses.ProjectJoinUseIssueKind.PATH_START_MISMATCH,
        "end_mismatch": uses.ProjectJoinUseIssueKind.PATH_END_MISMATCH,
    }
    for name, issue_kind in expected.items():
        use = cast(uses.ProjectNonConcreteJoinUse, _ledger(built, name).uses[0])
        assert use.state in {
            uses.ProjectJoinUseState.UNKNOWN,
            uses.ProjectJoinUseState.BLOCKED,
        }
        assert tuple(issue.kind for issue in use.issues) == (issue_kind,)
        assert not hasattr(built.use_set.index, "find_path")


def test_legacy_ir_and_joined_scalar_namespace_fail_closed() -> None:
    prefix = (
        "shape Order:\n"
        "    id: Int not null\n"
        "shape Customer:\n"
        "    id: Int not null\n"
        'source orders: Order is postgres.table("orders")\n'
        'source customers: Customer is postgres.table("customers")\n'
    )
    source = (
        prefix + "query joined:\n"
        "    from orders\n"
        "    inner join customers as customer:\n"
        "        from orders\n"
        "    select:\n"
        "        id\n"
    )
    script = _parse(source)
    semantic = analyze(script)
    assert semantic.diagnostics == ()
    result = build_ir(script, semantic.model)
    assert result.ir is None
    assert tuple((item.code, item.message) for item in result.diagnostics) == (
        (
            "PIE-I1000",
            "Missing semantic fact required for IR lowering: binary JOIN lowering for an authored relationship traversal",
        ),
    )
    scalar = analyze(_parse(source.replace("        id\n", "        customer.id\n", 1)))
    assert any(item.code == "PIE-S2102" for item in scalar.diagnostics)


def test_project_ir_constructor_rejects_a_forged_join_marker(
    tmp_path: Path,
) -> None:
    root = tmp_path / "forgery"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(
        "shape Row:\n"
        "    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query plain:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n",
        encoding="utf-8",
    )
    parsed = project_check.check_project_parse_only(root)
    semantic = build_empty_project_semantic_result(parsed)
    facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert facts is not None and attribution is not None
    fact = next(
        item
        for environment in facts.environments
        for item in environment.relation_facts
        if item.owner.identity.declared_name == "plain"
    )
    clause = cast(
        QueryDef,
        _parse(
            "query marked:\n"
            "    from rows\n"
            "    inner join rows as other:\n"
            "        from rows\n"
            "    select:\n"
            "        id\n"
        ).definitions[0],
    ).join_clauses[0]
    definition = cast(QueryDef, fact.owner.definition)
    object.__setattr__(definition, "join_clauses", (clause,))
    with pytest.raises(ValueError, match="cannot construct a concrete"):
        build_project_ir_single_relation_fragment(
            semantic=fact,
            attribution=attribution,
            allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
        )


def test_private_closed_vocabularies_and_slice11_boundaries() -> None:
    assert uses.__all__ == ()
    assert tuple(uses.ProjectJoinUseState) == (
        uses.ProjectJoinUseState.CONCRETE,
        uses.ProjectJoinUseState.UNKNOWN,
        uses.ProjectJoinUseState.BLOCKED,
        uses.ProjectJoinUseState.AMBIGUOUS,
    )
    source = (
        (REPO_ROOT / "src/pietto/_project/project_relationship_uses.py")
        .read_text(encoding="utf-8")
        .lower()
    )
    for forbidden in (
        "bfs",
        "dfs",
        "shortest_path",
        "projectirjoin",
        "optional grain",
        "sql join",
        "chasm",
    ):
        assert forbidden not in source
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "dc74cee6a0f6a67e396f12b4583a0d88d79ad130",
        "c32444755f191a45f68c7d9207979976ffc275dd",
        "33505927423",
        "A3/M26/D0",
        "AUTHORED_JOIN_DEFERRED",
        "concrete JOIN semantic use != concrete combined relation-row schema",
        "Phase 62 Slice 11 = NEXT / NOT IMPLEMENTED",
        "Add Phase 62 authored relationship join uses",
        "JOIN_USE_CARRIERS_DO_NOT_CLOSE_EXACT_BINDING_PATH_AND_STEP_EVIDENCE",
        "repair batch 1/1",
    ):
        assert evidence in normalized
