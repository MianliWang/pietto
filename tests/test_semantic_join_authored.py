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
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
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
    ComparisonExpr,
    DottedNameExpr,
    JoinClause,
    JoinTraversalStep,
    NameExpr,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import (
    CheckMode,
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
    analyze,
)
from pietto.semantic.analyzer import analyze_project_namespace
from pietto.semantic.model import (
    JoinEqualityInfo,
    JoinFieldRef,
    JoinInfo,
    JoinInputInfo,
    RelationJoinsInfo,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic import joins
from _pietto_semantic_joins import (
    JOIN_PREFIX,
    located,
    resolve_by_declaration,
    run_joins,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


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
    assert {
        "span",
        "kind",
        "target_relation_name",
        "target_binding_name",
        "source_binding_name",
        "traversal_steps",
    } <= {field.name for field in fields(JoinClause)}
    assert join_free.join_clauses == ()
    for identifier in ("inner", "left", "join", "via"):
        assert _parse(f"type {identifier} = Int\n").definitions[0].name == identifier


@pytest.mark.parametrize("kind", ("mark", "single"))
def test_unsupported_join_kinds_fail_closed_and_join_local_on_is_admitted(
    kind: str,
) -> None:
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
        JOIN_PREFIX
        + source.replace(f"{kind} join", "inner join")
        .replace(
            "        from orders\n",
            "        from orders\n        on orders.id == customer.id\n",
        )
        .replace("        id\n", "        orders.id\n"),
        path="join-on.pietto",
    )
    assert on_result.ast is not None and not on_result.diagnostics
    assert analyze(on_result.ast).diagnostics == ()


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


def test_legacy_ir_join_namespace_fails_closed() -> None:
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
    semantic = analyze_project_namespace(script)
    assert semantic.diagnostics == ()
    result = build_ir(script, semantic.model)
    assert result.ir is None
    assert tuple((item.code, item.message) for item in result.diagnostics) == (
        (
            "PIE-I1000",
            "Missing semantic fact required for IR lowering: resolved JOIN facts",
        ),
    )


_COMPLETES = "only when an EXPLICIT_MODULES project (schema version 2) completes"


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "query q:\n    from orders\n    right join customers as customer:\n"
            "        from orders\n        on orders.id == customer.id\n"
            "    select:\n        x = orders.id\n",
            [],
        ),
        (
            "query q:\n    from orders\n    cross join customers as customer:\n"
            "        from orders\n    select:\n        x = orders.id\n",
            [],
        ),
        (
            "query both:\n    union all:\n        from orders\n        from orders\n"
            "query r:\n    from both\n    select:\n        id\n",
            [
                (f"Set operations are available {_COMPLETES} them.", 9, 5),
                (f"Set-operation inputs are available {_COMPLETES} them: both", 13, 5),
            ],
        ),
    ),
)
def test_single_file_joins_are_admitted_and_set_refusals_remain(
    body: str,
    expected: list[tuple[str, int, int]],
) -> None:
    semantic = analyze(
        _parse(
            "shape Order:\n"
            "    id: Int not null\n"
            "shape Customer:\n"
            "    id: Int not null\n"
            'source orders: Order is postgres.table("orders")\n'
            'source customers: Customer is postgres.table("customers")\n'
            "\n" + body
        )
    )
    assert [
        (item.message, item.location.line, item.location.column)
        for item in semantic.diagnostics
        if item.code == "PIE-S2334"
    ] == expected


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize(
    "tail",
    (
        "    select:\n        n = customer.name\n",
        '    where customer.name == "x"\n    select:\n        orders.id\n',
        "    group by:\n        customer.name\n    select:\n        n = count()\n",
        "    let:\n        nm = customer.name\n    select:\n        n = nm\n",
        "    select:\n        orders.id\n    order by:\n        customer.name\n",
        "    select:\n        name\n",
    ),
)
def test_single_file_join_binding_fields_resolve_in_each_clause(
    mode: CheckMode, tail: str
) -> None:
    semantic = analyze(
        _parse(
            JOIN_PREFIX + "query q:\n    from orders\n"
            "    inner join customers as customer\n" + tail
        ),
        mode_override=mode,
    )
    assert semantic.diagnostics == ()
    query = cast(QueryDef, semantic.model.relation_symbols["q"])
    info = semantic.model.relation_joins[query]
    assert info.row_schema.joined
    assert any(
        read.input == 1 and read.field == "name" for read in info.field_reads.values()
    )


def test_single_file_join_binding_read_over_sources_without_a_shape_fails() -> None:
    semantic = analyze(
        _parse(
            'source orders is postgres.table("orders")\n'
            'source customers is postgres.table("customers")\n'
            "query joined:\n"
            "    from orders\n"
            "    inner join customers as customer:\n"
            "        from orders\n"
            "    select:\n"
            "        id\n"
            "        n = customer.name\n"
        )
    )

    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in semantic.diagnostics
    ] == [
        ("PIE-S2303", "Source orders has no bound shape; row schema is unknown", 1, 1),
        (
            "PIE-S2303",
            "Source customers has no bound shape; row schema is unknown",
            2,
            1,
        ),
        (
            "PIE-S2334",
            "A JOIN over orders, whose fields are not known, is not available "
            "in single files yet; give source orders a shape.",
            5,
            5,
        ),
        (
            "PIE-S2334",
            "A JOIN over customers, whose fields are not known, is not available "
            "in single files yet; give source customers a shape.",
            5,
            5,
        ),
    ]


_SINGLE_FILE_JOIN_PREFIX = """shape ARow:
    id: Int not null
    b_id: Int not null
shape BRow:
    id: Int not null
    c_id: Int not null
shape CRow:
    id: Int not null
source a_rows: ARow is postgres.table("a")
source b_rows: BRow is postgres.table("b")
source c_rows: CRow is postgres.table("c")
relationship ab:
    endpoint a: a_rows
    endpoint b: b_rows
    on a.b_id == b.id
relationship bc:
    endpoint b: b_rows
    endpoint c: c_rows
    on b.c_id == c.id
query joined:
    from a_rows
"""


@pytest.mark.parametrize(
    ("joins", "expected"),
    (
        (
            "    inner join b_rows as b:\n        from a_rows\n        via ab: a -> b\n",
            [],
        ),
        (
            "    left join c_rows as c:\n        from a_rows\n"
            "        via ab: a -> b\n        via bc: b -> c\n",
            [
                (
                    "PIE-S2334",
                    f"A JOIN with more than one `via` step is available {_COMPLETES} it.",
                    22,
                    5,
                )
            ],
        ),
        (
            "    inner join b_rows as b:\n        from a_rows\n"
            "    inner join c_rows as c:\n        from b\n        via bc: b -> c\n",
            [],
        ),
        (
            "    inner join b_rows as b:\n        from nowhere\n        via ab: a -> b\n",
            [("PIE-S2335", "Unknown JOIN source binding: nowhere", 22, 5)],
        ),
        (
            "    inner join b_rows as b:\n        from b\n        via ab: a -> b\n",
            [
                (
                    "PIE-S2335",
                    "JOIN source binding is the binding this JOIN introduces: b",
                    22,
                    5,
                )
            ],
        ),
        (
            # A SEMI or ANTI binding is not visible to a later JOIN.
            "    semi join b_rows as b:\n        from a_rows\n        via ab: a -> b\n"
            "    inner join c_rows as c:\n        from b\n        via bc: b -> c\n",
            [
                (
                    "PIE-S2335",
                    "JOIN source binding is a SEMI JOIN binding, which later JOINs cannot read: b",
                    25,
                    5,
                ),
            ],
        ),
        (
            "    inner join c_rows as c:\n        from b\n        via bc: b -> c\n"
            "    inner join b_rows as b:\n        from a_rows\n        via ab: a -> b\n",
            [
                (
                    "PIE-S2335",
                    "JOIN source binding is bound only by a later JOIN: b",
                    22,
                    5,
                )
            ],
        ),
        (
            "    inner join b_rows as b:\n        from a_rows\n"
            "    inner join b_rows as b:\n        from a_rows\n"
            "    inner join c_rows as c:\n        from b\n        via bc: b -> c\n",
            [
                ("PIE-S2335", "Duplicate JOIN binding name: b", 24, 26),
                ("PIE-S2335", "Ambiguous JOIN source binding: b", 26, 5),
            ],
        ),
        (
            "    inner join nowhere as n:\n        from a_rows\n",
            [("PIE-S2301", "Unknown relation: nowhere", 22, 5)],
        ),
        (
            "    inner join b_rows as b:\n        from a_rows\n        via nope: a -> b\n",
            [("PIE-S2335", "Unknown relationship in JOIN VIA: nope", 24, 9)],
        ),
        (
            "    inner join b_rows as b:\n        from a_rows\n        via ab: a -> x\n",
            [("PIE-S2335", "Unknown endpoint role in JOIN VIA ab: x", 24, 9)],
        ),
        (
            "    inner join b_rows as b:\n        from a_rows\n        via ab: a -> a\n",
            [
                (
                    "PIE-S2335",
                    "JOIN VIA ab uses one endpoint role as both source and target: a",
                    24,
                    9,
                )
            ],
        ),
        (
            "    inner join c_rows as c:\n        from a_rows\n"
            "        via ab: a -> b\n        via ab: a -> b\n",
            [
                (
                    "PIE-S2334",
                    f"A JOIN with more than one `via` step is available {_COMPLETES} it.",
                    22,
                    5,
                )
            ],
        ),
        (
            "    inner join a_rows as back:\n        from a_rows\n        via ab: b -> a\n",
            [
                (
                    "PIE-S2335",
                    "JOIN VIA path starts at b_rows, not at source binding a_rows "
                    "(a_rows)",
                    22,
                    5,
                )
            ],
        ),
        (
            "    inner join c_rows as c:\n        from a_rows\n        via ab: a -> b\n",
            [
                (
                    "PIE-S2335",
                    "JOIN VIA path ends at b_rows, not at the JOIN target c_rows",
                    22,
                    5,
                )
            ],
        ),
    ),
)
def test_single_file_join_reads_resolve_their_target_binding_and_via_steps(
    joins: str, expected: list[tuple[str, str, int, int]]
) -> None:
    semantic = analyze(
        _parse(
            _SINGLE_FILE_JOIN_PREFIX + joins + "    select:\n        n = a_rows.id\n"
        )
    )
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in semantic.diagnostics
    ] == expected


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


