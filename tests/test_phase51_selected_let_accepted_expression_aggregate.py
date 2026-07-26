from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path

import pytest

import pietto
import pietto._project as project_package
import pietto._project.aggregate_grouped_schema as aggregate_module
from pietto._project.aggregate_grouped_schema import (
    ProjectAggregateSchemaFacts,
    ProjectGroupedSchemaFacts,
    build_project_aggregate_schema_facts,
    build_project_grouped_schema_facts,
)
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsReason,
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
)
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticResult,
    ProjectSymbol,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import (
    CallExpr,
    Expression,
    NameExpr,
    QueryDef,
    SelectItem,
    SourceDef,
    TableDef,
)
from pietto.errors import SourceLocation

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_schema.py"
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md"
)
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase51-aggregate-expression-row-let-candidate-integration-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
LOCK_PATH = REPO_ROOT / "uv.lock"

EXPECTED_GATE2_PATHS = {
    "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md",
    "docs/spec/phase51-aggregate-expression-row-let-candidate-integration-v1.md",
    "src/pietto/_project/aggregate_grouped_schema.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase51_aggregate_only_project_row_schema.py",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
}

PHASE52_SLICE1_GATE2_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
    "tests/test_phase51_aggregate_only_project_row_schema.py",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
}

AggregateRow = tuple[SelectItem, ProjectRowField, ProjectAggregateResultFact]


@pytest.mark.parametrize(
    ("relation_kind", "grouped"),
    (
        ("table", False),
        ("table", True),
        ("query", False),
        ("query", True),
    ),
)
def test_selected_let_is_direct_aliased_call_with_table_query_wrapper_parity(
    tmp_path: Path,
    relation_kind: str,
    grouped: bool,
) -> None:
    relations = _relation_body(
        relation_kind=relation_kind,
        name="candidate",
        grouped=grouped,
        let_lines=("gross = amount + tax",),
        select_lines=("total = sum(gross)",),
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )
    rows = _aggregate_rows(
        definition,
        input_schema,
        upstream_symbol,
        grouped=grouped,
    )

    assert len(rows) == 1
    item, field, fact = rows[0]
    call = item.expression
    assert item.alias == "total"
    assert isinstance(call, CallExpr)
    assert len(call.arguments) == 1
    argument = call.arguments[0]
    assert isinstance(argument, NameExpr)
    assert argument.name == "gross"
    assert field == ProjectRowField(
        name="total",
        resolved_type=ProjectResolvedType(
            name="Int",
            kind=ProjectResolvedTypeKind.BUILTIN,
        ),
        nullability=ProjectRowFieldNullability.NULLABLE,
        field_def=None,
        provenance=field.provenance,
        result_role=ProjectRowResultRole.AGGREGATE_RESULT,
    )
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.AGGREGATE
    assert field.provenance.symbol is upstream_symbol
    assert field.provenance.location == _location(call)
    assert fact == ProjectAggregateResultFact(
        function="sum",
        output_name="total",
        grouped=grouped,
        argument_count=1,
        location=_location(call),
    )
    assert definition.let_clause is not None
    binding_expression = definition.let_clause.bindings[0].expression
    assert fact.location != _location(binding_expression)


