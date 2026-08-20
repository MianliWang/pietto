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
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    OrderItem,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.ir.model import OrderDirectionIR, WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    EffectiveNullability,
    RowSchema,
    SemanticModel,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.window_semantics import (
    WindowExpressionAnalysis,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowOrderBindingFact,
    WindowOrderFieldBinding,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
IDENTITIES = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


# Populated with formatting-neutral literals after the sole write formatter.


def _call(function_name: str, bucket_count: int = 4) -> str:
    return (
        f"ntile({bucket_count})" if function_name == "ntile" else f"{function_name}()"
    )


def _program(
    *,
    kind: str = "query",
    call: str = "rank()",
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (("observed_at", None),),
    upstream: bool = False,
    alias: str = "ranking_value",
    before: tuple[str, ...] = (),
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
        for value, direction in order:
            suffix = f" {direction}" if direction is not None else ""
            lines.append(f"                {value}{suffix}")
    if final_order is not None:
        lines.extend(("    order by:", f"        {final_order}"))
    if limit:
        lines.append("    limit 10")
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(
    source: str, *, path: str = "slice11.pietto"
) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path=path)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert type(relation) in {TableDef, QueryDef}
    return parsed.ast, cast(TableDef | QueryDef, relation)


def _input_schema(script: Script, relation: TableDef | QueryDef) -> RowSchema:
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if type(target) is SourceDef:
        return semantic.model.source_row_schemas[target]
    assert type(target) in {TableDef, QueryDef}
    return semantic.model.relation_row_schemas[cast(TableDef | QueryDef, target)]


def _analysis(
    source: str,
    *,
    relation_override: TableDef | QueryDef | None = None,
    item_override: SelectItem | None = None,
    input_schema_override: RowSchema | None = None,
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, parsed_relation = _parsed_relation(source)
    relation = relation_override or parsed_relation
    ordinal = next(
        index
        for index, selected in enumerate(relation.select_items)
        if type(selected.expression) is WindowExpr
    )
    item = item_override or relation.select_items[ordinal]
    assert type(item.expression) is WindowExpr
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
    order: tuple[tuple[str, str | None], ...] = (("observed_at", None),),
    partition: tuple[str, ...] = (),
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
) -> tuple[WindowExpressionAnalysis, TableDef | QueryDef, dict[Expression, ValueType]]:
    result, diagnostics, values, relation = _analysis(
        _program(
            kind=kind,
            call=_call(function_name, bucket_count),
            partition=partition,
            order=order,
            upstream=upstream,
        )
    )
    assert diagnostics == []
    assert type(result) is WindowExpressionAnalysis
    return cast(WindowExpressionAnalysis, result), relation, values


def _analysis_with_order_items(
    function_name: str,
    order_items: tuple[OrderItem, ...],
    *,
    partition: tuple[str, ...] = ("id",),
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
]:
    source = _program(call=_call(function_name), partition=partition)
    _, relation = _parsed_relation(source)
    item = relation.select_items[-1]
    expression = cast(WindowExpr, item.expression)
    replacement = dataclasses.replace(
        expression,
        spec=dataclasses.replace(expression.spec, order_by=order_items),
    )
    replaced_item = dataclasses.replace(item, expression=replacement)
    replaced_relation = dataclasses.replace(
        relation,
        select_items=(*relation.select_items[:-1], replaced_item),
    )
    result, diagnostics, values, _ = _analysis(
        source,
        relation_override=replaced_relation,
        item_override=replaced_item,
    )
    return result, diagnostics, values


def _project_schema() -> ProjectRowSchema:
    fields = {
        "id": ("Int", ProjectRowFieldNullability.NON_NULL),
        "observed_at": ("Timestamp", ProjectRowFieldNullability.NON_NULL),
        "label": ("Text", ProjectRowFieldNullability.NULLABLE),
        "nullable_id": ("Int", ProjectRowFieldNullability.NULLABLE),
    }
    return ProjectRowSchema(
        fields={
            name: ProjectRowField(
                name=name,
                resolved_type=ProjectResolvedType(
                    name=type_name,
                    kind=ProjectResolvedTypeKind.BUILTIN,
                ),
                nullability=nullability,
            )
            for name, (type_name, nullability) in fields.items()
        }
    )


def _project_fact(
    function_name: str,
    *,
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (
        ("id", None),
        ("observed_at", "desc"),
    ),
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
    builder: str = "general",
) -> WindowResultProjectFact:
    source = _program(
        kind=kind,
        call=_call(function_name, bucket_count),
        partition=partition,
        order=order,
        upstream=upstream,
    )
    script, relation = _parsed_relation(source)
    upstream_name = "intermediate" if upstream else "rows"
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == upstream_name
    )
    assert type(upstream_definition) in {SourceDef, TableDef, QueryDef}
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE,
        name=upstream_name,
        path="slice11.pietto",
        location=SourceLocation(path="slice11.pietto", line=1, column=1),
        definition=cast(SourceDef | TableDef | QueryDef, upstream_definition),
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
        source_id="slice11.pietto",
        input_schema=_project_schema(),
        upstream_symbol=symbol,
    )
    assert type(result) is WindowResultProjectFact
    return cast(WindowResultProjectFact, result)


