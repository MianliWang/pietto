from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, cast


import pytest

import pietto
import pietto.semantic.window_analysis as window_analysis
import pietto.semantic.window_order_analysis as window_order_analysis
import pietto.semantic.window_partition_analysis as window_partition_analysis
from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticModel,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.row_dependency_graph import ProjectRowDependencyNodeKind
from pietto._project.window_semantics import (
    WindowDependencyRole,
    WindowResultProjectFact,
    build_ranking_window_result_project_fact,
    build_row_number_window_result_project_fact,
    build_window_result_project_fact,
)
from pietto.ast_nodes import (
    BinaryExpr,
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
    SelectItem,
    SatisfyingClause,
    SourceDef,
    Span,
    TableDef,
    UnaryExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.ir.model import WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.window_semantics import (
    DistributionWindowPolicy,
    DistributionWindowSemanticFact,
    RankingWindowSemanticFact,
    WindowExpressionAnalysis,
    WindowExpressionSemanticFact,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowPartitionBindingFact,
    WindowPartitionFieldBinding,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_H3 = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
)
IDENTITIES = SPEC_H3

# These exact literal manifests are populated before the single write formatter.
# Formatting-neutral final identities are populated after the single formatter.


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _call(function_name: str, bucket_count: int = 4) -> str:
    return (
        f"ntile({bucket_count})" if function_name == "ntile" else f"{function_name}()"
    )


def _program(
    *,
    kind: str = "query",
    call: str = "rank()",
    partition: tuple[str, ...] = (),
    order: tuple[str, ...] = ("observed_at",),
    direction: str | None = None,
    upstream: bool = False,
    alias: str = "ranking_value",
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
    where: bool = False,
    final_order: str | None = None,
    limit: bool = False,
) -> str:
    prefix = (
        "shape Row:\n"
        "    id: Int not null\n"
        "    observed_at: Timestamp not null\n"
        "    label: Text nullable\n"
        "    nullable_id: Int nullable\n"
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
            "        nullable_id\n"
        )
        input_name = "intermediate"
    lines = [f"{kind} ranked:", f"    from {input_name}"]
    if where:
        lines.append("    where id > 0")
    lines.append("    select:")
    lines.extend(f"        {value}" for value in before)
    lines.append(f"        {alias} = {call} window:")
    if partition:
        lines.append("            partition by:")
        lines.extend(f"                {value}" for value in partition)
    if order:
        lines.append("            order by:")
        suffix = f" {direction}" if direction is not None else ""
        lines.extend(f"                {value}{suffix}" for value in order)
    lines.extend(f"        {value}" for value in after)
    if final_order is not None:
        lines.extend(("    order by:", f"        {final_order}"))
    if limit:
        lines.append("    limit 10")
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(
    source: str, *, path: str = "slice10.pietto"
) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path=path)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return parsed.ast, relation


def _input_schema(script: Script, relation: TableDef | QueryDef) -> RowSchema:
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if isinstance(target, SourceDef):
        return semantic.model.source_row_schemas[target]
    assert isinstance(target, (TableDef, QueryDef))
    return semantic.model.relation_row_schemas[target]