_INFERENCE = """shape Employee:
    id: Int not null
    boss_id: Int nullable
    dept_id: Int not null
    unique employee_key on id
shape Department:
    id: Int not null
    site_id: Int not null
    unique department_key on id
shape Site:
    id: Int not null
    unique site_key on id
source employees: Employee is postgres.table("employees")
source departments: Department is postgres.table("departments")
source sites: Site is postgres.table("sites")
relationship reports_to:
    endpoint report: employees
    endpoint boss: employees
    on report.boss_id == boss.id
relationship works_in: employees.dept_id == departments.id
relationship located_at: departments.site_id == sites.id
query chain_inferred:
    from employees
    inner join departments as d
    left join sites as s: via located_at
    select:
        id = employees.id
query chain_explicit:
    from employees
    inner join departments as d:
        from employees
    left join sites as s:
        from d
        via located_at: departments -> sites
    select:
        id = employees.id
query hops_inferred:
    from employees
    inner join sites as s:
        via works_in
        via located_at
    select:
        id = employees.id
query hops_explicit:
    from employees
    inner join sites as s:
        from employees
        via works_in: employees -> departments
        via located_at: departments -> sites
    select:
        id = employees.id
query boss_inferred:
    from employees
    left join employees as boss: via reports_to: report -> boss
    select:
        id = employees.id
query boss_explicit:
    from employees
    left join employees as boss:
        from employees
        via reports_to: report -> boss
    select:
        id = employees.id
query self_direct:
    from employees
    left join employees as boss
    select:
        id = employees.id
query self_roles_omitted:
    from employees
    left join employees as boss: via reports_to
    select:
        id = employees.id
query two_sources:
    from employees
    left join employees as boss: via reports_to: report -> boss
    inner join departments as d
    select:
        id = employees.id
query two_sources_via:
    from employees
    left join employees as boss: via reports_to: report -> boss
    inner join departments as d: via works_in
    select:
        id = employees.id
query no_relationship:
    from employees
    inner join sites as s
    select:
        id = employees.id
query start_unread:
    from sites
    inner join departments as d: via works_in
    select:
        id = sites.id
query end_unreached:
    from employees
    inner join sites as s: via works_in
    select:
        id = employees.id
query semi_hidden:
    from employees
    semi join departments as d
    inner join sites as s: via located_at
    select:
        id = employees.id
query blocked_input:
    from employees
    inner join chain_explicit as joined:
        from employees
    inner join departments as d
    select:
        id = employees.id
query self_unreached:
    from employees
    inner join departments as d: via reports_to
    select:
        id = employees.id
query after_on:
    from departments
    inner join departments as twin:
        from departments
        on twin.id == departments.id
    left join sites as s
    select:
        id = departments.id
"""


@pytest.fixture(scope="module")
def inferred(tmp_path_factory: pytest.TempPathFactory) -> Any:
    root = tmp_path_factory.mktemp("inferred-joins")
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(_INFERENCE, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    return build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )


def _inferred_ledger(completed: Any, name: str) -> uses.ProjectRelationJoinUseLedger:
    (ledger,) = (
        ledger
        for ledger in completed.roots.join_conditions.uses.ledgers
        if ledger.owner.definition.name == name
    )
    return ledger


@pytest.mark.parametrize("pair", ("chain", "hops", "boss"))
def test_an_omitted_from_or_via_roles_resolve_to_the_explicit_join(
    inferred: Any, pair: str
) -> None:
    """Inference finds the authored source and directions; nothing else moves."""
    found = _inferred_ledger(inferred, f"{pair}_inferred")
    written = _inferred_ledger(inferred, f"{pair}_explicit")
    assert len(found.uses) == len(written.uses)
    for use, explicit in zip(found.uses, written.uses, strict=True):
        assert isinstance(use, uses.ProjectConcreteJoinUse)
        assert isinstance(explicit, uses.ProjectConcreteJoinUse)
        assert (
            use.source_binding.identity.binding_position
            == explicit.source_binding.identity.binding_position
        )
        assert all(
            left.guarantee is right.guarantee
            for left, right in zip(use.path.steps, explicit.path.steps, strict=True)
        )
        assert [step.directions for step in use.step_uses] == [
            step.directions for step in explicit.step_uses
        ]
    assert all(use.clause.source_binding_name is None for use in found.uses)
    assert not any(f": {pair}_" in item.message for item in inferred.diagnostics)


def test_an_inferred_join_keeps_every_candidate_and_never_picks_one(
    inferred: Any,
) -> None:
    kinds = uses.ProjectJoinUseIssueKind

    def failed(name: str, position: int = -1) -> uses.ProjectNonConcreteJoinUse:
        use = _inferred_ledger(inferred, name).uses[position]
        assert type(use) is uses.ProjectNonConcreteJoinUse
        return use

    # Zero VIA: one source with two directions of one self relationship.
    direct = failed("self_direct")
    assert [issue.kind for issue in direct.issues] == [
        kinds.DIRECT_RELATIONSHIP_AMBIGUOUS
    ]
    assert (
        direct.source_binding is _inferred_ledger(inferred, "self_direct").bindings[0]
    )
    assert direct.direct_result is not None
    assert len(direct.direct_result.candidates) == 2
    # VIA without roles over a relation joined to itself keeps both directions.
    (step,) = failed("self_roles_omitted").step_uses
    assert [issue.kind for issue in step.issues] == [kinds.AMBIGUOUS_ENDPOINT_DIRECTION]
    assert len(step.directions) == 2
    # Two earlier bindings of employees: both stay, in binding order.
    for name in ("two_sources", "two_sources_via"):
        ledger = _inferred_ledger(inferred, name)
        use = failed(name)
        assert [issue.kind for issue in use.issues] == [kinds.AMBIGUOUS_SOURCE_BINDING]
        assert use.issues[0].causes == ledger.bindings[:2]
        assert use.source_binding is None
    # No candidate: the issue retains every visible binding it checked; a
    # SEMI JOIN target is not visible to later JOINs.
    for name, checked in (
        ("no_relationship", (0,)),
        ("start_unread", (0,)),
        ("semi_hidden", (0,)),
    ):
        ledger = _inferred_ledger(inferred, name)
        use = failed(name)
        assert [issue.kind for issue in use.issues] == [kinds.UNKNOWN_SOURCE_BINDING]
        assert use.issues[0].causes == tuple(ledger.bindings[i] for i in checked)
    (step,) = failed("end_unreached").step_uses
    assert [issue.kind for issue in step.issues] == [kinds.UNKNOWN_ENDPOINT_DIRECTION]
    # An earlier binding without concrete authority (a JOIN query) is no
    # candidate while no relationship joins its relation to the target.
    ledger = _inferred_ledger(inferred, "blocked_input")
    resolved = ledger.uses[1]
    assert type(resolved) is uses.ProjectConcreteJoinUse
    assert resolved.source_binding is ledger.bindings[0]


def test_an_inferred_join_failure_names_its_cause_at_the_join(inferred: Any) -> None:
    unavailable = "Project relation semantic completion is unavailable: "
    roles = "`via reports_to: report -> boss`"
    reverse = "`via reports_to: boss -> report`"
    works_in = "`via works_in: employees -> departments`"
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in inferred.diagnostics
    ] == [
        (
            "PIE-S2333",
            f"{unavailable}self_direct (JOIN boss matches 2 relationship directions "
            f"from employees: {roles} and {reverse}; write one of them)",
            66,
            5,
        ),
        (
            "PIE-S2333",
            f"{unavailable}self_roles_omitted (JOIN boss: relationship reports_to "
            f"joins employees to itself; write {roles} or {reverse})",
            71,
            5,
        ),
        (
            "PIE-S2333",
            f"{unavailable}two_sources (JOIN d matches relationships from 2 earlier "
            f"bindings: employees {works_in} and boss {works_in}; write "
            "`from <binding>`)",
            77,
            5,
        ),
        (
            "PIE-S2333",
            f"{unavailable}two_sources_via (JOIN d: `via works_in` starts at "
            "employees, which 2 earlier bindings read: employees and boss; write "
            "`from <binding>`)",
            83,
            5,
        ),
        (
            "PIE-S2333",
            f"{unavailable}no_relationship (JOIN s: no relationship joins employees "
            "to sites; declare one, or write `from` and `on`)",
            88,
            5,
        ),
        (
            "PIE-S2333",
            f"{unavailable}start_unread (JOIN d: `via works_in` starts at "
            "employees, which no earlier binding reads)",
            93,
            5,
        ),
        (
            "PIE-S2333",
            f"{unavailable}end_unreached (JOIN s: `via works_in` joins employees "
            "and departments, not sites)",
            98,
            5,
        ),
        (
            "PIE-S2334",
            "SEMI JOIN is available only when an EXPLICIT_MODULES project "
            "(schema version 2) completes it.",
            103,
            5,
        ),
        # A JOIN without `from` names its own cause beside another JOIN's
        # PIE-S2334.
        (
            "PIE-S2333",
            f"{unavailable}semi_hidden (JOIN s: `via located_at` starts at "
            "departments, which no earlier binding reads)",
            104,
            5,
        ),
        ("PIE-S2333", f"{unavailable}blocked_input", 107, 1),
        # A relation joined to itself cannot reach another relation, in
        # either role order.
        (
            "PIE-S2333",
            f"{unavailable}self_unreached (JOIN d: `via reports_to` joins "
            "employees to itself, not departments)",
            116,
            5,
        ),
        (
            "PIE-S2334",
            "JOIN-local ON is available only when an EXPLICIT_MODULES project "
            "(schema version 2) completes it.",
            123,
            9,
        ),
        (
            "PIE-S2333",
            f"{unavailable}after_on (JOIN s matches relationships from 2 earlier "
            "bindings: departments `via located_at: departments -> sites` and "
            "twin `via located_at: departments -> sites`; write `from <binding>`)",
            124,
            5,
        ),
    ]


