from __future__ import annotations

import dataclasses
from typing import Any, cast


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
    build_window_result_project_fact,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    GroupByClause,
    GroupByItem,
    LetBinding,
    LetClause,
    LiteralExpr,
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
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.generic_compatibility import (
    ConcreteTypeExpression,
    SignatureMatch,
    bind_signature,
)
from pietto.semantic.model import EffectiveNullability, TypeKind, ValueType
from pietto.semantic.nullability_formulas import (
    NonNullFormula,
    NullabilityEvaluationContext,
    NullabilityEvaluationMatch,
    evaluate_signature_result_nullability,
)
from pietto.semantic.window_semantics import (
    DistributionWindowPolicy,
    DistributionWindowSemanticFact,
    RankingAdvancePolicy,
    RankingWindowSemanticFact,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowResultAvailabilityKind,
)


def _program(
    *,
    kind: str = "query",
    call: str = "rank()",
    order: tuple[str, ...] = ("observed_at",),
    partition: tuple[str, ...] = (),
    direction: str | None = None,
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
    input_name = "rows"
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
    lines.append(f"        ranking_value = {call} window:")
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
    source: str, *, path: str = "slice8.pietto"
) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path=path)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return parsed.ast, relation


def _distribution_call(function_name: str, bucket_count: int = 4) -> str:
    if function_name == "ntile":
        return f"ntile({bucket_count})"
    return f"{function_name}()"


def _direct_distribution_analysis(
    source: str,
) -> tuple[
    DistributionWindowSemanticFact | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, relation = _parsed_relation(source, path="slice9.pietto")
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if isinstance(target, SourceDef):
        input_schema = semantic.model.source_row_schemas[target]
    else:
        assert isinstance(target, (TableDef, QueryDef))
        input_schema = semantic.model.relation_row_schemas[target]
    ordinal = next(
        index
        for index, selected in enumerate(relation.select_items)
        if isinstance(selected.expression, WindowExpr)
    )
    item = relation.select_items[ordinal]
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_distribution_window_expression(
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


def _canonical_distribution_fact(
    *,
    function_name: str = "percent_rank",
    bucket_count: int = 4,
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
) -> tuple[DistributionWindowSemanticFact, TableDef | QueryDef]:
    input_name = "intermediate" if upstream else "rows"
    order = f"{input_name}.observed_at" if qualified else "observed_at"
    result, diagnostics, _, relation = _direct_distribution_analysis(
        _program(
            kind=kind,
            call=_distribution_call(function_name, bucket_count),
            order=(order,),
            upstream=upstream,
            before=before,
            after=after,
        )
    )
    assert diagnostics == []
    assert isinstance(result, DistributionWindowSemanticFact)
    return result, relation


def _distribution_project_fact(
    *,
    function_name: str = "percent_rank",
    bucket_count: int = 4,
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
) -> WindowResultProjectFact:
    source = _program(
        kind=kind,
        call=_distribution_call(function_name, bucket_count),
        order=(
            f"{'intermediate' if upstream else 'rows'}.observed_at"
            if qualified
            else "observed_at",
        ),
        upstream=upstream,
    )
    script, relation = _parsed_relation(source, path="slice9.pietto")
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == ("intermediate" if upstream else "rows")
    )
    assert isinstance(upstream_definition, (SourceDef, TableDef, QueryDef))
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE,
        name=upstream_definition.name,
        path="slice9.pietto",
        location=SourceLocation(path="slice9.pietto", line=1, column=1),
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
    result = build_window_result_project_fact(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice9.pietto",
        input_schema=schema,
        upstream_symbol=symbol,
    )
    assert isinstance(result, WindowResultProjectFact)
    return result


def _assert_unsupported(
    source: str,
    *,
    code: str,
    message: str | None = None,
) -> tuple[WindowExpressionUnsupported, Diagnostic, TableDef | QueryDef]:
    result, diagnostics, _, relation = _direct_distribution_analysis(source)
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [code]
    if message is not None:
        assert diagnostics[0].message == message
    return result, diagnostics[0], relation


def test_distribution_window_semantic_fact_shape_is_frozen_and_exact() -> None:
    parameters = tuple(dataclasses.fields(DistributionWindowSemanticFact))
    assert tuple(item.name for item in parameters) == (
        "semantic_fact",
        "distribution_policy",
        "ranking_fact",
        "bucket_count",
    )
    fact, _ = _canonical_distribution_fact(function_name="percent_rank")
    params = getattr(DistributionWindowSemanticFact, "__dataclass_params__")
    assert params.frozen
    assert hasattr(DistributionWindowSemanticFact, "__slots__")
    assert all(item.kw_only for item in parameters)
    assert hash(fact) == hash(fact)


@pytest.mark.parametrize("case", range(16))
def test_distribution_window_semantic_fact_malformed_matrix_fails_closed(
    case: int,
) -> None:
    percent, _ = _canonical_distribution_fact(function_name="percent_rank")
    cume, _ = _canonical_distribution_fact(function_name="cume_dist")
    ntile, _ = _canonical_distribution_fact(function_name="ntile")
    dense_ranking = RankingWindowSemanticFact(
        semantic_fact=percent.semantic_fact,
        advance_policy=RankingAdvancePolicy.DENSE_PEER_RANK,
    )
    cume_gapped = RankingWindowSemanticFact(
        semantic_fact=cume.semantic_fact,
        advance_policy=RankingAdvancePolicy.GAPPED_PEER_RANK,
    )
    cases: tuple[tuple[dict[str, object], type[Exception]], ...] = (
        (
            {
                "semantic_fact": object(),
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": percent.ranking_fact,
                "bucket_count": None,
            },
            TypeError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": "percent_rank",
                "ranking_fact": percent.ranking_fact,
                "bucket_count": None,
            },
            TypeError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": object(),
                "bucket_count": None,
            },
            TypeError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": True,
            },
            TypeError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": None,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": dense_ranking,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": percent.ranking_fact,
                "bucket_count": 1,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": cume.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": cume_gapped,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": cume.semantic_fact,
                "distribution_policy": (
                    DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION
                ),
                "ranking_fact": cume_gapped,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": cume.semantic_fact,
                "distribution_policy": (
                    DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION
                ),
                "ranking_fact": None,
                "bucket_count": 1,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": (
                    DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION
                ),
                "ranking_fact": None,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": dense_ranking,
                "bucket_count": 4,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": 0,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": -1,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": cume.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": 4,
            },
            ValueError,
        ),
    )
    kwargs, error = cases[case]
    with pytest.raises(error):
        DistributionWindowSemanticFact(**cast(Any, kwargs))