@pytest.mark.parametrize("grouped", (False, True))
def test_exact_current_inline_expression_matrix_has_canonical_results(
    tmp_path: Path,
    grouped: bool,
) -> None:
    select_lines = (
        "count_plus = count(amount + tax)",
        "count_unary = count(-amount)",
        "count_modulo = count(amount % discount)",
        "count_float = count(score * weight)",
        "count_text = count(lower(trim(status)))",
        "count_len = count(len(status))",
        "count_bool = count(active and true)",
        "count_literal = count(amount + 1)",
        "distinct_text = count_distinct(lower(trim(status)))",
        "sum_int = sum(amount + tax)",
        "sum_unary = sum(-amount)",
        "sum_literal = sum(amount + 1)",
        "avg_float = avg(score * weight)",
        "avg_literal = avg(score + 1.5)",
        "sum_decimal = sum(price + fee)",
        "avg_decimal = avg(price - fee)",
    )
    relations = _relation_body(
        relation_kind="query",
        name="candidate",
        grouped=grouped,
        select_lines=select_lines,
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )
    rows = _aggregate_rows(
        definition,
        input_schema,
        upstream_symbol,
        grouped=grouped,
    )
    expected = (
        ("count_plus", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_unary", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_modulo", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_float", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_text", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_len", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_bool", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_literal", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        (
            "distinct_text",
            "count_distinct",
            "Int",
            ProjectRowFieldNullability.NON_NULL,
        ),
        ("sum_int", "sum", "Int", ProjectRowFieldNullability.NULLABLE),
        ("sum_unary", "sum", "Int", ProjectRowFieldNullability.NULLABLE),
        ("sum_literal", "sum", "Int", ProjectRowFieldNullability.NULLABLE),
        ("avg_float", "avg", "Float", ProjectRowFieldNullability.NULLABLE),
        ("avg_literal", "avg", "Float", ProjectRowFieldNullability.NULLABLE),
        ("sum_decimal", "sum", "Decimal", ProjectRowFieldNullability.NULLABLE),
        ("avg_decimal", "avg", "Decimal", ProjectRowFieldNullability.NULLABLE),
    )

    assert len(rows) == len(expected)
    assert tuple(item.alias for item, _, _ in rows) == tuple(
        alias for alias, _, _, _ in expected
    )
    for row, expected_row in zip(rows, expected, strict=True):
        _assert_aggregate_row(
            row,
            expected_alias=expected_row[0],
            expected_function=expected_row[1],
            expected_type=expected_row[2],
            expected_nullability=expected_row[3],
            grouped=grouped,
            upstream_symbol=upstream_symbol,
        )