def test_an_explicit_direct_join_names_its_ambiguous_directions(
    tmp_path: Path,
) -> None:
    """Zero VIA with `from` keeps its location and gains the candidate list."""
    directions = "`via reports_to: report -> boss` and `via reports_to: boss -> report`"
    root = tmp_path / "explicit"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(
        _INFERENCE.split("query chain_inferred:")[0]
        + "query self_from:\n    from employees\n    left join employees as boss:\n"
        "        from employees\n    select:\n        id = employees.id\n"
        "query twice_from:\n    from employees\n    left join employees as boss:\n"
        "        from employees\n    left join employees as peer:\n"
        "        from employees\n    select:\n        id = employees.id\n",
        encoding="utf-8",
    )
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(
            project_check.check_project_parse_only(root)
        )
    )
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in completed.diagnostics
    ] == [
        (
            "PIE-S2333",
            "Project relation semantic completion is unavailable: self_from (JOIN "
            "boss matches 2 relationship directions from employees: "
            f"{directions}; write one of them)",
            22,
            1,
        ),
        # One diagnostic per relation, as without the candidate lists.
        (
            "PIE-S2333",
            "Project relation semantic completion is unavailable: twice_from (JOIN "
            f"boss matches 2 relationship directions from employees: {directions}; "
            "write one of them; JOIN peer matches 2 relationship directions from "
            f"employees: {directions}; write one of them)",
            28,
            1,
        ),
    ]


def test_single_file_check_treats_an_inferred_join_like_its_explicit_form() -> None:
    """Inferred and written relationship paths resolve to the same JOIN inputs."""
    head = _INFERENCE.split("query chain_inferred:")[0]
    for body in (
        "query q:\n    from employees\n    inner join departments as d\n"
        "    left join sites as s: via located_at\n    select:\n        employees.id\n",
        "query q:\n    from employees\n    inner join departments as d:\n"
        "        from employees\n    left join sites as s:\n        from d\n"
        "        via located_at: departments -> sites\n    select:\n        employees.id\n",
    ):
        script = _parse(head + body)
        semantic = analyze(script)
        assert semantic.diagnostics == ()
        query = cast(QueryDef, semantic.model.relation_symbols["q"])
        assert tuple(
            join.relationship for join in semantic.model.relation_joins[query].joins
        ) == (
            "works_in",
            "located_at",
        )
        assert build_ir(script, semantic.model).diagnostics == ()
    # The written parts of an inferred JOIN are still checked.
    written = _parse(
        head + "query q:\n    from employees\n    inner join departments as d\n"
        "    left join sites as s: via nosuch\n    select:\n        employees.id\n"
    )
    assert [(d.code, d.message) for d in analyze(written).diagnostics] == [
        ("PIE-S2335", "JOIN s: `via nosuch` names no relationship of this module")
    ]


def _completed_project(root: Path, files: dict[str, str]) -> Any:
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    return build_project_completed_semantic_result(
        build_empty_project_semantic_result(
            project_check.check_project_parse_only(root)
        )
    )


_UNUSABLE = """shape Project:
    id: Int not null
    lead_id: Int not null
    dept_id: Int not null
    unique project_key on id
shape Employee:
    id: Int not null
    dept_id: Int not null
    unique employee_key on id
shape Department:
    id: Int not null
    unique department_key on id
source projects: Project is postgres.table("projects")
source employees: Employee is postgres.table("employees")
source departments: Department is postgres.table("departments")
relationship lead: employees.id == projects.lead_id
relationship works_in: employees.dept_id == departments.id
relationship proj_dept:
    endpoint p: projects
    endpoint d: departments
{on}query two:
    from projects
    inner join employees as e
    {kind} join departments as d
    select:
        id = projects.id
query one:
    from projects
    {kind} join departments as d
    select:
        id = projects.id
query via_only:
    from projects
    {kind} join departments as d: via proj_dept
    select:
        id = projects.id
query chosen:
    from projects
    inner join employees as e
    {kind} join departments as d: from e
    select:
        id = projects.id
query via_roles:
    from projects
    {kind} join departments as d: via proj_dept: p -> d
    select:
        id = projects.id
query written:
    from projects
    {kind} join departments as d:
        from projects
        via proj_dept: p -> d
    select:
        id = projects.id
"""


@pytest.mark.parametrize("kind", ("inner", "left"))
@pytest.mark.parametrize(
    ("on", "reason"),
    (
        ("", "it has no `on`"),
        (
            "    on p.dept_id < d.id\n",
            "its `on` is not only field equalities that a JOIN can use",
        ),
        (
            "    on p.dept_id == d.id or p.lead_id == d.id\n",
            "its `on` is not only field equalities that a JOIN can use",
        ),
    ),
    ids=("no_on", "less_than", "or"),
)
def test_a_relationship_that_cannot_be_used_keeps_its_binding_a_candidate(
    tmp_path: Path, kind: str, on: str, reason: str
) -> None:
    """A declared relationship is never passed over for another binding."""
    completed = _completed_project(
        tmp_path / "unusable",
        {"main.pietto": _UNUSABLE.format(on=on, kind=kind)},
    )
    unavailable = "Project relation semantic completion is unavailable: "
    line = 21 + on.count("\n")
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in completed.diagnostics
    ] == [
        (
            "PIE-S2333",
            f"{unavailable}two (JOIN d matches relationships from 2 earlier "
            f"bindings: projects relationship proj_dept (cannot be used: {reason}) "
            "and e `via works_in: employees -> departments`; write `from <binding>`)",
            line + 3,
            5,
        ),
        (
            "PIE-S2333",
            f"{unavailable}one (JOIN d: no relationship from projects to "
            f"departments can be used: proj_dept ({reason}))",
            line + 8,
            5,
        ),
        (
            "PIE-S2333",
            f"{unavailable}via_only (JOIN d: relationship proj_dept cannot be used: "
            f"{reason})",
            line + 13,
            5,
        ),
        # Without `from`, a VIA step with roles is named at the JOIN too...
        (
            "PIE-S2333",
            f"{unavailable}via_roles (JOIN d: relationship proj_dept cannot be "
            f"used: {reason})",
            line + 24,
            5,
        ),
        # ...while the fully written form keeps its bare message at the query.
        ("PIE-S2333", f"{unavailable}written", line + 27, 1),
    ]
    (two,) = (
        ledger
        for ledger in completed.roots.join_conditions.uses.ledgers
        if ledger.owner.definition.name == "two"
    )
    use = two.uses[1]
    assert type(use) is uses.ProjectNonConcreteJoinUse
    assert [issue.kind for issue in use.issues] == [
        uses.ProjectJoinUseIssueKind.AMBIGUOUS_SOURCE_BINDING
    ]
    assert use.issues[0].causes == two.bindings[:2]


def test_a_via_line_is_offered_only_for_a_relationship_of_the_module(
    tmp_path: Path,
) -> None:
    """A VIA step names only its own module's relationships."""
    shared = (
        "shape Employee:\n    id: Int not null\n    boss_id: Int nullable\n"
        "    dept_id: Int not null\n    unique employee_key on id\n"
        "shape Department:\n    id: Int not null\n    unique department_key on id\n"
        'source employees: Employee is postgres.table("employees")\n'
        'source departments: Department is postgres.table("departments")\n'
        "export:\n    source employees\n    source departments\n"
    )
    imports = 'import "shared.pietto":\n    source employees\n    source departments\n'
    completed = _completed_project(
        tmp_path / "modules",
        {
            "shared.pietto": shared,
            "other.pietto": imports
            + "relationship elsewhere: employees.boss_id == departments.id\n",
            "main.pietto": imports
            + "relationship works_in: employees.dept_id == departments.id\n"
            "query written:\n    from employees\n    inner join departments as d:\n"
            "        from employees\n    select:\n        id = employees.id\n"
            "query inferred:\n    from employees\n    inner join departments as d\n"
            "    select:\n        id = employees.id\n"
            "query named:\n    from employees\n"
            "    inner join departments as d: via elsewhere\n"
            "    select:\n        id = employees.id\n",
        },
    )
    cause = (
        "(JOIN d matches 2 relationship directions from employees: `via works_in: "
        "employees -> departments` and relationship elsewhere of other.pietto "
        "(employees -> departments); a `via` names only a relationship of this "
        "module)"
    )
    unavailable = "Project relation semantic completion is unavailable: "
    assert [
        (item.message, item.location.path, item.location.line, item.location.column)
        for item in completed.diagnostics
    ] == [
        (f"{unavailable}written {cause}", "main.pietto", 5, 1),
        (f"{unavailable}inferred {cause}", "main.pietto", 13, 5),
        (
            f"{unavailable}named (JOIN d: `via elsewhere` names no relationship of "
            "this module; a `via` cannot name relationship elsewhere of other.pietto)",
            "main.pietto",
            18,
            5,
        ),
    ]


@pytest.mark.parametrize(
    "on",
    ("    on p.nope == d.id\n", "    on x.dept_id == d.id\n"),
    ids=("unknown_field", "unknown_role"),
)
def test_a_relationship_with_declaration_errors_is_named_as_such(
    tmp_path: Path, on: str
) -> None:
    """Its PIE-S2604 is the declaration's error, not a non-equality `on`."""
    completed = _completed_project(
        tmp_path / "errors",
        {"main.pietto": _UNUSABLE.format(on=on, kind="inner")},
    )
    assert [item.code for item in completed.diagnostics][:1] == ["PIE-S2604"]
    assert (
        "Project relation semantic completion is unavailable: one (JOIN d: no "
        "relationship from projects to departments can be used: proj_dept (its "
        "declaration has errors))"
    ) in [item.message for item in completed.diagnostics]


