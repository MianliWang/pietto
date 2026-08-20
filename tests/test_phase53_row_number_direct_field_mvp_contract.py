from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import cast


import pytest

import pietto.semantic.window_analysis as window_analysis
from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.row_dependency_graph import ProjectRowDependencyNodeKind
from pietto._project.window_semantics import (
    WindowDependencyRole,
    WindowResultProjectFact,
    build_row_number_window_result_project_fact,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    GroupByClause,
    GroupByItem,
    LetBinding,
    LetClause,
    NameExpr,
    QueryDef,
    Script,
    SatisfyingClause,
    SelectItem,
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.ir.model import WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.generic_compatibility import (
    ConcreteTypeExpression,
    SignatureMatch,
    bind_signature,
)
from pietto.semantic.model import (
    EffectiveNullability,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.nullability_formulas import (
    NullabilityEvaluationContext,
    NullabilityEvaluationMatch,
    evaluate_signature_result_nullability,
)
from pietto.semantic.window_semantics import (
    WindowExpressionSemanticFact,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowResultAvailabilityKind,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _program(
    *,
    kind: str = "query",
    call: str = "row_number()",
    order: tuple[str, ...] = ("observed_at",),
    partition: tuple[str, ...] = (),
    direction: str | None = None,
    input_name: str = "rows",
    upstream: bool = False,
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
    where: bool = False,
    final_order: bool = False,
    limit: bool = False,
) -> str:
    prefix = (
        "shape Row:\n"
        "    id: Int not null\n"
        "    observed_at: Timestamp not null\n"
        "    label: Text\n"
        'source rows: Row is postgres.table("rows")\n'
    )
    if upstream:
        prefix += (
            "table intermediate:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "        observed_at\n"
            "        label\n"
        )
        input_name = "intermediate"
    lines = [f"{kind} ranked:", f"    from {input_name}"]
    if where:
        lines.append("    where id > 0")
    lines.append("    select:")
    lines.extend(f"        {value}" for value in before)
    lines.append(f"        rn = {call} window:")
    if partition:
        lines.append("            partition by:")
        lines.extend(f"                {value}" for value in partition)
    if order:
        lines.append("            order by:")
        suffix = f" {direction}" if direction is not None else ""
        lines.extend(f"                {value}{suffix}" for value in order)
    lines.extend(f"        {value}" for value in after)
    if final_order:
        lines.extend(("    order by:", "        observed_at"))
    if limit:
        lines.append("    limit 10")
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(
    source: str, *, path: str = "slice7.pietto"
) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path=path)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return parsed.ast, relation


def _direct_analysis(
    source: str,
    *,
    selected_output_ordinal: int | None = None,
) -> tuple[
    WindowExpressionSemanticFact | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, relation = _parsed_relation(source)
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if isinstance(target, SourceDef):
        input_schema = semantic.model.source_row_schemas[target]
    else:
        assert isinstance(target, (TableDef, QueryDef))
        input_schema = semantic.model.relation_row_schemas[target]
    ordinal = selected_output_ordinal
    if ordinal is None:
        ordinal = next(
            index
            for index, selected in enumerate(relation.select_items)
            if isinstance(selected.expression, WindowExpr)
        )
    item = relation.select_items[ordinal]
    assert isinstance(item.expression, WindowExpr)
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_row_number_window_expression(
        definition=relation,
        item=item,
        selected_output_ordinal=ordinal,
        source_id=item.expression.span.path or relation.name,
        input_schema=input_schema,
        field_qualifier=relation.from_clause.source_name,
        value_types=values,
        diagnostics=diagnostics,
    )
    return result, diagnostics, values, relation


def _canonical_fact(
    *,
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
    before: tuple[str, ...] = (),
) -> tuple[WindowExpressionSemanticFact, TableDef | QueryDef]:
    input_name = "intermediate" if upstream else "rows"
    order = f"{input_name}.observed_at" if qualified else "observed_at"
    result, diagnostics, _, relation = _direct_analysis(
        _program(
            kind=kind,
            order=(order,),
            upstream=upstream,
            before=before,
        )
    )
    assert diagnostics == []
    assert isinstance(result, WindowExpressionSemanticFact)
    return result, relation


def _project_fact(
    *,
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
) -> WindowResultProjectFact:
    semantic_fact, relation = _canonical_fact(
        kind=kind,
        qualified=qualified,
        upstream=upstream,
    )
    script, parsed_relation = _parsed_relation(
        _program(
            kind=kind,
            order=(
                f"{'intermediate' if upstream else 'rows'}.observed_at"
                if qualified
                else "observed_at",
            ),
            upstream=upstream,
        )
    )
    assert parsed_relation == relation
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == ("intermediate" if upstream else "rows")
    )
    assert isinstance(upstream_definition, (SourceDef, TableDef, QueryDef))
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=(ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE),
        name=upstream_definition.name,
        path="slice7.pietto",
        location=SourceLocation(path="slice7.pietto", line=1, column=1),
        definition=upstream_definition,
    )
    schema = ProjectRowSchema(
        fields={
            "observed_at": ProjectRowField(
                name="observed_at",
                resolved_type=ProjectResolvedType(
                    name="Timestamp",
                    kind=ProjectResolvedTypeKind.BUILTIN,
                ),
                nullability=ProjectRowFieldNullability.NON_NULL,
            )
        }
    )
    item = parsed_relation.select_items[-1]
    result = build_row_number_window_result_project_fact(
        definition=parsed_relation,
        item=item,
        selected_output_ordinal=len(parsed_relation.select_items) - 1,
        source_id="slice7.pietto",
        input_schema=schema,
        upstream_symbol=symbol,
    )
    assert isinstance(result, WindowResultProjectFact)
    assert result.semantic_fact == semantic_fact
    return result


@pytest.mark.parametrize("case", range(6))
def test_existing_window_syntax_ast_identity_and_span_authority_is_locked(
    case: int,
) -> None:
    order = ("rows.observed_at",) if case % 2 else ("observed_at",)
    script, relation = _parsed_relation(_program(order=order))
    del script
    expression = cast(WindowExpr, relation.select_items[0].expression)
    assertions = (
        isinstance(expression, WindowExpr),
        expression.spec.partition_by == (),
        len(expression.spec.order_by) == 1,
        expression.identity.namespace == (),
        expression.identity.name == "row_number",
        expression.span.path == "slice7.pietto",
    )
    assert assertions[case]


@pytest.mark.parametrize(
    "call",
    (
        "row_number()",
        "Row_Number()",
        "ROW_NUMBER()",
        "analytics.row_number()",
        "rank()",
        "dense_rank()",
        "percent_rank()",
        "cume_dist()",
        "ntile(4)",
        "lag()",
        "lead()",
        "custom()",
    ),
)
def test_exact_row_number_identity_legality_and_case_policy_are_exact(
    call: str,
) -> None:
    script, relation = _parsed_relation(_program(call=call))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    if call in {"row_number()", "rank()", "dense_rank()"}:
        assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
        assert expression in semantic.model.expression_value_types
    elif call in {"percent_rank()", "cume_dist()", "ntile(4)"}:
        assert not any(
            item.code in {"PIE-S2103", "PIE-S2104"} for item in semantic.diagnostics
        )
        assert expression in semantic.model.expression_value_types
    elif call in {"lag()", "lead()"}:
        matching = [item for item in semantic.diagnostics if item.code == "PIE-S2104"]
        assert len(matching) == 1
        assert matching[0].message == (
            f"Invalid arguments for function {call.removesuffix('()')}: "
            "expected 1 through 3, got 0"
        )
        assert matching[0].location.line == expression.call.span.line
    else:
        matching = [item for item in semantic.diagnostics if item.code == "PIE-S2103"]
        assert len(matching) == 1
        assert matching[0].location.line == expression.call.span.line


def test_row_number_zero_argument_generic_signature_is_exact() -> None:
    signature = window_analysis._ROW_NUMBER_SIGNATURE
    assert signature.type_variables == ()
    assert signature.parameters == ()
    result_expression = signature.result
    assert isinstance(result_expression, ConcreteTypeExpression)
    assert result_expression.logical_type.name == "Int"
    assert result_expression.logical_type.kind is TypeKind.BUILTIN


def test_row_number_signature_binding_returns_builtin_int_without_variables() -> None:
    result = bind_signature(window_analysis._ROW_NUMBER_SIGNATURE, ())
    assert isinstance(result, SignatureMatch)
    assert (
        result.bindings == result.constraint_evidence == result.omitted_positions == ()
    )
    assert (result.result_type.name, result.result_type.kind) == (
        "Int",
        TypeKind.BUILTIN,
    )


def test_row_number_non_null_formula_evaluates_exactly() -> None:
    result = evaluate_signature_result_nullability(
        window_analysis._ROW_NUMBER_RESULT_FORMULA,
        NullabilityEvaluationContext(argument_nullabilities=(), omitted_positions=()),
    )
    assert isinstance(result, NullabilityEvaluationMatch)
    assert result.value is EffectiveNullability.NON_NULL


@pytest.mark.parametrize(
    ("kind", "qualified"),
    (("query", False), ("query", True), ("table", False), ("table", True)),
)
def test_window_analysis_supported_result_shape_is_exact(
    kind: str, qualified: bool
) -> None:
    fact, _ = _canonical_fact(kind=kind, qualified=qualified)
    assert fact.identity.name == "row_number"
    assert fact.stage is WindowExpressionStage.WINDOW
    assert fact.result.kind is WindowResultAvailabilityKind.CONCRETE


@pytest.mark.parametrize(
    ("qualified", "upstream"),
    ((False, False), (True, False), (False, True), (True, True)),
)
def test_bare_and_immediate_qualified_order_field_success(
    qualified: bool, upstream: bool
) -> None:
    fact, _ = _canonical_fact(qualified=qualified, upstream=upstream)
    order = fact.expression.spec.order_by[0].expression
    assert isinstance(order, DottedNameExpr if qualified else NameExpr)


@pytest.mark.parametrize(
    ("kind", "upstream"),
    (("table", False), ("query", False), ("table", True), ("query", True)),
)
def test_table_query_direct_source_and_immediate_upstream_success(
    kind: str, upstream: bool
) -> None:
    fact, relation = _canonical_fact(kind=kind, upstream=upstream)
    assert isinstance(relation, TableDef if kind == "table" else QueryDef)
    assert fact.occurrence.relation_name == "ranked"


@pytest.mark.parametrize(
    "ordinary",
    (
        "id",
        "renamed = id",
        "literal = 1",
        "text = label",
        "sum_id = id + 1",
        "lowered = lower(label)",
    ),
)
def test_one_window_coexists_with_current_legal_non_window_outputs(
    ordinary: str,
) -> None:
    script, relation = _parsed_relation(_program(before=(ordinary,)))
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[1].expression)
    assert expression in semantic.model.expression_value_types
    assert "rn" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize("ordinary_count", range(4))
