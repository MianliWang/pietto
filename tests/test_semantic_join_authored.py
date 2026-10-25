from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

import pytest

from pietto._project import check as project_check
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowFieldNullability,
    build_empty_project_semantic_result,
)
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto._project.project_join_conditions import ProjectJoinConditionState
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import (
    ProjectIRAllocationState,
    ProjectIRNonConcreteSingleRelationFragment,
    build_project_ir_single_relation_fragment,
)
from pietto._project.project_ir_pipeline import build_project_ir_pipeline
from pietto._project.project_ir_verification import ProjectIRVerificationStatus
from pietto.ast_nodes import AuthoredJoinKind, QueryDef, Script, TableDef
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.ast_nodes import (
    ComparisonExpr,
    DottedNameExpr,
    JoinClause,
    NameExpr,
    SourceDef,
)
from pietto.ir import build_ir
from pietto.semantic import (
    CheckMode,
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
)
from pietto.semantic.analyzer import analyze_project_namespace
from pietto.semantic.model import (
    JoinFieldRef,
    JoinInfo,
    JoinInputInfo,
    RelationJoinsInfo,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic import joins
from pietto.semantic.join_relationships import (
    JoinBindingView,
    ResolvedJoinRelationship,
)
from _pietto_semantic_joins import JOIN_PREFIX, located, run_joins

_COMPLETES = "only when an EXPLICIT_MODULES project (schema version 2) completes"
_SAME_FILE_READ = (
    "`{0}` is a {1} of this file; single-file SQL reads it by name, so the SQL "
    "runs only where the database already has a relation named {0} (an "
    "EXPLICIT_MODULES project emits it as a CTE)"
)


def _same_file_read(
    name: str, kind: str, line: int, column: int
) -> tuple[str, Severity, str, int, int]:
    """The PIE-S2382 warning at a single-file read of the same-file `name`."""
    return (
        "PIE-S2382",
        Severity.WARNING,
        _SAME_FILE_READ.format(name, kind),
        line,
        column,
    )


def _graded(diagnostics: object) -> list[tuple[str, Severity, str, int, int]]:
    return [
        (
            item.code,
            item.severity,
            item.message,
            item.location.line,
            item.location.column,
        )
        for item in cast(tuple[Diagnostic, ...], diagnostics)
    ]


def _source() -> str:
    return """shape ARow:
    id: Int
    b_id: Int
    c_id: Int
shape BRow:
    id: Int
    c_id: Int
    b_key = unique(id)
shape CRow:
    id: Int
    c_key = unique(id)
shape DRow:
    id: Int
source a_rows: ARow = postgres.table("a")
source b_rows: BRow = postgres.table("b")
source c_rows: CRow = postgres.table("c")
source d_rows: DRow = postgres.table("d")
relationship ab(a: ARow, b: BRow):
    a.b_id == b.id
relationship bc(b: BRow, c: CRow):
    b.c_id == c.id
relationship ac(a: ARow, c: CRow):
    a.c_id == c.id
query explicit_one:
    from a_rows
    let b = b_rows
    inner join b on ab(a_rows, b)
    select:
        id
query explicit_multi:
    from a_rows
    let b = b_rows
    left join b on ab(a_rows, b)
    let c = c_rows
    left join c on bc(b, c)
    select:
        id
query branching:
    from a_rows
    let b = b_rows
    inner join b on ab(a_rows, b)
    let c = c_rows
    left join c on ac(a_rows, c)
    select:
        id
query repeated_inputs:
    from a_rows
    let first_b = b_rows
    inner join first_b on ab(a_rows, first_b)
    let second_b = b_rows
    inner join second_b on ab(a_rows, second_b)
    select:
        id
query joined_target:
    from a_rows
    let joined = explicit_one
    inner join joined on True
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
    completed: Any


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    root = tmp_path_factory.mktemp("authored-joins")
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(_source(), encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    semantic = build_empty_project_semantic_result(parsed)
    semantic_facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert semantic_facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    pipeline = build_project_ir_pipeline(
        semantic_result=semantic,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    completed = build_project_completed_semantic_result(semantic)
    return _Built(semantic=semantic, plan=plan, pipeline=pipeline, completed=completed)


def _conditions(built: _Built, name: str) -> tuple[Any, ...]:
    return tuple(
        condition
        for condition in built.completed.roots.join_conditions.entries
        if condition.ledger.owner.definition.name == name
    )


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
        "    let customer = customers\n"
        "    inner join customer on orders.customer_id == customer.id\n\n"
        "    let region = regions\n"
        "    left join region on customer.region_id == region.id\n\n"
        "    select:\n"
        "        id\n",
        path="ordered-joins.pietto",
    )
    relation = cast(QueryDef, script.definitions[0])
    assert tuple(item.kind for item in relation.join_clauses) == (
        AuthoredJoinKind.INNER,
        AuthoredJoinKind.LEFT,
    )
    assert tuple(item.name for item in relation.naming_declarations) == (
        "customer",
        "region",
    )
    assert tuple(
        (item.target_relation_name, item.target_binding_name, item.source_binding_name)
        for item in relation.join_clauses
    ) == (("customer", "customer", None), ("region", "region", None))
    first, second = relation.join_clauses
    assert first is not second
    assert first.span.path == second.span.path == "ordered-joins.pietto"
    assert (first.span.line, first.span.column, first.span.end_line) == (5, 5, 5)
    assert (second.span.line, second.span.column, second.span.end_line) == (8, 5, 8)
    assert all(
        item.uses_named_input and item.on_clause is not None for item in (first, second)
    )
    join_free = cast(
        TableDef,
        _parse("table plain:\n    from orders\n    select:\n        id\n").definitions[
            0
        ],
    )
    assert join_free.join_clauses == ()
    for identifier in ("inner", "left", "join", "via"):
        assert _parse(f"type {identifier} = Int\n").definitions[0].name == identifier


@pytest.mark.parametrize("kind", ("mark", "single"))
def test_unsupported_join_kinds_fail_closed(kind: str) -> None:
    source = (
        "query result:\n    from orders\n    let customer = customers\n"
        f"    {kind} join customer on True\n    select:\n        id\n"
    )
    result = parse_source(source, path=f"{kind}.pietto")
    assert result.ast is None and result.diagnostics
    # Only the JOIN kind differs from a program that parses.
    (join,) = cast(
        QueryDef, _parse(source.replace(f"{kind} join", "inner join")).definitions[0]
    ).join_clauses
    assert join.kind is AuthoredJoinKind.INNER


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


def test_named_join_inputs_keep_branching_repetition_and_left_null_identity(
    built: _Built,
) -> None:
    (one,) = _conditions(built, "explicit_one")
    multi_first, multi_last = _conditions(built, "explicit_multi")
    branch_first, branch_last = _conditions(built, "branching")
    repeated_first, repeated_second = _conditions(built, "repeated_inputs")
    for condition in (
        one,
        multi_first,
        multi_last,
        branch_first,
        branch_last,
        repeated_first,
        repeated_second,
    ):
        assert condition.ready and condition.mode == "M3"
        assert condition.use.clause.uses_named_input
        assert len(condition.mandatory_equalities) == 1
    assert (
        multi_first.use.clause.kind
        is multi_last.use.clause.kind
        is AuthoredJoinKind.LEFT
    )
    assert branch_first.use.clause.kind is AuthoredJoinKind.INNER
    assert branch_last.use.clause.kind is AuthoredJoinKind.LEFT
    for condition in (branch_first, branch_last):
        predicate = condition.environment.predicate_expression
        assert predicate is not None
        (call,) = predicate.calls
        assert call.arguments[0].occurrence is condition.ledger.bindings[0].site
        assert call.arguments[1].occurrence is condition.use.clause
        (equality,) = condition.mandatory_equalities
        assert equality.left.binding is condition.ledger.bindings[0]
        assert equality.right.binding is condition.use.target_binding

    first = repeated_first.environment.predicate_expression.calls[0]
    second = repeated_second.environment.predicate_expression.calls[0]
    assert first.template.declaration is second.template.declaration
    assert first.arguments[1].relation is second.arguments[1].relation
    assert first.arguments[1].occurrence is repeated_first.use.clause
    assert second.arguments[1].occurrence is repeated_second.use.clause
    assert first.arguments[1].occurrence is not second.arguments[1].occurrence
    assert repeated_first.use.identity != repeated_second.use.identity
    assert repeated_first.use.target_binding is repeated_first.ledger.bindings[1]
    assert repeated_second.use.target_binding is repeated_first.ledger.bindings[2]
    assert (
        repeated_first.use.target_binding.output
        is repeated_second.use.target_binding.output
    )

    left, right = (reference.target for reference in multi_last.references)
    assert left is not None and right is not None
    assert left.binding is multi_first.use.target_binding
    assert left.nullability is ProjectRowFieldNullability.NULLABLE
    assert left.null_extensions == (multi_first.use.identity,)
    assert right.binding is multi_last.use.target_binding
    assert right.nullability is ProjectRowFieldNullability.NON_NULL
    with pytest.raises(ValueError, match="exact"):
        replace(one, use=repeated_first.use)
    with pytest.raises(ValueError, match="output must match"):
        replace(one.ledger.bindings[0], output=one.use.target_binding.output)


def test_unavailable_join_target_keeps_its_exact_failed_producer(built: _Built) -> None:
    (condition,) = _conditions(built, "joined_target")
    # The unavailable named input is reported as an error, so the condition is
    # INVALID, never READY.
    assert condition.state is ProjectJoinConditionState.INVALID and not condition.ready
    target = condition.use.target_binding
    assert condition.environment.blocked_bindings == (target,)
    assert target.output is None and target.target is not None
    assert (
        target.target.target_occurrence.definition
        is _fact(built, "explicit_one").owner.definition
    )
    clause = condition.use.clause
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in condition.diagnostics
    ] == [
        (
            "PIE-S2335",
            "JOIN pre-match input or relationship authority is unavailable.",
            clause.span.line,
            clause.span.column,
        )
    ]


def test_single_file_set_refusals_keep_both_operations_and_downstream_inputs() -> None:
    semantic = analyze(
        _parse(
            "shape Order:\n    id: Int\n"
            "shape Customer:\n    id: Int\n"
            'source orders: Order = postgres.table("orders")\n'
            'source customers: Customer = postgres.table("customers")\n'
            "\nquery both:\n    union all:\n        from orders\n        from orders\n"
            "query r:\n    from both\n    select:\n        id\n"
        )
    )
    completes = "only when an EXPLICIT_MODULES project (schema version 2) completes"
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in semantic.diagnostics
    ] == [
        ("PIE-S2334", f"Set operations are available {completes} them.", 9, 5),
        (
            "PIE-S2334",
            f"Set-operation inputs are available {completes} them: both",
            13,
            5,
        ),
    ]


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
        "    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
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
            "    let other = rows\n"
            "    inner join other on rows.id == other.id\n"
            "    select:\n"
            "        id\n"
        ).definitions[0],
    ).join_clauses[0]
    definition = cast(QueryDef, fact.owner.definition)
    assert fact.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert definition.join_clauses == ()
    object.__setattr__(definition, "join_clauses", (clause,))
    with pytest.raises(ValueError, match="cannot construct a concrete"):
        build_project_ir_single_relation_fragment(
            semantic=fact,
            attribution=attribution,
            allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
        )


TYPED = (
    "shape Order:\n    id: Int\n"
    "shape Customer:\n    id: Int\n    name: Text\n"
    'source orders: Order = postgres.table("orders")\n'
    'source customers: Customer = postgres.table("customers")\n'
)

JOINED = (
    TYPED + "query joined:\n    from orders\n    let customer = customers\n"
    "    inner join customer on True\n"
)

FIELDS = {
    "select_known": "    select:\n        n = customer.name\n",
    "where_known_bare_id": '    where customer.name == "x"\n    select:\n        id\n',
    "group_known": "    group by:\n        customer.name\n    select:\n        n = count()\n",
    "let_known_bare_id": "    let nm = customer.name\n    select:\n        id\n",
    "order_known_bare_id": "    select:\n        id\n    order by:\n        customer.name\n",
    "window_known_bare_id": (
        "    select:\n        id\n        r = row_number() window(\n"
        "            partition by customer.name\n            order by id)\n"
    ),
    "both_missing": "    select:\n        a = customer.nope\n        b = orders.nope\n",
    "bare_unique": "    select:\n        name\n",
}

FIELD_EXPECTED = {
    "select_known": [],
    "where_known_bare_id": [
        (
            "PIE-S2335",
            "error",
            "Ambiguous field: id; write orders.id or customer.id",
            14,
            9,
            14,
            11,
        )
    ],
    "group_known": [],
    "let_known_bare_id": [
        (
            "PIE-S2335",
            "error",
            "Ambiguous field: id; write orders.id or customer.id",
            14,
            9,
            14,
            11,
        )
    ],
    "order_known_bare_id": [
        (
            "PIE-S2335",
            "error",
            "Ambiguous field: id; write orders.id or customer.id",
            13,
            9,
            13,
            11,
        )
    ],
    "window_known_bare_id": [
        (
            "PIE-S2334",
            "error",
            "Window functions over JOIN rows are available only when an EXPLICIT_MODULES project (schema version 2) completes them.",
            14,
            13,
            16,
            25,
        )
    ],
    "both_missing": [
        ("PIE-S2102", "error", "Unknown field: customer.nope", 13, 13, 13, 26),
        ("PIE-S2102", "error", "Unknown field: orders.nope", 14, 13, 14, 24),
    ],
    "bare_unique": [],
}


def _diagnostics(
    source: str,
) -> list[tuple[str, str, str, int, int, int | None, int | None]]:
    result = analyze(_parse(source, path="join-cases.pietto"))
    assert all(item.location.path == "join-cases.pietto" for item in result.diagnostics)
    return [
        (
            item.code,
            item.severity.value,
            item.message,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in result.diagnostics
    ]


@pytest.mark.parametrize("case", tuple(FIELDS))
def test_single_file_join_field_positions_keep_complete_diagnostics(case: str) -> None:
    assert _diagnostics(JOINED + FIELDS[case]) == FIELD_EXPECTED[case]


def test_single_file_join_without_shapes_reports_every_unknown_input() -> None:
    source = (
        'source orders = postgres.table("orders")\n'
        'source customers = postgres.table("customers")\n'
        "query joined:\n    from orders\n    let customer = customers\n"
        "    inner join customer on True\n    select:\n        id\n"
        "        n = customer.name\n"
    )
    assert _diagnostics(source) == [
        (
            "PIE-S2303",
            "warning",
            "Source orders has no bound shape; row schema is unknown",
            1,
            1,
            1,
            41,
        ),
        (
            "PIE-S2303",
            "warning",
            "Source customers has no bound shape; row schema is unknown",
            2,
            1,
            2,
            47,
        ),
        (
            "PIE-S2334",
            "error",
            "A JOIN over orders, whose fields are not known, is not available in single files yet; give source orders a shape.",
            6,
            5,
            6,
            32,
        ),
        (
            "PIE-S2334",
            "error",
            "A JOIN over customers, whose fields are not known, is not available in single files yet; give source customers a shape.",
            6,
            5,
            6,
            32,
        ),
    ]


TARGETS = (
    "shape ARow:\n    id: Int\n    b_id: Int\n"
    "shape BRow:\n    id: Int\n    c_id: Int\n"
    "shape CRow:\n    id: Int\n"
    'source a_rows: ARow = postgres.table("a")\n'
    'source b_rows: BRow = postgres.table("b")\n'
    'source c_rows: CRow = postgres.table("c")\n'
    "relationship ab(a: ARow, b: BRow):\n    a.b_id == b.id\n"
    "relationship bc(b: BRow, c: CRow):\n    b.c_id == c.id\n"
    "query joined:\n    from a_rows\n"
)

INPUTS = {
    "direct": "    let b = b_rows\n    inner join b on ab(a_rows, b)\n",
    "left_chain": (
        "    let b = b_rows\n    left join b on ab(a_rows, b)\n"
        "    let c = c_rows\n    left join c on bc(b, c)\n"
    ),
    "inner_chain": (
        "    let b = b_rows\n    inner join b on ab(a_rows, b)\n"
        "    let c = c_rows\n    inner join c on bc(b, c)\n"
    ),
    "unknown_input": "    let b = b_rows\n    inner join b on nowhere.b_id == b.id\n",
    # An `any` input (a SEMI JOIN before S6) is readable only inside its `any`.
    "hidden_semi": (
        "    let b = b_rows\n    where any(ab(a_rows, b) for b in b)\n"
        "    let c = c_rows\n    inner join c on bc(b, c)\n"
    ),
    # A later input cannot satisfy an earlier ON.
    "future_input": (
        "    let c = c_rows\n    inner join c on bc(b, c)\n"
        "    let b = b_rows\n    inner join b on ab(a_rows, b)\n"
    ),
    "duplicate_input": (
        "    let b = b_rows\n    inner join b on ab(a_rows, b)\n"
        "    let b = b_rows\n    inner join b on ab(a_rows, b)\n"
        "    let c = c_rows\n    inner join c on bc(b, c)\n"
    ),
    "missing_target": "    inner join nowhere on True\n",
}
INPUT_EXPECTED = {
    "direct": [],
    "left_chain": [],
    "inner_chain": [],
    "unknown_input": [
        (
            "PIE-S2335",
            "error",
            "JOIN ON reference is unknown: nowhere.b_id",
            19,
            21,
            19,
            33,
        )
    ],
    # The refused row argument is the only error: the call of the declared bc
    # is not an unknown function, b is no scalar read and c is this JOIN's input.
    "hidden_semi": [
        (
            "PIE-S2604",
            "error",
            "Unavailable row argument for relationship bc parameter b",
            21,
            24,
            21,
            25,
        )
    ],
    "future_input": [
        (
            "PIE-S2604",
            "error",
            "Unavailable row argument for relationship bc parameter b",
            19,
            24,
            19,
            25,
        )
    ],
    "duplicate_input": [
        ("PIE-S2604", "error", "Duplicate query local name: b", 20, 5, 20, 19),
        ("PIE-S2604", "error", "Ambiguous JOIN input: b", 21, 5, 21, 34),
    ],
}


@pytest.mark.parametrize("case", tuple(INPUTS))
def test_single_file_join_inputs_keep_complete_diagnostics(case: str) -> None:
    source = TARGETS + INPUTS[case] + "    select:\n        n = a_rows.id\n"
    if case == "missing_target":
        parsed = _parse(source, path="join-cases.pietto")
        query = cast(QueryDef, parsed.definitions[-1])
        (join,) = query.join_clauses
        expected = [
            (
                "PIE-S2301",
                "error",
                "Unknown relation: nowhere",
                join.span.line,
                join.span.column,
                join.span.end_line,
                join.span.end_column,
            )
        ]
    else:
        expected = INPUT_EXPECTED[case]
    assert _diagnostics(source) == expected


KIND_INPUTS = {
    "right": (
        "    let customer = customers\n    right join customer on True\n",
        "customer.name",
    ),
    "full": (
        "    let customer = customers\n    full join customer on True\n",
        "customer.name",
    ),
    "cross": (
        "    let customer = customers\n    cross join customer\n",
        "customer.name",
    ),
    # `[not] any` (a SEMI/ANTI JOIN before S6) binds its input only inside it.
    "semi": (
        "    let customer = customers\n    where any(True for customer in customer)\n",
        "customer.name",
    ),
    "anti": (
        "    let customer = customers\n"
        "    where not any(True for customer in customer)\n",
        "customer.name",
    ),
    "same_as_from": (
        "    let orders = customers\n    inner join orders on True\n",
        "orders.nope",
    ),
    "duplicate_name": (
        "    let customer = customers\n    inner join customer on True\n"
        "    let customer = customers\n    left join customer on True\n",
        "customer.name",
    ),
}

KIND_EXPECTED = {
    "right": [],
    "full": [],
    "cross": [],
    "semi": [("PIE-S2102", "error", "Unknown field: customer.name", 13, 13, 13, 26)],
    "anti": [("PIE-S2102", "error", "Unknown field: customer.name", 13, 13, 13, 26)],
    "same_as_from": [
        ("PIE-S2604", "error", "Ambiguous JOIN input: orders", 11, 5, 11, 30)
    ],
    "duplicate_name": [
        ("PIE-S2604", "error", "Duplicate query local name: customer", 12, 5, 12, 29),
        ("PIE-S2604", "error", "Ambiguous JOIN input: customer", 13, 5, 13, 31),
    ],
}


@pytest.mark.parametrize("case", tuple(KIND_INPUTS))
def test_join_binding_visibility_keeps_every_kind_and_name_collision(case: str) -> None:
    joins, field = KIND_INPUTS[case]
    source = (
        TYPED
        + "query joined:\n    from orders\n"
        + joins
        + f"    select:\n        n = {field}\n"
    )
    assert _diagnostics(source) == KIND_EXPECTED[case]


@pytest.mark.parametrize("kind", ("mark", "single"))
def test_unsupported_join_kinds_fail_closed_and_join_local_on_is_admitted(
    kind: str,
) -> None:
    source = (
        "query result:\n"
        "    from orders\n"
        "    let customer = customers\n"
        f"    {kind} join customer on orders.id == customer.id\n"
        "    select:\n"
        "        orders.id\n"
    )
    result = parse_source(source, path=f"{kind}.pietto")
    assert result.ast is None and result.diagnostics
    on_result = parse_source(
        JOIN_PREFIX + source.replace(f"{kind} join", "inner join"),
        path="join-on.pietto",
    )
    assert on_result.ast is not None and not on_result.diagnostics
    assert analyze(on_result.ast).diagnostics == ()


def test_legacy_ir_join_namespace_fails_closed() -> None:
    prefix = (
        "shape Order:\n"
        "    id: Int\n"
        "shape Customer:\n"
        "    id: Int\n"
        'source orders: Order = postgres.table("orders")\n'
        'source customers: Customer = postgres.table("customers")\n'
    )
    source = (
        prefix + "query joined:\n"
        "    from orders\n"
        "    let customer = customers\n"
        "    inner join customer on orders.id == customer.id\n"
        "    select:\n"
        "        orders.id\n"
    )
    script = _parse(source)
    semantic = analyze_project_namespace(script)
    assert semantic.diagnostics == ()
    assert semantic.script is not None
    result = build_ir(semantic.script, semantic.model)
    assert result.ir is None
    assert tuple((item.code, item.message) for item in result.diagnostics) == (
        (
            "PIE-I1000",
            "Missing semantic fact required for IR lowering: resolved JOIN facts",
        ),
    )


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "query q:\n    from orders\n    let customer = customers\n"
            "    right join customer on orders.id == customer.id\n"
            "    select:\n        x = orders.id\n",
            [],
        ),
        (
            "query q:\n    from orders\n    let customer = customers\n"
            "    cross join customer\n    select:\n        x = orders.id\n",
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
            "    id: Int\n"
            "shape Customer:\n"
            "    id: Int\n"
            'source orders: Order = postgres.table("orders")\n'
            'source customers: Customer = postgres.table("customers")\n'
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
        "    let nm = customer.name\n    select:\n        n = nm\n",
        "    select:\n        orders.id\n    order by:\n        customer.name\n",
        "    select:\n        name\n",
    ),
)
def test_single_file_join_binding_fields_resolve_in_each_clause(
    mode: CheckMode, tail: str
) -> None:
    semantic = analyze(
        _parse(
            JOIN_PREFIX + "query q:\n    from orders\n    let customer = customers\n"
            "    inner join customer on order_customer(orders, customer)\n" + tail
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


_JOIN_FACT_SOURCE = """shape Order:
    id: Int
    customer_id: Int
shape Customer:
    id: Int
    name: Text
source orders: Order = postgres.table("orders")
source customers: Customer = postgres.table("customers")
relationship order_customer(o: Order, c: Customer): o.customer_id == c.id
query result:
    from orders
    let customer = customers
    inner join customer on order_customer(orders, customer)
    select:
        customer.name
"""


def test_single_file_join_facts_copy_their_reads_and_default_to_no_joins() -> None:
    script = _parse(_JOIN_FACT_SOURCE)
    orders = cast(SourceDef, script.definitions[2])
    customers = cast(SourceDef, script.definitions[3])
    query = cast(QueryDef, script.definitions[4])
    join = query.join_clauses[0]
    assert join.on_clause is not None
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
                mode="M3",
                source_input=0,
                source_inferred=False,
                target_input=1,
                relationship=None,
                step=None,
                equalities=(),
                condition=join.on_clause.expression,
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
            "    from orders\n    right join nowhere on orders.id == nowhere.id\n"
            + _SELECT_ID,
            [("PIE-S2301", "Unknown relation: nowhere", 20, 5)],
            id="unknown_target",
        ),
        pytest.param(
            "    from orders\n    inner join both on True\n"
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
            "    from orders\n    cross join orders\n" + _SELECT_ID,
            [
                (
                    "PIE-S2335",
                    "JOIN binding cannot have the FROM input's name: orders",
                    20,
                    16,
                )
            ],
            id="binding_named_like_from",
        ),
        pytest.param(
            "    from orders\n    let r = regions\n    cross join r on r.id == orders.id\n"
            + _SELECT_ID,
            [("PIE-S2336", "CROSS JOIN cannot have ON or VIA.", 21, 5)],
            id="cross_with_on",
        ),
        pytest.param(
            "    from orders\n    let r = regions\n    cross join r\n"
            "    select:\n        n = row_number() window(order by orders.id)\n",
            [
                (
                    "PIE-S2334",
                    f"Window functions over JOIN rows are available {_COMPLETED} them.",
                    23,
                    13,
                )
            ],
            id="window_call",
        ),
        pytest.param(
            "    from orders\n    let r = regions\n    cross join r\n"
            "    let w = window(order by orders.id)\n" + _SELECT_ID,
            [
                (
                    "PIE-S2334",
                    f"Window functions over JOIN rows are available {_COMPLETED} them.",
                    22,
                    5,
                )
            ],
            id="named_window",
        ),
        pytest.param(
            "    from orders\n    let r = regions\n    cross join r\n"
            "    select:\n        n = count()\n    order by:\n        orders.id\n",
            [
                (
                    "PIE-S2334",
                    "ORDER BY is not available after an ungrouped aggregate over JOIN rows: "
                    "the result has one row; remove `order by`.",
                    24,
                    5,
                )
            ],
            id="aggregate_order_by",
        ),
        pytest.param(
            "    from tracked\n    let e = events\n    cross join e\n"
            "    select:\n        x = 1\n"
            "table tracked:\n    from events\n    select:\n        id\n"
            'source events = postgres.table("events")\n',
            [
                ("PIE-S2334", _SHAPELESS.format("tracked"), 21, 5),
                ("PIE-S2334", _SHAPELESS.format("events"), 21, 5),
            ],
            id="inputs_without_a_shape",
        ),
        pytest.param(
            "    from events\n    let again = events\n    cross join again\n"
            '    select:\n        x = 1\nsource events = postgres.table("events")\n',
            # One for the FROM input and one for the target, as for two sources.
            [
                ("PIE-S2334", _SHAPELESS.format("events"), 21, 5),
                ("PIE-S2334", _SHAPELESS.format("events"), 21, 5),
            ],
            id="self_join_without_a_shape",
        ),
        pytest.param(
            "    from orders\n    cross join nowhere on orders.id == 1\n" + _SELECT_ID,
            [
                ("PIE-S2301", "Unknown relation: nowhere", 20, 5),
                ("PIE-S2336", "CROSS JOIN cannot have ON or VIA.", 20, 5),
            ],
            id="written_parts_beside_an_unknown_target",
        ),
    ),
)
def test_single_file_join_structure_refuses_each_written_part(
    body: str,
    expected: list[tuple[str, str, int, int]],
) -> None:
    run = run_joins(_joined_query(body))
    assert located(run.diagnostics) == expected
    assert run.structures == {}


def test_single_file_join_structure_resolves_each_input_and_mode() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n"
            "    let c = customers\n"
            "    inner join c on order_customer(orders, c)\n"
            "    let r = regions\n"
            "    left join r on customer_region(c, r)\n"
            "    let s = customers\n"
            '    where any(order_customer(orders, s) and s.name != "" for s in s)\n'
            "    let r2 = regions\n"
            "    right join r2 on r2.id == c.region_id\n"
            "    let r3 = regions\n"
            "    cross join r3\n" + _SELECT_ID
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
        (3, "_pietto_any_1", "customers", False),
        (4, "r2", "regions", True),
        (5, "r3", "regions", True),
    ]
    assert structure.inputs[0].clause is None
    assert all(
        item.clause is clause
        for item, clause in zip(structure.inputs[1:], query.join_clauses, strict=True)
    )
    # Every JOIN reads the row accumulated from the FROM input; a relationship
    # call in `on` is a condition, not a relationship the JOIN resolves.
    assert [
        (
            join.ordinal,
            join.clause is query.join_clauses[join.ordinal - 1],
            join.mode,
            join.source_input,
            join.source_inferred,
            join.relationship,
        )
        for join in structure.joins
    ] == [
        (1, True, "M3", 0, False, None),
        (2, True, "M3", 0, False, None),
        (3, True, "M3", 0, False, None),
        (4, True, "M3", 0, False, None),
        (5, True, "M5", 0, False, None),
    ]


@pytest.mark.parametrize(
    ("later", "inputs"),
    (
        pytest.param(
            "    cross join c\n",
            [("_pietto_any_1", "customers", False), ("c", "customers", True)],
            id="binder_name",
        ),
        pytest.param(
            "    let _pietto_any_1 = regions\n    cross join _pietto_any_1\n",
            [("_pietto_any_2", "customers", False), ("_pietto_any_1", "regions", True)],
            id="generated_name",
        ),
    ),
)
def test_single_file_hidden_existence_binding_takes_no_authored_binding_name(
    later: str, inputs: list[tuple[str, str, bool]]
) -> None:
    """The hidden SEMI JOIN of a JOIN-prefix `any` is bound under a generated
    name no authored binding has: a later JOIN may bind the `any` binder's name,
    and an authored binding of the next generated name moves it on."""
    run = run_joins(
        _joined_query(
            "    from orders\n    let c = customers\n    where any(True for c in c)\n"
            + later
            + _SELECT_ID
        )
    )
    assert run.diagnostics == []
    structure = run.structures[run.relation("q")]
    assert [
        (item.binding, item.relation.name, item.visible) for item in structure.inputs
    ] == [("orders", "orders", True), *inputs]
    assert [join.clause.kind for join in structure.joins] == [
        AuthoredJoinKind.SEMI,
        AuthoredJoinKind.CROSS,
    ]


def test_single_file_join_structure_takes_the_relationship_resolution_as_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _joined_query(
        "    from orders\n    let c = customers\n    inner join c\n" + _SELECT_ID
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
            "    from orders\n    inner join nowhere\n"
            "    let c = customers\n    inner join c\n"
            "    let r = regions\n    inner join r\n" + _SELECT_ID
        )
    )
    assert located(run.diagnostics) == [
        ("PIE-S2301", "Unknown relation: nowhere", 20, 5)
    ]
    # The JOIN of the unknown relation resolves nothing; the later JOINs read
    # the row of the FROM input, which the failed input does not hide.
    assert (calls, run.structures) == (["c", "r"], {})
    unresolved = run_joins(
        _joined_query(
            "    from nowhere\n    let r = regions\n    cross join r\n"
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
            "    let c = customers\n    inner join c on order_customer(orders, c)\n",
            {**_ORDERS, "orders.customer_id": _NN, **_customers("c")},
            [()],
            id="inner_relationship_equality",
        ),
        pytest.param(
            "    let c = customers\n    left join c on order_customer(orders, c)\n",
            {**_ORDERS, **_customers("c", "id", "name")},
            [(1,)],
            id="left",
        ),
        pytest.param(
            "    let c = customers\n    right join c on orders.customer_id == c.id\n",
            {**_NULLABLE_ORDERS, **_customers("c")},
            [(0,)],
            id="right",
        ),
        pytest.param(
            "    let c = customers\n    full join c on orders.customer_id == c.id\n",
            {**_NULLABLE_ORDERS, **_customers("c", "id", "name")},
            [(0, 1)],
            id="full",
        ),
        pytest.param(
            "    let r = regions\n    cross join r\n",
            {**_ORDERS, "r.id": _NN, "r.label": _NN},
            [()],
            id="cross",
        ),
        # A JOIN-prefix `[not] any` is the hidden SEMI/ANTI JOIN: it keeps the
        # left row as it was, `orders.customer_id` not narrowed, and nulls none.
        pytest.param(
            "    let s = customers\n    where any(orders.customer_id == s.id for s in s)\n"
            "    let r = regions\n    cross join r\n",
            {**_ORDERS, "r.id": _NN, "r.label": _NN},
            [(), ()],
            id="semi",
        ),
        pytest.param(
            "    let s = customers\n"
            "    where not any(orders.customer_id == s.id for s in s)\n"
            "    let r = regions\n    cross join r\n",
            {**_ORDERS, "r.id": _NN, "r.label": _NN},
            [(), ()],
            id="anti",
        ),
        pytest.param(
            "    let s = customers\n    where any(orders.customer_id == s.id for s in s)\n"
            "    let r = regions\n    right join r on r.id == orders.amount\n",
            {**_NULLABLE_ORDERS, "r.id": _NN, "r.label": _NN},
            [(), (0,)],
            id="right_after_semi",
        ),
        pytest.param(
            "    let c = customers\n    left join c on orders.customer_id == c.id\n"
            "    let r = regions\n"
            '    inner join r on c.region_id == r.id and c.name != ""\n',
            {**_ORDERS, **_customers("c", "id", "name"), "r.id": _NN, "r.label": _NN},
            [(1,), ()],
            id="extension_outlasts_a_later_inner_join",
        ),
    ),
)
def test_single_file_joined_rows_follow_each_join_kind(
    joins_text: str,
    expected: dict[str, str],
    extends: list[tuple[int, ...]],
) -> None:
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
            "    let c = customers\n"
            "    left join c on orders.customer_id == c.id\n"
            "    let r = regions\n"
            "    inner join r on c.region_id == r.id\n" + _SELECT_ID
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


def test_single_file_join_reads_resolve_against_the_visible_bindings() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n"
            "    let customer = customers\n"
            "    inner join customer on order_customer(orders, customer)\n"
            "    let big = amount > 10\n"
            '    where big and customer.name != ""\n'
            "    select:\n        order_id = orders.id\n        name\n"
            "    order by:\n        customer.id desc\n"
        )
    )
    checks, value_types = run.checks()
    query = run.relation("q")
    info = checks.facts[query]
    assert (checks.diagnostics, checks.reads) == ((), ())
    (join_clause,) = query.join_clauses
    assert join_clause.on_clause is not None
    condition = join_clause.on_clause.expression
    assert isinstance(condition, ComparisonExpr)
    # The relationship call in `on` reads its row arguments as the two inputs.
    assert info.field_reads[condition.left] == JoinFieldRef(
        input=0, field="customer_id"
    )
    assert info.field_reads[condition.right] == JoinFieldRef(input=1, field="id")
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
        and leaf not in (condition.left, condition.right)
    ) == [
        (22, 15, "amount", 0, "amount"),
        (23, 19, "customer.name", 1, "name"),
        (25, 20, "orders.id", 0, "id"),
        (26, 9, "name", 1, "name"),
        (28, 9, "customer.id", 1, "id"),
    ]
    rows = run.rows("q")
    assert len(info.field_reads) == 7
    assert rows is not None and info.row_schema == rows.tail
    assert [(item.ordinal, item.binding) for item in info.inputs] == [
        (0, "orders"),
        (1, "customer"),
    ]
    (join,) = info.joins
    integer = ResolvedType("Int", TypeKind.BUILTIN)
    assert join == JoinInfo(
        ordinal=1,
        clause=join_clause,
        kind=AuthoredJoinKind.INNER,
        mode="M3",
        source_input=0,
        source_inferred=False,
        target_input=1,
        relationship=None,
        step=None,
        equalities=(),
        condition=condition,
        null_extends=(),
    )
    assert (value_types[condition.left], value_types[condition.right]) == (
        ValueType(integer, EffectiveNullability.NULLABLE),
        ValueType(integer, EffectiveNullability.NON_NULL),
    )


def test_single_file_self_join_reads_keep_their_inputs_apart() -> None:
    run = run_joins(
        _joined_query(
            "    from customers\n    let peer = customers\n"
            "    left join peer on peer.region_id == customers.region_id\n"
            "    select:\n        customer_id = customers.id\n        peer_id = peer.id\n"
        )
    )
    checks, _ = run.checks()
    info = checks.facts[run.relation("q")]
    assert sorted(
        (leaf.span.line, leaf.span.column, read.input, read.field)
        for leaf, read in info.field_reads.items()
    ) == [
        (21, 23, 1, "region_id"),
        (21, 41, 0, "region_id"),
        (23, 23, 0, "id"),
        (24, 19, 1, "id"),
    ]
    assert info.joins[0].null_extends == (1,)


def test_single_file_join_reads_inside_def_arguments_resolve() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n    let r = regions\n    cross join r\n"
            "    where inc(r.id) > 1\n"
            "    select:\n        bumped = inc(orders.amount)\n"
            "def inc(x: Int) -> Int | None: return x + 1\n"
        )
    )
    checks, _ = run.checks()
    info = checks.facts[run.relation("q")]
    assert sorted(
        (leaf.span.line, leaf.span.column, read.input, read.field)
        for leaf, read in info.field_reads.items()
    ) == [(22, 15, 1, "id"), (24, 22, 0, "amount")]


def test_single_file_join_equalities_follow_the_written_roles() -> None:
    run = run_joins(
        _joined_query(
            "    from customers\n"
            "    let peer = customers\n"
            "    inner join peer on referral(peer, customers)\n"
            "    select:\n        x = customers.id\n"
            "relationship referral(referrer: Customer, referee: Customer): "
            "referrer.region_id == referee.id\n"
        )
    )
    checks, value_types = run.checks()
    query = run.relation("q")
    (join,) = checks.facts[query].joins
    condition = join.condition
    assert isinstance(condition, ComparisonExpr)
    # The call's first argument plays `referrer`, the left operand of the
    # declared body, and the FROM input plays `referee`.
    assert (join.mode, join.source_inferred, join.relationship, join.equalities) == (
        "M3",
        False,
        None,
        (),
    )
    reads = checks.facts[query].field_reads
    assert (reads[condition.left], reads[condition.right]) == (
        JoinFieldRef(input=1, field="region_id"),
        JoinFieldRef(input=0, field="id"),
    )
    assert (
        value_types[condition.left].nullability,
        value_types[condition.right].nullability,
    ) == (
        EffectiveNullability.NULLABLE,
        EffectiveNullability.NON_NULL,
    )


def test_single_file_join_reads_that_fail_say_why() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n"
            "    let customer = customers\n"
            "    inner join customer on order_customer(orders, customer)\n"
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
        ("PIE-S2335", "Ambiguous field: id; write orders.id or customer.id", 22, 11),
        ("PIE-S2102", "Unknown field: customer.nope", 24, 16),
        (
            "PIE-S2102",
            "Unknown field: customers.name; customers names a relation, not a binding: write customer.name",
            25,
            15,
        ),
        ("PIE-S2102", "Unknown field: elsewhere.x", 26, 17),
        ("PIE-S2102", "Unknown field: customer.name.x", 27, 16),
    ]
    assert (checks.facts, checks.diagnostics) == ({}, ())
    # Each failed read keeps exactly its own diagnostic, at the read; a bare
    # name that no binding has, and every other code, stay as they are.
    at = {read.message: read.location for read in checks.reads}
    elsewhere = SourceLocation(path="joins.pietto", line=28, column=16)

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
            "    from orders\n    let r = regions\n    cross join r\n"
            "    select:\n        n = row_number() window(order by orders.id)\n"
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
        at("PIE-S2102", 23, 9),
        at("PIE-S2380", 23, 42),
        at("PIE-S2334", 23, 13),
        at("PIE-S2102", 27, 13),
    ]
    assert joins.join_post_pass(before, checks) == [before[2], before[3]]


def test_single_file_join_with_an_unknown_input_row_says_so_unless_explained() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n    let t = tally\n    cross join t\n"
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
            21,
            5,
        )
    ]
    assert located(joins.join_post_pass([], checks)) == unexplained
    # An ERROR inside a relation it reads explains the unknown row.
    explained = Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message="stand-in",
        location=SourceLocation(path="joins.pietto", line=25, column=5),
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
            21,
            5,
        )
    ]


def test_single_file_join_over_a_join_relation_whose_row_is_unknown_says_so_once() -> (
    None
):
    run = run_joins(
        _joined_query(
            "    from orders\n    let m = middle\n    cross join m\n"
            + _SELECT_ID
            + "table middle:\n    from orders\n    let t = tally\n    cross join t\n"
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
            27,
            5,
        )
    ]


def test_single_file_join_input_rows_are_built_for_the_given_relations() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n    let s = customers\n"
            "    where any(order_customer(orders, s) for s in s)\n"
            "    let r = regions\n    cross join r\n"
            + _SELECT_ID
            + "query bad:\n    from orders\n    cross join nowhere\n"
            + _SELECT_ID
            + "query plain:\n    from orders\n"
            + _SELECT_ID
            + "query derived:\n    from orders\n    let t = tally\n    cross join t\n"
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


def test_single_file_join_structures_resolve_every_join_target_for_cycles() -> None:
    run = run_joins(
        _joined_query(
            "    from orders\n    let c = customers\n"
            "    inner join c on order_customer(orders, c)\n"
            "    let t = tally\n    cross join t\n"
            + _SELECT_ID
            + "query bad:\n    from nowhere\n    let again = q\n    cross join again\n"
            "    cross join missing\n"
            "    cross join both\n"
            + _SELECT_ID
            + "table tally:\n    from orders\n    select:\n        id\n"
            "query both:\n    union all:\n        from orders\n        from orders\n"
        )
    )
    query, bad = run.relation("q"), run.relation("bad")
    assert located(run.diagnostics) == [
        ("PIE-S2301", "Unknown relation: missing", 30, 5),
        (
            "PIE-S2334",
            f"Set-operation inputs are available {_COMPLETED} them: both",
            31,
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
    parsed = parse_source(JOIN_PREFIX)
    assert parsed.ast is not None
    # The body of order_customer, `order.customer_id == customer.id`.
    comparison = cast(ComparisonExpr, parsed.ast.relationship_templates[0].body)

    def misread(
        clause: JoinClause,
        *,
        written_source: JoinBindingView | None,
        **_: Any,
    ) -> ResolvedJoinRelationship:
        assert written_source is not None
        return ResolvedJoinRelationship(
            source=written_source,
            source_inferred=False,
            relationship="order_customer",
            step=None,
            source_role="order",
            target_role="customer",
            pairs=(
                (
                    "nope",
                    "id",
                    comparison,
                    cast(DottedNameExpr, comparison.left),
                    cast(DottedNameExpr, comparison.right),
                ),
            ),
        )

    monkeypatch.setattr(joins, "resolve_join_relationship", misread)
    run = run_joins(
        _joined_query(
            "    from orders\n    let c = customers\n    inner join c\n" + _SELECT_ID
        )
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
            "    let customer = customers\n"
            "    inner join customer on order_customer(orders, customer)\n"
            '    where customer.name == "x"\n'
            "    select:\n        n = row_number() window(order by orders.id)\n",
            [
                (
                    "PIE-S2334",
                    "Window functions over JOIN rows are available only when "
                    "an EXPLICIT_MODULES project (schema version 2) completes them.",
                    24,
                    13,
                )
            ],
        ),
        (
            "    let customer = customers\n"
            "    inner join customer on order_customer(orders, customer)\n"
            '    where customer.name == "x"\n'
            "    select:\n        n = count()\n"
            "    order by:\n        customer.name\n",
            [
                (
                    "PIE-S2334",
                    "ORDER BY is not available after an ungrouped aggregate over JOIN rows: "
                    "the result has one row; remove `order by`.",
                    25,
                    5,
                )
            ],
        ),
        (
            "    let customer = q\n    cross join customer\n"
            '    where customer.name == "x"\n'
            "    select:\n        name = customer.name\n",
            [
                ("PIE-S2302", "Relation cycle detected: q -> q", 21, 5),
                ("PIE-S2382", _SAME_FILE_READ.format("q", "query"), 21, 5),
            ],
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
    assert all(
        item.severity is Severity.WARNING
        for item in result.diagnostics
        if item.code == "PIE-S2382"
    )
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
    let target = second
    cross join target
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
    # Each JOIN or FROM read of a same-file table or query warns once.
    assert _graded(result.diagnostics) == [
        _same_file_read("second", "table", 21, 5),
        _same_file_read("q", "query", 25, 5),
        _same_file_read("first", "table", 29, 5),
    ]
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
    let peer = projected
    cross join peer
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
    assert _graded(result.diagnostics) == [
        _same_file_read("projected", "table", 19, 5),
        _same_file_read("projected", "table", 21, 5),
    ]
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
    let peer = customers
    cross join peer
    let peer_key = peer.id
    group by:
        customers.id
        peer_key
    select:
        customer_id = customers.id
        other_id = peer.id
        n = count()
    having n > 0
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
    let customer = customers
    cross join customer
    select:
        n = count(orders.amount)
"""
        ),
        mode_override=mode,
    )
    assert located(result.diagnostics) == [
        (
            "PIE-S2381",
            "An aggregate may read rows that a JOIN repeats; match a declared "
            "unique key of customer whose fields are never None in `on` with a "
            "relationship call, use `any(...)` for an input that only filters "
            "rows, or aggregate in a separate query first",
            23,
            13,
        )
    ]


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize("negation", ("", "not "), ids=("semi", "anti"))
def test_join_any_binder_read_after_its_hidden_join_is_one_diagnostic_per_read(
    mode: CheckMode, negation: str
) -> None:
    """The binder of a JOIN-prefix `any` is no binding of the hidden SEMI/ANTI
    JOIN it becomes: a read of its name after it is one unknown field."""
    result = analyze(
        _parse(
            JOIN_PREFIX
            + f"""query q:
    from orders
    let customer = customers
    where {negation}any(customer.id == orders.customer_id for customer in customer)
    let later = regions
    cross join later
    select:
        n = customer.name
"""
        ),
        mode_override=mode,
    )
    assert located(result.diagnostics) == [
        ("PIE-S2102", "Unknown field: customer.name", 25, 13)
    ]