_UNMODELLED = """shape Employee:
    id: Int not null
    dept_id: Int not null
    unique employee_key on id
shape Department:
    id: Int not null
    unique department_key on id
source employees: Employee is postgres.table("employees")
source departments: Department is postgres.table("departments")
relationship works_in: employees.dept_id == departments.id
{relationship}query joined:
    from employees
    inner join departments as d
    select:
        id = d.id
query result:
    from employees
    inner join joined as j:
        from employees
        on j.id == employees.id
    inner join departments as d
    select:
        id = employees.id
query series:
    from generate_series(1, 3, 1) as n
    inner join employees as e:
        from n
        on e.id == n.n
    inner join departments as d
    select:
        id = e.id
"""


def test_an_unmodelled_earlier_binding_blocks_only_when_it_may_be_the_source(
    tmp_path: Path,
) -> None:
    """A JOIN query or a table function binding has no relationship authority:
    it is left out of the lookup unless a relationship joins its relation to
    the target, and then the JOIN without `from` names it."""
    clear = _completed_project(
        tmp_path / "clear", {"main.pietto": _UNMODELLED.format(relationship="")}
    )
    assert clear.diagnostics == ()
    for name, source in (("result", 0), ("series", 1)):
        (condition,) = (
            entry
            for entry in clear.roots.join_conditions.entries
            if entry.ledger.owner.definition.name == name
            and entry.use.identity.join_position == 1
        )
        assert condition.ready
        assert condition.environment.source_candidates == (
            condition.ledger.bindings[source],
        )
    blocked = _completed_project(
        tmp_path / "blocked",
        {
            "main.pietto": _UNMODELLED.format(
                relationship="relationship joined_dept: joined.id == departments.id\n"
            )
        },
    )
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in blocked.diagnostics
    ] == [
        (
            "PIE-S2334",
            "JOIN-local ON is available only when an EXPLICIT_MODULES project "
            "(schema version 2) completes it.",
            21,
            9,
        ),
        (
            "PIE-S2333",
            "Project relation semantic completion is unavailable: result (JOIN d: "
            "earlier binding j may be its source, but a relationship JOIN cannot "
            "read joined; write `from <binding>`)",
            22,
            5,
        ),
    ]


def test_a_relationship_on_an_unreadable_endpoint_says_so(tmp_path: Path) -> None:
    """A JOIN query endpoint, not the `on`, keeps the relationship from a JOIN;
    `from` alone does not help, a JOIN-local `on` does."""
    text = _UNMODELLED.format(
        relationship="relationship joined_dept: joined.id == departments.id\n"
    ) + (
        "query via_joined:\n    from joined\n"
        "    inner join departments as d: via joined_dept\n"
        "    select:\n        id = joined.id\n"
        "query bare_joined:\n    from joined\n    inner join departments as d\n"
        "    select:\n        id = joined.id\n"
    )
    lines = text.split("\n")
    via_line = lines.index("    inner join departments as d: via joined_dept") + 1
    bare_line = lines.index("query bare_joined:") + 3
    completed = _completed_project(tmp_path / "joined", {"main.pietto": text})
    unavailable = "Project relation semantic completion is unavailable: "
    assert [
        (item.message, item.location.line, item.location.column)
        for item in completed.diagnostics
        if item.location.line >= via_line
    ] == [
        (
            f"{unavailable}via_joined (JOIN d: relationship joined_dept cannot be "
            "used: a relationship JOIN cannot read its endpoint joined)",
            via_line,
            5,
        ),
        (
            f"{unavailable}bare_joined (JOIN d: earlier binding joined may be its "
            "source, but a relationship JOIN cannot read joined; write `from` and "
            "`on` instead)",
            bare_line,
            5,
        ),
    ]


_STEPS = """shape Employee:
    id: Int not null
    dept_id: Int not null
    unique employee_key on id
shape Department:
    id: Int not null
    site_id: Int not null
    unique department_key on id
shape Site:
    id: Int not null
    unique site_key on id
source employees: Employee is postgres.table("employees")
source departments: Department is postgres.table("departments")
source sites: Site is postgres.table("sites")
relationship works_in:
    endpoint emp: employees
    endpoint dep: departments
    on emp.dept_id == dep.id
relationship slack:
    endpoint emp: employees
    endpoint dep: departments
relationship located_at:
    endpoint dep: departments
    endpoint site: sites
    on dep.site_id == site.id
query result:
    from employees
{on_join}    inner join {join}
    select:
        id = employees.id
"""


@pytest.mark.parametrize("with_on", (False, True), ids=("alone", "beside_on"))
@pytest.mark.parametrize(
    ("join", "cause"),
    (
        (
            "departments as d: via workz_in",
            "JOIN d: `via workz_in` names no relationship of this module",
        ),
        (
            "departments as d: via workz_in: emp -> dep",
            "JOIN d: `via workz_in` names no relationship of this module",
        ),
        (
            "departments as d: via works_in: emp -> nope",
            "JOIN d: relationship works_in has no endpoint role nope; its roles are "
            "emp and dep",
        ),
        (
            "departments as d: via works_in: emp -> emp",
            "JOIN d: `via works_in: emp -> emp` names one role as both source and "
            "target",
        ),
        (
            "departments as d: via slack: emp -> dep",
            "JOIN d: relationship slack cannot be used: it has no `on`",
        ),
        (
            "sites as st:\n        via works_in\n        via located_at: dep -> nope",
            "JOIN st: relationship located_at has no endpoint role nope; its roles "
            "are dep and site",
        ),
    ),
    ids=(
        "unknown",
        "unknown_with_roles",
        "unknown_role",
        "one_role_twice",
        "roles_over_unusable",
        "blocked_by_later_step",
    ),
)
def test_a_failing_via_step_of_an_inferred_join_is_named_at_the_join(
    tmp_path: Path, with_on: bool, join: str, cause: str
) -> None:
    """Whatever else the relation reports, as for the omitted parts."""
    on_join = (
        "    inner join sites as s:\n        from employees\n"
        "        on s.id == employees.id\n"
        if with_on
        else ""
    )
    text = _STEPS.format(on_join=on_join, join=join)
    lines = text.split("\n")
    join_line = lines.index(f"    inner join {join.splitlines()[0]}") + 1
    completed = _completed_project(tmp_path / "steps", {"main.pietto": text})
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in completed.diagnostics
    ] == [
        *(
            (
                (
                    "PIE-S2334",
                    "JOIN-local ON is available only when an EXPLICIT_MODULES "
                    "project (schema version 2) completes it.",
                    join_line - 1,
                    9,
                ),
            )
            if with_on
            else ()
        ),
        (
            "PIE-S2333",
            f"Project relation semantic completion is unavailable: result ({cause})",
            join_line,
            5,
        ),
    ]


def test_a_failing_via_step_keeps_its_explicit_and_single_file_reports(
    tmp_path: Path,
) -> None:
    """Project failure stays relation-level; inferred single-file paths name the JOIN."""
    written = _STEPS.format(
        on_join="",
        join="departments as d:\n        from employees\n        via works_in: emp -> nope",
    )
    completed = _completed_project(tmp_path / "written", {"main.pietto": written})
    assert [
        (item.message, item.location.line, item.location.column)
        for item in completed.diagnostics
    ] == [("Project relation semantic completion is unavailable: result", 26, 1)]
    for join, message in (
        (
            "departments as d: via workz_in",
            "JOIN d: `via workz_in` names no relationship of this module",
        ),
        (
            "departments as d: via works_in: emp -> nope",
            "JOIN d: relationship works_in has no endpoint role nope; its roles are emp and dep",
        ),
    ):
        text = _STEPS.format(on_join="", join=join)
        header = f"    inner join {join}"
        semantic = analyze(_parse(text))
        assert [
            (item.code, item.message, item.location.line, item.location.column)
            for item in semantic.diagnostics
        ] == [
            (
                "PIE-S2335",
                message,
                text.split("\n").index(header) + 1,
                5,
            )
        ]


_JOIN_FACT_SOURCE = """shape Order:
    id: Int not null
    customer_id: Int not null
shape Customer:
    id: Int not null
    name: Text not null
source orders: Order is postgres.table("orders")
source customers: Customer is postgres.table("customers")
relationship order_customer:
    endpoint o: orders
    endpoint c: customers
    on o.customer_id == c.id
query result:
    from orders
    inner join customers as customer:
        from orders
        via order_customer: o -> c
    select:
        customer.name
"""


def test_single_file_join_facts_copy_their_reads_and_default_to_no_joins() -> None:
    script = _parse(_JOIN_FACT_SOURCE)
    orders = cast(SourceDef, script.definitions[2])
    customers = cast(SourceDef, script.definitions[3])
    query = cast(QueryDef, script.definitions[4])
    join = query.join_clauses[0]
    base_match = script.relationships[0].base_match
    assert base_match is not None
    comparison = cast(ComparisonExpr, base_match.expression)
    read = query.select_items[0].expression
    integer = ResolvedType("Int", TypeKind.BUILTIN)
    non_null = EffectiveNullability.NON_NULL
    row = RowSchema(
        fields={
            key: RowField(name=key, resolved_type=resolved, nullability=non_null)
            for key, resolved in (
                ("orders.id", integer),
                ("orders.customer_id", integer),
                ("customer.id", integer),
                ("customer.name", ResolvedType("Text", TypeKind.BUILTIN)),
            )
        },
        joined=True,
    )
    equality = JoinEqualityInfo(
        left=JoinFieldRef(input=0, field="customer_id"),
        right=JoinFieldRef(input=1, field="id"),
        left_type=ValueType(integer, non_null),
        right_type=ValueType(integer, non_null),
        comparison=comparison,
        left_operand=cast(DottedNameExpr, comparison.left),
        right_operand=cast(DottedNameExpr, comparison.right),
    )
    reads = {read: JoinFieldRef(input=1, field="name")}
    info = RelationJoinsInfo(
        inputs=(
            JoinInputInfo(
                ordinal=0, binding="orders", relation=orders, clause=None, visible=True
            ),
            JoinInputInfo(
                ordinal=1,
                binding="customer",
                relation=customers,
                clause=join,
                visible=True,
            ),
        ),
        joins=(
            JoinInfo(
                ordinal=1,
                clause=join,
                kind=AuthoredJoinKind.INNER,
                mode="M2",
                source_input=0,
                source_inferred=False,
                target_input=1,
                relationship="order_customer",
                step=join.traversal_steps[0],
                equalities=(equality,),
                condition=None,
                null_extends=(),
            ),
        ),
        row_schema=row,
        field_reads=reads,
    )
    reads.clear()
    model = SemanticModel(mode=CheckMode.CHECKED, relation_joins={query: info})

    assert dict(info.field_reads) == {read: JoinFieldRef(input=1, field="name")}
    assert dict(model.relation_joins) == {query: info}
    read_only = "'mappingproxy' object does not support item assignment"
    with pytest.raises(TypeError, match=read_only):
        info.field_reads[read] = JoinFieldRef(input=0, field="id")  # type: ignore[index]
    with pytest.raises(TypeError, match=read_only):
        model.relation_joins[query] = info  # type: ignore[index]
    assert tuple(row.fields) == (
        "orders.id",
        "orders.customer_id",
        "customer.id",
        "customer.name",
    )
    assert (row.joined, RowSchema().joined) == (True, False)
    assert SemanticModel(mode=CheckMode.CHECKED).relation_joins == {}