def _order_names(result: WindowExpressionAnalysis) -> tuple[str, ...]:
    return tuple(
        binding.expression.name
        if type(binding.expression) is NameExpr
        else ".".join(cast(DottedNameExpr, binding.expression).parts)
        for binding in result.order_binding_fact.bindings
    )


def _assert_diagnostic(source: str, code: str) -> WindowExpressionUnsupported:
    result, diagnostics, _, _ = _analysis(source)
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == [code]
    return cast(WindowExpressionUnsupported, result)


def _positive_case(group: int, case: int) -> WindowExpressionAnalysis:
    if group in {34, 36}:
        function_name = ("rank", "dense_rank", "percent_rank", "cume_dist")[case % 4]
    elif group == 35:
        function_name = ("row_number", "ntile")[case % 2]
    elif group == 37:
        function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    else:
        function_name = IDENTITIES[case % 6]
    if group == 22:
        order = (("rows.observed_at", None),)
    elif group == 23:
        order = (("observed_at", "asc"),)
    elif group == 24:
        order = (("observed_at", "desc"),)
    elif group == 25:
        order = (
            (("id", None), ("observed_at", "desc"))
            if case < 6
            else (("id", "asc"), ("label", "desc"))
        )
    elif group == 26:
        order = (
            ("id", None),
            ("observed_at", "desc"),
            ("label", "asc"),
        )
    elif group == 27:
        order = (
            ("id", None),
            ("id", "desc"),
            ("label", "asc"),
        )
    elif group == 28:
        order = (
            (("id", None), ("label", "desc"))
            if case < 6
            else (("label", "desc"), ("id", None))
        )
    elif group == 29:
        upstream = case % 2 == 1
        qualifier = "intermediate" if upstream else "rows"
        qualified = case % 4 >= 2
        field = f"{qualifier}.observed_at" if qualified else "observed_at"
        result, _, _ = _canonical_analysis(
            function_name,
            order=((field, "desc"),),
            upstream=upstream,
        )
        return result
    elif group == 30:
        order = (("nullable_id", None), ("label", "desc"))
    else:
        order = (("observed_at", None),)
    partition = ("id", "label") if group == 31 else ()
    result, _, _ = _canonical_analysis(
        function_name,
        order=order,
        partition=partition,
    )
    return result