@pytest.mark.parametrize("case", range(3))
def test_identity_to_distribution_policy_signature_mapping_is_exact_and_ordered(
    case: int,
) -> None:
    rows = window_analysis._DISTRIBUTION_FUNCTIONS
    expected = (
        ("percent_rank", DistributionWindowPolicy.PERCENT_RANK),
        ("cume_dist", DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION),
        ("ntile", DistributionWindowPolicy.BALANCED_BUCKETS),
    )
    row = rows[case % 3]
    assert len(rows) == 3
    assert (row[0].name, row[1]) == expected[case % 3]
    assert row[0].namespace == ()
    assert row[0].role.value == "window_function"


@pytest.mark.parametrize("case", range(3))
def test_distribution_signatures_are_exact(case: int) -> None:
    identity, _, signature, formula = window_analysis._DISTRIBUTION_FUNCTIONS[case]
    assert signature.type_variables == ()
    assert len(signature.parameters) == (1 if identity.name == "ntile" else 0)
    if identity.name == "ntile":
        parameter = signature.parameters[0]
        assert parameter.position == 0
        assert isinstance(parameter.type_expression, ConcreteTypeExpression)
        assert parameter.type_expression.logical_type.name == "Int"
        assert not parameter.optional
    assert isinstance(signature.result, ConcreteTypeExpression)
    assert signature.result.logical_type.name == (
        "Int" if identity.name == "ntile" else "Float"
    )
    assert formula.signature is signature


@pytest.mark.parametrize("case", range(3))
def test_distribution_signature_binding_returns_builtin_float_or_int(case: int) -> None:
    identity, _, signature, _ = window_analysis._DISTRIBUTION_FUNCTIONS[case % 3]
    arguments = (
        (window_analysis._DISTRIBUTION_INT_RESULT_IDENTITY,)
        if identity.name == "ntile"
        else ()
    )
    match = bind_signature(signature, arguments)
    assert isinstance(match, SignatureMatch)
    assert match.result_type.name == ("Int" if identity.name == "ntile" else "Float")
    assert match.result_type.kind is TypeKind.BUILTIN
    assert match.bindings == ()
    assert match.omitted_positions == ()