_COMPLETED = "only when an EXPLICIT_MODULES project (schema version 2) completes"
_SELECT_ID = "    select:\n        x = orders.id\n"
_SHAPELESS = (
    "A JOIN over {}, whose fields are not known, is not available in single "
    "files yet; give source events a shape."
)


def _joined_query(body: str) -> str:
    return JOIN_PREFIX + "query q:\n" + body


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        pytest.param(
            "    from orders\n    right join nowhere as n:\n        from orders\n"
            "        on orders.id == n.id\n" + _SELECT_ID,
            [("PIE-S2301", "Unknown relation: nowhere", 20, 5)],
            id="unknown_target",
        ),
        pytest.param(
            "    from orders\n    inner join both as b: from orders\n"
            + _SELECT_ID
            + "query both:\n    union all:\n        from orders\n        from orders\n",
            [
                (
                    "PIE-S2334",
                    f"Set-operation inputs are available {_COMPLETED} them: both",
                    20,
                    5,
                )
            ],
            id="set_operation_target",
        ),
        pytest.param(
            "    from orders\n    cross join customers as orders: from orders\n"
            + _SELECT_ID,
            [
                (
                    "PIE-S2335",
                    "JOIN binding cannot have the FROM input's name: orders",
                    20,
                    29,
                )
            ],
            id="binding_named_like_from",
        ),
        pytest.param(
            "    from orders\n    semi join customers as c: from orders\n"
            "    cross join regions as c: from orders\n" + _SELECT_ID,
            [("PIE-S2335", "Duplicate JOIN binding name: c", 21, 27)],
            id="binding_named_like_a_semi_binding",
        ),
        pytest.param(
            "    from orders\n    cross join regions as r: from nowhere\n" + _SELECT_ID,
            [("PIE-S2335", "Unknown JOIN source binding: nowhere", 20, 5)],
            id="unknown_source",
        ),
        pytest.param(
            "    from orders\n    cross join regions as r: from r\n" + _SELECT_ID,
            [
                (
                    "PIE-S2335",
                    "JOIN source binding is the binding this JOIN introduces: r",
                    20,
                    5,
                )
            ],
            id="own_binding_as_source",
        ),
        pytest.param(
            "    from orders\n    cross join regions as r: from c\n"
            "    cross join customers as c: from orders\n" + _SELECT_ID,
            [
                (
                    "PIE-S2335",
                    "JOIN source binding is bound only by a later JOIN: c",
                    20,
                    5,
                )
            ],
            id="later_binding_as_source",
        ),
        pytest.param(
            "    from orders\n    cross join customers as c: from orders\n"
            "    cross join customers as c: from orders\n"
            "    cross join regions as r: from c\n" + _SELECT_ID,
            [
                ("PIE-S2335", "Duplicate JOIN binding name: c", 21, 29),
                ("PIE-S2335", "Ambiguous JOIN source binding: c", 22, 5),
            ],
            id="ambiguous_source",
        ),
        pytest.param(
            "    from orders\n    cross join regions as r:\n        from orders\n"
            "        on r.id == orders.id\n" + _SELECT_ID,
            [("PIE-S2336", "CROSS JOIN cannot have ON or VIA.", 20, 5)],
            id="cross_with_on",
        ),
        pytest.param(
            "    from orders\n    inner join regions as r:\n        from orders\n"
            "        via order_customer\n        via customer_region\n"
            "        on r.id == 1\n" + _SELECT_ID,
            [
                (
                    "PIE-S2336",
                    "JOIN-local ON refinement requires exactly one VIA step.",
                    20,
                    5,
                )
            ],
            id="several_steps_with_on",
        ),
        pytest.param(
            "    from orders\n    right join regions as r:\n        from orders\n"
            "        via order_customer\n        via customer_region\n" + _SELECT_ID,
            [("PIE-S2336", "This JOIN kind requires a direct binary input.", 20, 5)],
            id="several_steps_of_a_right_join",
        ),
        pytest.param(
            "    from orders\n    left join regions as r:\n        from orders\n"
            "        via order_customer\n        via customer_region\n" + _SELECT_ID,
            [
                (
                    "PIE-S2334",
                    f"A JOIN with more than one `via` step is available {_COMPLETED} it.",
                    20,
                    5,
                )
            ],
            id="several_steps",
        ),
        pytest.param(
            "    from orders\n    cross join regions as r: from orders\n"
            "    select:\n        n = row_number() window:\n            order by:\n"
            "                orders.id\n",
            [
                (
                    "PIE-S2334",
                    f"Window functions over JOIN rows are available {_COMPLETED} them.",
                    22,
                    13,
                )
            ],
            id="window_call",
        ),
        pytest.param(
            "    from orders\n    cross join regions as r: from orders\n"
            + _SELECT_ID
            + "    window w:\n        order by:\n            orders.id\n",
            [
                (
                    "PIE-S2334",
                    f"Window functions over JOIN rows are available {_COMPLETED} them.",
                    23,
                    5,
                )
            ],
            id="named_window",
        ),
        pytest.param(
            "    from orders\n    cross join regions as r: from orders\n"
            "    select:\n        n = count()\n    order by:\n        orders.id\n",
            [
                (
                    "PIE-S2334",
                    "ORDER BY is not available after an ungrouped aggregate over JOIN rows: "
                    "the result has one row; remove `order by`.",
                    23,
                    5,
                )
            ],
            id="aggregate_order_by",
        ),
        pytest.param(
            "    from tracked\n    cross join events as e: from tracked\n"
            "    select:\n        x = 1\n"
            "table tracked:\n    from events\n    select:\n        id\n"
            'source events is postgres.table("events")\n',
            [
                ("PIE-S2334", _SHAPELESS.format("tracked"), 20, 5),
                ("PIE-S2334", _SHAPELESS.format("events"), 20, 5),
            ],
            id="inputs_without_a_shape",
        ),
        pytest.param(
            "    from events\n    cross join events as again: from events\n"
            '    select:\n        x = 1\nsource events is postgres.table("events")\n',
            # One for the FROM input and one for the target, as for two sources.
            [
                ("PIE-S2334", _SHAPELESS.format("events"), 20, 5),
                ("PIE-S2334", _SHAPELESS.format("events"), 20, 5),
            ],
            id="self_join_without_a_shape",
        ),
        pytest.param(
            "    from orders\n    cross join nowhere as orders:\n        from nobody\n"
            "        on orders.id == 1\n" + _SELECT_ID,
            [
                ("PIE-S2301", "Unknown relation: nowhere", 20, 5),
                (
                    "PIE-S2335",
                    "JOIN binding cannot have the FROM input's name: orders",
                    20,
                    27,
                ),
                ("PIE-S2336", "CROSS JOIN cannot have ON or VIA.", 20, 5),
            ],
            id="written_parts_beside_an_unknown_target",
        ),
    ),
)
def test_single_file_join_structure_refuses_each_written_part(
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    expected: list[tuple[str, str, int, int]],
) -> None:
    monkeypatch.setattr(joins, "resolve_join_relationship", resolve_by_declaration)
    run = run_joins(_joined_query(body))
    assert located(run.diagnostics) == expected
    assert run.structures == {}


def test_single_file_join_structure_resolves_each_input_and_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(joins, "resolve_join_relationship", resolve_by_declaration)
    run = run_joins(
        _joined_query(
            "    from orders\n"
            "    inner join customers as c\n"
            "    left join regions as r: via customer_region: customers -> regions\n"
            "    semi join customers as s:\n        from orders\n"
            '        via order_customer\n        on s.name != ""\n'
            "    right join regions as r2:\n        from c\n"
            "        on r2.id == c.region_id\n"
            "    cross join regions as r3: from orders\n" + _SELECT_ID
        )
    )
    query = run.relation("q")
    structure = run.structures[query]
    assert run.diagnostics == []
    assert [
        (item.ordinal, item.binding, item.relation.name, item.visible)
        for item in structure.inputs
    ] == [
        (0, "orders", "orders", True),
        (1, "c", "customers", True),
        (2, "r", "regions", True),
        (3, "s", "customers", False),
        (4, "r2", "regions", True),
        (5, "r3", "regions", True),
    ]
    assert structure.inputs[0].clause is None
    assert all(
        item.clause is clause
        for item, clause in zip(structure.inputs[1:], query.join_clauses, strict=True)
    )
    assert [
        (
            join.ordinal,
            join.clause is query.join_clauses[join.ordinal - 1],
            join.mode,
            join.source_input,
            join.source_inferred,
            None if join.relationship is None else join.relationship.relationship,
        )
        for join in structure.joins
    ] == [
        (1, True, "M1", 0, True, "order_customer"),
        (2, True, "M2", 1, True, "customer_region"),
        (3, True, "M4", 0, False, "order_customer"),
        (4, True, "M3", 1, False, None),
        (5, True, "M5", 0, False, None),
    ]


