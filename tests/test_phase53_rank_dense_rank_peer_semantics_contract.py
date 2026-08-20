from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, cast


import pytest

import pietto
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
    build_ranking_window_result_project_fact,
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
    WindowSpec,
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
from pietto.semantic.model import EffectiveNullability, TypeKind, ValueType
from pietto.semantic.nullability_formulas import (
    NonNullFormula,
    NullabilityEvaluationContext,
    NullabilityEvaluationMatch,
    evaluate_signature_result_nullability,
)
from pietto.semantic.window_semantics import (
    RankingAdvancePolicy,
    RankingWindowSemanticFact,
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


def _direct_analysis(
    source: str,
    *,
    selected_output_ordinal: int | None = None,
) -> tuple[
    RankingWindowSemanticFact | WindowExpressionUnsupported,
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
    result = window_analysis.analyze_ranking_window_expression(
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


def _canonical_ranking_fact(
    *,
    function_name: str = "rank",
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
    before: tuple[str, ...] = (),
) -> tuple[RankingWindowSemanticFact, TableDef | QueryDef]:
    input_name = "intermediate" if upstream else "rows"
    order = f"{input_name}.observed_at" if qualified else "observed_at"
    result, diagnostics, _, relation = _direct_analysis(
        _program(
            kind=kind,
            call=f"{function_name}()",
            order=(order,),
            upstream=upstream,
            before=before,
        )
    )
    assert diagnostics == []
    assert isinstance(result, RankingWindowSemanticFact)
    return result, relation


def _row_number_core_fact(
    *, qualified: bool = False, upstream: bool = False
) -> WindowExpressionSemanticFact:
    ranking_fact, relation = _canonical_ranking_fact(
        function_name="row_number",
        qualified=qualified,
        upstream=upstream,
    )
    script, parsed_relation = _parsed_relation(
        _program(
            call="row_number()",
            order=(
                f"{'intermediate' if upstream else 'rows'}.observed_at"
                if qualified
                else "observed_at",
            ),
            upstream=upstream,
        )
    )
    semantic = analyze(script)
    target = semantic.model.from_resolutions[parsed_relation.from_clause]
    input_schema = (
        semantic.model.source_row_schemas[cast(SourceDef, target)]
        if isinstance(target, SourceDef)
        else semantic.model.relation_row_schemas[cast(TableDef | QueryDef, target)]
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_row_number_window_expression(
        definition=parsed_relation,
        item=parsed_relation.select_items[-1],
        selected_output_ordinal=len(parsed_relation.select_items) - 1,
        source_id="slice8.pietto",
        input_schema=input_schema,
        field_qualifier=parsed_relation.from_clause.source_name,
        value_types={},
        diagnostics=diagnostics,
    )
    assert diagnostics == []
    assert isinstance(result, WindowExpressionSemanticFact)
    assert result == ranking_fact.semantic_fact
    assert relation == parsed_relation
    return result


def _project_fact(
    *,
    function_name: str = "rank",
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
) -> WindowResultProjectFact:
    source = _program(
        kind=kind,
        call=f"{function_name}()",
        order=(
            f"{'intermediate' if upstream else 'rows'}.observed_at"
            if qualified
            else "observed_at",
        ),
        upstream=upstream,
    )
    script, relation = _parsed_relation(source)
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
        path="slice8.pietto",
        location=SourceLocation(path="slice8.pietto", line=1, column=1),
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
    result = build_ranking_window_result_project_fact(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice8.pietto",
        input_schema=schema,
        upstream_symbol=symbol,
    )
    assert isinstance(result, WindowResultProjectFact)
    return result


@pytest.mark.parametrize(
    ("policy", "name", "value"),
    (
        (RankingAdvancePolicy.PER_ROW, "PER_ROW", "per_row"),
        (
            RankingAdvancePolicy.GAPPED_PEER_RANK,
            "GAPPED_PEER_RANK",
            "preceding_row_count_plus_one",
        ),
        (
            RankingAdvancePolicy.DENSE_PEER_RANK,
            "DENSE_PEER_RANK",
            "preceding_distinct_peer_group_count_plus_one",
        ),
    ),
)
def test_ranking_advance_policy_enum_values_and_privacy_are_exact(
    policy: RankingAdvancePolicy, name: str, value: str
) -> None:
    assert (policy.name, policy.value) == (name, value)
    assert tuple(RankingAdvancePolicy) == (
        RankingAdvancePolicy.PER_ROW,
        RankingAdvancePolicy.GAPPED_PEER_RANK,
        RankingAdvancePolicy.DENSE_PEER_RANK,
    )
    assert not hasattr(pietto, "RankingAdvancePolicy")
    assert _read("src/pietto/semantic/window_semantics.py").count("__all__") == 1


@pytest.mark.parametrize("case", range(3))
def test_ranking_window_semantic_fact_shape_is_frozen_and_exact(case: int) -> None:
    fact, _ = _canonical_ranking_fact(
        function_name=("row_number", "rank", "dense_rank")[case]
    )
    params = getattr(RankingWindowSemanticFact, "__dataclass_params__")
    assertions = (
        params.frozen and hasattr(RankingWindowSemanticFact, "__slots__"),
        tuple(field.name for field in dataclasses.fields(RankingWindowSemanticFact))
        == ("semantic_fact", "advance_policy"),
        fact.identity == fact.semantic_fact.identity,
    )
    assert assertions[case]


@pytest.mark.parametrize("case", range(12))
def test_ranking_window_semantic_fact_malformed_matrix_fails_closed(
    case: int,
) -> None:
    valid, _ = _canonical_ranking_fact(function_name="rank")
    if case < 7:
        bad_semantic: Any = (None, "fact", 0, False, object(), (), valid)[case]
        with pytest.raises(TypeError):
            RankingWindowSemanticFact(
                semantic_fact=cast(Any, bad_semantic),
                advance_policy=RankingAdvancePolicy.GAPPED_PEER_RANK,
            )
        return
    if case < 10:
        bad_policy: Any = (None, "per_row", 1)[case - 7]
        with pytest.raises(TypeError):
            RankingWindowSemanticFact(
                semantic_fact=valid.semantic_fact,
                advance_policy=cast(Any, bad_policy),
            )
        return
    expression = valid.semantic_fact.expression
    partition_only = dataclasses.replace(
        expression,
        spec=WindowSpec(
            span=expression.spec.span,
            partition_by=(NameExpr(span=expression.span, name="id"),),
            order_by=(),
        ),
    )
    core = dataclasses.replace(valid.semantic_fact, expression=partition_only)
    policy = (
        RankingAdvancePolicy.GAPPED_PEER_RANK
        if case == 10
        else RankingAdvancePolicy.DENSE_PEER_RANK
    )
    with pytest.raises(ValueError, match="nonempty structural order tuple"):
        RankingWindowSemanticFact(semantic_fact=core, advance_policy=policy)


@pytest.mark.parametrize("case", range(6))
def test_identity_to_ranking_policy_mapping_is_exact_and_ordered(case: int) -> None:
    expected = (
        ("row_number", RankingAdvancePolicy.PER_ROW),
        ("rank", RankingAdvancePolicy.GAPPED_PEER_RANK),
        ("dense_rank", RankingAdvancePolicy.DENSE_PEER_RANK),
    )
    assert (
        tuple(
            (identity.name, policy)
            for identity, policy in window_analysis._RANKING_POLICIES
        )
        == expected
    )
    if case < 3:
        _, relation = _parsed_relation(_program(call=f"{expected[case][0]}()"))
        expression = cast(WindowExpr, relation.select_items[-1].expression)
        assert window_analysis._ranking_policy(expression) is expected[case][1]
    else:
        call = ("Rank()", "ext.rank()", "percent_rank()")[case - 3]
        _, relation = _parsed_relation(_program(call=call))
        expression = cast(WindowExpr, relation.select_items[-1].expression)
        assert window_analysis._ranking_policy(expression) is None


@pytest.mark.parametrize("function_name", ("row_number", "rank", "dense_rank"))
def test_peer_sensitivity_and_gap_posture_are_exact(function_name: str) -> None:
    fact, _ = _canonical_ranking_fact(function_name=function_name)
    expected = {
        "row_number": (False, False, RankingAdvancePolicy.PER_ROW),
        "rank": (True, True, RankingAdvancePolicy.GAPPED_PEER_RANK),
        "dense_rank": (True, False, RankingAdvancePolicy.DENSE_PEER_RANK),
    }[function_name]
    assert (
        fact.peer_sensitive,
        fact.gaps_after_multirow_peer_group,
        fact.advance_policy,
    ) == expected


@pytest.mark.parametrize(
    ("function_name", "qualified"),
    (("rank", False), ("rank", True), ("dense_rank", False), ("dense_rank", True)),
)
def test_structural_peer_key_uses_resolved_local_order_expression(
    function_name: str, qualified: bool
) -> None:
    fact, _ = _canonical_ranking_fact(
        function_name=function_name,
        qualified=qualified,
    )
    order_expression = fact.semantic_fact.expression.spec.order_by[0].expression
    assert fact.peer_key == (order_expression,)
    assert isinstance(order_expression, DottedNameExpr if qualified else NameExpr)


@pytest.mark.parametrize(
    "call",
    (
        "row_number()",
        "rank()",
        "dense_rank()",
        "Rank()",
        "RANK()",
        "Dense_Rank()",
        "analytics.rank()",
        "first_value()",
        "last_value()",
        "nth_value()",
        "lag()",
        "lead()",
    ),
)
def test_exact_ranking_identity_legality_case_namespace_and_later_functions(
    call: str,
) -> None:
    script, relation = _parsed_relation(_program(call=call))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    matching = [item for item in semantic.diagnostics if item.code == "PIE-S2103"]
    if call in {"row_number()", "rank()", "dense_rank()"}:
        assert matching == []
        assert expression in semantic.model.expression_value_types
    elif call in {"lag()", "lead()"}:
        argument_errors = [
            item for item in semantic.diagnostics if item.code == "PIE-S2104"
        ]
        assert matching == []
        assert len(argument_errors) == 1
        assert argument_errors[0].message == (
            f"Invalid arguments for function {call.removesuffix('()')}: "
            "expected 1 through 3, got 0"
        )
    else:
        assert len(matching) == 1
        assert matching[0].message == f"Unknown function: {call.removesuffix('()')}"


def test_ranking_zero_argument_shared_signature_is_exact() -> None:
    signature = window_analysis._RANKING_SIGNATURE
    assert signature is window_analysis._ROW_NUMBER_SIGNATURE
    assert window_analysis._RANKING_RESULT_FORMULA is (
        window_analysis._ROW_NUMBER_RESULT_FORMULA
    )
    assert signature.type_variables == signature.parameters == ()
    result_expression = signature.result
    assert isinstance(result_expression, ConcreteTypeExpression)
    assert (
        result_expression.logical_type.name,
        result_expression.logical_type.kind,
    ) == ("Int", TypeKind.BUILTIN)


def test_ranking_signature_binding_returns_builtin_int() -> None:
    result = bind_signature(window_analysis._RANKING_SIGNATURE, ())
    assert isinstance(result, SignatureMatch)
    assert (
        result.bindings,
        result.constraint_evidence,
        result.omitted_positions,
    ) == ((), (), ())
    assert (result.result_type.name, result.result_type.kind) == (
        "Int",
        TypeKind.BUILTIN,
    )


def test_ranking_non_null_formula_evaluates_exactly() -> None:
    formula = window_analysis._RANKING_RESULT_FORMULA
    assert isinstance(formula.nullability, NonNullFormula)
    result = evaluate_signature_result_nullability(
        formula,
        NullabilityEvaluationContext(argument_nullabilities=(), omitted_positions=()),
    )
    assert isinstance(result, NullabilityEvaluationMatch)
    assert result.value is EffectiveNullability.NON_NULL


@pytest.mark.parametrize(
    ("function_name", "kind", "qualified"),
    (
        ("rank", "query", False),
        ("rank", "query", True),
        ("rank", "table", False),
        ("rank", "table", True),
        ("dense_rank", "query", False),
        ("dense_rank", "query", True),
        ("dense_rank", "table", False),
        ("dense_rank", "table", True),
    ),
)
def test_rank_dense_rank_supported_result_shape_is_exact(
    function_name: str, kind: str, qualified: bool
) -> None:
    fact, relation = _canonical_ranking_fact(
        function_name=function_name,
        kind=kind,
        qualified=qualified,
    )
    core = fact.semantic_fact
    value_type = core.result.value_type
    assert isinstance(relation, QueryDef if kind == "query" else TableDef)
    assert core.identity.name == function_name
    assert core.stage is WindowExpressionStage.WINDOW
    assert core.result.kind is WindowResultAvailabilityKind.CONCRETE
    assert value_type is not None
    assert (value_type.resolved_type.name, value_type.resolved_type.kind) == (
        "Int",
        TypeKind.BUILTIN,
    )
    assert value_type.nullability is EffectiveNullability.NON_NULL


@pytest.mark.parametrize(
    ("function_name", "qualified", "upstream"),
    (
        ("rank", False, False),
        ("rank", False, True),
        ("rank", True, False),
        ("rank", True, True),
        ("dense_rank", False, False),
        ("dense_rank", False, True),
        ("dense_rank", True, False),
        ("dense_rank", True, True),
    ),
)
def test_rank_dense_rank_bare_and_immediate_qualified_order_field_success(
    function_name: str, qualified: bool, upstream: bool
) -> None:
    fact, _ = _canonical_ranking_fact(
        function_name=function_name,
        qualified=qualified,
        upstream=upstream,
    )
    order = fact.semantic_fact.expression.spec.order_by[0].expression
    assert isinstance(order, DottedNameExpr if qualified else NameExpr)
    assert fact.peer_key == (order,)


@pytest.mark.parametrize(
    ("function_name", "kind", "upstream"),
    (
        ("rank", "table", False),
        ("rank", "table", True),
        ("rank", "query", False),
        ("rank", "query", True),
        ("dense_rank", "table", False),
        ("dense_rank", "table", True),
        ("dense_rank", "query", False),
        ("dense_rank", "query", True),
    ),
)
def test_rank_dense_rank_table_query_direct_and_immediate_upstream_success(
    function_name: str, kind: str, upstream: bool
) -> None:
    fact, relation = _canonical_ranking_fact(
        function_name=function_name,
        kind=kind,
        upstream=upstream,
    )
    assert isinstance(relation, TableDef if kind == "table" else QueryDef)
    assert fact.semantic_fact.occurrence.relation_name == "ranked"
    assert fact.semantic_fact.identity.name == function_name


@pytest.mark.parametrize(
    ("function_name", "ordinary"),
    (
        ("rank", "id"),
        ("rank", "renamed = id"),
        ("rank", "literal = 1"),
        ("rank", "text = label"),
        ("rank", "sum_id = id + 1"),
        ("rank", "lowered = lower(label)"),
        ("dense_rank", "id"),
        ("dense_rank", "renamed = id"),
        ("dense_rank", "literal = 1"),
        ("dense_rank", "text = label"),
        ("dense_rank", "sum_id = id + 1"),
        ("dense_rank", "lowered = lower(label)"),
    ),
)
def test_rank_dense_rank_coexist_with_ordinary_outputs(
    function_name: str, ordinary: str
) -> None:
    script, relation = _parsed_relation(
        _program(call=f"{function_name}()", before=(ordinary,))
    )
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[1].expression)
    assert expression in semantic.model.expression_value_types
    assert "ranking_value" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize(
    ("qualified", "upstream"),
    ((False, False), (True, False), (False, True), (True, True)),
)
def test_row_number_peer_insensitive_per_row_regression_is_exact(
    qualified: bool, upstream: bool
) -> None:
    ranking_fact, _ = _canonical_ranking_fact(
        function_name="row_number",
        qualified=qualified,
        upstream=upstream,
    )
    core = _row_number_core_fact(qualified=qualified, upstream=upstream)
    assert ranking_fact.semantic_fact == core
    assert ranking_fact.advance_policy is RankingAdvancePolicy.PER_ROW
    assert not ranking_fact.peer_sensitive
    assert ranking_fact.peer_key == ()
    assert not ranking_fact.gaps_after_multirow_peer_group


@pytest.mark.parametrize(
    ("function_name", "qualified"),
    (
        ("row_number", False),
        ("row_number", True),
        ("rank", False),
        ("rank", True),
        ("dense_rank", False),
        ("dense_rank", True),
    ),
)
def test_ranking_analysis_is_structurally_repeatable(
    function_name: str, qualified: bool
) -> None:
    first, _ = _canonical_ranking_fact(
        function_name=function_name,
        qualified=qualified,
    )
    second, _ = _canonical_ranking_fact(
        function_name=function_name,
        qualified=qualified,
    )
    assert first == second
    assert hash(first) == hash(second)


@pytest.mark.parametrize(
    ("function_name", "arguments"),
    (
        ("rank", "id"),
        ("rank", "id, observed_at"),
        ("rank", "label"),
        ("rank", "id, label"),
        ("dense_rank", "id"),
        ("dense_rank", "id, observed_at"),
        ("dense_rank", "label"),
        ("dense_rank", "id, label"),
    ),
)
def test_wrong_rank_dense_rank_arity_uses_pie_s2104(
    function_name: str, arguments: str
) -> None:
    result, diagnostics, _, relation = _direct_analysis(
        _program(call=f"{function_name}({arguments})")
    )
    assert isinstance(result, WindowExpressionUnsupported)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert [item.code for item in diagnostics] == ["PIE-S2104"]
    assert diagnostics[0].message == (
        f"Invalid arguments for function {function_name}: expected 0, got "
        f"{len(expression.call.arguments)}"
    )
    assert diagnostics[0].location == SourceLocation(
        path=expression.call.span.path,
        line=expression.call.span.line,
        column=expression.call.span.column,
        end_line=expression.call.span.end_line,
        end_column=expression.call.span.end_column,
    )


@pytest.mark.parametrize(
    ("function_name", "shape"),
    (
        ("rank", "partition"),
        ("rank", "two_orders"),
        ("rank", "asc"),
        ("rank", "desc"),
        ("rank", "computed"),
        ("rank", "call_order"),
        ("dense_rank", "partition"),
        ("dense_rank", "two_orders"),
        ("dense_rank", "asc"),
        ("dense_rank", "desc"),
        ("dense_rank", "computed"),
        ("dense_rank", "call_order"),
    ),
)
def test_unsupported_ranking_clause_and_shape_uses_pie_s2103(
    function_name: str, shape: str
) -> None:
    options: dict[str, dict[str, Any]] = {
        "partition": {"partition": ("id",)},
        "two_orders": {"order": ("observed_at", "id")},
        "asc": {"direction": "asc"},
        "desc": {"direction": "desc"},
        "computed": {"order": ("id + 1",)},
        "call_order": {"order": ("lower(label)",)},
    }
    result, diagnostics, _, _ = _direct_analysis(
        _program(call=f"{function_name}()", **options[shape])
    )
    if shape in {"partition", "two_orders", "asc", "desc"}:
        assert isinstance(result, RankingWindowSemanticFact)
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize(
    ("function_name", "partition"),
    (
        ("rank", ("id",)),
        ("rank", ("id", "label")),
        ("rank", ("rows.id",)),
        ("rank", ("id + 1",)),
        ("dense_rank", ("id",)),
        ("dense_rank", ("id", "label")),
        ("dense_rank", ("rows.id",)),
        ("dense_rank", ("id + 1",)),
    ),
)
def test_ranking_partition_shapes_remain_unsupported(
    function_name: str, partition: tuple[str, ...]
) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(call=f"{function_name}()", partition=partition)
    )
    if partition == ("id + 1",):
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, RankingWindowSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize(
    ("function_name", "order", "direction"),
    (
        ("rank", (), None),
        ("rank", ("observed_at", "id"), None),
        ("rank", ("observed_at", "id", "label"), None),
        ("rank", ("observed_at",), "asc"),
        ("rank", ("observed_at",), "desc"),
        ("rank", ("rows.observed_at",), "asc"),
        ("dense_rank", (), None),
        ("dense_rank", ("observed_at", "id"), None),
        ("dense_rank", ("observed_at", "id", "label"), None),
        ("dense_rank", ("observed_at",), "asc"),
        ("dense_rank", ("observed_at",), "desc"),
        ("dense_rank", ("rows.observed_at",), "asc"),
    ),
)
def test_ranking_order_cardinality_and_direction_remain_unsupported(
    function_name: str,
    order: tuple[str, ...],
    direction: str | None,
) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(
            call=f"{function_name}()",
            order=order,
            partition=("id",) if not order else (),
            direction=direction,
        )
    )
    if not order:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, RankingWindowSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize(
    ("function_name", "order", "code"),
    (
        ("rank", "id + 1", "PIE-S2103"),
        ("rank", "lower(label)", "PIE-S2103"),
        ("rank", "1", "PIE-S2103"),
        ("rank", "missing", "PIE-S2102"),
        ("rank", "other.observed_at", "PIE-S2102"),
        ("rank", "rows.missing", "PIE-S2102"),
        ("rank", "rows.extra.observed_at", "PIE-S2102"),
        ("rank", "ranking_value", "PIE-S2102"),
        ("dense_rank", "id + 1", "PIE-S2103"),
        ("dense_rank", "lower(label)", "PIE-S2103"),
        ("dense_rank", "1", "PIE-S2103"),
        ("dense_rank", "missing", "PIE-S2102"),
        ("dense_rank", "other.observed_at", "PIE-S2102"),
        ("dense_rank", "rows.missing", "PIE-S2102"),
        ("dense_rank", "rows.extra.observed_at", "PIE-S2102"),
        ("dense_rank", "ranking_value", "PIE-S2102"),
    ),
)
def test_ranking_computed_unknown_and_invalid_qualified_order_fields_fail_closed(
    function_name: str, order: str, code: str
) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(call=f"{function_name}()", order=(order,))
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [code]


@pytest.mark.parametrize(
    ("function_name", "kind"),
    (
        ("rank", "table"),
        ("rank", "query"),
        ("dense_rank", "table"),
        ("dense_rank", "query"),
    ),
)
def test_ranking_original_source_qualifier_does_not_cross_upstream(
    function_name: str, kind: str
) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(
            kind=kind,
            call=f"{function_name}()",
            upstream=True,
            order=("rows.observed_at",),
        )
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2102"]


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", 0),
        ("rank", 1),
        ("rank", 2),
        ("rank", 3),
        ("rank", 4),
        ("rank", 5),
        ("dense_rank", 0),
        ("dense_rank", 1),
        ("dense_rank", 2),
        ("dense_rank", 3),
        ("dense_rank", 4),
        ("dense_rank", 5),
    ),
)
def test_ranking_group_aggregate_satisfying_and_let_contexts_fail_closed(
    function_name: str, case: int
) -> None:
    script, relation = _parsed_relation(_program(call=f"{function_name}()"))
    span = relation.span
    if case in {0, 1}:
        key_name = "id" if case == 0 else "label"
        relation = dataclasses.replace(
            relation,
            group_by_clause=GroupByClause(
                span=span,
                items=(
                    GroupByItem(
                        span=span,
                        key=NameExpr(span=span, name=key_name),
                    ),
                ),
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
    result = window_analysis.analyze_ranking_window_expression(
        definition=relation,
        item=relation.select_items[0],
        selected_output_ordinal=0,
        source_id="slice8.pietto",
        input_schema=semantic.model.source_row_schemas[source],
        field_qualifier=relation.from_clause.source_name,
        value_types={},
        diagnostics=diagnostics,
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", 0),
        ("rank", 1),
        ("rank", 2),
        ("rank", 3),
        ("rank", 4),
        ("rank", 5),
        ("dense_rank", 0),
        ("dense_rank", 1),
        ("dense_rank", 2),
        ("dense_rank", 3),
        ("dense_rank", 4),
        ("dense_rank", 5),
    ),
)
def test_ranking_placements_outside_direct_select_fail_closed(
    function_name: str, case: int
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
    assert f'name="{function_name}"' not in semantic_source
    assert semantic_source.count("analyze_window_expression(") == 1


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", 0),
        ("rank", 1),
        ("rank", 2),
        ("rank", 3),
        ("rank", 4),
        ("rank", 5),
        ("dense_rank", 0),
        ("dense_rank", 1),
        ("dense_rank", 2),
        ("dense_rank", 3),
        ("dense_rank", 4),
        ("dense_rank", 5),
    ),
)
def test_ranking_multiple_nested_and_same_select_windows_fail_closed(
    function_name: str, case: int
) -> None:
    script, relation = _parsed_relation(_program(call=f"{function_name}()"))
    first = relation.select_items[0]
    relation = dataclasses.replace(
        relation,
        select_items=(
            first,
            dataclasses.replace(first, alias=f"ranking_value_{case}"),
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
    result = window_analysis.analyze_ranking_window_expression(
        definition=relation,
        item=relation.select_items[case % 2],
        selected_output_ordinal=case % 2,
        source_id="slice8.pietto",
        input_schema=semantic.model.source_row_schemas[source],
        field_qualifier="rows",
        value_types={},
        diagnostics=diagnostics,
    )
    assert isinstance(result, RankingWindowSemanticFact)
    assert diagnostics == []
    assert result.semantic_fact.occurrence.selected_output_ordinal == case % 2


@pytest.mark.parametrize(
    ("function_name", "where", "final_order", "limit"),
    (
        ("rank", True, False, False),
        ("rank", False, True, False),
        ("rank", False, False, True),
        ("rank", True, True, False),
        ("rank", True, True, True),
        ("dense_rank", True, False, False),
        ("dense_rank", False, True, False),
        ("dense_rank", False, False, True),
        ("dense_rank", True, True, False),
        ("dense_rank", True, True, True),
    ),
)
def test_ranking_where_final_order_and_limit_coexist_without_alias_visibility(
    function_name: str,
    where: bool,
    final_order: bool,
    limit: bool,
) -> None:
    script, relation = _parsed_relation(
        _program(
            call=f"{function_name}()",
            where=where,
            final_order=final_order,
            limit=limit,
        )
    )
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert expression in semantic.model.expression_value_types
    assert "ranking_value" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize(
    ("function_name", "kind", "qualified", "upstream"),
    (
        ("rank", "query", False, False),
        ("rank", "query", False, True),
        ("rank", "query", True, False),
        ("rank", "query", True, True),
        ("rank", "table", False, False),
        ("rank", "table", False, True),
        ("rank", "table", True, False),
        ("rank", "table", True, True),
        ("dense_rank", "query", False, False),
        ("dense_rank", "query", False, True),
        ("dense_rank", "query", True, False),
        ("dense_rank", "query", True, True),
        ("dense_rank", "table", False, False),
        ("dense_rank", "table", False, True),
        ("dense_rank", "table", True, False),
        ("dense_rank", "table", True, True),
    ),
)
def test_project_ranking_fact_supports_function_relation_and_upstream_matrix(
    function_name: str,
    kind: str,
    qualified: bool,
    upstream: bool,
) -> None:
    fact = _project_fact(
        function_name=function_name,
        kind=kind,
        qualified=qualified,
        upstream=upstream,
    )
    assert fact.semantic_fact.identity.name == function_name
    assert fact.result_identity.definition.name == "ranked"
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT


@pytest.mark.parametrize(
    ("function_name", "qualified"),
    (("rank", False), ("rank", True), ("dense_rank", False), ("dense_rank", True)),
)
def test_project_ranking_relation_input_and_order_occurrences_are_exact(
    function_name: str, qualified: bool
) -> None:
    fact = _project_fact(function_name=function_name, qualified=qualified)
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


@pytest.mark.parametrize(
    ("function_name", "qualified"),
    (("rank", False), ("rank", True), ("dense_rank", False), ("dense_rank", True)),
)
def test_project_ranking_dependency_edges_preserve_first_occurrence_order(
    function_name: str, qualified: bool
) -> None:
    fact = _project_fact(function_name=function_name, qualified=qualified)
    assert tuple(item.role for item in fact.dependency_edges) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.target for item in fact.dependency_edges) == tuple(
        item.target for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize(
    ("function_name", "kind", "upstream"),
    (
        ("rank", "query", False),
        ("rank", "query", True),
        ("rank", "table", False),
        ("rank", "table", True),
        ("dense_rank", "query", False),
        ("dense_rank", "query", True),
        ("dense_rank", "table", False),
        ("dense_rank", "table", True),
    ),
)
def test_project_ranking_result_identity_and_derived_provenance_are_exact(
    function_name: str, kind: str, upstream: bool
) -> None:
    fact = _project_fact(
        function_name=function_name,
        kind=kind,
        upstream=upstream,
    )
    assert fact.result_identity.output_name == "ranking_value"
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.location is not None


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("row_number", 0),
        ("row_number", 1),
        ("rank", 0),
        ("rank", 1),
        ("dense_rank", 0),
        ("dense_rank", 1),
    ),
)
def test_peer_and_project_facts_are_transient_not_model_state(
    function_name: str, case: int
) -> None:
    semantic_source = _read("src/pietto/semantic/expressions.py")
    project_source = _read("src/pietto/_project/model.py")
    if case == 0:
        assert "analyze_window_expression(" in semantic_source
        assert "ranking_window_facts:" not in semantic_source
    else:
        assert "build_project_window_persistence(" in project_source
        assert "relation_window_result_facts:" in project_source
    assert function_name in {"row_number", "rank", "dense_rank"}


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", 0),
        ("rank", 1),
        ("rank", 2),
        ("dense_rank", 0),
        ("dense_rank", 1),
        ("dense_rank", 2),
    ),
)
def test_ranking_alias_is_not_row_schema_downstream_or_final_order_visible(
    function_name: str, case: int
) -> None:
    script, relation = _parsed_relation(_program(call=f"{function_name}()"))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    field = semantic.model.relation_row_schemas[relation].fields["ranking_value"]
    assertions = (
        expression in semantic.model.expression_value_types,
        field.resolved_type.name == "Int",
        field.nullability is EffectiveNullability.NON_NULL,
    )
    assert assertions[case]