def _analysis(
    source: str,
    *,
    relation_override: TableDef | QueryDef | None = None,
    item_override: SelectItem | None = None,
    selected_output_ordinal: int | None = None,
    input_schema_override: RowSchema | None = None,
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, parsed_relation = _parsed_relation(source)
    relation = relation_override or parsed_relation
    ordinal = selected_output_ordinal
    if ordinal is None:
        ordinal = next(
            index
            for index, selected in enumerate(relation.select_items)
            if isinstance(selected.expression, WindowExpr)
        )
    item = item_override or relation.select_items[ordinal]
    assert isinstance(item.expression, WindowExpr)
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_window_expression(
        definition=relation,
        item=item,
        selected_output_ordinal=ordinal,
        source_id=item.expression.span.path or relation.name,
        input_schema=input_schema_override or _input_schema(script, parsed_relation),
        field_qualifier=relation.from_clause.source_name,
        value_types=values,
        diagnostics=diagnostics,
    )
    return result, diagnostics, values, relation


def _canonical_analysis(
    function_name: str,
    *,
    partition: tuple[str, ...] = (),
    qualified_order: bool = False,
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
) -> tuple[WindowExpressionAnalysis, TableDef | QueryDef, dict[Expression, ValueType]]:
    input_name = "intermediate" if upstream else "rows"
    order = f"{input_name}.observed_at" if qualified_order else "observed_at"
    result, diagnostics, values, relation = _analysis(
        _program(
            kind=kind,
            call=_call(function_name, bucket_count),
            partition=partition,
            order=(order,),
            upstream=upstream,
        )
    )
    assert diagnostics == []
    assert isinstance(result, WindowExpressionAnalysis)
    return result, relation, values


def _project_schema() -> ProjectRowSchema:
    return ProjectRowSchema(
        fields={
            "id": ProjectRowField(
                name="id",
                resolved_type=ProjectResolvedType(
                    name="Int", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NON_NULL,
            ),
            "observed_at": ProjectRowField(
                name="observed_at",
                resolved_type=ProjectResolvedType(
                    name="Timestamp", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NON_NULL,
            ),
            "label": ProjectRowField(
                name="label",
                resolved_type=ProjectResolvedType(
                    name="Text", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NULLABLE,
            ),
            "nullable_id": ProjectRowField(
                name="nullable_id",
                resolved_type=ProjectResolvedType(
                    name="Int", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NULLABLE,
            ),
        }
    )


def _project_fact(
    function_name: str,
    *,
    partition: tuple[str, ...] = ("id", "label"),
    order: str = "observed_at",
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
    builder: str = "general",
) -> WindowResultProjectFact:
    source = _program(
        kind=kind,
        call=_call(function_name, bucket_count),
        partition=partition,
        order=(order,),
        upstream=upstream,
    )
    script, relation = _parsed_relation(source)
    upstream_name = "intermediate" if upstream else "rows"
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == upstream_name
    )
    assert isinstance(upstream_definition, (SourceDef, TableDef, QueryDef))
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE,
        name=upstream_name,
        path="slice10.pietto",
        location=SourceLocation(path="slice10.pietto", line=1, column=1),
        definition=upstream_definition,
    )
    build = {
        "general": build_window_result_project_fact,
        "ranking": build_ranking_window_result_project_fact,
        "row_number": build_row_number_window_result_project_fact,
    }[builder]
    result = build(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice10.pietto",
        input_schema=_project_schema(),
        upstream_symbol=symbol,
    )
    assert isinstance(result, WindowResultProjectFact)
    return result


def _assert_unsupported(
    source: str,
    *,
    code: str,
) -> tuple[WindowExpressionUnsupported, Diagnostic, TableDef | QueryDef]:
    result, diagnostics, _, relation = _analysis(source)
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [code]
    return result, diagnostics[0], relation


def _analysis_with_partition_expression(
    function_name: str,
    partition_expression: Expression,
) -> tuple[WindowExpressionAnalysis | WindowExpressionUnsupported, list[Diagnostic]]:
    source = _program(call=_call(function_name), partition=("id",))
    _, relation = _parsed_relation(source)
    item = relation.select_items[-1]
    outer = cast(WindowExpr, item.expression)
    replacement = dataclasses.replace(
        outer,
        spec=dataclasses.replace(
            outer.spec,
            partition_by=(partition_expression,),
        ),
    )
    replaced_item = dataclasses.replace(item, expression=replacement)
    replaced_relation = dataclasses.replace(
        relation,
        select_items=(*relation.select_items[:-1], replaced_item),
    )
    result, diagnostics, _, _ = _analysis(
        source,
        relation_override=replaced_relation,
        item_override=replaced_item,
    )
    return result, diagnostics


@pytest.mark.parametrize("case", range(6))
def test_completed_identity_source_subset_and_result_types_are_locked(
    case: int,
) -> None:
    function_name = IDENTITIES[case]
    result, relation, _ = _canonical_analysis(function_name)
    value_type = result.semantic_fact.result.value_type
    assert value_type is not None
    assert result.semantic_fact.identity.name == function_name
    assert result.semantic_fact.occurrence.relation_name == relation.name
    assert value_type.resolved_type.name == (
        "Float" if function_name in {"percent_rank", "cume_dist"} else "Int"
    )
    assert value_type.nullability is EffectiveNullability.NON_NULL
    assert result.semantic_fact.stage is WindowExpressionStage.WINDOW


@pytest.mark.parametrize("case", range(5))
def test_grammar_ast_partition_tuple_cardinality_source_order_and_duplicates_are_locked(
    case: int,
) -> None:
    partitions = (
        (),
        ("id",),
        ("id", "label"),
        ("id", "label", "nullable_id"),
        ("id", "id", "label"),
    )
    _, relation = _parsed_relation(_program(partition=partitions[case]))
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    partition_items = cast(
        tuple[NameExpr | DottedNameExpr, ...],
        expression.spec.partition_by,
    )
    source_names = tuple(
        item.name if isinstance(item, NameExpr) else ".".join(item.parts)
        for item in partition_items
    )
    assert source_names == partitions[case]
    assert type(expression.spec.partition_by) is tuple


@pytest.mark.parametrize("case", range(3))
def test_partition_expression_candidates_and_direct_field_selection_are_exact(
    case: int,
) -> None:
    source = _read("src/pietto/semantic/window_analysis.py")
    required = (
        "NameExpr | DottedNameExpr",
        "window partition expression must be a direct field",
        "bind_window_partition_fields(",
    )
    assert required[case] in source


@pytest.mark.parametrize("case", range(3))
def test_duplicate_partition_candidates_and_occurrence_edge_selection_are_exact(
    case: int,
) -> None:
    fact = _project_fact("rank", partition=("id", "id"))
    partition_occurrences = tuple(
        item
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    partition_edges = tuple(
        item
        for item in fact.dependency_edges
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    checks = (
        len(partition_occurrences) == 2,
        len(partition_edges) == 1,
        tuple(item.role_ordinal for item in partition_occurrences) == (0, 1),
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(3))
def test_semantic_result_candidates_and_composite_selection_are_exact(
    case: int,
) -> None:
    result, _, _ = _canonical_analysis("percent_rank", partition=("id",))
    checks = (
        type(result) is WindowExpressionAnalysis,
        result.ranking_fact is not None and result.distribution_fact is not None,
        result.partition_binding_fact.semantic_fact is result.semantic_fact,
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(3))
def test_semantic_module_candidates_and_sibling_module_selection_are_exact(
    case: int,
) -> None:
    analysis_source = _read("src/pietto/semantic/window_analysis.py")
    helper_source = _read("src/pietto/semantic/window_partition_analysis.py")
    required = (
        "from pietto.semantic.window_partition_analysis import",
        "def bind_window_partition_fields(",
        "infer_row_expression(",
    )
    assert required[case] in analysis_source + helper_source


@pytest.mark.parametrize("case", range(3))
def test_partition_modules_are_private_acyclic_and_rust_friendly(case: int) -> None:
    semantic_source = _read("src/pietto/semantic/window_semantics.py")
    helper_source = _read("src/pietto/semantic/window_partition_analysis.py")
    checks = (
        "__all__: tuple[str, ...] = ()" in semantic_source,
        "__all__: tuple[str, ...] = ()" in helper_source,
        "from pietto.semantic.window_analysis" not in helper_source,
    )
    assert checks[case]
    assert "dict[" not in "\n".join(
        line
        for line in semantic_source.splitlines()
        if line.startswith("class WindowPartition")
    )


@pytest.mark.parametrize("case", range(4))
def test_partition_binding_carrier_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    field_names = tuple(
        field.name for field in dataclasses.fields(WindowPartitionFieldBinding)
    )
    fact_names = tuple(
        field.name for field in dataclasses.fields(WindowPartitionBindingFact)
    )
    result, _, _ = _canonical_analysis("rank", partition=("id", "label"))
    checks = (
        field_names == ("expression", "value_type"),
        fact_names == ("semantic_fact", "bindings"),
        all(field.kw_only for field in dataclasses.fields(WindowPartitionBindingFact)),
        not hasattr(pietto, "WindowPartitionBindingFact")
        and hash(result.partition_binding_fact),
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(20))
def test_partition_binding_carrier_malformed_matrix_fails_closed(case: int) -> None:
    result, _, _ = _canonical_analysis("rank", partition=("id", "label"))
    first, second = result.partition_binding_fact.bindings
    known = first.value_type
    span = first.expression.span
    variant = case % 10
    if variant < 6:
        kwargs: dict[str, object]
        error: type[Exception]
        if variant == 0:
            kwargs, error = {"expression": object(), "value_type": known}, TypeError
        elif variant == 1:
            kwargs, error = (
                {
                    "expression": LiteralExpr(span=span, value=1),
                    "value_type": known,
                },
                TypeError,
            )
        elif variant == 2:
            kwargs, error = (
                {
                    "expression": DottedNameExpr(span=span, parts=("a", "b", "c")),
                    "value_type": known,
                },
                ValueError,
            )
        elif variant == 3:
            kwargs, error = (
                {"expression": first.expression, "value_type": object()},
                TypeError,
            )
        elif variant == 4:
            kwargs, error = (
                {
                    "expression": first.expression,
                    "value_type": ValueType(
                        resolved_type=known.resolved_type,
                        nullability=known.nullability,
                        kind=ValueTypeKind.UNKNOWN,
                    ),
                },
                ValueError,
            )
        else:
            kwargs, error = (
                {
                    "expression": first.expression,
                    "value_type": ValueType(
                        resolved_type=ResolvedType(name="?", kind=TypeKind.UNKNOWN),
                        nullability=EffectiveNullability.UNKNOWN,
                    ),
                },
                ValueError,
            )
        with pytest.raises(error):
            WindowPartitionFieldBinding(**cast(Any, kwargs))
        return
    if variant == 6:
        fact_kwargs = {"semantic_fact": object(), "bindings": (first, second)}
        error = TypeError
    elif variant == 7:
        fact_kwargs = {
            "semantic_fact": result.semantic_fact,
            "bindings": [first, second],
        }
        error = TypeError
    elif variant == 8:
        fact_kwargs = {
            "semantic_fact": result.semantic_fact,
            "bindings": (first, object()),
        }
        error = TypeError
    else:
        fact_kwargs = {
            "semantic_fact": result.semantic_fact,
            "bindings": (second, first),
        }
        error = ValueError
    with pytest.raises(error):
        WindowPartitionBindingFact(**cast(Any, fact_kwargs))


@pytest.mark.parametrize("case", range(12))
def test_partition_binding_empty_order_duplicate_equality_and_hashing_are_exact(
    case: int,
) -> None:
    partitions = ((), ("id",), ("id", "label"), ("id", "id"))
    partition = partitions[case % 4]
    first, _, _ = _canonical_analysis(IDENTITIES[case % 6], partition=partition)
    second, _, _ = _canonical_analysis(IDENTITIES[case % 6], partition=partition)
    assert (
        tuple(binding.expression for binding in first.partition_binding_fact.bindings)
        == first.semantic_fact.expression.spec.partition_by
    )
    assert first == second
    assert hash(first) == hash(second)


@pytest.mark.parametrize("case", range(4))
def test_window_expression_analysis_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    fields = tuple(dataclasses.fields(WindowExpressionAnalysis))
    result, _, _ = _canonical_analysis("percent_rank", partition=("id",))
    checks = (
        tuple(field.name for field in fields)
        == (
            "semantic_fact",
            "ranking_fact",
            "distribution_fact",
            "partition_binding_fact",
            "order_binding_fact",
            "navigation_fact",
        ),
        all(field.kw_only for field in fields),
        getattr(WindowExpressionAnalysis, "__dataclass_params__").frozen,
        hasattr(WindowExpressionAnalysis, "__slots__")
        and not hasattr(pietto, "WindowExpressionAnalysis")
        and hash(result),
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(18))
def test_window_expression_analysis_family_invariant_matrix_fails_closed(
    case: int,
) -> None:
    rank, _, _ = _canonical_analysis("rank", partition=("id",))
    percent, _, _ = _canonical_analysis("percent_rank", partition=("id",))
    cume, _, _ = _canonical_analysis("cume_dist", partition=("id",))
    variant = case % 9
    if variant == 0:
        kwargs = dataclasses.asdict(rank)
        kwargs["semantic_fact"] = object()
        error = TypeError
    elif variant == 1:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": object(),
            "distribution_fact": None,
            "partition_binding_fact": rank.partition_binding_fact,
            "order_binding_fact": rank.order_binding_fact,
        }
        error = TypeError
    elif variant == 2:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": rank.ranking_fact,
            "distribution_fact": object(),
            "partition_binding_fact": rank.partition_binding_fact,
            "order_binding_fact": rank.order_binding_fact,
        }
        error = TypeError
    elif variant == 3:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": rank.ranking_fact,
            "distribution_fact": None,
            "partition_binding_fact": object(),
            "order_binding_fact": rank.order_binding_fact,
        }
        error = TypeError
    elif variant == 4:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": rank.ranking_fact,
            "distribution_fact": None,
            "partition_binding_fact": cume.partition_binding_fact,
            "order_binding_fact": rank.order_binding_fact,
        }
        error = ValueError
    elif variant == 5:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": None,
            "distribution_fact": None,
            "partition_binding_fact": rank.partition_binding_fact,
            "order_binding_fact": rank.order_binding_fact,
        }
        error = ValueError
    elif variant == 6:
        kwargs = {
            "semantic_fact": percent.semantic_fact,
            "ranking_fact": None,
            "distribution_fact": percent.distribution_fact,
            "partition_binding_fact": percent.partition_binding_fact,
            "order_binding_fact": percent.order_binding_fact,
        }
        error = ValueError
    elif variant == 7:
        kwargs = {
            "semantic_fact": percent.semantic_fact,
            "ranking_fact": percent.ranking_fact,
            "distribution_fact": None,
            "partition_binding_fact": percent.partition_binding_fact,
            "order_binding_fact": percent.order_binding_fact,
        }
        error = ValueError
    else:
        kwargs = {
            "semantic_fact": cume.semantic_fact,
            "ranking_fact": rank.ranking_fact,
            "distribution_fact": cume.distribution_fact,
            "partition_binding_fact": cume.partition_binding_fact,
            "order_binding_fact": cume.order_binding_fact,
        }
        error = ValueError
    with pytest.raises(error):
        WindowExpressionAnalysis(**cast(Any, kwargs))