def test_window_occurrence_identity_uses_source_relation_ordinal_and_span(
    ordinary_count: int,
) -> None:
    before = tuple(
        "id" if index == 0 else f"id_{index} = id" for index in range(ordinary_count)
    )
    fact, relation = _canonical_fact(before=before)
    assert fact.occurrence.source_id == "slice7.pietto"
    assert fact.occurrence.relation_name == relation.name
    assert fact.occurrence.selected_output_ordinal == ordinary_count
    assert fact.occurrence.span == fact.expression.span


def test_concrete_result_is_int_non_null_window_stage() -> None:
    fact, _ = _canonical_fact()
    value_type = fact.result.value_type
    assert value_type is not None
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.resolved_type.name == "Int"
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.nullability is EffectiveNullability.NON_NULL
    assert fact.stage is WindowExpressionStage.WINDOW


@pytest.mark.parametrize("case", range(8))
def test_window_unsupported_evidence_and_diagnostic_mapping_are_exact(
    case: int,
) -> None:
    sources = (
        _program(call="percent_rank()"),
        _program(call="row_number(id)"),
        _program(partition=("id + 1",)),
        _program(order=("observed_at", "id")),
        _program(direction="desc"),
        _program(order=("id + 1",)),
        _program(order=("missing",)),
        _program(order=("other.observed_at",)),
    )
    result, diagnostics, _, _ = _direct_analysis(sources[case])
    if case in {3, 4}:
        assert isinstance(result, WindowExpressionSemanticFact)
        assert diagnostics == []
        return
    assert isinstance(result, WindowExpressionUnsupported)
    assert result.reason.strip()
    expected = "PIE-S2104" if case == 1 else "PIE-S2102" if case >= 6 else "PIE-S2103"
    assert [item.code for item in diagnostics] == [expected]