@pytest.mark.parametrize("grouped", (False, True))
def test_concrete_direct_qualified_chained_and_computed_row_let_matrix(
    tmp_path: Path,
    grouped: bool,
) -> None:
    let_lines = (
        "amount_value = amount",
        "qualified_amount = users.amount",
        "chained_amount = qualified_amount",
        "gross = amount + tax",
        "net = gross - discount",
        "weighted = score * weight",
        "normalized = lower(trim(status))",
        "normalized_again = normalized",
        "status_length = len(status)",
        "active_value = active and true",
    )
    select_lines = (
        "count_direct = count(amount_value)",
        "count_qualified = count(qualified_amount)",
        "count_chained = count(chained_amount)",
        "count_computed = count(net)",
        "count_length = count(status_length)",
        "count_active = count(active_value)",
        "distinct_normalized = count_distinct(normalized)",
        "distinct_chained = count_distinct(normalized_again)",
        "sum_gross = sum(gross)",
        "sum_chained = sum(net)",
        "avg_weighted = avg(weighted)",
    )
    relations = _relation_body(
        relation_kind="table",
        name="candidate",
        grouped=grouped,
        let_lines=let_lines,
        select_lines=select_lines,
    )
    _, semantic_result, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )
    assert semantic_result.model is not None
    let_facts = semantic_result.model.relation_let_scope_facts[definition]
    assert let_facts.status is ProjectLetScopeFactsStatus.CONCRETE
    assert let_facts.reason is ProjectLetScopeFactsReason.UPSTREAM_CONCRETE
    assert tuple(let_facts.value_types) == tuple(
        line.partition(" = ")[0] for line in let_lines
    )

    rows = _aggregate_rows(
        definition,
        input_schema,
        upstream_symbol,
        grouped=grouped,
    )
    expected = (
        ("count_direct", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_qualified", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_chained", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_computed", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_length", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        ("count_active", "count", "Int", ProjectRowFieldNullability.NON_NULL),
        (
            "distinct_normalized",
            "count_distinct",
            "Int",
            ProjectRowFieldNullability.NON_NULL,
        ),
        (
            "distinct_chained",
            "count_distinct",
            "Int",
            ProjectRowFieldNullability.NON_NULL,
        ),
        ("sum_gross", "sum", "Int", ProjectRowFieldNullability.NULLABLE),
        ("sum_chained", "sum", "Int", ProjectRowFieldNullability.NULLABLE),
        ("avg_weighted", "avg", "Float", ProjectRowFieldNullability.NULLABLE),
    )
    assert len(rows) == len(expected)
    for row, expected_row in zip(rows, expected, strict=True):
        _assert_aggregate_row(
            row,
            expected_alias=expected_row[0],
            expected_function=expected_row[1],
            expected_type=expected_row[2],
            expected_nullability=expected_row[3],
            grouped=grouped,
            upstream_symbol=upstream_symbol,
        )
        source_argument = row[0].expression
        assert isinstance(source_argument, CallExpr)
        assert isinstance(source_argument.arguments[0], NameExpr)


@pytest.mark.parametrize(
    "relations",
    (
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        exported = gross\n",
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        "        total_value = sum(amount)\n"
        "    select:\n"
        "        total = total_value\n",
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        total = sum(users.gross)\n",
        "query candidate:\n"
        "    from users\n"
        "    select:\n"
        "        subtotal = amount + tax\n"
        "        total = sum(subtotal)\n",
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        total = sum(gross) + 1\n",
    ),
)
def test_selected_let_direct_call_boundary_rejects_ordinary_hidden_qualified_alias_and_composed_forms(
    tmp_path: Path,
    relations: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )

    assert (
        build_project_aggregate_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


@pytest.mark.parametrize(
    "expression",
    (
        "count(1)",
        "sum(1)",
        "count(amount / tax)",
        "sum(amount / tax)",
        "count(amount > 1)",
        'count(matches(status, "x"))',
        "count_distinct(len(status))",
        "min(amount + tax)",
        "max(score * weight)",
        "sum(avg(amount))",
        "sum(amount) + 1",
    ),
)
def test_unsupported_inline_literal_division_comparison_call_extrema_nested_and_composed_forms_return_none(
    tmp_path: Path,
    expression: str,
) -> None:
    relations = _relation_body(
        relation_kind="query",
        name="candidate",
        grouped=False,
        select_lines=(f"result = {expression}",),
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )

    assert _candidate(definition, input_schema, upstream_symbol) is None


@pytest.mark.parametrize(
    ("let_lines", "select_lines"),
    (
        (("value = amount",), ("keep = count()", "result = min(value)")),
        (("value = amount",), ("keep = count()", "result = max(value)")),
        (("one = 1",), ("keep = count()", "result = sum(one)")),
        (("ratio = amount / tax",), ("keep = count()", "result = sum(ratio)")),
        (("flag = amount > 1",), ("keep = count()", "result = count(flag)")),
        (
            ("normalized = lower(status)",),
            ("keep = count()", "result = sum(normalized)"),
        ),
        (
            ("gross = net + tax", "net = amount"),
            ("keep = count()",),
        ),
        (("gross = gross + tax",), ("keep = count()",)),
        (("gross = net", "net = gross"), ("keep = count()",)),
        (("gross = amount", "gross = tax"), ("keep = count()",)),
        (("amount = tax",), ("keep = count()",)),
        (("users = amount",), ("keep = count()",)),
        (("gross = missing",), ("keep = count()",)),
        (("gross = wrong.amount",), ("keep = count()",)),
        (("gross = sum(amount)",), ("keep = count()",)),
        (("gross = amount",), ("gross = count()",)),
    ),
)
def test_unsupported_or_invalid_row_let_scope_blocks_the_complete_wrapper(
    tmp_path: Path,
    let_lines: tuple[str, ...],
    select_lines: tuple[str, ...],
) -> None:
    relations = _relation_body(
        relation_kind="query",
        name="candidate",
        grouped=False,
        let_lines=let_lines,
        select_lines=select_lines,
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )

    assert _candidate(definition, input_schema, upstream_symbol) is None


@pytest.mark.parametrize(
    "let_lines",
    (
        ("gross = net + tax", "net = amount"),
        ("gross = gross + tax",),
        ("gross = net", "net = gross"),
        ("gross = amount", "gross = tax"),
        ("amount = tax",),
        ("users = amount",),
        ("gross = missing",),
        ("gross = wrong.amount",),
        ("gross = sum(amount)",),
    ),
)
def test_invalid_visibility_shadow_cycle_unknown_and_aggregate_let_facts_are_non_concrete(
    tmp_path: Path,
    let_lines: tuple[str, ...],
) -> None:
    relations = _relation_body(
        relation_kind="query",
        name="candidate",
        grouped=False,
        let_lines=let_lines,
        select_lines=("keep = count()",),
    )
    _, semantic_result, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )
    assert semantic_result.model is not None
    facts = semantic_result.model.relation_let_scope_facts[definition]

    assert facts.status is ProjectLetScopeFactsStatus.UNKNOWN
    assert _candidate(definition, input_schema, upstream_symbol) is None


@pytest.mark.parametrize("grouped", (False, True))
@pytest.mark.parametrize(
    ("status", "reason"),
    (
        (
            ProjectLetScopeFactsStatus.UNKNOWN,
            ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED,
        ),
        (
            ProjectLetScopeFactsStatus.DEFERRED,
            ProjectLetScopeFactsReason.UPSTREAM_DEFERRED,
        ),
        (
            ProjectLetScopeFactsStatus.BLOCKED,
            ProjectLetScopeFactsReason.UPSTREAM_BLOCKED,
        ),
    ),
)
def test_wrappers_build_one_relation_level_let_scope_and_accept_only_absent_or_concrete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    grouped: bool,
    status: ProjectLetScopeFactsStatus,
    reason: ProjectLetScopeFactsReason,
) -> None:
    relations = _relation_body(
        relation_kind="query",
        name="candidate",
        grouped=grouped,
        let_lines=("gross = amount + tax",),
        select_lines=("total = sum(gross)",),
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )
    clause = definition.let_clause
    assert clause is not None
    calls: list[dict[str, object]] = []

    def fake_let_scope_builder(**kwargs: object) -> ProjectRelationLetScopeFacts:
        calls.append(dict(kwargs))
        return ProjectRelationLetScopeFacts(
            status=status,
            reason=reason,
            clause=clause,
            bindings=clause.bindings,
            binding_expressions={
                binding.name: binding.expression for binding in clause.bindings
            },
        )

    monkeypatch.setattr(
        aggregate_module,
        "build_project_relation_let_scope_facts",
        fake_let_scope_builder,
    )

    assert (
        _candidate(
            definition,
            input_schema,
            upstream_symbol,
            grouped=grouped,
        )
        is None
    )
    assert len(calls) == 1
    assert calls[0] == {
        "definition": definition,
        "input_schema": input_schema,
        "upstream_definition": upstream_symbol.definition,
    }