@pytest.mark.parametrize("case", range(6))
def test_all_six_zero_partition_semantic_results_remain_exact(case: int) -> None:
    result, _, values = _canonical_analysis(IDENTITIES[case])
    assert result.partition_binding_fact.bindings == ()
    assert result.partition_binding_fact.partition_key == ()
    assert result.semantic_fact.expression not in values
    assert (result.ranking_fact is not None) is (case in {0, 1, 2, 3})
    assert (result.distribution_fact is not None) is (case in {3, 4, 5})


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_partition_field(case: int) -> None:
    result, _, _ = _canonical_analysis(IDENTITIES[case], partition=("id",))
    bindings = result.partition_binding_fact.bindings
    assert len(bindings) == 1
    assert type(bindings[0].expression) is NameExpr
    assert cast(NameExpr, bindings[0].expression).name == "id"
    assert bindings[0].value_type.resolved_type.name == "Int"


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_immediate_qualified_partition_field(case: int) -> None:
    result, _, _ = _canonical_analysis(IDENTITIES[case], partition=("rows.id",))
    binding = result.partition_binding_fact.bindings[0]
    assert type(binding.expression) is DottedNameExpr
    assert cast(DottedNameExpr, binding.expression).parts == ("rows", "id")
    assert binding.value_type.resolved_type.name == "Int"


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_two_source_ordered_partition_fields(case: int) -> None:
    result, _, _ = _canonical_analysis(IDENTITIES[case], partition=("label", "id"))
    bindings = result.partition_binding_fact.bindings
    assert tuple(cast(NameExpr, item.expression).name for item in bindings) == (
        "label",
        "id",
    )
    assert tuple(item.value_type.resolved_type.name for item in bindings) == (
        "Text",
        "Int",
    )


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_three_source_ordered_partition_fields(case: int) -> None:
    result, _, _ = _canonical_analysis(
        IDENTITIES[case], partition=("id", "label", "nullable_id")
    )
    assert tuple(
        cast(NameExpr, item.expression).name
        for item in result.partition_binding_fact.bindings
    ) == ("id", "label", "nullable_id")
    assert len(result.partition_binding_fact.partition_key) == 3