@pytest.mark.parametrize("case", range(3))
def test_distribution_non_null_formulas_evaluate_exactly(case: int) -> None:
    identity, _, _, formula = window_analysis._DISTRIBUTION_FUNCTIONS[case]
    nullability = (EffectiveNullability.NON_NULL,) if identity.name == "ntile" else ()
    result = evaluate_signature_result_nullability(
        formula,
        NullabilityEvaluationContext(
            argument_nullabilities=nullability,
            omitted_positions=(),
        ),
    )
    assert isinstance(result, NullabilityEvaluationMatch)
    assert result.value is EffectiveNullability.NON_NULL
    assert isinstance(formula.nullability, NonNullFormula)


def test_percent_rank_abstract_structural_semantics_are_exact() -> None:
    fact, _ = _canonical_distribution_fact(function_name="percent_rank")
    assert fact.distribution_policy is DistributionWindowPolicy.PERCENT_RANK
    assert isinstance(fact.ranking_fact, RankingWindowSemanticFact)
    assert fact.ranking_fact.advance_policy is RankingAdvancePolicy.GAPPED_PEER_RANK
    assert fact.ranking_fact.semantic_fact is fact.semantic_fact
    assert fact.bucket_count is None
    assert fact.peer_sensitive and fact.peer_key == fact.structural_order_key


def test_cume_dist_abstract_structural_semantics_are_exact() -> None:
    fact, _ = _canonical_distribution_fact(function_name="cume_dist")
    assert fact.distribution_policy is DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION
    assert fact.identity.name == "cume_dist"
    assert fact.ranking_fact is None
    assert fact.bucket_count is None
    assert fact.peer_sensitive
    assert fact.peer_key == fact.structural_order_key


@pytest.mark.parametrize("case", range(8))
def test_ntile_balanced_bucket_semantics_and_bucket_count_are_exact(case: int) -> None:
    bucket_count = (1, 2, 3, 4, 7, 8, 16, 31)[case]
    fact, _ = _canonical_distribution_fact(
        function_name="ntile",
        bucket_count=bucket_count,
    )
    assert fact.distribution_policy is DistributionWindowPolicy.BALANCED_BUCKETS
    assert fact.bucket_count == bucket_count
    assert fact.ranking_fact is None
    assert not fact.peer_sensitive
    assert fact.peer_key == ()
    assert len(fact.structural_order_key) == 1


@pytest.mark.parametrize("case", (*range(9), 14))
def test_exact_distribution_identity_legality_case_namespace_and_later_functions(
    case: int,
) -> None:
    calls = {
        0: "percent_rank()",
        1: "cume_dist()",
        2: "ntile(4)",
        3: "Percent_rank()",
        4: "CUME_DIST()",
        5: "NTILE(4)",
        6: "pkg.percent_rank()",
        7: "pkg.cume_dist()",
        8: "pkg.ntile(4)",
        14: "percent_rank_extra()",
    }
    source = _program(call=calls[case])
    result, diagnostics, _, _ = _direct_distribution_analysis(source)
    if case < 3:
        assert isinstance(result, DistributionWindowSemanticFact)
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(3))
def test_ntile_literal_ast_shape_and_argument_classification_are_exact(
    case: int,
) -> None:
    arguments = ("1", "4", "32")
    result, diagnostics, _, relation = _direct_distribution_analysis(
        _program(call=f"ntile({arguments[case]})")
    )
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert len(expression.call.arguments) == 1
    argument = expression.call.arguments[0]
    assert type(argument) is LiteralExpr
    assert type(argument.value) is int and argument.value > 0
    assert isinstance(result, DistributionWindowSemanticFact)
    assert diagnostics == []


