from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from pathlib import Path
import re
from typing import cast

import pytest

import test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation as slice7
from pietto._project import project_completion as completion
from pietto._project import project_joined_row_filter as row_filter
from pietto._project import project_scalar_namespaces as namespaces
from pietto._project import project_scalar_references as references
from pietto._project.model import ProjectRowFieldNullability
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_ir_properties import ProjectIRPropertyAvailability
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputRelationalProperties,
)
from pietto.ast_nodes import (
    CallExpr,
    ComparisonExpr,
    IsNullExpr,
    QueryDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import EffectiveNullability, ValueTypeKind


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_row_filter.py"
NAMESPACE_PRODUCTION = REPO_ROOT / "src/pietto/_project/project_scalar_namespaces.py"
SPEC = REPO_ROOT / "docs/spec/phase63-slice8-joined-row-filtering-v1.md"
SPEC_HEADINGS = (
    "Decision And Live Authority",
    "Generic Joined-Namespace Expression Adapter",
    "Slice-7 Admission And Canonical Collection",
    "WHERE Namespace And Predicate Law",
    "SQL Three-Valued Row Retention",
    "Row And Nullability Preservation",
    "Relational Property Preservation Witness",
    "Historical And Later-Stage Boundary",
    "Differential Compatibility",
    "Exact Changed-Path Closure",
    "Assurance And Publication",
    "Slice 9 Handoff",
)

FILTER_SOURCE = """
shape ReturnRow:
    id: Int not null
    order_id: Int not null
    amount: Int nullable
    unique return_key on id
source returns: ReturnRow is postgres.table("returns")
relationship order_returns:
    endpoint orders: orders
    endpoint returns: returns
    on orders.id == returns.order_id
query where_base_qualified:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where customers.id > 0
    select:
        id
query where_target_unqualified:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where amount > 0
    select:
        id
query where_binding_qualified:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where purchase.amount > 0
    select:
        id
query where_let_chain:
    from customers
    left join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    let:
        floor = 1
        adjusted = purchase.amount + floor
    where adjusted > floor
    select:
        id
query where_nullable_comparison:
    from customers
    left join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where purchase.amount > 0
    select:
        id
query where_is_null:
    from customers
    left join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where purchase.id is null
    select:
        id
query where_is_not_null:
    from customers
    left join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where purchase.id is not null
    select:
        id
query where_builtin_call:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where len("x") > 0
    select:
        id
query where_ambiguous:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where id > 0
    select:
        id
query where_unknown_field:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where missing > 0
    select:
        id
query where_hidden_intermediate:
    from customers
    inner join returns as returned:
        from customers
        via customer_orders: customer -> orders
        via order_returns: orders -> returns
    where orders.product_id > 0
    select:
        id
query where_projection_alias:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where projected > 0
    select:
        projected = purchase.amount
query where_relation_name_fallback:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where orders.amount > 0
    select:
        id
query where_known_int:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where purchase.customer_id
    select:
        id
query where_known_text:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where "text"
    select:
        id
query where_invalid_operator:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where "text" + 1
    select:
        id
query where_unknown_function:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where not_a_builtin(purchase.amount) > 0
    select:
        id
query where_invalid_window_call:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where row_number() > 0
    select:
        id
query where_aggregate:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where sum(purchase.amount) > 0
    select:
        id
query where_equality_no_refinement:
    from customers
    inner join orders as purchase:
        from customers
        via customer_orders: customer -> orders
    where customers.id == purchase.customer_id
    select:
        id
"""

SINGLE_INPUT_PREFIX = """shape Row:
    id: Int not null
    amount: Int nullable
source rows: Row is postgres.table("rows")
"""


@dataclass(frozen=True, slots=True)
class _Built:
    completion: completion.ProjectCompletion
    filters: row_filter.ProjectJoinedRowFilterSet


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    files = slice7._project_files()
    files["c.pietto"] = files["c.pietto"].replace(
        "export:\n",
        FILTER_SOURCE + "export:\n",
        1,
    )
    semantic = slice7._semantic_project(
        tmp_path_factory.mktemp("p63s8") / "project",
        files,
        reverse_creation=False,
    )
    completed = completion.build_project_completion(slice7._phase62(semantic))
    return _Built(
        completion=completed,
        filters=row_filter.build_project_joined_row_filters(completed),
    )


def _result(
    built: _Built,
    name: str,
) -> row_filter.ProjectJoinedRowFilterResult:
    matches = tuple(
        result
        for result in built.filters.results
        if result.entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _error_codes(result: row_filter.ProjectJoinedRowFilterResult) -> tuple[str, ...]:
    return tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )


def test_generic_adapter_retains_exact_post_let_fields_lets_and_function_identity(
    built: _Built,
) -> None:
    for name in (
        "where_base_qualified",
        "where_target_unqualified",
        "where_binding_qualified",
    ):
        result = _result(built, name)
        assert type(result) is row_filter.ProjectConcreteJoinedRowFilter
        analysis = result.expression_analysis
        assert type(analysis) is namespaces.ProjectConcreteJoinedNamespaceExpression
        assert analysis.namespace is result.joined_semantics.post_let
        assert result.where_clause is not None
        assert analysis.expression is result.where_clause.expression
        assert analysis.value_type.resolved_type.name == "Bool"
        assert all(
            type(resolution) is references.ProjectScalarReferenceResolution
            and resolution.status is ProjectModuleCandidateBucketStatus.CONCRETE
            for resolution in analysis.resolutions
        )

    let_result = _result(built, "where_let_chain")
    assert type(let_result) is row_filter.ProjectConcreteJoinedRowFilter
    let_analysis = let_result.expression_analysis
    assert type(let_analysis) is namespaces.ProjectConcreteJoinedNamespaceExpression
    assert tuple(type(resolution) for resolution in let_analysis.resolutions) == (
        namespaces.ProjectJoinedLetReferenceResolution,
        namespaces.ProjectJoinedLetReferenceResolution,
    )
    assert tuple(
        resolution.target.occurrence.binding.name
        for resolution in let_analysis.resolutions
        if type(resolution) is namespaces.ProjectJoinedLetReferenceResolution
    ) == ("adjusted", "floor")
    assert let_analysis.namespace.let_values is let_result.joined_semantics.let_values
    rebuilt = namespaces.build_project_joined_let_namespaces(
        let_analysis.namespace.binding_environment
    )
    assert type(rebuilt) is namespaces.ProjectConcreteJoinedLetNamespaces
    assert tuple(value.value_type for value in rebuilt.values) == tuple(
        value.value_type for value in let_analysis.namespace.let_values
    )

    call_result = _result(built, "where_builtin_call")
    assert type(call_result) is row_filter.ProjectConcreteJoinedRowFilter
    call_analysis = call_result.expression_analysis
    assert type(call_analysis) is namespaces.ProjectConcreteJoinedNamespaceExpression
    expression = call_analysis.expression
    assert type(expression) is ComparisonExpr and type(expression.left) is CallExpr
    assert call_analysis.resolutions == ()
    assert expression.left.callee not in call_analysis.value_types


@pytest.mark.parametrize(
    ("name", "status"),
    (
        ("where_ambiguous", ProjectModuleCandidateBucketStatus.AMBIGUOUS),
        ("where_unknown_field", ProjectModuleCandidateBucketStatus.ABSENT),
        ("where_hidden_intermediate", ProjectModuleCandidateBucketStatus.ABSENT),
        ("where_projection_alias", ProjectModuleCandidateBucketStatus.ABSENT),
        ("where_relation_name_fallback", ProjectModuleCandidateBucketStatus.ABSENT),
    ),
)
def test_where_visibility_blockers_remain_complete_and_fail_closed(
    built: _Built,
    name: str,
    status: ProjectModuleCandidateBucketStatus,
) -> None:
    result = _result(built, name)
    assert type(result) is row_filter.ProjectNonConcreteJoinedRowFilter
    assert result.reason is (
        row_filter.ProjectJoinedRowFilterNonConcreteReason.NAMESPACE_EXPRESSION_NON_CONCRETE
    )
    analysis = result.expression_analysis
    assert type(analysis) is namespaces.ProjectNonConcreteJoinedNamespaceExpression
    assert analysis.value_type is None
    assert analysis.kernel_value_type is None
    assert len(analysis.blocking_resolutions) == 1
    assert analysis.blocking_resolutions[0].status is status
    assert result.post_filter is result.preservation is None
    assert result.fields == ()


@pytest.mark.parametrize(
    ("name", "code"),
    (
        ("where_invalid_operator", "PIE-S2105"),
        ("where_unknown_function", "PIE-S2103"),
        ("where_invalid_window_call", "PIE-S2103"),
    ),
)
def test_existing_kernel_and_invalid_window_behavior_remain_fail_closed(
    built: _Built,
    name: str,
    code: str,
) -> None:
    result = _result(built, name)
    assert type(result) is row_filter.ProjectNonConcreteJoinedRowFilter
    analysis = result.expression_analysis
    assert type(analysis) is namespaces.ProjectNonConcreteJoinedNamespaceExpression
    assert analysis.kernel_value_type is not None
    assert analysis.value_type is None
    assert _error_codes(result) == (code,)


def test_predicate_consumer_accepts_bool_and_rejects_only_known_non_bool(
    built: _Built,
) -> None:
    nullable = _result(built, "where_nullable_comparison")
    is_null = _result(built, "where_is_null")
    is_not_null = _result(built, "where_is_not_null")
    for result in (nullable, is_null, is_not_null):
        assert type(result) is row_filter.ProjectConcreteJoinedRowFilter
        assert result.kind is row_filter.ProjectJoinedRowFilterKind.AUTHORED_WHERE
        assert result.expression_analysis is not None
        assert result.expression_analysis.value_type.resolved_type.name == "Bool"
    assert type(nullable) is row_filter.ProjectConcreteJoinedRowFilter
    assert type(is_null) is row_filter.ProjectConcreteJoinedRowFilter
    assert nullable.expression_analysis is not None
    assert (
        nullable.expression_analysis.value_type.nullability
        is EffectiveNullability.UNKNOWN
    )
    assert is_null.expression_analysis is not None
    assert type(is_null.expression_analysis.expression) is IsNullExpr

    for name in ("where_known_int", "where_known_text"):
        result = _result(built, name)
        assert type(result) is row_filter.ProjectNonConcreteJoinedRowFilter
        assert result.reason is (
            row_filter.ProjectJoinedRowFilterNonConcreteReason.KNOWN_NON_BOOL_PREDICATE
        )
        assert _error_codes(result) == ("PIE-S2202",)
        assert result.diagnostics[0].message == (
            "Expected Bool expression in where clause"
        )

    unknown = _result(built, "where_unknown_field")
    assert type(unknown) is row_filter.ProjectNonConcreteJoinedRowFilter
    assert "PIE-S2202" not in _error_codes(unknown)
    aggregate = _result(built, "where_aggregate")
    assert type(aggregate) is row_filter.ProjectNonConcreteJoinedRowFilter
    assert aggregate.reason is (
        row_filter.ProjectJoinedRowFilterNonConcreteReason.INVALID_PREDICATE_CONTEXT
    )
    assert _error_codes(aggregate) == ("PIE-S2308",)
    assert aggregate.diagnostics[0].message == (
        "Aggregate sum() is not allowed in where clause; "
        "use it only as a direct aliased select projection"
    )


def test_three_valued_effect_is_declarative_and_distinct_from_nullability(
    built: _Built,
) -> None:
    result = _result(built, "where_nullable_comparison")
    assert type(result) is row_filter.ProjectConcreteJoinedRowFilter
    assert tuple(
        (effect.truth, effect.retain_row) for effect in result.retention_effects
    ) == (
        (row_filter.ProjectSQLPredicateTruth.TRUE, True),
        (row_filter.ProjectSQLPredicateTruth.FALSE, False),
        (row_filter.ProjectSQLPredicateTruth.UNKNOWN, False),
    )
    assert row_filter.ProjectSQLPredicateTruth.UNKNOWN != (EffectiveNullability.UNKNOWN)
    with pytest.raises(ValueError, match="Only SQL TRUE"):
        row_filter.ProjectJoinedRowRetentionEffect(
            truth=row_filter.ProjectSQLPredicateTruth.UNKNOWN,
            retain_row=True,
        )


def test_preservation_witness_reuses_exact_slice6_properties_and_nulling(
    built: _Built,
) -> None:
    result = _result(built, "where_is_not_null")
    equality = _result(built, "where_equality_no_refinement")
    assert type(result) is row_filter.ProjectConcreteJoinedRowFilter
    assert type(equality) is row_filter.ProjectConcreteJoinedRowFilter
    joined = result.joined_semantics
    witness = result.preservation
    bridge = joined.property_bridge
    assert witness.joined_semantics is joined
    assert witness.input_property_bridge is bridge
    assert witness.fields is joined.fields is result.fields
    assert witness.multiplicity is row_filter.ProjectJoinedRowMultiplicity.BAG
    assert bridge.relational is witness.input_property_bridge.relational
    assert type(bridge.relational) is ProjectIROutputRelationalProperties
    assert bridge.relational.output is joined.final_output
    assert witness.input_property_bridge.keys is bridge.keys
    assert witness.input_property_bridge.fds is bridge.fds
    assert witness.input_property_bridge.fd_index is bridge.fd_index
    assert witness.input_property_bridge.grain is bridge.grain
    assert witness.input_property_bridge.null_extension is bridge.null_extension
    assert witness.input_property_bridge.ordering is bridge.ordering
    assert bridge.ordering.availability is ProjectIRPropertyAvailability.UNKNOWN

    right_id = next(
        field
        for field in result.fields
        if field.joined_field.evidence.name == "id" and field.nulling_joins
    )
    assert right_id.joined_field.evidence.nullability is (
        ProjectRowFieldNullability.NON_NULL
    )
    assert right_id.effective_nullability is ProjectRowFieldNullability.NULLABLE
    assert right_id.scalar_field.value_type.nullability is (
        EffectiveNullability.NULLABLE
    )
    assert right_id is next(
        field for field in joined.fields if field.joined_field is right_id.joined_field
    )
    assert result.where_clause is not None
    assert result.expression_analysis is not None
    assert result.where_clause.expression is result.expression_analysis.expression

    equality_bridge = equality.joined_semantics.property_bridge
    assert equality.preservation.input_property_bridge is equality_bridge
    assert equality_bridge.relational.output is equality.joined_semantics.final_output
    assert tuple(map(id, equality_bridge.keys)) == tuple(
        map(id, equality.preservation.input_property_bridge.keys)
    )
    assert tuple(map(id, equality_bridge.fds)) == tuple(
        map(id, equality.preservation.input_property_bridge.fds)
    )
    assert tuple(map(id, equality_bridge.relational.value_classes)) == tuple(
        map(id, equality.preservation.input_property_bridge.relational.value_classes)
    )
    assert tuple(map(id, equality_bridge.grain.factors)) == tuple(
        map(id, equality.preservation.input_property_bridge.grain.factors)
    )
    assert tuple(map(id, equality_bridge.grain.dependencies)) == tuple(
        map(id, equality.preservation.input_property_bridge.grain.dependencies)
    )


def test_completion_admission_is_exact_canonical_and_ledger_preserving(
    built: _Built,
) -> None:
    entries_before = built.completion.entries
    expected = tuple(
        entry
        for entry in entries_before
        if type(entry) is completion.ProjectEffectiveOutputTerminal
        and entry.reason
        is completion.ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
    )
    assert tuple(result.entry for result in built.filters.results) == expected
    assert built.filters.completion is built.completion
    assert built.completion.entries is entries_before
    assert all(
        result.entry.joined_completion is result.joined_semantics
        for result in built.filters.results
    )
    ignored = tuple(
        entry for entry in entries_before if not any(entry is item for item in expected)
    )
    assert ignored
    assert not any(
        result.entry is entry for result in built.filters.results for entry in ignored
    )

    absent = _result(built, "joined_a")
    assert type(absent) is row_filter.ProjectConcreteJoinedRowFilter
    assert absent.kind is row_filter.ProjectJoinedRowFilterKind.ABSENT
    assert absent.where_clause is absent.expression_analysis is None
    assert absent.retention_effects == ()
    assert absent.preservation.input_property_bridge is (
        absent.joined_semantics.property_bridge
    )

    eligible = cast(completion.ProjectEffectiveOutputTerminal, expected[0])
    with pytest.raises(ValueError, match="exact ledger membership"):
        row_filter.build_project_joined_row_filter(
            built.completion,
            replace(eligible),
        )


def _single_input_decision(body: str) -> tuple[bool, tuple[str, ...]]:
    parsed = parse_source(
        SINGLE_INPUT_PREFIX + "query filtered:\n" + body,
        path="single-input-where.pietto",
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    result = analyze(parsed.ast)
    definition = cast(QueryDef, result.model.relation_symbols["filtered"])
    assert definition.where_clause is not None
    value_type = result.model.expression_value_types.get(
        definition.where_clause.expression
    )
    errors = tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    concrete = (
        not errors
        and value_type is not None
        and value_type.kind is ValueTypeKind.KNOWN
        and value_type.resolved_type.name == "Bool"
    )
    return concrete, errors


@pytest.mark.parametrize(
    ("joined_name", "body", "expected_code"),
    (
        (
            "where_target_unqualified",
            "    from rows\n    where amount > 0\n    select:\n        id\n",
            None,
        ),
        (
            "where_let_chain",
            "    from rows\n"
            "    let:\n"
            "        floor = 1\n"
            "        adjusted = amount + floor\n"
            "    where adjusted > floor\n"
            "    select:\n"
            "        id\n",
            None,
        ),
        (
            "where_known_int",
            "    from rows\n    where id\n    select:\n        id\n",
            "PIE-S2202",
        ),
        (
            "where_unknown_field",
            "    from rows\n    where missing > 0\n    select:\n        id\n",
            "PIE-S2102",
        ),
        (
            "where_aggregate",
            "    from rows\n    where sum(amount) > 0\n    select:\n        id\n",
            "PIE-S2308",
        ),
    ),
)
def test_equivalent_single_input_where_decisions_remain_compatible(
    built: _Built,
    joined_name: str,
    body: str,
    expected_code: str | None,
) -> None:
    public_concrete, public_errors = _single_input_decision(body)
    joined = _result(built, joined_name)
    joined_concrete = type(joined) is row_filter.ProjectConcreteJoinedRowFilter
    assert joined_concrete is public_concrete
    if expected_code is None:
        assert public_errors == _error_codes(joined) == ()
    else:
        assert expected_code in public_errors
        if expected_code != "PIE-S2102":
            assert _error_codes(joined) == (expected_code,)


def test_scope_dependency_spec_and_inventory_are_exact() -> None:
    source = PRODUCTION.read_text(encoding="utf-8")
    namespace_source = NAMESPACE_PRODUCTION.read_text(encoding="utf-8")
    imports = tuple(
        alias.name
        for node in ast.walk(ast.parse(source))
        if type(node) is ast.Import
        for alias in node.names
    ) + tuple(
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if type(node) is ast.ImportFrom
    )
    assert not any(
        name.startswith(("pietto.sql", "pietto.cli", "pyarrow")) for name in imports
    )
    for forbidden in (
        "ProjectIRSnapshotScope(",
        "ProjectIROutputRelationalProperties(",
        "build_project_completion(",
        "build_project_joined_row_semantics(",
        "GROUP_AGGREGATE",
        "WINDOW_EVALUATION",
        "FINAL_PROJECTION",
    ):
        assert forbidden not in source
    assert "infer_row_expression(" not in source
    assert namespace_source.count("infer_row_expression(") == 2

    document = SPEC.read_text(encoding="utf-8")
    assert tuple(re.findall(r"^## (.+)$", document, re.MULTILINE)) == SPEC_HEADINGS
    changed_paths = tuple(
        re.findall(r"^\| `([AM])` \| `([^`]+)` \|$", document, re.MULTILINE)
    )
    assert len(changed_paths) == len(set(changed_paths)) == 8
    assert sum(status == "A" for status, _ in changed_paths) == 3
    assert sum(status == "M" for status, _ in changed_paths) == 5
    normalized = " ".join(document.split()).replace("`", "")
    for evidence in (
        "POST_LET",
        "SQL TRUE -> retain row",
        "SQL FALSE -> drop row",
        "SQL UNKNOWN -> drop row",
        "relationship base condition != JOIN-local ON refinement != post-JOIN ROW_FILTER / WHERE",
        "existing Phase-62 property objects remain input premises",
        "production 169 -> 170 and tests 412 -> 413",
        "Slice 9 becomes NEXT / NOT IMPLEMENTED",
        "Slice 9 is not begun here",
    ):
        assert evidence in normalized