@pytest.mark.parametrize(
    "arguments", ("id", "id, observed_at", "id, observed_at, label", "id,")
)
def test_wrong_row_number_arity_uses_pie_s2104(arguments: str) -> None:
    result, diagnostics, _, relation = _direct_analysis(
        _program(call=f"row_number({arguments})")
    )
    assert isinstance(result, WindowExpressionUnsupported)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    assert [item.code for item in diagnostics] == ["PIE-S2104"]
    assert diagnostics[0].message == (
        "Invalid arguments for function row_number: expected 0, got "
        f"{len(expression.call.arguments)}"
    )


@pytest.mark.parametrize("case", range(10))
def test_unsupported_clause_and_shape_diagnostics_use_pie_s2103(case: int) -> None:
    sources = (
        _program(call="percent_rank()"),
        _program(call="cume_dist()"),
        _program(partition=("id + 1",)),
        _program(order=("observed_at", "id")),
        _program(direction="asc"),
        _program(direction="desc"),
        _program(order=("id + 1",)),
        _program(order=("lower(label)",)),
        _program(order=("1",)),
        _program(call="analytics.row_number()"),
    )
    result, diagnostics, _, _ = _direct_analysis(sources[case])
    if case in {3, 4, 5}:
        assert isinstance(result, WindowExpressionSemanticFact)
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize(
    "partition", (("id",), ("id", "label"), ("rows.id",), ("id + 1",))
)
def test_partition_shapes_remain_unsupported(partition: tuple[str, ...]) -> None:
    result, diagnostics, _, _ = _direct_analysis(_program(partition=partition))
    if partition == ("id + 1",):
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, WindowExpressionSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize(
    ("order", "direction"),
    (
        ((), None),
        (("observed_at", "id"), None),
        (("observed_at", "id", "label"), None),
        (("observed_at",), "asc"),
        (("observed_at",), "desc"),
        (("rows.observed_at",), "asc"),
    ),
)
def test_local_order_cardinality_and_direction_remain_unsupported(
    order: tuple[str, ...], direction: str | None
) -> None:
    source = _program(
        order=order, partition=("id",) if not order else (), direction=direction
    )
    result, diagnostics, _, _ = _direct_analysis(source)
    if not order:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, WindowExpressionSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize(
    ("order", "code"),
    (
        ("id + 1", "PIE-S2103"),
        ("lower(label)", "PIE-S2103"),
        ("1", "PIE-S2103"),
        ("missing", "PIE-S2102"),
        ("other.observed_at", "PIE-S2102"),
        ("rows.missing", "PIE-S2102"),
        ("rows.extra.observed_at", "PIE-S2102"),
        ("rn", "PIE-S2102"),
    ),
)
def test_computed_unknown_and_invalid_qualified_order_fields_fail_closed(
    order: str, code: str
) -> None:
    result, diagnostics, _, _ = _direct_analysis(_program(order=(order,)))
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [code]


