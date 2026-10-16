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
    assert on_result.ast is not None and not on_result.diagnostics
    assert any(d.code == "PIE-S2334" for d in analyze(on_result.ast).diagnostics)


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
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in scalar.diagnostics
    ] == [("PIE-S2102", f"Unknown field: customer.id{_JOIN_BINDING}", 12, 9)]


_COMPLETES = "only when an EXPLICIT_MODULES project (schema version 2) completes"


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "query q:\n    from orders\n    right join customers as customer:\n"
            "        from orders\n        on orders.id == customer.id\n"
            "    select:\n        x = orders.id\n",
            [
                (f"RIGHT JOIN is available {_COMPLETES} it.", 10, 5),
                (f"JOIN-local ON is available {_COMPLETES} it.", 12, 9),
            ],
        ),
        (
            "query q:\n    from orders\n    cross join customers as customer:\n"
            "        from orders\n    select:\n        x = orders.id\n",
            [(f"CROSS JOIN is available {_COMPLETES} it.", 10, 5)],
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
def test_single_file_join_and_set_refusals_point_to_explicit_modules(
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


_JOIN_BINDING = (
    "; JOIN binding fields are not available in single-file mode "
    "(use an EXPLICIT_MODULES project)"
)


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "    select:\n        n = customer.name\n",
            [("customer.name", 13, 13)],
        ),
        (
            '    where customer.name == "x"\n    select:\n        id\n',
            [("customer.name", 12, 11)],
        ),
        (
            "    group by:\n        customer.name\n    select:\n        n = count()\n",
            [("customer.name", 13, 9)],
        ),
        (
            "    let:\n        nm = customer.name\n    select:\n        id\n",
            [("customer.name", 13, 14)],
        ),
        (
            "    select:\n        id\n    order by:\n        customer.name\n",
            [("customer.name", 15, 9)],
        ),
        (
            "    select:\n        id\n        r = row_number() window:\n"
            "            partition by:\n                customer.name\n"
            "            order by:\n                id\n",
            [("customer.name", 16, 17)],
        ),
        (
            "    select:\n        a = customer.nope\n        b = orders.nope\n",
            [("customer.nope", 13, 13), ("orders.nope", 14, 13)],
        ),
        ("    select:\n        name\n", [("name", 13, 9)]),
    ),
)
def test_single_file_join_binding_fields_say_why_they_are_unknown(
    body: str,
    expected: list[tuple[str, int, int]],
) -> None:
    semantic = analyze(
        _parse(
            "shape Order:\n"
            "    id: Int not null\n"
            "shape Customer:\n"
            "    id: Int not null\n"
            "    name: Text not null\n"
            'source orders: Order is postgres.table("orders")\n'
            'source customers: Customer is postgres.table("customers")\n'
            "query joined:\n"
            "    from orders\n"
            "    inner join customers as customer:\n"
            "        from orders\n" + body
        )
    )
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in semantic.diagnostics
    ] == [
        (
            "PIE-S2102",
            f"Unknown field: {name}"
            # A field the JOIN target lacks, such as customer.nope, stays bare.
            + (_JOIN_BINDING if name in ("customer.id", "customer.name") else ""),
            line,
            column,
        )
        for name, line, column in expected
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
            [],
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
                    "PIE-S2334",
                    "SEMI JOIN is available only when an EXPLICIT_MODULES project "
                    "(schema version 2) completes it.",
                    22,
                    5,
                ),
                ("PIE-S2335", "Unknown JOIN source binding: b", 25, 5),
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
            [("PIE-S2335", "Ambiguous JOIN source binding: b", 26, 5)],
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
                    "PIE-S2335",
                    "JOIN VIA steps do not connect: a step ends at b_rows and the "
                    "next starts at a_rows",
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


@pytest.mark.parametrize(
    ("join", "field", "hinted"),
    (
        ("right join customers as customer", "customer.name", True),
        ("full join customers as customer", "customer.name", True),
        ("cross join customers as customer", "customer.name", True),
        # A project does not expose SEMI or ANTI binding fields either.
        ("semi join customers as customer", "customer.name", False),
        ("anti join customers as customer", "customer.name", False),
        # A binding named like the FROM input is not singled out.
        ("inner join customers as orders", "orders.nope", False),
        # Nor is a binding name two JOINs share: it has no single target.
        (
            "inner join customers as customer:\n        from orders\n"
            "    left join customers as customer",
            "customer.name",
            False,
        ),
    ),
)
def test_join_binding_hint_follows_the_kinds_a_project_exposes(
    join: str, field: str, hinted: bool
) -> None:
    on = (
        ""
        if join.startswith(("cross", "inner"))
        else "        on orders.id == customer.id\n"
    )
    semantic = analyze(
        _parse(
            "shape Order:\n"
            "    id: Int not null\n"
            "shape Customer:\n"
            "    id: Int not null\n"
            "    name: Text not null\n"
            'source orders: Order is postgres.table("orders")\n'
            'source customers: Customer is postgres.table("customers")\n'
            f"query joined:\n    from orders\n    {join}:\n        from orders\n"
            f"{on}    select:\n        n = {field}\n"
        )
    )
    assert [
        item.message for item in semantic.diagnostics if item.code == "PIE-S2102"
    ] == [f"Unknown field: {field}" + (_JOIN_BINDING if hinted else "")]


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
    # An earlier binding without concrete authority leaves the lookup blocked.
    ledger = _inferred_ledger(inferred, "blocked_input")
    blocked = failed("blocked_input")
    assert [issue.kind for issue in blocked.issues] == [kinds.BLOCKED_SOURCE_BINDING]
    assert blocked.issues[0].causes == (ledger.bindings[1],)


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
    """Single-file checks do not resolve JOIN sources or roles either way."""
    head = _INFERENCE.split("query chain_inferred:")[0]
    for body in (
        "query q:\n    from employees\n    inner join departments as d\n"
        "    left join sites as s: via located_at\n    select:\n        id\n",
        "query q:\n    from employees\n    inner join departments as d:\n"
        "        from employees\n    left join sites as s:\n        from d\n"
        "        via located_at: departments -> sites\n    select:\n        id\n",
    ):
        script = _parse(head + body)
        semantic = analyze(script)
        assert semantic.diagnostics == ()
        assert [item.code for item in build_ir(script, semantic.model).diagnostics] == [
            "PIE-I1000"
        ]
    # The written parts of an inferred JOIN are still checked.
    written = _parse(
        head + "query q:\n    from employees\n    inner join departments as d\n"
        "    left join sites as s: via nosuch\n    select:\n        id\n"
    )
    assert [(d.code, d.message) for d in analyze(written).diagnostics] == [
        ("PIE-S2335", "Unknown relationship in JOIN VIA: nosuch")
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
    ]