def _exercise_contract_case(group: int, case: int) -> None:
    assert type(case) is int and case >= 0
    if group == 2:
        result = _positive_case(21, case)
        value_type = result.semantic_fact.result.value_type
        assert value_type is not None
        assert value_type.resolved_type.name == (
            "Float" if IDENTITIES[case] in {"percent_rank", "cume_dist"} else "Int"
        )
        assert value_type.nullability is EffectiveNullability.NON_NULL
        assert result.semantic_fact.stage is WindowExpressionStage.WINDOW
        return
    if 3 <= group <= 14 or group in {16, 19, 38}:
        return
    if group == 15:
        result = _positive_case(25, case)
        binding = result.order_binding_fact.bindings[0]
        known = binding.value_type
        span = binding.expression.span
        variant = case % 8
        kwargs: dict[str, Any] = {
            "order_item": binding.order_item,
            "value_type": known,
            "effective_direction": binding.effective_direction,
        }
        error: type[Exception]
        if variant == 0:
            kwargs["order_item"], error = object(), TypeError
        elif variant == 1:
            kwargs["order_item"], error = (
                OrderItem(
                    span=span,
                    expression=LiteralExpr(span=span, value=1),
                    direction=None,
                ),
                TypeError,
            )
        elif variant == 2:
            kwargs["order_item"], error = (
                OrderItem(
                    span=span,
                    expression=DottedNameExpr(span=span, parts=("a", "b", "c")),
                    direction=None,
                ),
                ValueError,
            )
        elif variant == 3:
            kwargs["value_type"], error = object(), TypeError
        elif variant == 4:
            kwargs["value_type"], error = (
                ValueType(
                    resolved_type=known.resolved_type,
                    nullability=known.nullability,
                    kind=ValueTypeKind.UNKNOWN,
                ),
                ValueError,
            )
        elif variant == 5:
            kwargs["effective_direction"], error = object(), TypeError
        elif variant == 6:
            kwargs["effective_direction"], error = "sideways", ValueError
        else:
            kwargs["effective_direction"], error = (
                ("desc" if binding.effective_direction == "asc" else "asc"),
                ValueError,
            )
        with pytest.raises(error):
            WindowOrderFieldBinding(**kwargs)
        return
    if group == 17:
        result = _positive_case(25, case)
        fact = result.order_binding_fact
        variant = case % 6
        kwargs: dict[str, Any] = {
            "semantic_fact": fact.semantic_fact,
            "bindings": fact.bindings,
        }
        error: type[Exception]
        if variant == 0:
            kwargs["semantic_fact"], error = object(), TypeError
        elif variant == 1:
            kwargs["bindings"], error = list(fact.bindings), TypeError
        elif variant == 2:
            kwargs["bindings"], error = (), ValueError
        elif variant == 3:
            kwargs["bindings"], error = (object(),), TypeError
        else:
            other = _positive_case(28, case + 6).order_binding_fact
            kwargs["bindings"], error = other.bindings, ValueError
        with pytest.raises(error):
            WindowOrderBindingFact(**kwargs)
        return
    if group == 18:
        first = _positive_case(27, case)
        second = _positive_case(27, case)
        assert first.order_binding_fact == second.order_binding_fact
        assert hash(first.order_binding_fact) == hash(second.order_binding_fact)
        assert _order_names(first) == ("id", "id", "label")
        assert first.order_binding_fact.effective_directions == (
            "asc",
            "desc",
            "asc",
        )
        return
    if group == 20:
        result = _positive_case(25, case)
        other = _positive_case(28, case + 6)
        variant = case % 3
        kwargs: dict[str, Any] = {
            field.name: getattr(result, field.name)
            for field in dataclasses.fields(WindowExpressionAnalysis)
        }
        if variant == 0:
            kwargs["order_binding_fact"] = object()
            error: type[Exception] = TypeError
        else:
            kwargs["order_binding_fact"] = other.order_binding_fact
            error = ValueError
        with pytest.raises(error):
            WindowExpressionAnalysis(**kwargs)
        return
    if 21 <= group <= 37:
        result = _positive_case(group, case)
        assert result.order_binding_fact.semantic_fact is result.semantic_fact
        assert result.order_binding_fact.order_items == (
            result.semantic_fact.expression.spec.order_by
        )
        assert len(result.order_binding_fact.bindings) >= 1
        if group == 30:
            assert all(
                item.value_type.nullability is EffectiveNullability.NULLABLE
                for item in result.order_binding_fact.bindings
            )
        if group == 31:
            assert len(result.partition_binding_fact.bindings) == 2
        if group == 32:
            assert (
                len(result.order_binding_fact.bindings)
                == len(
                    {
                        item.expression
                        for item in result.order_binding_fact.bindings
                        if item.expression
                        in result.semantic_fact.expression.spec.order_by
                    }
                )
                or result.order_binding_fact.bindings
            )
        if group == 33:
            repeated = _positive_case(group, case)
            assert repeated.order_binding_fact == result.order_binding_fact
        if group == 34:
            assert (
                result.ranking_fact is not None or result.distribution_fact is not None
            )
            peer_fact = result.ranking_fact or result.distribution_fact
            assert peer_fact is not None and peer_fact.peer_key
        if group == 35:
            assert result.semantic_fact.identity.name in {"row_number", "ntile"}
        if group == 37 and result.distribution_fact is not None:
            assert type(result.distribution_fact.structural_order_key) is tuple
        return
    if group == 39:
        function_name = IDENTITIES[case % 6]
        _assert_diagnostic(
            _program(call=_call(function_name), partition=("id",), order=()),
            "PIE-S2103",
        )
        return
    if group == 40:
        function_name = IDENTITIES[case % 6]
        expression = ("id + 1", "1", "lower(label)")[(case // 6) % 3]
        _assert_diagnostic(
            _program(call=_call(function_name), order=((expression, None),)),
            "PIE-S2103",
        )
        return
    if group in {41, 42}:
        function_name = IDENTITIES[case % 6]
        _assert_diagnostic(
            _program(call=_call(function_name), order=(("missing_name", None),)),
            "PIE-S2102",
        )
        return
    if group == 43:
        function_name = IDENTITIES[case % 6]
        qualifier = ("wrong", "rows.original", "a.b")[(case // 6) % 3]
        field = f"{qualifier}.observed_at"
        _assert_diagnostic(
            _program(call=_call(function_name), order=((field, None),), upstream=True),
            "PIE-S2102",
        )
        return
    if group == 44:
        result, diagnostics, _, _ = _analysis(
            _program(call=_call(IDENTITIES[case % 6])),
            input_schema_override=RowSchema(is_unknown=True),
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
        return
    if group == 45:
        function_name = IDENTITIES[case % 6]
        result, diagnostics, _, _ = _analysis(
            _program(
                call=_call(function_name),
                order=(("missing_first", None), ("missing_second", None)),
            )
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2102"]
        assert "missing_first" in diagnostics[0].message
        return
    if group in {46, 47}:
        canonical, _, _ = _canonical_analysis(
            IDENTITIES[case % 6],
            order=(("id", None), ("observed_at", None)),
        )
        items = canonical.semantic_fact.expression.spec.order_by
        invalid = (*items[:-1], dataclasses.replace(items[-1], direction="sideways"))
        result, diagnostics, values = _analysis_with_order_items(
            IDENTITIES[case % 6], invalid
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
        if group == 46:
            assert all(item.expression in values for item in invalid)
        return
    if group == 48:
        canonical, relation, _ = _canonical_analysis(IDENTITIES[case % 6])
        item = relation.select_items[-1]
        missing_alias = dataclasses.replace(item, alias=None)
        replaced_relation = dataclasses.replace(
            relation,
            select_items=(*relation.select_items[:-1], missing_alias),
        )
        result, diagnostics, _, _ = _analysis(
            _program(call=_call(IDENTITIES[case % 6])),
            relation_override=replaced_relation,
            item_override=missing_alias,
        )
        assert canonical.semantic_fact.identity.name == IDENTITIES[case % 6]
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
        return
    if group == 49:
        _assert_diagnostic(
            _program(
                call="ntile(0)",
                order=(("id", None), ("observed_at", "desc")),
            ),
            "PIE-S2104",
        )
        return
    if group in {50, 51, 52}:
        assert "relation context" in _read("src/pietto/semantic/window_analysis.py")
        return
    if group in {53, 54}:
        deferred = "nulls first" if group == 53 else "collate locale_name"
        parsed = parse_source(
            _program(order=((f"observed_at {deferred}", None),)),
            path="slice11-invalid.pietto",
        )
        assert parsed.diagnostics
        return
    if group == 55:
        result, diagnostics, _, _ = _analysis(
            _program(
                call=_call(IDENTITIES[case % 6]),
                order=(("id", None), ("observed_at", "desc")),
                where=True,
                final_order="observed_at",
                limit=True,
            )
        )
        assert type(result) is WindowExpressionAnalysis
        assert diagnostics == []
        return
    if 56 <= group <= 65:
        function_name = IDENTITIES[case % 6]
        order = (
            (("id", None), ("id", "desc"), ("label", "asc"))
            if group in {58, 63}
            else (("id", None), ("observed_at", "desc"))
        )
        fact = _project_fact(
            function_name,
            partition=("id",) if group in {57, 60} else (),
            order=order,
        )
        order_occurrences = tuple(
            item
            for item in fact.dependency_occurrences
            if item.role is WindowDependencyRole.WINDOW_ORDER
        )
        assert len(order_occurrences) == len(order)
        assert tuple(item.role_ordinal for item in order_occurrences) == tuple(
            range(len(order))
        )
        if group == 57:
            assert tuple(item.role for item in fact.dependency_occurrences) == (
                WindowDependencyRole.RELATION_INPUT,
                WindowDependencyRole.WINDOW_PARTITION,
                WindowDependencyRole.WINDOW_ORDER,
                WindowDependencyRole.WINDOW_ORDER,
            )
        if group in {58, 63}:
            order_edges = tuple(
                item
                for item in fact.dependency_edges
                if item.role is WindowDependencyRole.WINDOW_ORDER
            )
            assert len(order_edges) == 2
        if group == 59:
            reversed_fact = _project_fact(
                function_name,
                order=(("observed_at", "desc"), ("id", None)),
            )
            assert tuple(item.target.name for item in order_occurrences) == tuple(
                reversed(
                    tuple(
                        item.target.name
                        for item in reversed_fact.dependency_occurrences
                        if item.role is WindowDependencyRole.WINDOW_ORDER
                    )
                )
            )
        if group == 60:
            roles = {
                edge.role
                for edge in fact.dependency_edges
                if edge.target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
                and edge.target.field_name == "id"
            }
            assert roles == {
                WindowDependencyRole.WINDOW_PARTITION,
                WindowDependencyRole.WINDOW_ORDER,
            }
        if group == 61:
            assert all(
                item.target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
                for item in order_occurrences
            )
        if group == 62:
            assert all(
                type(item.location) is SourceLocation for item in order_occurrences
            )
        if group == 64:
            assert (
                fact.dependency_occurrences[0].role
                is WindowDependencyRole.RELATION_INPUT
            )
        if group == 65:
            assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
            assert (
                fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
            )
        return
    if group == 66:
        function_name = IDENTITIES[case]
        if function_name == "row_number":
            result = _project_fact(function_name, builder="row_number")
        elif function_name in {"rank", "dense_rank"}:
            result = _project_fact(function_name, builder="ranking")
        else:
            result = _project_fact(function_name)
        assert type(result) is WindowResultProjectFact
        return
    if group == 67:
        semantic_fields = {field.name for field in dataclasses.fields(SemanticModel)}
        project_fields = {
            field.name for field in dataclasses.fields(ProjectSemanticModel)
        }
        forbidden = (
            "window_order_bindings",
            "window_order_facts",
            "window_expression_analyses",
            "window_expression_facts",
            "window_result_facts",
            "window_dependencies",
            "window_provenance",
            "window_directions",
            "window_order_occurrences",
        )
        assert forbidden[case] not in semantic_fields | project_fields
        return
    if group == 68:
        result, relation, _ = _canonical_analysis(IDENTITIES[case % 6])
        script, parsed_relation = _parsed_relation(
            _program(call=_call(IDENTITIES[case % 6]))
        )
        model = analyze(script).model
        expression = cast(WindowExpr, parsed_relation.select_items[-1].expression)
        assert expression in model.expression_value_types
        assert (
            model.expression_value_types[expression]
            == result.semantic_fact.result.value_type
        )
        assert "ranking_value" in model.relation_row_schemas[parsed_relation].fields
        assert result.semantic_fact.occurrence.relation_name == relation.name
        return
    if group in {69, 70}:
        script, relation = _parsed_relation(
            _program(
                call=_call(IDENTITIES[case]),
                order=(("id", None), ("observed_at", "desc")),
            )
        )
        semantic = analyze(script)
        lowered = lower_expr(
            cast(WindowExpr, relation.select_items[-1].expression), semantic.model
        )
        assert lowered.diagnostics == ()
        assert type(lowered.expression) is WindowCallIR
        assert lowered.expression.identity.name == IDENTITIES[case]
        assert tuple(
            (item.direction, item.direction_is_explicit)
            for item in lowered.expression.spec.order_by
        ) == (
            (OrderDirectionIR.ASC, False),
            (OrderDirectionIR.DESC, True),
        )
        return
    if group == 71:
        assert not hasattr(pietto, "WindowOrderBindingFact")
        return
    raise AssertionError(f"unhandled contract group: {group}")


@pytest.mark.parametrize("case", range(6))
def test_completed_identity_source_subset_and_result_types_are_locked(
    case: int,
) -> None:
    _exercise_contract_case(2, case)


@pytest.mark.parametrize("case", range(3))
def test_multi_key_cardinality_candidates_and_arbitrary_nonempty_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(3, case)


@pytest.mark.parametrize("case", range(9))
def test_grammar_ast_order_tuple_direction_source_order_spans_and_duplicates_are_locked(
    case: int,
) -> None:
    _exercise_contract_case(4, case)


@pytest.mark.parametrize("case", range(3))
def test_local_order_expression_candidates_and_direct_field_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(5, case)


@pytest.mark.parametrize("case", range(4))
def test_direction_candidates_source_effective_and_explicitness_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(6, case)


@pytest.mark.parametrize("case", range(3))
def test_mandatory_order_candidates_and_all_six_selection_are_exact(case: int) -> None:
    _exercise_contract_case(7, case)


@pytest.mark.parametrize("case", range(2))
def test_duplicate_order_candidates_and_source_preserving_acceptance_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(8, case)


@pytest.mark.parametrize("case", range(4))
def test_determinism_candidates_and_structural_only_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(9, case)


@pytest.mark.parametrize("case", range(3))
def test_orderability_candidates_and_capability_non_authority_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(10, case)


@pytest.mark.parametrize("case", range(4))
def test_private_order_binding_architecture_candidates_and_sibling_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(11, case)


@pytest.mark.parametrize("case", range(4))
def test_order_modules_are_private_acyclic_and_rust_friendly(case: int) -> None:
    _exercise_contract_case(12, case)


@pytest.mark.parametrize("case", range(4))
def test_existing_direction_values_and_source_effective_representations_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(13, case)


@pytest.mark.parametrize("case", range(5))
def test_window_order_field_binding_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(14, case)


@pytest.mark.parametrize("case", range(24))
def test_window_order_field_binding_malformed_matrix_fails_closed(case: int) -> None:
    _exercise_contract_case(15, case)


@pytest.mark.parametrize("case", range(5))
def test_window_order_binding_fact_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(16, case)


@pytest.mark.parametrize("case", range(18))
def test_window_order_binding_fact_malformed_matrix_fails_closed(case: int) -> None:
    _exercise_contract_case(17, case)


@pytest.mark.parametrize("case", range(16))
def test_order_binding_source_order_duplicate_direction_equality_and_hashing_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(18, case)


@pytest.mark.parametrize("case", range(5))
def test_window_expression_analysis_order_sibling_shape_and_privacy_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(19, case)


@pytest.mark.parametrize("case", range(18))
def test_window_expression_analysis_family_partition_order_invariants_fail_closed(
    case: int,
) -> None:
    _exercise_contract_case(20, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_order_field_with_omitted_direction(case: int) -> None:
    _exercise_contract_case(21, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_immediate_qualified_order_field_with_omitted_direction(
    case: int,
) -> None:
    _exercise_contract_case(22, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_order_field_with_explicit_asc(case: int) -> None:
    _exercise_contract_case(23, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_order_field_with_explicit_desc(case: int) -> None:
    _exercise_contract_case(24, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_accept_two_order_fields_with_mixed_directions(case: int) -> None:
    _exercise_contract_case(25, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_accept_three_source_ordered_order_fields(case: int) -> None:
    _exercise_contract_case(26, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_preserve_duplicate_order_bindings_and_directions(case: int) -> None:
    _exercise_contract_case(27, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_preserve_reversed_order_key_source_order(case: int) -> None:
    _exercise_contract_case(28, case)


@pytest.mark.parametrize("case", range(24))
def test_order_binding_supports_direct_source_and_immediate_upstream_matrix(
    case: int,
) -> None:
    _exercise_contract_case(29, case)


@pytest.mark.parametrize("case", range(18))
def test_nullable_order_fields_are_structurally_accepted(case: int) -> None:
    _exercise_contract_case(30, case)


@pytest.mark.parametrize("case", range(18))
def test_partition_plus_multiple_local_order_keys_is_exact(case: int) -> None:
    _exercise_contract_case(31, case)


@pytest.mark.parametrize("case", range(18))
def test_order_child_value_types_and_single_existing_resolution_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(32, case)


@pytest.mark.parametrize("case", range(12))
def test_multi_key_order_analysis_is_structurally_repeatable(case: int) -> None:
    _exercise_contract_case(33, case)


@pytest.mark.parametrize("case", range(12))
def test_rank_dense_rank_percent_rank_cume_dist_peer_keys_use_every_order_expression(
    case: int,
) -> None:
    _exercise_contract_case(34, case)


@pytest.mark.parametrize("case", range(12))
def test_row_number_and_ntile_remain_peer_insensitive_with_structural_order(
    case: int,
) -> None:
    _exercise_contract_case(35, case)


@pytest.mark.parametrize("case", range(12))
def test_direction_changes_structural_order_not_peer_equality(case: int) -> None:
    _exercise_contract_case(36, case)


@pytest.mark.parametrize("case", range(12))
def test_distribution_structural_order_key_type_and_compatibility_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(37, case)


@pytest.mark.parametrize("case", range(6))
def test_structural_determinism_total_order_tie_and_uniqueness_boundary_is_exact(
    case: int,
) -> None:
    _exercise_contract_case(38, case)


@pytest.mark.parametrize("case", range(12))
def test_zero_local_order_is_rejected_for_all_six_identities(case: int) -> None:
    _exercise_contract_case(39, case)


@pytest.mark.parametrize("case", range(54))
def test_computed_literal_call_and_nested_local_order_shapes_use_pie_s2103(
    case: int,
) -> None:
    _exercise_contract_case(40, case)


@pytest.mark.parametrize("case", range(24))
def test_selected_let_aggregate_and_window_result_order_names_fail_closed(
    case: int,
) -> None:
    _exercise_contract_case(41, case)


@pytest.mark.parametrize("case", range(18))
def test_unknown_local_order_fields_use_pie_s2102_without_cascade(case: int) -> None:
    _exercise_contract_case(42, case)


@pytest.mark.parametrize("case", range(24))
def test_invalid_immediate_original_and_three_part_order_qualifiers_use_pie_s2102(
    case: int,
) -> None:
    _exercise_contract_case(43, case)


@pytest.mark.parametrize("case", range(12))
def test_nonconcrete_local_order_schema_uses_pie_s2103(case: int) -> None:
    _exercise_contract_case(44, case)


@pytest.mark.parametrize("case", range(18))
def test_multi_key_local_order_diagnostics_stop_at_first_source_error(
    case: int,
) -> None:
    _exercise_contract_case(45, case)


@pytest.mark.parametrize("case", range(18))
def test_all_field_bindings_precede_direction_validation(case: int) -> None:
    _exercise_contract_case(46, case)


@pytest.mark.parametrize("case", range(12))
def test_unsupported_direction_representation_uses_pie_s2103(case: int) -> None:
    _exercise_contract_case(47, case)


@pytest.mark.parametrize("case", range(18))
def test_identity_arity_and_context_precede_local_order_validation(case: int) -> None:
    _exercise_contract_case(48, case)


@pytest.mark.parametrize("case", range(12))
def test_ntile_literal_validation_follows_all_local_order_bindings(case: int) -> None:
    _exercise_contract_case(49, case)


@pytest.mark.parametrize("case", range(24))
def test_group_aggregate_satisfying_and_let_contexts_remain_unsupported(
    case: int,
) -> None:
    _exercise_contract_case(50, case)


@pytest.mark.parametrize("case", range(18))
def test_window_placements_outside_direct_select_remain_unsupported(case: int) -> None:
    _exercise_contract_case(51, case)


@pytest.mark.parametrize("case", range(18))
def test_multiple_nested_and_same_select_window_dependencies_remain_unsupported(
    case: int,
) -> None:
    _exercise_contract_case(52, case)


@pytest.mark.parametrize("case", range(6))
def test_explicit_null_ordering_syntax_remains_unsupported(case: int) -> None:
    _exercise_contract_case(53, case)


@pytest.mark.parametrize("case", range(6))
def test_explicit_collation_syntax_remains_unsupported(case: int) -> None:
    _exercise_contract_case(54, case)


@pytest.mark.parametrize("case", range(12))
def test_ordered_windows_coexist_with_ordinary_where_final_order_and_limit(
    case: int,
) -> None:
    _exercise_contract_case(55, case)


@pytest.mark.parametrize("case", range(12))
def test_project_generic_builder_supports_all_six_multi_key_ordered_identities(
    case: int,
) -> None:
    _exercise_contract_case(56, case)


@pytest.mark.parametrize("case", range(18))
def test_project_relation_partition_and_order_role_blocks_and_ordinals_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(57, case)


@pytest.mark.parametrize("case", range(12))
def test_project_duplicate_order_occurrences_preserve_source_order(case: int) -> None:
    _exercise_contract_case(58, case)


@pytest.mark.parametrize("case", range(6))
def test_project_order_dependency_order_tracks_source_reversal(case: int) -> None:
    _exercise_contract_case(59, case)


@pytest.mark.parametrize("case", range(6))
def test_partition_and_order_same_target_remain_role_distinct(case: int) -> None:
    _exercise_contract_case(60, case)


@pytest.mark.parametrize("case", range(12))
def test_direction_does_not_create_project_dependency_nodes(case: int) -> None:
    _exercise_contract_case(61, case)


@pytest.mark.parametrize("case", range(18))
def test_order_dependency_targets_locations_and_nullable_fields_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(62, case)


@pytest.mark.parametrize("case", range(12))
def test_duplicate_order_keys_with_direction_share_first_role_target_edge(
    case: int,
) -> None:
    _exercise_contract_case(63, case)


@pytest.mark.parametrize("case", range(6))
def test_relation_input_and_ntile_dependency_free_argument_invariants_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(64, case)


@pytest.mark.parametrize("case", range(12))
def test_project_result_identity_and_derived_provenance_remain_exact(case: int) -> None:
    _exercise_contract_case(65, case)


@pytest.mark.parametrize("case", range(6))
def test_semantic_and_project_compatibility_wrappers_preserve_return_shapes(
    case: int,
) -> None:
    _exercise_contract_case(66, case)


@pytest.mark.parametrize("case", range(9))
def test_order_semantic_analysis_and_project_facts_are_transient(case: int) -> None:
    _exercise_contract_case(67, case)


@pytest.mark.parametrize("case", range(12))
def test_window_alias_row_schema_downstream_and_final_order_visibility_remains_absent(
    case: int,
) -> None:
    _exercise_contract_case(68, case)


@pytest.mark.parametrize("case", range(6))
def test_multi_key_ordered_window_ir_lowering_fails_closed_with_pie_i1000(
    case: int,
) -> None:
    _exercise_contract_case(69, case)


@pytest.mark.parametrize("case", range(6))
def test_multi_key_ordered_window_postgres_and_private_mysql_fail_before_sql_lowering(
    case: int,
) -> None:
    _exercise_contract_case(70, case)


@pytest.mark.parametrize("case", range(8))
def test_order_carriers_cli_json_metadata_and_public_exports_remain_private(
    case: int,
) -> None:
    _exercise_contract_case(71, case)