@pytest.mark.parametrize("grouped", (False, True))
def test_repeated_duplicate_alias_occurrences_keep_source_call_identity(
    tmp_path: Path,
    grouped: bool,
) -> None:
    relations = _relation_body(
        relation_kind="query",
        name="candidate",
        grouped=grouped,
        let_lines=("gross = amount + tax",),
        select_lines=("repeated = sum(gross)", "repeated = sum(gross)"),
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )
    rows = _aggregate_rows(
        definition,
        input_schema,
        upstream_symbol,
        grouped=grouped,
    )

    assert len(rows) == 2
    first_item, first_field, first_fact = rows[0]
    second_item, second_field, second_fact = rows[1]
    assert first_item.alias == second_item.alias == "repeated"
    assert first_item != second_item
    assert first_field.name == second_field.name == "repeated"
    assert first_field is not second_field
    assert first_fact is not second_fact
    assert first_fact.location != second_fact.location
    assert first_fact.location == _location(first_item.expression)
    assert second_fact.location == _location(second_item.expression)


@pytest.mark.parametrize("grouped", (False, True))
def test_valid_member_plus_invalid_expression_returns_no_partial_candidate(
    tmp_path: Path,
    grouped: bool,
) -> None:
    relations = _relation_body(
        relation_kind="query",
        name="candidate",
        grouped=grouped,
        select_lines=("valid = count()", "invalid = min(amount + tax)"),
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relations,
    )

    assert (
        _candidate(
            definition,
            input_schema,
            upstream_symbol,
            grouped=grouped,
        )
        is None
    )