def test_single_file_join_structure_takes_the_relationship_resolution_as_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _joined_query(
        "    from orders\n    inner join customers as c\n" + _SELECT_ID
    )
    calls: list[str] = []

    def silent(clause: Any, **_: Any) -> tuple[Diagnostic, ...]:
        calls.append(clause.target_binding_name)
        return ()

    monkeypatch.setattr(joins, "resolve_join_relationship", silent)
    run = run_joins(source)
    # A relationship whose own declaration errors decide the JOIN: no
    # structure and nothing more reported.
    assert (run.diagnostics, run.structures, calls) == ([], {}, ["c"])
    reported = Diagnostic(
        code="PIE-S2335",
        severity=Severity.ERROR,
        message="stand-in",
        location=SourceLocation(path=None, line=1, column=1),
    )
    monkeypatch.setattr(
        joins, "resolve_join_relationship", lambda clause, **_: (reported,)
    )
    run = run_joins(source)
    assert (run.diagnostics, run.structures) == ([reported], {})


def test_single_file_join_structure_resolves_no_relationship_from_a_failed_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        joins,
        "resolve_join_relationship",
        lambda clause, **_: calls.append(clause.target_binding_name) or (),
    )
    run = run_joins(
        _joined_query(
            "    from orders\n    inner join nowhere as n: from orders\n"
            "    inner join customers as c\n    inner join regions as r: from n\n"
            + _SELECT_ID
        )
    )
    assert located(run.diagnostics) == [
        ("PIE-S2301", "Unknown relation: nowhere", 20, 5)
    ]
    assert (calls, run.structures) == ([], {})
    unresolved = run_joins(
        _joined_query(
            "    from nowhere\n    cross join regions as r: from nowhere\n"
            "    select:\n        x = 1\n"
        )
    )
    # The FROM input's own PIE-S2301 is the error; JOIN analysis adds none.
    assert (unresolved.diagnostics, unresolved.structures) == ([], {})


_N = EffectiveNullability.NULLABLE.value
_NN = EffectiveNullability.NON_NULL.value
_ORDERS = {"orders.id": _NN, "orders.customer_id": _N, "orders.amount": _NN}
_NULLABLE_ORDERS = dict.fromkeys(_ORDERS, _N)


def _customers(binding: str, *nullable: str) -> dict[str, str]:
    row = {"id": _NN, "name": _NN, "region_id": _N, "active": _N}
    row.update(dict.fromkeys(nullable, _N))
    return {f"{binding}.{name}": value for name, value in row.items()}


def _nullability(row: RowSchema) -> dict[str, str]:
    return {key: field.nullability.value for key, field in row.fields.items()}


@pytest.mark.parametrize(
    ("joins_text", "expected", "extends"),
    (
        pytest.param(
            "    inner join customers as c\n",
            {**_ORDERS, "orders.customer_id": _NN, **_customers("c")},
            [()],
            id="inner_relationship_equality",
        ),
        pytest.param(
            "    left join customers as c\n",
            {**_ORDERS, **_customers("c", "id", "name")},
            [(1,)],
            id="left",
        ),
        pytest.param(
            "    right join customers as c:\n        from orders\n"
            "        on orders.customer_id == c.id\n",
            {**_NULLABLE_ORDERS, **_customers("c")},
            [(0,)],
            id="right",
        ),
        pytest.param(
            "    full join customers as c:\n        from orders\n"
            "        on orders.customer_id == c.id\n",
            {**_NULLABLE_ORDERS, **_customers("c", "id", "name")},
            [(0, 1)],
            id="full",
        ),
        pytest.param(
            "    cross join regions as r: from orders\n",
            {**_ORDERS, "r.id": _NN, "r.label": _NN},
            [()],
            id="cross",
        ),
        pytest.param(
            "    semi join customers as s:\n        from orders\n"
            "        on orders.customer_id == s.id\n",
            _ORDERS,
            [()],
            id="semi",
        ),
        pytest.param(
            "    anti join customers as s:\n        from orders\n"
            "        on orders.customer_id == s.id\n",
            _ORDERS,
            [()],
            id="anti",
        ),
        pytest.param(
            "    semi join customers as s:\n        from orders\n"
            "        on orders.customer_id == s.id\n"
            "    right join regions as r:\n        from orders\n"
            "        on r.id == orders.amount\n",
            {**_NULLABLE_ORDERS, "r.id": _NN, "r.label": _NN},
            [(), (0,)],
            id="right_after_semi",
        ),
        pytest.param(
            "    left join customers as c:\n        from orders\n"
            "        on orders.customer_id == c.id\n"
            "    inner join regions as r:\n        from c\n"
            '        on c.region_id == r.id and c.name != ""\n',
            {**_ORDERS, **_customers("c", "id", "name"), "r.id": _NN, "r.label": _NN},
            [(1,), ()],
            id="extension_outlasts_a_later_inner_join",
        ),
    ),
)
def test_single_file_joined_rows_follow_each_join_kind(
    monkeypatch: pytest.MonkeyPatch,
    joins_text: str,
    expected: dict[str, str],
    extends: list[tuple[int, ...]],
) -> None:
    monkeypatch.setattr(joins, "resolve_join_relationship", resolve_by_declaration)
    run = run_joins(_joined_query("    from orders\n" + joins_text + _SELECT_ID))
    assert run.diagnostics == []
    rows = run.rows("q")
    assert rows is not None and rows.tail.joined and not rows.tail.is_unknown
    assert _nullability(rows.tail) == expected
    assert all(field.name == key for key, field in rows.tail.fields.items())
    checks, _ = run.checks()
    facts = checks.facts[run.relation("q")]
    assert [join.null_extends for join in facts.joins] == extends


def test_single_file_join_on_rows_read_the_rows_before_each_join() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n"
            "    left join customers as c:\n        from orders\n"
            "        on orders.customer_id == c.id\n"
            "    inner join regions as r:\n        from c\n"
            "        on c.region_id == r.id\n" + _SELECT_ID
        )
    )
    rows = run.rows("q")
    assert rows is not None
    first, second = rows.on
    assert _nullability(first) == {**_ORDERS, **_customers("c")}
    assert _nullability(second) == {
        **_ORDERS,
        **_customers("c", "id", "name"),
        "r.id": _NN,
        "r.label": _NN,
    }
    assert first.joined and second.joined
    customer_name = second.fields["c.name"]
    assert (customer_name.resolved_type.name, customer_name.definition) == (
        "Text",
        run.model.source_row_schemas[
            cast(SourceDef, run.model.relation_symbols["customers"])
        ]
        .fields["name"]
        .definition,
    )
    structure = run.structures[run.relation("q")]
    unknown = RowSchema(is_unknown=True)
    assert joins.join_rows(structure, lambda relation: unknown) is None
    assert joins.join_input_row(structure, lambda relation: unknown) == unknown
    assert joins.join_input_row(structure, run.schema_of) == rows.tail


def test_single_file_join_reads_resolve_against_the_visible_bindings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(joins, "resolve_join_relationship", resolve_by_declaration)
    run = run_joins(
        _joined_query(
            "    from orders\n"
            "    inner join customers as customer\n"
            "    let:\n        big = amount > 10\n"
            '    where big and customer.name != ""\n'
            "    select:\n        order_id = orders.id\n        name\n"
            "    order by:\n        customer.id desc\n"
        )
    )
    checks, _ = run.checks()
    query = run.relation("q")
    info = checks.facts[query]
    assert (checks.diagnostics, checks.reads) == ((), ())
    assert sorted(
        (
            leaf.span.line,
            leaf.span.column,
            ".".join(leaf.parts) if isinstance(leaf, DottedNameExpr) else leaf.name,
            read.input,
            read.field,
        )
        for leaf, read in info.field_reads.items()
        if isinstance(leaf, (DottedNameExpr, NameExpr))
    ) == [
        (22, 15, "amount", 0, "amount"),
        (23, 19, "customer.name", 1, "name"),
        (25, 20, "orders.id", 0, "id"),
        (26, 9, "name", 1, "name"),
        (28, 9, "customer.id", 1, "id"),
    ]
    rows = run.rows("q")
    assert len(info.field_reads) == 5
    assert rows is not None and info.row_schema == rows.tail
    assert [(item.ordinal, item.binding) for item in info.inputs] == [
        (0, "orders"),
        (1, "customer"),
    ]
    (join,) = info.joins
    (equality,) = join.equalities
    relationship = run.script.relationships[0].base_match
    assert relationship is not None
    comparison = cast(ComparisonExpr, relationship.expression)
    integer = ResolvedType("Int", TypeKind.BUILTIN)
    assert join == JoinInfo(
        ordinal=1,
        clause=query.join_clauses[0],
        kind=AuthoredJoinKind.INNER,
        mode="M1",
        source_input=0,
        source_inferred=True,
        target_input=1,
        relationship="order_customer",
        step=None,
        equalities=(
            JoinEqualityInfo(
                left=JoinFieldRef(input=0, field="customer_id"),
                right=JoinFieldRef(input=1, field="id"),
                left_type=ValueType(integer, EffectiveNullability.NULLABLE),
                right_type=ValueType(integer, EffectiveNullability.NON_NULL),
                comparison=comparison,
                left_operand=cast(DottedNameExpr, comparison.left),
                right_operand=cast(DottedNameExpr, comparison.right),
            ),
        ),
        condition=None,
        null_extends=(),
    )
    assert equality.left_operand is comparison.left


def test_single_file_self_join_reads_keep_their_inputs_apart() -> None:
    run = run_joins(
        _joined_query(
            "    from customers\n    left join customers as peer:\n"
            "        from customers\n"
            "        on peer.region_id == customers.region_id\n"
            "    select:\n        customer_id = customers.id\n        peer_id = peer.id\n"
        )
    )
    checks, _ = run.checks()
    info = checks.facts[run.relation("q")]
    assert sorted(
        (leaf.span.line, leaf.span.column, read.input, read.field)
        for leaf, read in info.field_reads.items()
    ) == [
        (22, 12, 1, "region_id"),
        (22, 30, 0, "region_id"),
        (24, 23, 0, "id"),
        (25, 19, 1, "id"),
    ]
    assert info.joins[0].null_extends == (1,)