def test_join_relation_name_hint_lists_every_visible_binding_in_order() -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + """query q:
    from orders
    let first = customers
    cross join first
    let second = customers
    cross join second
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
            25,
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
    let customer = customers
    {kind} join customer on orders.customer_id == customer.id
    select:
        n = inc({field})
def inc(x: Int) -> Int | None: return x + 1
"""
        )
    )
    assert located(result.diagnostics) == (
        [
            (
                "PIE-S2395",
                "Invalid argument for def inc at position 1 (x): "
                "expected Int, got Int | None",
                23,
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
    let peer = q
    cross join peer on peer.id == orders.id
    select:
        id = peer.id
"""
        )
    )
    assert _graded(result.diagnostics) == [
        ("PIE-S2302", Severity.ERROR, "Relation cycle detected: q -> q", 21, 5),
        ("PIE-S2336", Severity.ERROR, "CROSS JOIN cannot have ON or VIA.", 21, 5),
        _same_file_read("q", "query", 21, 5),
    ]


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_refused_join_window_keeps_unrelated_scalar_errors(mode: CheckMode) -> None:
    result = analyze(
        _parse(
            JOIN_PREFIX
            + """query q:
    from orders
    let customer = customers
    cross join customer
    select:
        n = row_number() window(order by orders.id)
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
            23,
            13,
        ),
        ("PIE-S2103", "Unknown function: frob", 24, 15),
    ]