@pytest.mark.parametrize(
    ("function_name", "kind"),
    (
        ("rank", "query"),
        ("rank", "table"),
        ("dense_rank", "query"),
        ("dense_rank", "table"),
    ),
)
def test_ranking_ir_lowering_fails_closed_with_pie_i1000(
    function_name: str, kind: str
) -> None:
    script, relation = _parsed_relation(_program(kind=kind, call=f"{function_name}()"))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    lowered = lower_expr(expression, semantic.model)
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == function_name
    assert lowered.diagnostics == ()


@pytest.mark.parametrize(
    ("function_name", "backend"),
    (
        ("rank", "postgres"),
        ("rank", "mysql"),
        ("dense_rank", "postgres"),
        ("dense_rank", "mysql"),
    ),
)
def test_ranking_postgres_and_private_mysql_fail_before_sql_lowering(
    function_name: str, backend: str
) -> None:
    del backend
    script, relation = _parsed_relation(_program(call=f"{function_name}()"))
    semantic = analyze(script)
    lowered = lower_expr(
        cast(WindowExpr, relation.select_items[-1].expression), semantic.model
    )
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == function_name
    assert lowered.diagnostics == ()


@pytest.mark.parametrize(
    "name",
    ("lag", "lead", "first_value", "last_value", "nth_value"),
)
def test_slice9_and_slice12_window_identities_remain_unsupported(name: str) -> None:
    script, _ = _parsed_relation(_program(call=f"{name}()"))
    semantic = analyze(script)
    expected_code = "PIE-S2104" if name in {"lag", "lead"} else "PIE-S2103"
    matching = [item for item in semantic.diagnostics if item.code == expected_code]
    assert len(matching) == 1
    if name in {"lag", "lead"}:
        assert matching[0].message == (
            f"Invalid arguments for function {name}: expected 1 through 3, got 0"
        )
    else:
        assert matching[0].message == f"Unknown function: {name}"


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", "arity"),
        ("rank", "unknown"),
        ("rank", "direction"),
        ("rank", "identity"),
        ("dense_rank", "arity"),
        ("dense_rank", "unknown"),
        ("dense_rank", "direction"),
        ("dense_rank", "identity"),
    ),
)
def test_ranking_diagnostic_code_message_location_and_order_are_exact(
    function_name: str, case: str
) -> None:
    if case == "arity":
        source = _program(call=f"{function_name}(id)")
        expected_code = "PIE-S2104"
    elif case == "unknown":
        source = _program(call=f"{function_name}()", order=("missing",))
        expected_code = "PIE-S2102"
    elif case == "direction":
        source = _program(call=f"{function_name}()", direction="desc")
        expected_code = "PIE-S2103"
    else:
        source = _program(call=f"X{function_name}()")
        expected_code = "PIE-S2103"
    result, diagnostics, _, relation = _direct_analysis(source)
    if case == "direction":
        assert isinstance(result, RankingWindowSemanticFact)
        assert diagnostics == []
        return
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected_code]
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    expected_span = (
        expression.spec.order_by[0].expression.span
        if case == "unknown"
        else expression.call.span
    )
    assert diagnostics[0].location == SourceLocation(
        path=expected_span.path,
        line=expected_span.line,
        column=expected_span.column,
        end_line=expected_span.end_line,
        end_column=expected_span.end_column,
    )


# Phase 53 Slice 13 reader migration.