def test_single_file_join_reads_inside_def_arguments_resolve() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n    cross join regions as r: from orders\n"
            "    where inc(r.id) > 1\n"
            "    select:\n        bumped = inc(orders.amount)\n"
            "def inc(x: Int not null) -> Int nullable: return x + 1\n"
        )
    )
    checks, _ = run.checks()
    info = checks.facts[run.relation("q")]
    assert sorted(
        (leaf.span.line, leaf.span.column, read.input, read.field)
        for leaf, read in info.field_reads.items()
    ) == [(21, 15, 1, "id"), (23, 22, 0, "amount")]


def test_single_file_join_equalities_follow_the_written_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(joins, "resolve_join_relationship", resolve_by_declaration)
    run = run_joins(
        _joined_query(
            "    from customers\n"
            "    inner join customers as peer: via referral: referee -> referrer\n"
            "    select:\n        x = customers.id\n"
            "relationship referral:\n    endpoint referrer: customers\n"
            "    endpoint referee: customers\n    on referrer.region_id == referee.id\n"
        )
    )
    checks, _ = run.checks()
    (join,) = checks.facts[run.relation("q")].joins
    (equality,) = join.equalities
    comparison = equality.comparison
    # The source plays `referee`, the right operand of the declared conjunct.
    assert (join.mode, join.source_inferred, join.step) == (
        "M2",
        True,
        run.relation("q").join_clauses[0].traversal_steps[0],
    )
    assert (equality.left, equality.right) == (
        JoinFieldRef(input=0, field="id"),
        JoinFieldRef(input=1, field="region_id"),
    )
    assert (equality.left_operand, equality.right_operand) == (
        comparison.right,
        comparison.left,
    )
    assert (equality.left_type.nullability, equality.right_type.nullability) == (
        EffectiveNullability.NON_NULL,
        EffectiveNullability.NULLABLE,
    )


def test_single_file_join_reads_that_fail_say_why(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(joins, "resolve_join_relationship", resolve_by_declaration)
    run = run_joins(
        _joined_query(
            "    from orders\n"
            "    inner join customers as customer\n"
            "    where id > 1\n"
            "    select:\n"
            "        nope = customer.nope\n"
            "        rel = customers.name\n"
            "        other = elsewhere.x\n"
            "        deep = customer.name.x\n"
            "        bare = nothing\n"
        )
    )
    checks, _ = run.checks()
    assert located(checks.reads) == [
        ("PIE-S2335", "Ambiguous field: id; write orders.id or customer.id", 21, 11),
        ("PIE-S2102", "Unknown field: customer.nope", 23, 16),
        (
            "PIE-S2102",
            "Unknown field: customers.name; customers names a relation, not a binding: write customer.name",
            24,
            15,
        ),
        ("PIE-S2102", "Unknown field: elsewhere.x", 25, 17),
        ("PIE-S2102", "Unknown field: customer.name.x", 26, 16),
    ]
    assert (checks.facts, checks.diagnostics) == ({}, ())
    # Each failed read keeps exactly its own diagnostic, at the read; a bare
    # name that no binding has, and every other code, stay as they are.
    at = {read.message: read.location for read in checks.reads}
    elsewhere = SourceLocation(path="joins.pietto", line=27, column=16)

    def found(code: str, message: str, location: SourceLocation) -> Diagnostic:
        return Diagnostic(
            code=code, severity=Severity.ERROR, message=message, location=location
        )

    ambiguous = at["Ambiguous field: id; write orders.id or customer.id"]
    nope = at["Unknown field: customer.nope"]
    before = [
        found("PIE-S2102", "Unknown field: id", ambiguous),
        found("PIE-S2105", "stand-in", ambiguous),
        found("PIE-S2102", "Unknown field: customer.nope", nope),
        found("PIE-S2102", "Unknown field: customer.nope", nope),
        found("PIE-S2102", "Unknown field: nothing", elsewhere),
    ]
    assert joins.join_post_pass(before, checks) == [
        before[1],
        before[4],
        *checks.reads,
    ]


def test_single_file_join_post_pass_drops_reads_of_relations_it_does_not_analyse() -> (
    None
):
    run = run_joins(
        _joined_query(
            "    from orders\n    cross join regions as r: from orders\n"
            "    select:\n        n = row_number() window:\n            order by:\n"
            "                orders.id\n"
            "query plain:\n    from orders\n    select:\n        x = orders.id\n"
        )
    )
    checks, _ = run.checks()
    query = run.relation("q")
    assert checks.unanalysed == (query.span,)

    def at(code: str, line: int, column: int) -> Diagnostic:
        return Diagnostic(
            code=code,
            severity=Severity.ERROR,
            message="stand-in",
            location=SourceLocation(path="joins.pietto", line=line, column=column),
        )

    before = [
        at("PIE-S2102", 22, 9),
        at("PIE-S2380", 24, 17),
        at("PIE-S2334", 22, 13),
        at("PIE-S2102", 28, 13),
    ]
    assert joins.join_post_pass(before, checks) == [before[2], before[3]]


def test_single_file_join_with_an_unknown_input_row_says_so_unless_explained() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n    cross join tally as t: from orders\n"
            + _SELECT_ID
            + "table tally:\n    from orders\n    select:\n        id\n"
        )
    )
    tally = run.relation("tally")
    query = run.relation("q")
    rows = {**run.model.relation_row_schemas, tally: RowSchema(is_unknown=True)}
    checks, _ = run.checks(rows)
    assert (checks.facts, checks.reads, checks.unanalysed) == ({}, (), (query.span,))
    unexplained = [
        (
            "PIE-S2334",
            "A JOIN over tally, whose fields are not known, is not available in "
            "single files yet.",
            20,
            5,
        )
    ]
    assert located(joins.join_post_pass([], checks)) == unexplained
    # An ERROR inside a relation it reads explains the unknown row.
    explained = Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message="stand-in",
        location=SourceLocation(path="joins.pietto", line=24, column=5),
    )
    assert joins.join_post_pass([explained], checks) == [explained]
    warning = replace(explained, severity=Severity.WARNING)
    assert located(joins.join_post_pass([warning], checks))[1:] == unexplained
    orders = cast(SourceDef, run.model.relation_symbols["orders"])
    sources = {**run.model.source_row_schemas, orders: RowSchema(is_unknown=True)}
    from_checks = joins.check_join_semantics(
        run.script,
        run.structures,
        relation_symbols=run.model.relation_symbols,
        source_row_schemas=sources,
        relation_row_schemas=run.model.relation_row_schemas,
        expression_value_types={},
        type_expansions=run.model.type_expansions,
    )
    assert located(joins.join_post_pass([], from_checks)) == [
        (
            "PIE-S2334",
            "A JOIN over orders, whose fields are not known, is not available in "
            "single files yet.",
            20,
            5,
        )
    ]


def test_single_file_join_over_a_join_relation_whose_row_is_unknown_says_so_once() -> (
    None
):
    run = run_joins(
        _joined_query(
            "    from orders\n    cross join middle as m: from orders\n"
            + _SELECT_ID
            + "table middle:\n    from orders\n    cross join tally as t: from orders\n"
            "    select:\n        y = orders.id\n"
            "table tally:\n    from orders\n    select:\n        id\n"
        )
    )
    query, middle, tally = (run.relation(name) for name in ("q", "middle", "tally"))
    unknown = RowSchema(is_unknown=True)
    checks, _ = run.checks(
        {**run.model.relation_row_schemas, tally: unknown, middle: unknown}
    )
    assert run.diagnostics == []
    assert (checks.facts, checks.unanalysed) == ({}, (query.span, middle.span))
    # middle says why its row is unknown; q, which reads middle, adds nothing.
    assert located(joins.join_post_pass([], checks)) == [
        (
            "PIE-S2334",
            "A JOIN over tally, whose fields are not known, is not available in "
            "single files yet.",
            25,
            5,
        )
    ]


def test_single_file_join_input_rows_are_built_for_the_given_relations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(joins, "resolve_join_relationship", resolve_by_declaration)
    run = run_joins(
        _joined_query(
            "    from orders\n    semi join customers as s: from orders\n"
            "    cross join regions as r: from orders\n"
            + _SELECT_ID
            + "query bad:\n    from orders\n    cross join nowhere as n: from orders\n"
            + _SELECT_ID
            + "query plain:\n    from orders\n"
            + _SELECT_ID
            + "query derived:\n    from orders\n    cross join tally as t: from orders\n"
            + _SELECT_ID
            + "table tally:\n    from orders\n    select:\n        total = orders.amount\n"
        )
    )
    query, bad, derived, tally = (
        run.relation(name) for name in ("q", "bad", "derived", "tally")
    )
    total = RowField(
        "total", ResolvedType("Int", TypeKind.BUILTIN), EffectiveNullability.NULLABLE
    )
    sources = run.model.source_row_schemas
    relations = {
        **run.model.relation_row_schemas,
        tally: RowSchema(fields={"total": total}),
    }
    every = joins.joined_input_rows(
        run.script.definitions,
        run.structures,
        source_row_schemas=sources,
        relation_row_schemas=relations,
    )
    assert list(every) == [query, bad, derived]
    assert every[bad] == RowSchema(is_unknown=True)
    assert list(every[query].fields) == [
        "orders.id",
        "orders.customer_id",
        "orders.amount",
        "r.id",
        "r.label",
    ]
    # One relation builds only its own row; a table input's row is the
    # relation row it is given.
    only = joins.joined_input_rows(
        (derived,),
        run.structures,
        source_row_schemas=sources,
        relation_row_schemas=relations,
    )
    assert list(only) == [derived]
    assert only[derived] == every[derived]
    assert list(only[derived].fields)[3:] == ["t.total"]
    assert only[derived].fields["t.total"] == replace(total, name="t.total")