def test_expression_and_row_let_aggregate_relations_are_concrete_private_and_persisted(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query aggregate_expression:\n"
            "    from users\n"
            "    select:\n"
            "        total = sum(amount + tax)\n"
            "table grouped_row_let:\n"
            "    from users\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        region\n"
            "    select:\n"
            "        region\n"
            "        total = sum(gross)\n",
        )
    )
    assert semantic_result.model is not None
    model = semantic_result.model
    aggregate_expression = _derived_definition(parse_result, "aggregate_expression")
    grouped_row_let = _derived_definition(parse_result, "grouped_row_let")
    assert tuple(model.relation_aggregate_result_facts) == (
        aggregate_expression,
        grouped_row_let,
    )

    for definition, expected_fields in (
        (aggregate_expression, ("total",)),
        (grouped_row_let, ("region", "total")),
    ):
        state = model.relation_row_schema_states[definition]
        assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
        assert state.reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
        schema = state.schema
        assert schema is not None
        assert schema is model.relation_row_schemas[definition]
        assert tuple(schema.fields) == expected_fields
        assert tuple(model.relation_aggregate_result_facts[definition]) == ("total",)
        assert schema.fields["total"].result_role is (
            ProjectRowResultRole.AGGREGATE_RESULT
        )

    assert model.relation_let_scope_facts[aggregate_expression].status is (
        ProjectLetScopeFactsStatus.ABSENT
    )
    grouped_let_facts = model.relation_let_scope_facts[grouped_row_let]
    assert grouped_let_facts.status is ProjectLetScopeFactsStatus.CONCRETE
    assert grouped_let_facts.clause is grouped_row_let.let_clause
    assert tuple(grouped_let_facts.binding_expressions) == ("gross",)

    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)
    model_source = MODEL_PATH.read_text(encoding="utf-8")
    module_source = HELPER_PATH.read_text(encoding="utf-8")
    no_group_source = inspect.getsource(build_project_aggregate_schema_facts)
    grouped_source = inspect.getsource(build_project_grouped_schema_facts)
    let_scope_source = inspect.getsource(
        aggregate_module._build_project_aggregate_let_scope_facts
    )
    selected_source = inspect.getsource(
        aggregate_module._build_project_aggregate_selected_result
    )
    argument_source = inspect.getsource(
        aggregate_module._project_aggregate_argument_type
    )

    assert project_package.__all__ == ()
    assert "aggregate_grouped_schema" not in model_source
    assert "ProjectSemanticModel" not in module_source
    assert "ProjectRowSchema(" not in no_group_source
    assert "ProjectRowSchema(" not in grouped_source
    assert "semantic_api.analyze" not in module_source
    assert "from pietto.semantic import analyze" not in module_source
    assert "import pietto.semantic as semantic_api" not in module_source
    assert "row_dependency_graph" not in module_source
    assert "row_lineage" not in module_source
    assert "_build_project_aggregate_let_scope_facts" in no_group_source
    assert "_build_project_aggregate_let_scope_facts" in grouped_source
    assert "build_project_relation_let_scope_facts" in let_scope_source
    assert "effective_semantic_aggregate_argument_expression" in argument_source
    assert "is_supported_semantic_aggregate_argument_expression" in argument_source
    assert "ProjectRowSchema(" not in selected_source
    finalizer_signature = inspect.signature(
        aggregate_module.build_project_aggregate_grouped_schema_finalization
    )
    assert tuple(finalizer_signature.parameters) == (
        "definition",
        "input_schema",
        "upstream_symbol",
        "fallback_path",
        "let_scope_facts",
    )
    assert finalizer_signature.parameters["let_scope_facts"].default is None
    for name in (
        "ProjectAggregateSchemaFacts",
        "ProjectGroupedSchemaFacts",
        "build_project_aggregate_schema_facts",
        "build_project_grouped_schema_facts",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
        assert name not in serialized


def test_plan_contract_versions_protected_boundaries_and_exact_dirty_set() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    spec = SPEC_PATH.read_text(encoding="utf-8")
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    lock = LOCK_PATH.read_text(encoding="utf-8")
    plan_lines = plan.splitlines()

    assert plan_lines.count("### Slice 6 Gate 2 Bounded Implementation Status") == 1
    assert "## Slice 6 Gate 2 Bounded Implementation Status" not in plan_lines
    assert spec.splitlines()[0] == (
        "# Phase 51 Aggregate Expression And Row-let Candidate Integration v1"
    )
    for required in (
        "Selected-let And Accepted-expression Aggregate Integration",
        "direct `CallExpr`",
        "ProjectRelationLetScopeFacts.value_types",
        "ABSENT",
        "CONCRETE",
        "UNKNOWN",
        "DEFERRED",
        "BLOCKED",
        "all-or-none",
        "exactly 15 paths",
        "Ruff remains `0.15.21`",
        "ruff check --fix",
        "/tmp/pietto-phase51-slice6-gate2-evidence-and-diff.txt",
        "There is no same-gate repair or rerun after validation begins.",
    ):
        assert required in spec, required
    for slice_number in range(7, 11):
        assert f"Slice {slice_number}" in spec

    assert '"ruff>=0.16.0"' in pyproject
    assert 'name = "ruff"\nversion = "0.16.0"' in lock

    protected_paths = (
        "docs/spec/pietto-roadmap-phase45-60-v1.md",
        "docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md",
        "docs/spec/phase51-private-result-role-output-identity-v1.md",
        "docs/spec/phase51-group-key-project-row-schema-foundation-v1.md",
        "docs/spec/phase51-aggregate-only-result-candidate-foundation-v1.md",
        "docs/spec/phase51-grouped-key-aggregate-candidate-assembly-v1.md",
        "src/pietto/_project/model.py",
        "src/pietto/_project/__init__.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/let_scope_facts.py",
        "src/pietto/_project/row_expression_schema.py",
        "src/pietto/_project/row_expression_type_facts.py",
        "src/pietto/_project/row_dependency_graph.py",
        "src/pietto/_project/row_lineage.py",
        "src/pietto/semantic",
        "src/pietto/ir",
        "src/pietto/sql",
        "scripts",
        ".github",
        "pyproject.toml",
        "uv.lock",
        "tests/fixtures",
        "tests/goldens",
        "examples",
    )
    protected = subprocess.run(
        ["git", "diff", "--exit-code", "--", *protected_paths],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert protected.returncode == 0
    assert protected.stdout == ""
    assert protected.stderr == ""

    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    dirty_paths = {line[3:] for line in status.stdout.splitlines()}
    assert dirty_paths in (set(), EXPECTED_GATE2_PATHS, PHASE52_SLICE1_GATE2_PATHS)


def _aggregate_rows(
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    *,
    grouped: bool,
) -> tuple[AggregateRow, ...]:
    if grouped:
        return _grouped_rows(definition, input_schema, upstream_symbol)
    return _no_group_rows(definition, input_schema, upstream_symbol)


def _no_group_rows(
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
) -> tuple[AggregateRow, ...]:
    facts = build_project_aggregate_schema_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert isinstance(facts, ProjectAggregateSchemaFacts)
    return tuple(
        (item, result.field, result.fact)
        for item, result in facts.selected_results.items()
    )


def _grouped_rows(
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
) -> tuple[AggregateRow, ...]:
    facts = build_project_grouped_schema_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert isinstance(facts, ProjectGroupedSchemaFacts)
    rows: list[AggregateRow] = []
    for item, result in facts.selected_results.items():
        fact = result.aggregate_fact
        if fact is not None:
            rows.append((item, result.field, fact))
    return tuple(rows)


def _candidate(
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    *,
    grouped: bool = False,
) -> ProjectAggregateSchemaFacts | ProjectGroupedSchemaFacts | None:
    if grouped:
        return build_project_grouped_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
    return build_project_aggregate_schema_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )


def _assert_aggregate_row(
    row: AggregateRow,
    *,
    expected_alias: str,
    expected_function: str,
    expected_type: str,
    expected_nullability: ProjectRowFieldNullability,
    grouped: bool,
    upstream_symbol: ProjectSymbol,
) -> None:
    item, field, fact = row
    call = item.expression
    assert isinstance(call, CallExpr)
    assert item.alias == expected_alias
    assert field.name == expected_alias
    assert field.resolved_type == ProjectResolvedType(
        name=expected_type,
        kind=ProjectResolvedTypeKind.BUILTIN,
    )
    assert field.nullability is expected_nullability
    assert field.field_def is None
    assert field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.AGGREGATE
    assert field.provenance.symbol is upstream_symbol
    assert field.provenance.location == _location(call)
    assert fact.function == expected_function
    assert fact.output_name == expected_alias
    assert fact.grouped is grouped
    assert fact.argument_count == 1
    assert fact.location == _location(call)


def _candidate_inputs(
    root: Path,
    relations: str,
    *,
    definition_name: str = "candidate",
) -> tuple[
    ProjectParseCheckResult,
    ProjectSemanticResult,
    TableDef | QueryDef,
    ProjectRowSchema,
    ProjectSymbol,
]:
    parse_result, semantic_result = _project_semantic_result(_project(root, relations))
    assert semantic_result.model is not None
    definition = _derived_definition(parse_result, definition_name)
    source = _source_definition(parse_result, "users")
    input_schema = semantic_result.model.source_row_schemas[source]
    upstream_symbol = semantic_result.model.relation_resolutions[definition.from_clause]
    return (
        parse_result,
        semantic_result,
        definition,
        input_schema,
        upstream_symbol,
    )


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project(root: Path, relations: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    (root / "models.pietto").write_text(
        "shape User:\n"
        "    active: Bool not null\n"
        "    optional_active: Bool nullable\n"
        "    amount: Int not null\n"
        "    tax: Int nullable\n"
        "    discount: Int not null\n"
        "    score: Float not null\n"
        "    weight: Float nullable\n"
        "    price: Decimal not null\n"
        "    fee: Decimal nullable\n"
        "    status: Text not null\n"
        "    region: Text nullable\n"
        "    created_at: Timestamp not null\n"
        "    customer_id: UUID not null\n"
        "    raw: Bytes not null\n"
        "    payload: Json not null\n"
        "    anything: Any nullable\n"
        'source users: User is postgres.table("users")\n'
        f"{relations}",
        encoding="utf-8",
    )
    return root


def _relation_body(
    *,
    relation_kind: str,
    name: str,
    grouped: bool,
    select_lines: tuple[str, ...],
    let_lines: tuple[str, ...] = (),
) -> str:
    body = f"{relation_kind} {name}:\n    from users\n"
    if let_lines:
        body += "    let:\n"
        body += "".join(f"        {line}\n" for line in let_lines)
    if grouped:
        body += "    group by:\n        region\n"
    body += "    select:\n"
    if grouped:
        body += "        region\n"
    body += "".join(f"        {line}\n" for line in select_lines)
    return body


def _source_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> SourceDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, SourceDef) and definition.name == name:
                return definition
    raise AssertionError(f"Source definition not found: {name}")


def _derived_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (TableDef, QueryDef)) and definition.name == name:
                return definition
    raise AssertionError(f"Derived relation not found: {name}")


def _location(expression: Expression) -> SourceLocation:
    span = expression.span
    return SourceLocation(
        path=span.path or "models.pietto",
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