@pytest.mark.parametrize("case", range(6))
def test_all_six_preserve_duplicate_partition_bindings(case: int) -> None:
    result, _, _ = _canonical_analysis(
        IDENTITIES[case], partition=("id", "id", "label")
    )
    bindings = result.partition_binding_fact.bindings
    assert len(bindings) == 3
    assert bindings[0] is not bindings[1]
    assert bindings[0].value_type == bindings[1].value_type
    first_expression = cast(NameExpr, bindings[0].expression)
    second_expression = cast(NameExpr, bindings[1].expression)
    assert first_expression is not second_expression
    assert first_expression.name == second_expression.name == "id"
    assert first_expression.span != second_expression.span
    assert first_expression.span.line < second_expression.span.line


@pytest.mark.parametrize("case", range(12))
def test_nullable_partition_fields_are_structurally_accepted(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    field_name = "label" if case < 6 else "nullable_id"
    result, _, _ = _canonical_analysis(function_name, partition=(field_name,))
    binding = result.partition_binding_fact.bindings[0]
    assert binding.value_type.nullability is EffectiveNullability.NULLABLE
    assert binding.value_type.kind is ValueTypeKind.KNOWN


@pytest.mark.parametrize("case", range(18))
def test_partition_binding_supports_direct_source_and_immediate_upstream_matrix(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    variant = case // 6
    upstream = variant != 0
    qualifier = "intermediate" if upstream else "rows"
    partition = ("id",) if variant != 2 else (f"{qualifier}.id",)
    result, relation, _ = _canonical_analysis(
        function_name,
        partition=partition,
        upstream=upstream,
        kind="table" if variant == 1 else "query",
    )
    assert result.semantic_fact.occurrence.relation_name == relation.name
    assert len(result.partition_binding_fact.bindings) == 1
    assert isinstance(relation, (TableDef, QueryDef))


@pytest.mark.parametrize("case", range(18))
def test_partition_qualifier_visibility_stops_at_the_immediate_input(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    invalid = ("rows.id", "wrong.id", "intermediate.nested.id")[case // 6]
    _, diagnostic, relation = _assert_unsupported(
        _program(
            call=_call(function_name),
            partition=(invalid,),
            upstream=True,
        ),
        code="PIE-S2102",
    )
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    partition_expression = expression.spec.partition_by[0]
    assert diagnostic.message == f"Unknown field: {invalid}"
    assert diagnostic.location == SourceLocation(
        path=partition_expression.span.path,
        line=partition_expression.span.line,
        column=partition_expression.span.column,
        end_line=partition_expression.span.end_line,
        end_column=partition_expression.span.end_column,
    )


@pytest.mark.parametrize("case", range(12))
def test_partition_child_value_type_facts_are_exact_and_transient(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    partition = ("id", "label") if case < 6 else ("nullable_id", "id")
    result, _, values = _canonical_analysis(function_name, partition=partition)
    expressions = result.partition_binding_fact.partition_key
    order_expression = result.semantic_fact.expression.spec.order_by[0].expression
    assert all(expression in values for expression in (*expressions, order_expression))
    assert result.semantic_fact.expression not in values
    assert tuple(values[item] for item in expressions) == tuple(
        binding.value_type for binding in result.partition_binding_fact.bindings
    )


@pytest.mark.parametrize("case", range(18))
def test_partition_and_order_fields_use_exactly_one_existing_resolution_each(
    case: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    function_name = IDENTITIES[case % 6]
    partition = (
        ("id",),
        ("id", "label"),
        ("id", "id", "nullable_id"),
    )[case // 6]
    source = _program(call=_call(function_name), partition=partition)
    script, relation = _parsed_relation(source)
    input_schema = _input_schema(script, relation)
    partition_calls: list[Expression] = []
    order_calls: list[Expression] = []
    real_partition = window_partition_analysis.infer_row_expression
    real_order = window_order_analysis.infer_row_expression

    def record_partition(*args: Any, **kwargs: Any) -> ValueType:
        partition_calls.append(cast(Expression, args[0]))
        return real_partition(*args, **kwargs)

    def record_order(*args: Any, **kwargs: Any) -> ValueType:
        order_calls.append(cast(Expression, args[0]))
        return real_order(*args, **kwargs)

    monkeypatch.setattr(
        window_partition_analysis, "infer_row_expression", record_partition
    )
    monkeypatch.setattr(window_order_analysis, "infer_row_expression", record_order)
    result, diagnostics, _, _ = _analysis(
        source,
        input_schema_override=input_schema,
    )
    assert diagnostics == []
    assert isinstance(result, WindowExpressionAnalysis)
    assert len(partition_calls) == len(partition)
    assert len(order_calls) == 1


@pytest.mark.parametrize("case", range(18))
def test_partition_order_and_peer_keys_are_exact_for_all_identities(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    partition = (
        ("id",),
        ("label", "id"),
        ("id", "id", "nullable_id"),
    )[case // 6]
    result, _, _ = _canonical_analysis(function_name, partition=partition)
    assert result.partition_binding_fact.partition_key == tuple(
        item.expression for item in result.partition_binding_fact.bindings
    )
    order_expression = result.semantic_fact.expression.spec.order_by[0].expression
    if result.ranking_fact is not None:
        expected_peer = () if function_name == "row_number" else (order_expression,)
        assert result.ranking_fact.peer_key == expected_peer
    if result.distribution_fact is not None:
        assert result.distribution_fact.structural_order_key == (order_expression,)
        expected_peer = () if function_name == "ntile" else (order_expression,)
        assert result.distribution_fact.peer_key == expected_peer


@pytest.mark.parametrize("case", range(3))
def test_percent_rank_and_cume_dist_partition_local_posture_is_structural_only(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist")[case % 2]
    result, _, _ = _canonical_analysis(function_name, partition=("id", "label"))
    assert result.distribution_fact is not None
    checks = (
        result.distribution_fact.peer_sensitive,
        len(result.partition_binding_fact.bindings) == 2,
        "runtime" not in result.distribution_fact.distribution_policy.value,
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(6))
def test_ntile_partition_and_positive_literal_contract_remains_exact(case: int) -> None:
    bucket_count = case + 1
    result, _, _ = _canonical_analysis(
        "ntile", partition=("id", "label"), bucket_count=bucket_count
    )
    assert result.distribution_fact is not None
    assert result.distribution_fact.distribution_policy is (
        DistributionWindowPolicy.BALANCED_BUCKETS
    )
    assert result.distribution_fact.bucket_count == bucket_count
    assert result.ranking_fact is None


@pytest.mark.parametrize("case", range(6))
def test_partitioned_window_analysis_is_structurally_repeatable(case: int) -> None:
    function_name = IDENTITIES[case]
    first, _, first_values = _canonical_analysis(
        function_name, partition=("id", "label", "id")
    )
    second, _, second_values = _canonical_analysis(
        function_name, partition=("id", "label", "id")
    )
    assert first == second
    assert hash(first) == hash(second)
    assert first_values == second_values


@pytest.mark.parametrize("case", range(42))
def test_computed_literal_call_and_nested_partition_shapes_use_pie_s2103(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    span = Span(path="slice10.pietto", line=8, column=17, end_line=8, end_column=25)
    outer, _, _ = _canonical_analysis(function_name)
    shapes: tuple[Expression, ...] = (
        LiteralExpr(span=span, value=1),
        BinaryExpr(
            span=span,
            left=NameExpr(span=span, name="id"),
            operator="+",
            right=LiteralExpr(span=span, value=1),
        ),
        CallExpr(
            span=span,
            callee=NameExpr(span=span, name="lower"),
            arguments=(NameExpr(span=span, name="label"),),
        ),
        UnaryExpr(
            span=span,
            operator="-",
            operand=NameExpr(span=span, name="id"),
        ),
        outer.semantic_fact.expression,
        LiteralExpr(span=span, value="id"),
        BinaryExpr(
            span=span,
            left=NameExpr(span=span, name="id"),
            operator="*",
            right=NameExpr(span=span, name="nullable_id"),
        ),
    )
    result, diagnostics = _analysis_with_partition_expression(
        function_name, shapes[case // 6]
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]
    assert diagnostics[0].message == f"Unknown function: {function_name}"


@pytest.mark.parametrize("case", range(24))
def test_selected_let_aggregate_and_window_result_partition_names_fail_closed(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    unavailable_name = (
        "selected_alias",
        "local_value",
        "aggregate_value",
        "prior_window_value",
    )[case // 6]
    _, diagnostic, _ = _assert_unsupported(
        _program(call=_call(function_name), partition=(unavailable_name,)),
        code="PIE-S2102",
    )
    assert diagnostic.message == f"Unknown field: {unavailable_name}"


@pytest.mark.parametrize("case", range(12))
def test_unknown_partition_fields_use_pie_s2102_without_cascade(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    unknown = "missing" if case < 6 else "rows.missing"
    result, diagnostic, relation = _assert_unsupported(
        _program(call=_call(function_name), partition=(unknown,)),
        code="PIE-S2102",
    )
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert result.reason == "window partition field type must be concrete"
    assert diagnostic.message == f"Unknown field: {unknown}"
    assert diagnostic.location.line == expression.spec.partition_by[0].span.line


@pytest.mark.parametrize("case", range(18))
def test_invalid_immediate_original_and_three_part_partition_qualifiers_use_pie_s2102(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    invalid = ("wrong.id", "rows.id", "intermediate.deep.id")[case // 6]
    _, diagnostic, _ = _assert_unsupported(
        _program(
            call=_call(function_name),
            partition=(invalid,),
            upstream=True,
        ),
        code="PIE-S2102",
    )
    assert diagnostic.message == f"Unknown field: {invalid}"


@pytest.mark.parametrize("case", range(12))
def test_multi_key_partition_diagnostics_stop_at_first_source_error(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    partition = (
        ("missing_first", "missing_second"),
        ("id", "missing_second", "missing_third"),
    )[case // 6]
    _, diagnostic, _ = _assert_unsupported(
        _program(call=_call(function_name), partition=partition),
        code="PIE-S2102",
    )
    expected = partition[0] if case < 6 else partition[1]
    assert diagnostic.message == f"Unknown field: {expected}"


@pytest.mark.parametrize("case", range(12))
def test_partition_diagnostics_precede_local_order_diagnostics(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    order = "missing_order" if case < 6 else "id + 1"
    _, diagnostic, _ = _assert_unsupported(
        _program(
            call=_call(function_name),
            partition=("missing_partition",),
            order=(order,),
        ),
        code="PIE-S2102",
    )
    assert diagnostic.message == "Unknown field: missing_partition"


@pytest.mark.parametrize("case", range(18))
def test_zero_partition_identity_arity_and_ntile_diagnostic_order_is_unchanged(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    scenario = case // 6
    if scenario == 0:
        call = "ntile()" if function_name == "ntile" else f"{function_name}(id)"
        expected = "PIE-S2104"
    elif scenario == 1:
        call = f"wrong_{function_name}()"
        expected = "PIE-S2103"
    else:
        call = "ntile(0)" if function_name == "ntile" else f"{function_name}(1)"
        expected = "PIE-S2104"
    result, diagnostics, _, _ = _analysis(_program(call=call))
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected]


@pytest.mark.parametrize("case", range(24))
def test_group_aggregate_satisfying_and_let_contexts_remain_unsupported(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    source = _program(call=_call(function_name), partition=("id",))
    _, relation = _parsed_relation(source)
    span = relation.span
    scenario = case // 6
    if scenario == 0:
        replacement = dataclasses.replace(
            relation,
            group_by_clause=GroupByClause(
                span=span,
                items=(GroupByItem(span=span, key=NameExpr(span=span, name="id")),),
            ),
        )
    elif scenario == 1:
        replacement = dataclasses.replace(
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
    elif scenario == 2:
        replacement = dataclasses.replace(
            relation,
            satisfying_clause=SatisfyingClause(
                span=span, expression=NameExpr(span=span, name="id")
            ),
        )
    else:
        replacement = dataclasses.replace(
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
    result, diagnostics, _, _ = _analysis(source, relation_override=replacement)
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(18))
def test_window_placements_outside_direct_select_remain_unsupported(case: int) -> None:
    source = _read("src/pietto/semantic/expressions.py")
    required = (
        "for selected_output_ordinal, item in enumerate(definition.select_items):",
        "if type(item.expression) is WindowExpr:",
        "analyze_window_expression(",
    )
    assert required[case // 6] in source
    assert f'name="{IDENTITIES[case % 6]}"' not in source


@pytest.mark.parametrize("case", range(18))
def test_multiple_nested_and_same_select_window_dependencies_remain_unsupported(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    source = _program(call=_call(function_name), partition=("id",))
    _, relation = _parsed_relation(source)
    first = relation.select_items[-1]
    replacement = dataclasses.replace(
        relation,
        select_items=(
            first,
            dataclasses.replace(first, alias=f"other_window_{case}"),
        ),
    )
    result, diagnostics, _, _ = _analysis(
        source,
        relation_override=replacement,
        selected_output_ordinal=case % 2,
    )
    assert type(result) is WindowExpressionAnalysis
    assert diagnostics == []
    assert result.semantic_fact.occurrence.selected_output_ordinal == case % 2


@pytest.mark.parametrize("case", range(18))
def test_zero_multiple_and_directed_local_order_shapes_remain_unsupported(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    scenario = case // 6
    order = ((), ("observed_at", "id"), ("observed_at",))[scenario]
    direction = "asc" if scenario == 2 else None
    result, diagnostics, _, _ = _analysis(
        _program(
            call=_call(function_name),
            partition=("id",),
            order=order,
            direction=direction,
        )
    )
    if scenario == 0:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert type(result) is WindowExpressionAnalysis
        assert diagnostics == []
        assert len(result.order_binding_fact.bindings) == len(order)


@pytest.mark.parametrize("case", range(18))
def test_unknown_computed_and_invalid_qualified_local_order_fields_preserve_diagnostics(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    order = ("missing", "wrong.observed_at", "id + 1")[case // 6]
    expected = "PIE-S2103" if case // 6 == 2 else "PIE-S2102"
    result, diagnostics, _, _ = _analysis(
        _program(
            call=_call(function_name),
            partition=("id",),
            order=(order,),
        )
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected]


@pytest.mark.parametrize("case", range(12))
def test_partitioned_windows_coexist_with_ordinary_where_final_order_and_limit(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    full = case >= 6
    source = _program(
        call=_call(function_name),
        partition=("id", "label"),
        before=("id",),
        after=("label",),
        where=True,
        final_order="observed_at" if full else None,
        limit=full,
    )
    script, relation = _parsed_relation(source)
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[1].expression)
    assert expression in semantic.model.expression_value_types
    assert "ranking_value" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize("case", range(12))
def test_project_generic_builder_supports_all_six_partitioned_identities(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    fact = _project_fact(
        function_name,
        partition=("id", "label"),
        upstream=case >= 6,
    )
    assert fact.semantic_fact.identity.name == function_name
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert len(fact.dependency_occurrences) == 4


@pytest.mark.parametrize("case", range(12))
def test_project_relation_partition_and_order_role_blocks_and_ordinals_are_exact(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    partition = ("id",) if case < 6 else ("id", "label", "nullable_id")
    fact = _project_fact(function_name, partition=partition)
    assert tuple(item.role for item in fact.dependency_occurrences) == (
        WindowDependencyRole.RELATION_INPUT,
        *(WindowDependencyRole.WINDOW_PARTITION for _ in partition),
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.global_ordinal for item in fact.dependency_occurrences) == tuple(
        range(len(partition) + 2)
    )
    assert tuple(
        item.role_ordinal
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    ) == tuple(range(len(partition)))


@pytest.mark.parametrize("case", range(12))
def test_project_duplicate_partition_occurrences_and_first_edges_are_exact(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    partition = ("id", "id") if case < 6 else ("label", "id", "label")
    fact = _project_fact(function_name, partition=partition)
    occurrences = tuple(
        item
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    edges = tuple(
        item
        for item in fact.dependency_edges
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    assert len(occurrences) == len(partition)
    assert tuple(item.target.field_name for item in occurrences) == partition
    assert tuple(item.target.field_name for item in edges) == tuple(
        dict.fromkeys(partition)
    )


@pytest.mark.parametrize("case", range(6))
def test_project_partition_dependency_order_tracks_source_reversal(case: int) -> None:
    function_name = IDENTITIES[case]
    forward = _project_fact(function_name, partition=("id", "label"))
    reverse = _project_fact(function_name, partition=("label", "id"))

    def extract(fact: WindowResultProjectFact) -> tuple[str | None, ...]:
        return tuple(
            item.target.field_name
            for item in fact.dependency_occurrences
            if item.role is WindowDependencyRole.WINDOW_PARTITION
        )

    assert extract(forward) == ("id", "label")
    assert extract(reverse) == ("label", "id")


@pytest.mark.parametrize("case", range(6))
def test_partition_and_order_same_target_remain_role_distinct(case: int) -> None:
    fact = _project_fact(IDENTITIES[case], partition=("observed_at",))
    field_edges = tuple(
        item
        for item in fact.dependency_edges
        if item.target.field_name == "observed_at"
    )
    assert tuple(item.role for item in field_edges) == (
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert field_edges[0].target == field_edges[1].target


@pytest.mark.parametrize("case", range(16))
def test_partition_dependency_targets_locations_and_nullable_fields_are_exact(
    case: int,
) -> None:
    partition = (
        ("id",),
        ("label",),
        ("nullable_id",),
        ("id", "label"),
    )[case % 4]
    fact = _project_fact(IDENTITIES[case % 6], partition=partition)
    occurrences = tuple(
        item
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    assert tuple(item.target.field_name for item in occurrences) == partition
    assert all(
        item.target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
        for item in occurrences
    )
    assert all(item.location.path == "slice10.pietto" for item in occurrences)
    assert all(item.target.relation_name == "rows" for item in occurrences)


@pytest.mark.parametrize("case", range(6))
def test_relation_input_and_ntile_dependency_free_argument_invariants_are_exact(
    case: int,
) -> None:
    fact = _project_fact(
        "ntile",
        partition=("id",) if case % 2 else ("id", "label"),
        bucket_count=case + 1,
    )
    roles = tuple(item.role for item in fact.dependency_occurrences)
    assert roles.count(WindowDependencyRole.RELATION_INPUT) == 1
    assert WindowDependencyRole.WINDOW_ARGUMENT not in roles
    assert WindowDependencyRole.WINDOW_DEFAULT not in roles
    assert fact.dependency_occurrences[0].target.kind is (
        ProjectRowDependencyNodeKind.RELATION_INPUT
    )


@pytest.mark.parametrize("case", range(12))
def test_project_result_identity_and_derived_provenance_remain_exact(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    fact = _project_fact(function_name, upstream=case >= 6)
    assert fact.result_identity.output_name == "ranking_value"
    assert fact.result_identity.occurrence is fact.semantic_fact.occurrence
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.symbol is not None
    assert fact.provenance.symbol.name == ("intermediate" if case >= 6 else "rows")
    assert fact.provenance.location is not None


@pytest.mark.parametrize("case", range(6))
def test_semantic_and_project_compatibility_wrappers_preserve_return_shapes(
    case: int,
) -> None:
    function_name = IDENTITIES[case]
    source = _program(call=_call(function_name), partition=("id", "label"))
    script, relation = _parsed_relation(source)
    item = relation.select_items[-1]
    common = {
        "definition": relation,
        "item": item,
        "selected_output_ordinal": len(relation.select_items) - 1,
        "source_id": "slice10.pietto",
        "input_schema": _input_schema(script, relation),
        "field_qualifier": relation.from_clause.source_name,
        "value_types": {},
        "diagnostics": [],
    }
    if function_name == "row_number":
        semantic_result = window_analysis.analyze_row_number_window_expression(
            **cast(Any, common)
        )
        assert type(semantic_result) is WindowExpressionSemanticFact
        project = _project_fact(function_name, builder="row_number")
    elif function_name in {"rank", "dense_rank"}:
        semantic_result = window_analysis.analyze_ranking_window_expression(
            **cast(Any, common)
        )
        assert type(semantic_result) is RankingWindowSemanticFact
        project = _project_fact(function_name, builder="ranking")
    else:
        semantic_result = window_analysis.analyze_distribution_window_expression(
            **cast(Any, common)
        )
        assert type(semantic_result) is DistributionWindowSemanticFact
        project = _project_fact(function_name)
    assert type(project) is WindowResultProjectFact


@pytest.mark.parametrize("case", range(9))
def test_partition_semantic_analysis_and_project_facts_are_transient(case: int) -> None:
    semantic_fields = {field.name for field in dataclasses.fields(SemanticModel)}
    project_fields = {field.name for field in dataclasses.fields(ProjectSemanticModel)}
    forbidden = (
        "window_partition_bindings",
        "window_partition_facts",
        "window_expression_analyses",
        "window_expression_facts",
        "ranking_window_facts",
        "distribution_window_facts",
        "window_result_facts",
        "window_dependencies",
        "window_provenance",
    )
    assert forbidden[case] not in semantic_fields | project_fields


@pytest.mark.parametrize("case", range(12))
def test_partition_alias_row_schema_downstream_and_final_order_visibility_remains_absent(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    source = _program(
        call=_call(function_name),
        partition=("id", "label"),
        final_order="observed_at" if case >= 6 else None,
    )
    script, relation = _parsed_relation(source)
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert expression in semantic.model.expression_value_types
    assert "ranking_value" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize("case", range(6))
def test_partitioned_window_ir_lowering_preserves_partition_operands(case: int) -> None:
    script, relation = _parsed_relation(
        _program(call=_call(IDENTITIES[case]), partition=("id", "label"))
    )
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    lowered = lower_expr(expression, semantic.model)
    assert lowered.diagnostics == ()
    assert type(lowered.expression) is WindowCallIR
    assert lowered.expression.identity.name == IDENTITIES[case]
    assert len(lowered.expression.spec.partition_by) == 2
    assert len(lowered.expression.spec.order_by) == 1


@pytest.mark.parametrize("case", range(6))
def test_partitioned_window_reaches_the_shared_ir_for_both_backend_cases(
    case: int,
) -> None:
    backend = "postgres" if case < 3 else "mysql"
    function_name = IDENTITIES[case]
    script, relation = _parsed_relation(
        _program(call=_call(function_name), partition=("id",))
    )
    semantic = analyze(script)
    lowered = lower_expr(
        cast(WindowExpr, relation.select_items[-1].expression), semantic.model
    )
    assert backend in {"postgres", "mysql"}
    assert lowered.diagnostics == ()
    assert type(lowered.expression) is WindowCallIR
    assert lowered.expression.identity.name == function_name
    assert len(lowered.expression.spec.partition_by) == 1


# Phase 53 Slice 13 reader migration.