@pytest.mark.parametrize("kind", ("table", "query"))
def test_original_source_qualifier_does_not_cross_immediate_upstream(kind: str) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(kind=kind, upstream=True, order=("rows.observed_at",))
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2102"]


@pytest.mark.parametrize("case", range(6))
def test_group_aggregate_satisfying_and_let_relations_remain_unsupported(
    case: int,
) -> None:
    script, relation = _parsed_relation(_program())
    span = relation.span
    if case in {0, 1}:
        relation = dataclasses.replace(
            relation,
            group_by_clause=GroupByClause(
                span=span,
                items=(GroupByItem(span=span, key=NameExpr(span=span, name="id")),),
            ),
        )
    elif case in {2, 3}:
        argument = () if case == 2 else (NameExpr(span=span, name="id"),)
        relation = dataclasses.replace(
            relation,
            select_items=(
                *relation.select_items,
                SelectItem(
                    span=span,
                    alias="aggregate_value",
                    expression=CallExpr(
                        span=span,
                        callee=NameExpr(
                            span=span,
                            name="count" if case == 2 else "sum",
                        ),
                        arguments=argument,
                    ),
                ),
            ),
        )
    elif case == 4:
        relation = dataclasses.replace(
            relation,
            satisfying_clause=SatisfyingClause(
                span=span,
                expression=NameExpr(span=span, name="id"),
            ),
        )
    else:
        relation = dataclasses.replace(
            relation,
            let_clause=LetClause(
                span=span,
                bindings=(
                    LetBinding(
                        span=span,
                        name="local_id",
                        expression=NameExpr(span=span, name="id"),
                    ),
                ),
            ),
        )
    semantic = analyze(script)
    source = cast(
        SourceDef,
        semantic.model.from_resolutions[
            cast(QueryDef, script.definitions[-1]).from_clause
        ],
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_row_number_window_expression(
        definition=relation,
        item=relation.select_items[0],
        selected_output_ordinal=0,
        source_id="slice7.pietto",
        input_schema=semantic.model.source_row_schemas[source],
        field_qualifier=relation.from_clause.source_name,
        value_types={},
        diagnostics=diagnostics,
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(6))
def test_window_expression_placements_outside_direct_select_fail_closed(
    case: int,
) -> None:
    semantic_source = _read("src/pietto/semantic/expressions.py")
    protected = (
        "if isinstance(expression, WindowExpr):",
        "_unknown_function_diagnostic(",
        "return _UNKNOWN_VALUE_TYPE",
        "where clause",
        "order by",
        "allow_aggregate_projection",
    )
    assert protected[case] in semantic_source


@pytest.mark.parametrize("case", range(6))
def test_multiple_nested_and_same_select_windows_remain_unsupported(case: int) -> None:
    script, relation = _parsed_relation(_program())
    first = relation.select_items[0]
    relation = dataclasses.replace(
        relation,
        select_items=(first, dataclasses.replace(first, alias=f"rn_{case}")),
    )
    semantic = analyze(script)
    source = cast(
        SourceDef,
        semantic.model.from_resolutions[
            cast(QueryDef, script.definitions[-1]).from_clause
        ],
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_row_number_window_expression(
        definition=relation,
        item=relation.select_items[case % 2],
        selected_output_ordinal=case % 2,
        source_id="slice7.pietto",
        input_schema=semantic.model.source_row_schemas[source],
        field_qualifier="rows",
        value_types={},
        diagnostics=diagnostics,
    )
    assert type(result) is WindowExpressionSemanticFact
    assert diagnostics == []
    assert result.occurrence.selected_output_ordinal == case % 2


@pytest.mark.parametrize(
    ("where", "final_order", "limit"),
    (
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, False),
        (True, True, True),
    ),
)
def test_where_final_order_and_limit_can_coexist_without_window_alias_use(
    where: bool, final_order: bool, limit: bool
) -> None:
    script, relation = _parsed_relation(
        _program(where=where, final_order=final_order, limit=limit)
    )
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    assert expression in semantic.model.expression_value_types
    assert "rn" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize(
    ("kind", "upstream"),
    (("query", False), ("table", False), ("query", True), ("table", True)),
)
def test_project_window_fact_supports_table_query_and_upstream_matrix(
    kind: str, upstream: bool
) -> None:
    fact = _project_fact(kind=kind, upstream=upstream)
    assert isinstance(fact, WindowResultProjectFact)
    assert fact.result_identity.definition.name == "ranked"


@pytest.mark.parametrize("case", range(4))
def test_project_relation_input_and_order_occurrences_are_exact(case: int) -> None:
    fact = _project_fact(qualified=bool(case % 2), upstream=bool(case // 2))
    occurrences = fact.dependency_occurrences
    assert tuple(item.global_ordinal for item in occurrences) == (0, 1)
    assert tuple(item.role_ordinal for item in occurrences) == (0, 0)
    assert tuple(item.role for item in occurrences) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.target.kind for item in occurrences) == (
        ProjectRowDependencyNodeKind.RELATION_INPUT,
        ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
    )


@pytest.mark.parametrize("qualified", (False, True))
def test_project_dependency_edges_preserve_role_and_first_occurrence_order(
    qualified: bool,
) -> None:
    fact = _project_fact(qualified=qualified)
    assert tuple(item.role for item in fact.dependency_edges) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.target for item in fact.dependency_edges) == tuple(
        item.target for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize("case", range(4))
def test_project_result_identity_and_derived_provenance_are_exact(case: int) -> None:
    fact = _project_fact(kind="table" if case % 2 else "query", upstream=case >= 2)
    assert fact.result_identity.output_name == "rn"
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.location is not None


@pytest.mark.parametrize("case", range(3))
def test_project_fact_is_transient_not_model_or_schema_state(case: int) -> None:
    source = _read("src/pietto/_project/model.py") + _read(
        "src/pietto/_project/window_persistence.py"
    )
    required = (
        "build_project_window_persistence(",
        "relation_window_result_facts:",
        "ProjectRowResultRole.WINDOW_RESULT",
    )
    assert required[case] in source


@pytest.mark.parametrize("case", range(4))
def test_window_alias_is_not_downstream_or_final_order_visible(case: int) -> None:
    script, relation = _parsed_relation(_program())
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    field = semantic.model.relation_row_schemas[relation].fields["rn"]
    assertions = (
        expression in semantic.model.expression_value_types,
        field.resolved_type.name == "Int",
        field.nullability is EffectiveNullability.NON_NULL,
        "relation_window_result_facts" in _read("src/pietto/_project/model.py"),
    )
    assert assertions[case]


@pytest.mark.parametrize("kind", ("query", "table"))
def test_ir_lowering_fails_closed_with_pie_i1000(kind: str) -> None:
    script, relation = _parsed_relation(_program(kind=kind))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[0].expression)
    lowered = lower_expr(expression, semantic.model)
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == "row_number"
    assert lowered.diagnostics == ()


@pytest.mark.parametrize("backend", ("postgres", "mysql"))
def test_postgres_and_private_mysql_requests_fail_before_sql_lowering(
    backend: str,
) -> None:
    del backend
    script, relation = _parsed_relation(_program())
    semantic = analyze(script)
    lowered = lower_expr(
        cast(WindowExpr, relation.select_items[0].expression), semantic.model
    )
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == "row_number"
    assert lowered.diagnostics == ()


@pytest.mark.parametrize("case", range(6))
def test_ordinary_scalar_direct_field_and_final_order_behavior_is_unchanged(
    case: int,
) -> None:
    sources = (
        _program(before=("id",)),
        _program(before=("renamed = id",)),
        _program(before=("text = label",)),
        _program(before=("lowered = lower(label)",)),
        _program(where=True),
        _program(final_order=True),
    )
    script, _ = _parsed_relation(sources[case])
    semantic = analyze(script)
    assert not any(
        item.code in {"PIE-S2102", "PIE-S2103"} for item in semantic.diagnostics
    )


@pytest.mark.parametrize(
    "name",
    ("rank", "dense_rank", "percent_rank", "cume_dist", "ntile", "lag", "lead"),
)
def test_non_row_number_window_identities_remain_semantically_unsupported(
    name: str,
) -> None:
    call = "ntile(4)" if name == "ntile" else f"{name}()"
    script, _ = _parsed_relation(_program(call=call))
    semantic = analyze(script)
    assert all(item.code != "PIE-S2103" for item in semantic.diagnostics)
    if name in {"lag", "lead"}:
        matching = [item for item in semantic.diagnostics if item.code == "PIE-S2104"]
        assert len(matching) == 1
        assert matching[0].message == (
            f"Invalid arguments for function {name}: expected 1 through 3, got 0"
        )
    else:
        assert all(item.code != "PIE-S2104" for item in semantic.diagnostics)


# Phase 53 Slice 13 reader migration.