@pytest.mark.parametrize("case", range(12))
def test_distribution_supported_result_shape_is_exact(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    qualified = (case // 3) % 2 == 1
    fact, relation = _canonical_distribution_fact(
        function_name=function_name,
        qualified=qualified,
        upstream=case >= 6,
    )
    value_type = fact.semantic_fact.result.value_type
    assert value_type is not None
    assert fact.semantic_fact.result.kind is WindowResultAvailabilityKind.CONCRETE
    assert value_type.resolved_type.name == (
        "Int" if function_name == "ntile" else "Float"
    )
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.nullability is EffectiveNullability.NON_NULL
    assert isinstance(relation, QueryDef)
    assert fact.identity.name == function_name
    assert fact.semantic_fact.occurrence.relation_name == relation.name
    assert fact.semantic_fact.stage is WindowExpressionStage.WINDOW
    assert fact.semantic_fact.expression.spec.partition_by == ()
    assert len(fact.structural_order_key) == 1
    assert isinstance(
        fact.structural_order_key[0],
        DottedNameExpr if qualified else NameExpr,
    )


@pytest.mark.parametrize("case", (3, 4, 5, 9, 10, 11))
def test_distribution_table_query_direct_and_immediate_upstream_success(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    fact, relation = _canonical_distribution_fact(
        function_name=function_name,
        kind="table",
        upstream=case >= 6,
    )
    assert isinstance(relation, TableDef)
    assert fact.identity.name == function_name
    assert len(fact.structural_order_key) == 1


@pytest.mark.parametrize("case", range(6))
def test_distribution_coexists_with_ordinary_outputs(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    before = ("id",) if case < 3 else ("copied_label = label",)
    after = ("label",) if case < 3 else ("id",)
    fact, relation = _canonical_distribution_fact(
        function_name=function_name,
        before=before,
        after=after,
    )
    assert fact.semantic_fact.occurrence.selected_output_ordinal == 1
    assert len(relation.select_items) == 3


@pytest.mark.parametrize("case", range(6))
def test_distribution_analysis_is_structurally_repeatable(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    source = _program(
        call=_distribution_call(function_name),
        order=("rows.observed_at" if case >= 3 else "observed_at",),
    )
    first, first_diagnostics, first_values, _ = _direct_distribution_analysis(source)
    second, second_diagnostics, second_values, _ = _direct_distribution_analysis(source)
    assert isinstance(first, DistributionWindowSemanticFact)
    assert first == second
    assert hash(first) == hash(cast(DistributionWindowSemanticFact, second))
    assert first_diagnostics == second_diagnostics == []
    assert first_values == second_values


@pytest.mark.parametrize("case", range(8))
def test_wrong_distribution_arity_uses_pie_s2104(case: int) -> None:
    calls = (
        "percent_rank(id)",
        "percent_rank(1, 2)",
        "cume_dist(id)",
        "cume_dist(1, 2)",
        "ntile()",
        "ntile(1, 2)",
        "ntile(1, 2, 3)",
        "percent_rank(1, 2, 3)",
    )
    expected_name = calls[case].split("(", 1)[0]
    expected_count = calls[case].count(",") + (0 if calls[case].endswith("()") else 1)
    expected_arity = 1 if expected_name == "ntile" else 0
    _, diagnostic, relation = _assert_unsupported(
        _program(call=calls[case]),
        code="PIE-S2104",
        message=(
            f"Invalid arguments for function {expected_name}: expected "
            f"{expected_arity}, got {expected_count}"
        ),
    )
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert diagnostic.location == SourceLocation(
        path=expression.call.span.path,
        line=expression.call.span.line,
        column=expression.call.span.column,
        end_line=expression.call.span.end_line,
        end_column=expression.call.span.end_column,
    )


@pytest.mark.parametrize("case", range(12))
def test_invalid_ntile_argument_uses_pie_s2104(case: int) -> None:
    arguments = (
        "0",
        "-1",
        "-9",
        "1.0",
        '"4"',
        "true",
        "false",
        "null",
        "id",
        "rows.id",
        "id + 1",
        "lower(label)",
    )
    _, diagnostic, relation = _assert_unsupported(
        _program(call=f"ntile({arguments[case]})"),
        code="PIE-S2104",
        message=(
            "Invalid arguments for function ntile: expected one positive integer "
            "literal"
        ),
    )
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert diagnostic.location == SourceLocation(
        path=expression.call.span.path,
        line=expression.call.span.line,
        column=expression.call.span.column,
        end_line=expression.call.span.end_line,
        end_column=expression.call.span.end_column,
    )


def _analyze_distribution_relation_override(
    script: Script,
    original_relation: TableDef | QueryDef,
    relation: TableDef | QueryDef,
    *,
    selected_output_ordinal: int = 0,
) -> tuple[
    DistributionWindowSemanticFact | WindowExpressionUnsupported, list[Diagnostic]
]:
    semantic = analyze(script)
    target = semantic.model.from_resolutions[original_relation.from_clause]
    input_schema = (
        semantic.model.source_row_schemas[cast(SourceDef, target)]
        if isinstance(target, SourceDef)
        else semantic.model.relation_row_schemas[cast(TableDef | QueryDef, target)]
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_distribution_window_expression(
        definition=relation,
        item=relation.select_items[selected_output_ordinal],
        selected_output_ordinal=selected_output_ordinal,
        source_id="slice9.pietto",
        input_schema=input_schema,
        field_qualifier=relation.from_clause.source_name,
        value_types={},
        diagnostics=diagnostics,
    )
    return result, diagnostics


@pytest.mark.parametrize("case", (0, 1, 2, 6, 7, 8))
def test_unsupported_distribution_clause_and_shape_uses_pie_s2103(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    span = relation.span
    if scenario == 0:
        relation = dataclasses.replace(
            relation,
            select_items=(dataclasses.replace(relation.select_items[0], alias=None),),
        )
    else:
        relation = dataclasses.replace(
            relation,
            select_items=(
                *relation.select_items,
                SelectItem(
                    span=span,
                    alias="aggregate_value",
                    expression=CallExpr(
                        span=span,
                        callee=NameExpr(span=span, name="count"),
                        arguments=(),
                    ),
                ),
            ),
        )
    result, diagnostics = _analyze_distribution_relation_override(
        script,
        cast(TableDef | QueryDef, script.definitions[-1]),
        relation,
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(12))
def test_distribution_partition_shapes_remain_unsupported(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    partitions = (
        ("id",),
        ("rows.id",),
        ("id + 1",),
        ("id", "label"),
    )
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(
            call=_distribution_call(function_name),
            partition=partitions[case // 3],
        )
    )
    if case // 3 == 2:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, DistributionWindowSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize("case", (*range(12), *range(15, 18)))
def test_distribution_order_cardinality_and_direction_remain_unsupported(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    order, direction = {
        0: ((), None),
        1: (("observed_at", "id"), None),
        2: (("observed_at",), "asc"),
        3: (("observed_at",), "desc"),
        5: (("1",), None),
    }[scenario]
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(
            call=_distribution_call(function_name),
            order=order,
            partition=("id",) if not order else (),
            direction=direction,
        )
    )
    if scenario in {1, 2, 3}:
        assert isinstance(result, DistributionWindowSemanticFact)
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", (0, 1, 2, *range(6, 18)))
def test_distribution_computed_unknown_and_invalid_qualified_order_fields_fail_closed(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    order = {
        0: "id + 1",
        2: "rows.missing",
        3: "wrong.observed_at",
        4: "rows.nested.observed_at",
        5: "lower(label)",
    }[scenario]
    expected_code = "PIE-S2103" if scenario in {0, 5} else "PIE-S2102"
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(call=_distribution_call(function_name), order=(order,))
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected_code]


@pytest.mark.parametrize("case", range(6))
def test_distribution_original_source_qualifier_does_not_cross_upstream(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    kind = "table" if case >= 3 else "query"
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(
            kind=kind,
            call=_distribution_call(function_name),
            upstream=True,
            order=("rows.observed_at",),
        )
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2102"]


@pytest.mark.parametrize("case", range(12))
def test_distribution_group_aggregate_satisfying_and_let_contexts_fail_closed(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case % 4
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    span = relation.span
    if scenario == 0:
        relation = dataclasses.replace(
            relation,
            group_by_clause=GroupByClause(
                span=span,
                items=(
                    GroupByItem(
                        span=span,
                        key=NameExpr(span=span, name="id"),
                    ),
                ),
            ),
        )
    elif scenario == 1:
        relation = dataclasses.replace(
            relation,
            select_items=(
                *relation.select_items,
                SelectItem(
                    span=span,
                    alias="aggregate_value",
                    expression=CallExpr(
                        span=span,
                        callee=NameExpr(span=span, name="sum"),
                        arguments=(NameExpr(span=span, name="id"),),
                    ),
                ),
            ),
        )
    elif scenario == 2:
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
    result, diagnostics = _analyze_distribution_relation_override(
        script,
        cast(TableDef | QueryDef, script.definitions[-1]),
        relation,
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(6))
def test_distribution_multiple_nested_and_same_select_windows_fail_closed(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    first = relation.select_items[0]
    relation = dataclasses.replace(
        relation,
        select_items=(
            first,
            dataclasses.replace(first, alias=f"distribution_value_{case}"),
        ),
    )
    result, diagnostics = _analyze_distribution_relation_override(
        script,
        cast(TableDef | QueryDef, script.definitions[-1]),
        relation,
        selected_output_ordinal=case % 2,
    )
    assert type(result) is DistributionWindowSemanticFact
    assert diagnostics == []
    assert result.semantic_fact.occurrence.selected_output_ordinal == case % 2


@pytest.mark.parametrize("case", range(12))
def test_distribution_where_final_order_and_limit_coexist_without_alias_visibility(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    combinations = (
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, True),
    )
    where, final_order, limit = combinations[scenario]
    script, relation = _parsed_relation(
        _program(
            call=_distribution_call(function_name),
            where=where,
            final_order=final_order,
            limit=limit,
        ),
        path="slice9.pietto",
    )
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert expression in semantic.model.expression_value_types
    assert "ranking_value" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize("case", range(21))
def test_project_distribution_fact_supports_function_relation_and_upstream_matrix(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    kind, qualified, upstream = (
        ("query", False, False),
        ("query", True, False),
        ("query", False, True),
        ("table", True, False),
        ("table", False, True),
        ("table", True, True),
        ("query", True, True),
    )[case // 3]
    fact = _distribution_project_fact(
        function_name=function_name,
        kind=kind,
        qualified=qualified,
        upstream=upstream,
    )
    occurrences = fact.dependency_occurrences
    assert fact.semantic_fact.identity.name == function_name
    assert fact.result_identity.definition.name == "ranked"
    assert fact.result_identity.output_name == "ranking_value"
    assert fact.result_identity.occurrence == fact.semantic_fact.occurrence
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.symbol is not None
    assert fact.provenance.location is not None
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
    assert tuple(item.role for item in fact.dependency_edges) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.target for item in fact.dependency_edges) == tuple(
        item.target for item in occurrences
    )


@pytest.mark.parametrize("case", range(6))
def test_project_ntile_literal_has_no_window_argument_dependency(case: int) -> None:
    fact = _distribution_project_fact(
        function_name="ntile",
        bucket_count=(1, 2, 3, 4, 8, 16)[case],
        qualified=case % 2 == 1,
        upstream=case >= 3,
    )
    roles = tuple(item.role for item in fact.dependency_occurrences)
    assert WindowDependencyRole.WINDOW_ARGUMENT not in roles
    assert WindowDependencyRole.WINDOW_DEFAULT not in roles
    assert roles == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )


@pytest.mark.parametrize("case", range(3))
def test_distribution_alias_is_not_row_schema_downstream_or_final_order_visible(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert expression in semantic.model.expression_value_types
    field = semantic.model.relation_row_schemas[relation].fields["ranking_value"]
    assert field.resolved_type.name == ("Float" if function_name != "ntile" else "Int")


@pytest.mark.parametrize(
    "name",
    ("lag", "lead", "first_value", "last_value", "nth_value"),
)
def test_slice12_and_future_window_identities_remain_unsupported(name: str) -> None:
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(call=f"{name}()")
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]
    assert diagnostics[0].message == f"Unknown function: {name}"


@pytest.mark.parametrize("case", (3, 4, 6, 7, 8, 12, 13, 14))
def test_distribution_diagnostic_code_message_location_and_order_are_exact(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    if scenario == 1:
        source = _program(call=f"{function_name}(1)")
        expected_code = "PIE-S2104"
        location_kind = "call"
    elif scenario == 2:
        source = _program(
            call=_distribution_call(function_name),
            order=("missing",),
        )
        expected_code = "PIE-S2102"
        location_kind = "order"
    else:
        source = _program(call=f"X{_distribution_call(function_name)}")
        expected_code = "PIE-S2103"
        location_kind = "call"
    result, diagnostics, _, relation = _direct_distribution_analysis(source)
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected_code]
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    span = (
        expression.spec.order_by[0].expression.span
        if location_kind == "order"
        else expression.call.span
    )
    assert diagnostics[0].location == SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