def test_single_file_join_structures_resolve_every_join_target_for_cycles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(joins, "resolve_join_relationship", resolve_by_declaration)
    run = run_joins(
        _joined_query(
            "    from orders\n    inner join customers as c\n"
            "    cross join tally as t: from orders\n"
            + _SELECT_ID
            + "query bad:\n    from nowhere\n    cross join q as again: from nowhere\n"
            "    cross join missing as m: from nowhere\n"
            "    cross join both as b: from nowhere\n"
            + _SELECT_ID
            + "table tally:\n    from orders\n    select:\n        id\n"
            "query both:\n    union all:\n        from orders\n        from orders\n"
        )
    )
    query, bad = run.relation("q"), run.relation("bad")
    assert located(run.diagnostics) == [
        ("PIE-S2301", "Unknown relation: missing", 27, 5),
        (
            "PIE-S2334",
            f"Set-operation inputs are available {_COMPLETED} them: both",
            28,
            5,
        ),
    ]
    assert list(run.structures) == [query]
    # Every JOIN whose target is a relation, in a relation with a structure
    # or not, in definition and JOIN order.
    assert list(run.join_resolutions) == [*query.join_clauses, bad.join_clauses[0]]
    assert [relation.name for relation in run.join_resolutions.values()] == [
        "customers",
        "tally",
        "q",
    ]
    assert run.join_resolutions[bad.join_clauses[0]] is query


def test_single_file_join_facts_fail_closed_on_a_pair_the_rows_lack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def misread(clause: JoinClause, **arguments: Any) -> object:
        resolved = resolve_by_declaration(clause, **arguments)
        assert not isinstance(resolved, tuple)
        ((_, target_field, comparison, source_operand, target_operand),) = (
            resolved.pairs
        )
        return replace(
            resolved,
            pairs=(("nope", target_field, comparison, source_operand, target_operand),),
        )

    monkeypatch.setattr(joins, "resolve_join_relationship", misread)
    run = run_joins(
        _joined_query("    from orders\n    inner join customers as c\n" + _SELECT_ID)
    )
    checks, _ = run.checks()
    assert (run.diagnostics, list(run.structures)) == ([], [run.relation("q")])
    # No facts, so IR refuses the relation; nothing is reported at check.
    assert (checks.facts, checks.diagnostics, checks.reads) == ({}, (), ())


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "    inner join customers as customer\n"
            '    where customer.name == "x"\n'
            "    select:\n        n = row_number() window:\n"
            "            order by:\n                orders.id\n",
            [
                (
                    "PIE-S2334",
                    "Window functions over JOIN rows are available only when "
                    "an EXPLICIT_MODULES project (schema version 2) completes them.",
                    23,
                    13,
                )
            ],
        ),
        (
            "    inner join customers as customer\n"
            '    where customer.name == "x"\n'
            "    select:\n        n = count()\n"
            "    order by:\n        customer.name\n",
            [
                (
                    "PIE-S2334",
                    "ORDER BY is not available after an ungrouped aggregate over JOIN rows: "
                    "the result has one row; remove `order by`.",
                    24,
                    5,
                )
            ],
        ),
        (
            "    cross join q as customer: from orders\n"
            '    where customer.name == "x"\n'
            "    select:\n        name = customer.name\n",
            [("PIE-S2302", "Relation cycle detected: q -> q", 20, 5)],
        ),
    ),
)
def test_join_phase_a_and_cycles_suppress_only_unavailable_row_reads(
    mode: CheckMode, body: str, expected: list[tuple[str, str, int, int]]
) -> None:
    result = analyze(
        _parse(JOIN_PREFIX + "query q:\n    from orders\n" + body), mode_override=mode
    )
    assert located(result.diagnostics) == expected
    query = cast(QueryDef, result.model.relation_symbols["q"])
    assert query not in result.model.relation_joins
    assert result.model.relation_row_schemas[query].is_unknown


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_join_dependency_fixpoint_types_forward_derived_targets(
    mode: CheckMode,
) -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + """query q:
    from orders
    cross join second as target: from orders
    select:
        n = target.plus + 1
query reader:
    from q
    select:
        n
table second:
    from first
    select:
        plus = base + 1
table first:
    from customers
    select:
        base = id + 1
"""
        ),
        mode_override=mode,
    )
    assert result.diagnostics == ()
    for name, field in (
        ("q", "n"),
        ("reader", "n"),
        ("second", "plus"),
        ("first", "base"),
    ):
        relation = cast(TableDef | QueryDef, result.model.relation_symbols[name])
        schema = result.model.relation_row_schemas[relation]
        assert not schema.is_unknown
        assert schema.fields[field].resolved_type.name == "Int"
        assert schema.fields[field].nullability is EffectiveNullability.UNKNOWN
    query = cast(QueryDef, result.model.relation_symbols["q"])
    assert result.model.relation_joins[query].inputs[1].relation.name == "second"


def test_join_fixpoint_keeps_self_join_occurrences_distinct() -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + """query q:
    from projected
    cross join projected as peer: from projected
    select:
        left_value = projected.value
        right_value = peer.value
table projected:
    from orders
    select:
        value = amount + 1
"""
        )
    )
    assert result.diagnostics == ()
    query = cast(QueryDef, result.model.relation_symbols["q"])
    info = result.model.relation_joins[query]
    assert [info.field_reads[item.expression] for item in query.select_items] == [
        JoinFieldRef(input=0, field="value"),
        JoinFieldRef(input=1, field="value"),
    ]
    assert tuple(result.model.relation_row_schemas[query].fields) == (
        "left_value",
        "right_value",
    )


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_join_group_keys_keep_self_join_identity_through_let_and_outputs(
    mode: CheckMode,
) -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + """query q:
    from customers
    cross join customers as peer: from customers
    let:
        peer_key = peer.id
    group by:
        customers.id
        peer_key
    select:
        customer_id = customers.id
        other_id = peer.id
        n = count()
    satisfying:
        n > 0
    order by:
        other_id
"""
        ),
        mode_override=mode,
    )
    assert result.diagnostics == ()
    query = cast(QueryDef, result.model.relation_symbols["q"])
    assert query.group_by_clause is not None and query.let_clause is not None
    info = result.model.relation_joins[query]
    assert info.field_reads[query.group_by_clause.items[0].key] == JoinFieldRef(
        input=0, field="id"
    )
    assert info.field_reads[query.let_clause.bindings[0].expression] == JoinFieldRef(
        input=1, field="id"
    )
    assert tuple(result.model.relation_row_schemas[query].fields) == (
        "customer_id",
        "other_id",
        "n",
    )


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_join_analyzer_runs_fanout_refusal_after_resolving_reads(
    mode: CheckMode,
) -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + """query q:
    from orders
    cross join customers as customer: from orders
    select:
        n = count(orders.amount)
"""
        ),
        mode_override=mode,
    )
    assert located(result.diagnostics) == [
        (
            "PIE-S2381",
            "An aggregate may read rows repeated by JOIN customer; "
            "group by a unique key of customer whose fields are all not null",
            22,
            13,
        )
    ]


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_join_hidden_binding_reason_is_one_diagnostic_per_read(
    mode: CheckMode, kind: str
) -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + f"""query q:
    from orders
    {kind} join customers as customer:
        from orders
        on customer.id == orders.customer_id
    select:
        n = customer.name
"""
        ),
        mode_override=mode,
    )
    assert located(result.diagnostics) == [
        (
            "PIE-S2102",
            f"Unknown field: customer.name; customer is a {kind.upper()} JOIN binding, "
            "which only its own `on` can read",
            24,
            13,
        )
    ]


def test_join_relation_name_hint_lists_every_visible_binding_in_order() -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + """query q:
    from orders
    cross join customers as first: from orders
    cross join customers as second: from orders
    select:
        n = customers.name
"""
        )
    )
    assert located(result.diagnostics) == [
        (
            "PIE-S2102",
            "Unknown field: customers.name; customers names a relation, not a binding: "
            "write first.name or second.name",
            23,
            13,
        )
    ]


@pytest.mark.parametrize(
    ("kind", "field", "nullable"),
    (
        ("inner", "orders.customer_id", False),
        ("left", "customer.id", True),
        ("right", "orders.id", True),
        ("full", "customer.id", True),
    ),
)
def test_join_output_nullability_reaches_def_parameter_checks(
    kind: str, field: str, nullable: bool
) -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + f"""query q:
    from orders
    {kind} join customers as customer:
        from orders
        on orders.customer_id == customer.id
    select:
        n = inc({field})
def inc(x: Int not null) -> Int nullable: return x + 1
"""
        )
    )
    assert located(result.diagnostics) == (
        [
            (
                "PIE-S2395",
                "Invalid argument for def inc at position 1 (x): "
                "expected Int not null, got Int nullable",
                24,
                13,
            )
        ]
        if nullable
        else []
    )


def test_join_cycle_is_found_even_when_its_written_combination_is_invalid() -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + """query q:
    from orders
    cross join q as peer:
        from orders
        on peer.id == orders.id
    select:
        id = peer.id
"""
        )
    )
    assert located(result.diagnostics) == [
        ("PIE-S2302", "Relation cycle detected: q -> q", 20, 5),
        ("PIE-S2336", "CROSS JOIN cannot have ON or VIA.", 20, 5),
    ]


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_refused_join_window_keeps_unrelated_scalar_errors(mode: CheckMode) -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + """query q:
    from orders
    cross join customers as customer: from orders
    select:
        n = row_number() window:
            order by:
                orders.id
        bad = frob(1)
"""
        ),
        mode_override=mode,
    )
    assert located(result.diagnostics) == [
        (
            "PIE-S2334",
            "Window functions over JOIN rows are available only when "
            "an EXPLICIT_MODULES project (schema version 2) completes them.",
            22,
            13,
        ),
        ("PIE-S2103", "Unknown function: frob", 25, 15),
    ]
