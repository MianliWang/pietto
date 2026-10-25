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
    build_window_result_project_fact,
)
from pietto.ast_nodes import (
    ComparisonExpr,
    Expression,
    GroupByClause,
    GroupByItem,
    LetBinding,
    LetClause,
    LiteralExpr,
    NameExpr,
    QueryDef,
    SatisfyingClause,
    Script,
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.ir.model import WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.generic_compatibility import SignatureMatch
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.nullability_formulas import (
    NullabilityEvaluationMatch,
    NullabilityFormulaKind,
)
from pietto.semantic.window_semantics import (
    NavigationDefaultFact,
    NavigationDirection,
    NavigationOffsetFact,
    NavigationWindowSemanticFact,
    WindowExpressionAnalysis,
    WindowExpressionUnsupported,
    WindowOrderBindingFact,
    WindowPartitionBindingFact,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
IDENTITIES = ("lag", "lead")


# Populated from the binding plan before the pre-formatter audit.


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _program(
    call: str,
    *,
    alias: bool = True,
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (("id", None),),
    extra_window: bool = False,
    kind: str = "query",
) -> str:
    prefix = (
        "enum Status:\n"
        "    active\n"
        "    paused\n"
        "shape Payload:\n"
        "    code: Int\n"
        "type Alias = Int\n"
        "shape Row:\n"
        "    id: Int\n"
        "    nullable_id: Int | None\n"
        "    score: Float\n"
        "    nullable_score: Float | None\n"
        "    label: Text | None\n"
        "    flag: Bool\n"
        "    status: Status\n"
        "    payload: Payload | None\n"
        "    alias_value: Alias | None\n"
        'source rows: Row = postgres.table("rows")\n'
    )
    lines = [f"{kind} navigated:", "    from rows", "    select:"]
    if extra_window:
        lines.extend(
            (
                "        ranking_value = row_number() window(",
                "            order by",
                "                id)",
            )
        )
    selected = f"navigation_value = {call} window(" if alias else f"{call} window("
    lines.append(f"        {selected}")
    if partition:
        lines.append("            partition by")
        lines.extend(
            ",\n".join(f"                {value}" for value in partition).splitlines()
        )
    if order:
        lines.append("            order by")
        lines.extend(
            ",\n".join(
                f"                {value}"
                + (f" {direction}" if direction is not None else "")
                for value, direction in order
            ).splitlines()
        )
    lines[-1] += ")"
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(source: str) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path="slice12.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert type(relation) in {TableDef, QueryDef}
    return parsed.ast, cast(TableDef | QueryDef, relation)


def _replace_call_argument_with_comparison(
    relation: TableDef | QueryDef,
    position: int,
) -> TableDef | QueryDef:
    items = list(relation.select_items)
    ordinal = max(
        index for index, item in enumerate(items) if type(item.expression) is WindowExpr
    )
    item = items[ordinal]
    window = cast(WindowExpr, item.expression)
    arguments = list(window.call.arguments)
    span = arguments[position].span
    arguments[position] = ComparisonExpr(
        span=span,
        left=NameExpr(span=span, name="id"),
        operator="=",
        right=LiteralExpr(span=span, value=1),
    )
    items[ordinal] = dataclasses.replace(
        item,
        expression=dataclasses.replace(
            window,
            call=dataclasses.replace(window.call, arguments=tuple(arguments)),
        ),
    )
    return dataclasses.replace(relation, select_items=tuple(items))


def _row_schema() -> RowSchema:
    definitions = {
        "id": ("Int", TypeKind.BUILTIN, EffectiveNullability.NON_NULL),
        "nullable_id": ("Int", TypeKind.BUILTIN, EffectiveNullability.NULLABLE),
        "score": ("Float", TypeKind.BUILTIN, EffectiveNullability.NON_NULL),
        "nullable_score": (
            "Float",
            TypeKind.BUILTIN,
            EffectiveNullability.NULLABLE,
        ),
        "label": ("Text", TypeKind.BUILTIN, EffectiveNullability.NULLABLE),
        "flag": ("Bool", TypeKind.BUILTIN, EffectiveNullability.NON_NULL),
        "status": ("Status", TypeKind.ENUM, EffectiveNullability.NON_NULL),
        "payload": ("Payload", TypeKind.SHAPE, EffectiveNullability.NULLABLE),
        "alias_value": (
            "Alias",
            TypeKind.TYPE_ALIAS,
            EffectiveNullability.NULLABLE,
        ),
        "unknown_type": (
            "Unknown",
            TypeKind.UNKNOWN,
            EffectiveNullability.UNKNOWN,
        ),
        "unknown_nullability": (
            "Int",
            TypeKind.BUILTIN,
            EffectiveNullability.UNKNOWN,
        ),
    }
    return RowSchema(
        fields={
            name: RowField(
                name=name,
                resolved_type=ResolvedType(name=type_name, kind=type_kind),
                nullability=nullability,
            )
            for name, (type_name, type_kind, nullability) in definitions.items()
        }
    )


def _analysis(
    call: str,
    *,
    alias: bool = True,
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (("id", None),),
    extra_window: bool = False,
    relation_override: TableDef | QueryDef | None = None,
    schema: RowSchema | None = None,
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    Script,
    TableDef | QueryDef,
]:
    script, parsed_relation = _parsed_relation(
        _program(
            call,
            partition=partition,
            order=order,
            extra_window=extra_window,
        )
    )
    if not alias:
        parsed_relation = dataclasses.replace(
            parsed_relation,
            select_items=tuple(
                dataclasses.replace(item, alias=None)
                if type(item.expression) is WindowExpr
                else item
                for item in parsed_relation.select_items
            ),
        )
    relation = relation_override or parsed_relation
    ordinal = max(
        index
        for index, item in enumerate(relation.select_items)
        if type(item.expression) is WindowExpr
    )
    item = relation.select_items[ordinal]
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_window_expression(
        definition=relation,
        item=item,
        selected_output_ordinal=ordinal,
        source_id="slice12.pietto",
        input_schema=schema or _row_schema(),
        field_qualifier=relation.from_clause.source_name,
        value_types=values,
        diagnostics=diagnostics,
    )
    return result, diagnostics, values, script, relation


def _success(
    call: str,
    **kwargs: Any,
) -> tuple[WindowExpressionAnalysis, dict[Expression, ValueType], TableDef | QueryDef]:
    result, diagnostics, values, _, relation = _analysis(call, **kwargs)
    assert diagnostics == []
    assert type(result) is WindowExpressionAnalysis
    assert result.navigation_fact is not None
    return result, values, relation


def _failure(call: str, code: str, **kwargs: Any) -> WindowExpressionUnsupported:
    result, diagnostics, _, _, _ = _analysis(call, **kwargs)
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == [code]
    return result


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
            "nullable_id": ProjectRowField(
                name="nullable_id",
                resolved_type=ProjectResolvedType(
                    name="Int", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NULLABLE,
            ),
            "label": ProjectRowField(
                name="label",
                resolved_type=ProjectResolvedType(
                    name="Text", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NULLABLE,
            ),
        }
    )


def _project_fact(
    call: str,
    *,
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (("id", None),),
) -> WindowResultProjectFact:
    script, relation = _parsed_relation(
        _program(call, partition=partition, order=order)
    )
    source = next(item for item in script.definitions if type(item) is SourceDef)
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.SOURCE,
        name="rows",
        path="slice12.pietto",
        location=SourceLocation(path="slice12.pietto", line=1, column=1),
        definition=cast(SourceDef, source),
    )
    result = build_window_result_project_fact(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice12.pietto",
        input_schema=_project_schema(),
        upstream_symbol=symbol,
    )
    assert type(result) is WindowResultProjectFact
    return result


def _result_nullability(call: str) -> EffectiveNullability:
    result, _, _ = _success(call)
    value_type = result.semantic_fact.result.value_type
    assert value_type is not None
    return value_type.nullability


def test_frontend_call_ast_and_spans_need_no_grammar_or_generated_change() -> None:
    _, relation = _parsed_relation(_program("lag(id, 0, nullable_id)"))
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert tuple(type(item) for item in expression.call.arguments) == (
        NameExpr,
        LiteralExpr,
        NameExpr,
    )
    assert all(item.span.path == "slice12.pietto" for item in expression.call.arguments)


@pytest.mark.parametrize("case", range(2))
def test_navigation_identities_are_exact_unqualified_lowercase(case: int) -> None:
    identity = IDENTITIES[case]
    result, _, _ = _success(f"{identity}(id)")
    assert result.semantic_fact.identity.namespace == ()
    assert result.semantic_fact.identity.name == identity
    assert result.navigation_fact is not None
    assert result.navigation_fact.direction.value == identity


@pytest.mark.parametrize("case", range(8))
def test_unsupported_navigation_identity_spellings_fail_closed(case: int) -> None:
    names = ("Lag", "Lead", "LAG", "LEAD", "rows.lag", "rows.lead", "lagged", "leading")
    _failure(f"{names[case]}(id)", "PIE-S2103")


@pytest.mark.parametrize("case", range(6))
def test_navigation_accepts_each_selected_arity(case: int) -> None:
    identity = IDENTITIES[case // 3]
    arguments = ("id", "id, 0", "id, 2, nullable_id")[case % 3]
    result, _, _ = _success(f"{identity}({arguments})")
    assert len(result.semantic_fact.expression.call.arguments) == case % 3 + 1


@pytest.mark.parametrize("case", range(4))
def test_navigation_rejects_zero_and_over_three_arguments(case: int) -> None:
    identity = IDENTITIES[case // 2]
    arguments = "" if case % 2 == 0 else "id, 1, id, id"
    _failure(f"{identity}({arguments})", "PIE-S2104")


@pytest.mark.parametrize("case", range(8))
def test_navigation_alias_and_relation_context_requirements_are_preserved(
    case: int,
) -> None:
    identity = IDENTITIES[case // 4]
    local_case = case % 4
    if local_case == 0:
        _failure(f"{identity}(id)", "PIE-S2103", alias=False)
        return
    _, parsed = _parsed_relation(_program(f"{identity}(id)"))
    span = parsed.span
    if local_case == 1:
        relation = dataclasses.replace(
            parsed,
            group_by_clause=GroupByClause(
                span=span,
                items=(GroupByItem(span=span, key=NameExpr(span=span, name="id")),),
            ),
        )
    elif local_case == 2:
        relation = dataclasses.replace(
            parsed,
            satisfying_clause=SatisfyingClause(
                span=span, expression=NameExpr(span=span, name="id")
            ),
        )
    else:
        relation = dataclasses.replace(
            parsed,
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
    _failure(f"{identity}(id)", "PIE-S2103", relation_override=relation)


@pytest.mark.parametrize("case", (0, 1, 4, 5))
def test_navigation_rejects_same_select_nested_and_multiple_window_outputs(
    case: int,
) -> None:
    identity = IDENTITIES[case % 2]
    if case < 4:
        result, _, relation = _success(f"{identity}(id)", extra_window=True)
        assert result.semantic_fact.occurrence.selected_output_ordinal == 1
        assert len(relation.select_items) == 2
    else:
        _failure(f"{identity}(lower(id))", "PIE-S2104")


@pytest.mark.parametrize("case", range(16))
def test_value_accepts_bare_and_immediate_qualified_fields(case: int) -> None:
    identity = IDENTITIES[case // 8]
    fields = ("id", "nullable_id", "score", "nullable_score")
    field = fields[(case % 8) // 2]
    expression = field if case % 2 == 0 else f"rows.{field}"
    result, values, _ = _success(f"{identity}({expression})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.value_expression in values
    assert fact.value_type.kind is ValueTypeKind.KNOWN


@pytest.mark.parametrize("case", range(8))
def test_value_accepts_selected_scalar_literal_kinds(case: int) -> None:
    identity = IDENTITIES[case // 4]
    literal = ("True", '"fallback"', "7", "1.5")[case % 4]
    result, _, _ = _success(f"{identity}({literal})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert not fact.value_always_null
    assert type(fact.value_expression) is LiteralExpr


@pytest.mark.parametrize("case", range(8))
def test_value_null_binding_uses_concrete_explicit_default(case: int) -> None:
    identity = IDENTITIES[case // 4]
    default = ("id", "score", '"fallback"', "False")[case % 4]
    result, _, _ = _success(f"{identity}(None, 1, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.value_always_null
    assert fact.signature_match.bindings[0].first_parameter_position == 0


@pytest.mark.parametrize("case", range(4))
def test_value_rejects_unbound_null_without_concrete_default(case: int) -> None:
    identity = IDENTITIES[case // 2]
    call = f"{identity}(None)" if case % 2 == 0 else f"{identity}(None, 1, None)"
    _failure(call, "PIE-S2104")


@pytest.mark.parametrize("case", range(14))
def test_value_rejects_nonselected_expression_shapes(case: int) -> None:
    identity = IDENTITIES[case // 7]
    expressions = (
        "-id",
        "id + 1",
        "id = 1",
        "1 <= id <= 2",
        "id is None",
        "lower(label)",
        "rank()",
    )
    expression = expressions[case % 7]
    if expression == "id = 1":
        call = f"{identity}(id)"
        _, relation = _parsed_relation(_program(call))
        result, diagnostics, _, _, _ = _analysis(
            call,
            relation_override=_replace_call_argument_with_comparison(relation, 0),
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2104"]
        return
    _failure(f"{identity}({expression})", "PIE-S2104")


@pytest.mark.parametrize("case", range(4))
def test_value_unknown_field_reports_PIE_S2102_at_value_span(case: int) -> None:
    identity = IDENTITIES[case // 2]
    expression = "missing" if case % 2 == 0 else "rows.missing"
    result, diagnostics, _, _, relation = _analysis(f"{identity}({expression})")
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == ["PIE-S2102"]
    value = cast(WindowExpr, relation.select_items[-1].expression).call.arguments[0]
    assert diagnostics[0].location.column == value.span.column


@pytest.mark.parametrize("case", range(4))
def test_value_original_or_three_part_qualifier_reports_PIE_S2104(case: int) -> None:
    identity = IDENTITIES[case // 2]
    expression = "original.id" if case % 2 == 0 else "rows.original.id"
    _failure(f"{identity}({expression})", "PIE-S2104")


@pytest.mark.parametrize("case", range(4))
def test_value_nonconcrete_type_and_type_alias_fail_closed(case: int) -> None:
    identity = IDENTITIES[case // 2]
    field = ("unknown_type", "alias_value")[case % 2]
    _failure(f"{identity}({field})", "PIE-S2104")


def test_an_unknown_nullability_is_read_only_where_the_result_does_not_read_it() -> (
    None
):
    """A value or default of known type whose nullability is unknown, such as
    an earlier relation's computed column, is accepted where the result's
    nullability does not depend on it: `first_value`, `last_value`,
    `nth_value`, and `lag` or `lead` without a default or with a nullable
    one, at an offset other than 0. Where it does, as at offset 0 or beside a
    non-null default, the call stays PIE-S2104, after the offset and type
    checks every value has. Before, every call was PIE-S2104 at the value."""
    accepted = {
        "lag(unknown_nullability)": EffectiveNullability.NULLABLE,
        "lead(unknown_nullability, 2)": EffectiveNullability.NULLABLE,
        "lag(unknown_nullability, 1, nullable_id)": EffectiveNullability.NULLABLE,
        "lead(unknown_nullability, 1, None)": EffectiveNullability.NULLABLE,
        "lag(nullable_id, 1, unknown_nullability)": EffectiveNullability.NULLABLE,
        "lead(id, 0, unknown_nullability)": EffectiveNullability.NON_NULL,
        "first_value(unknown_nullability)": EffectiveNullability.NULLABLE,
        "last_value(unknown_nullability)": EffectiveNullability.NULLABLE,
        "nth_value(unknown_nullability, 2)": EffectiveNullability.NULLABLE,
    }
    refused = {
        "lag(unknown_nullability, 0)": "lag: value type must be concrete",
        "lead(unknown_nullability, 1, id)": "lead: value type must be concrete",
        "lag(id, 1, unknown_nullability)": "lag: default type must be concrete",
        "lead(unknown_nullability, -1)": (
            "lead: offset must be a nonnegative integer literal"
        ),
        "lag(unknown_nullability, 1, label)": (
            "lag: value and default must have the same exact type"
        ),
    }
    outcomes: dict[str, object] = {}
    for call in (*accepted, *refused):
        result, diagnostics, _, _, _ = _analysis(call)
        if type(result) is WindowExpressionAnalysis:
            assert diagnostics == []
            outcomes[call] = result.semantic_fact.result.value_type
        else:
            assert type(result) is WindowExpressionUnsupported
            outcomes[call] = [
                (item.code, item.message, item.location.line, item.location.column)
                for item in diagnostics
            ]

    assert outcomes == {
        **{
            call: ValueType(
                resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
                nullability=nullability,
            )
            for call, nullability in accepted.items()
        },
        **{
            call: [("PIE-S2104", f"Invalid arguments for function {message}", 21, 28)]
            for call, message in refused.items()
        },
    }


@pytest.mark.parametrize("case", range(2))
def test_offset_omitted_records_effective_one(case: int) -> None:
    result, _, _ = _success(f"{IDENTITIES[case]}(id)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.offset_fact.omitted
    assert fact.offset_fact.effective_value == 1


@pytest.mark.parametrize("case", range(2))
def test_offset_zero_is_legal_and_recorded_exactly(case: int) -> None:
    result, _, _ = _success(f"{IDENTITIES[case]}(id, 0)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert not fact.offset_fact.omitted
    assert fact.offset_fact.effective_value == 0


@pytest.mark.parametrize("case", range(8))
def test_offset_positive_integer_has_no_semantic_upper_bound(case: int) -> None:
    identity = IDENTITIES[case // 4]
    offset = (1, 2, 4096, 10**80)[case % 4]
    result, _, _ = _success(f"{identity}(id, {offset})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.offset_fact.effective_value == offset


@pytest.mark.parametrize("case", range(2))
def test_offset_rejects_negative_unary_integer(case: int) -> None:
    _failure(f"{IDENTITIES[case]}(id, -1)", "PIE-S2104")


@pytest.mark.parametrize("case", range(8))
def test_offset_rejects_bool_float_text_and_null_literals(case: int) -> None:
    identity = IDENTITIES[case // 4]
    offset = ("True", "1.5", '"2"', "None")[case % 4]
    _failure(f"{identity}(id, {offset})", "PIE-S2104")


@pytest.mark.parametrize("case", range(8))
def test_offset_rejects_field_call_parameter_and_nonliteral_shapes(case: int) -> None:
    identity = IDENTITIES[case // 4]
    offset = ("id", "lower(label)", "id + 1", "id is None")[case % 4]
    _failure(f"{identity}(id, {offset})", "PIE-S2104")


@pytest.mark.parametrize("case", range(2))
def test_offset_failure_precedes_default_analysis(case: int) -> None:
    result, diagnostics, _, _, _ = _analysis(f"{IDENTITIES[case]}(id, -1, missing)")
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == ["PIE-S2104"]
    assert "offset" in diagnostics[0].message


@pytest.mark.parametrize("case", range(8))
def test_default_accepts_bare_and_immediate_qualified_fields(case: int) -> None:
    identity = IDENTITIES[case // 4]
    default = ("id", "rows.id", "nullable_id", "rows.nullable_id")[case % 4]
    result, _, _ = _success(f"{identity}(id, 1, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert not fact.default_fact.omitted
    assert not fact.default_fact.always_null


@pytest.mark.parametrize("case", range(10))
def test_default_accepts_selected_scalar_literal_kinds_and_null(case: int) -> None:
    identity = IDENTITIES[case // 5]
    default = ("True", '"fallback"', "7", "1.5", "None")[case % 5]
    value = ("flag", "label", "id", "score", "id")[case % 5]
    result, _, _ = _success(f"{identity}({value}, 1, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.default_fact.always_null is (default == "None")


@pytest.mark.parametrize("case", range(14))
def test_default_rejects_nonselected_expression_shapes(case: int) -> None:
    identity = IDENTITIES[case // 7]
    expressions = (
        "-id",
        "id + 1",
        "id = 1",
        "1 <= id <= 2",
        "id is None",
        "lower(label)",
        "rank()",
    )
    expression = expressions[case % 7]
    if expression == "id = 1":
        call = f"{identity}(id, 1, id)"
        _, relation = _parsed_relation(_program(call))
        result, diagnostics, _, _, _ = _analysis(
            call,
            relation_override=_replace_call_argument_with_comparison(relation, 2),
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2104"]
        return
    _failure(f"{identity}(id, 1, {expression})", "PIE-S2104")


@pytest.mark.parametrize("case", range(4))
def test_default_unknown_field_reports_PIE_S2102_at_default_span(case: int) -> None:
    identity = IDENTITIES[case // 2]
    default = "missing" if case % 2 == 0 else "rows.missing"
    result, diagnostics, _, _, relation = _analysis(f"{identity}(id, 1, {default})")
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == ["PIE-S2102"]
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert diagnostics[0].location.column == expression.call.arguments[2].span.column


@pytest.mark.parametrize("case", range(12))
def test_exact_generic_compatibility_accepts_matching_value_and_default(
    case: int,
) -> None:
    identity = IDENTITIES[case // 6]
    pairs = (
        ("id", "nullable_id"),
        ("score", "nullable_score"),
        ("label", '"fallback"'),
        ("flag", "False"),
        ("status", "status"),
        ("payload", "payload"),
    )
    value, default = pairs[case % 6]
    result, _, _ = _success(f"{identity}({value}, 1, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert type(fact.signature_match) is SignatureMatch


@pytest.mark.parametrize("case", range(12))
def test_exact_generic_compatibility_rejects_cross_type_pairs_without_promotion(
    case: int,
) -> None:
    identity = IDENTITIES[case // 6]
    pairs = (
        ("id", "score"),
        ("score", "id"),
        ("label", "id"),
        ("flag", "label"),
        ("status", "label"),
        ("payload", "status"),
    )
    value, default = pairs[case % 6]
    _failure(f"{identity}({value}, 1, {default})", "PIE-S2104")


@pytest.mark.parametrize("case", range(8))
def test_null_default_is_compatible_after_value_binds_T(case: int) -> None:
    identity = IDENTITIES[case // 4]
    value = ("id", "score", "label", "status")[case % 4]
    result, _, _ = _success(f"{identity}({value}, 1, None)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.default_fact.always_null
    assert fact.signature_match.result_type.name == fact.value_type.resolved_type.name


@pytest.mark.parametrize("case", range(8))
def test_value_null_binds_T_from_concrete_default_only(case: int) -> None:
    identity = IDENTITIES[case // 4]
    default = ("id", "score", "label", "status")[case % 4]
    result, _, _ = _success(f"{identity}(None, 2, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert (
        fact.signature_match.result_type.name
        == cast(ValueType, fact.default_fact.value_type).resolved_type.name
    )


@pytest.mark.parametrize(
    "call",
    (
        "lag(status)",
        "lead(status, 2)",
        "lag(None, 1, status)",
        "lead(status, 1, status)",
    ),
)
def test_an_enum_result_keeps_its_declaration_for_later_readers(call: str) -> None:
    """A lag or lead result has the type T binds to, the enum's declaration
    included, as a first_value result has, so a later relation may combine
    its column with a field of that enum. Before, the result named the enum
    without its declaration: `coalesce(previous, status)` was PIE-S2104 and
    the conditional PIE-S2105."""
    source = (
        "enum Status:\n    active\n    paused\n"
        "shape Row:\n    id: Int\n    status: Status\n"
        'source rows: Row = postgres.table("rows")\n'
        "table navigated:\n    from rows\n    select:\n        id\n        status\n"
        f"        previous = {call} window(\n            order by\n"
        "                id)\n"
        "query later:\n    from navigated\n    select:\n        id\n"
        "        v = coalesce(previous, status)\n"
        "        w = previous if previous is None else status\n"
    )
    parsed = parse_source(source, path="navigated.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    semantic = analyze(parsed.ast)
    # Only the read of a table of the file is warned about.
    assert [
        (item.code, item.location.line, item.location.column)
        for item in semantic.diagnostics
    ] == [("PIE-S2382", 17, 5)]
    enum, navigated = parsed.ast.definitions[0], parsed.ast.definitions[3]
    assert type(navigated) is TableDef
    schema = semantic.model.relation_row_schemas[navigated]
    assert schema.fields["previous"].resolved_type == ResolvedType(
        name="Status", kind=TypeKind.ENUM, definition=enum
    )


def test_a_computed_column_of_an_earlier_relation_is_a_window_value() -> None:
    """A computed column such as `v = m + 1` has a known type and an unknown
    nullability; a later relation's `lag`, `lead`, `first_value`,
    `last_value` and `nth_value` of it give a nullable column of that type.
    `lag(v, 0)` and `lag(v, 1, 0)`, whose result would have the column's
    unknown nullability, stay PIE-S2104. Before, every one was PIE-S2104
    `value type must be concrete`."""
    window = "window(\n            order by\n                id)\n"
    source = (
        "shape Row:\n    id: Int\n    m: Int\n"
        'source rows: Row = postgres.table("rows")\n'
        "table computed:\n    from rows\n    select:\n        id\n        v = m + 1\n"
        "query later:\n    from computed\n    select:\n        id\n"
        f"        previous = lag(v) {window}"
        f"        following = lead(v, 2) {window}"
        f"        first = first_value(v) {window}"
        f"        last = last_value(v) {window}"
        f"        nth = nth_value(v, 2) {window}"
        "query refused:\n    from computed\n    select:\n        id\n"
        f"        same = lag(v, 0) {window}"
        f"        defaulted = lag(v, 1, 0) {window}"
    )
    parsed = parse_source(source, path="computed.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    semantic = analyze(parsed.ast)
    lines = source.splitlines()

    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in semantic.diagnostics
    ] == [
        *(
            (
                "PIE-S2382",
                "`computed` is a table of this file; single-file SQL reads it by "
                "name, so the SQL runs only where the database already has a "
                "relation named computed (an EXPLICIT_MODULES project emits it as "
                "a CTE)",
                number + 1,
                5,
            )
            for number, line in enumerate(lines)
            if line == "    from computed"
        ),
        (
            "PIE-S2104",
            "Invalid arguments for function lag: value type must be concrete",
            lines.index("        same = lag(v, 0) window(") + 1,
            16,
        ),
        (
            "PIE-S2104",
            "Invalid arguments for function lag: value type must be concrete",
            lines.index("        defaulted = lag(v, 1, 0) window(") + 1,
            21,
        ),
    ]
    later = parsed.ast.definitions[3]
    assert type(later) is QueryDef
    assert {
        name: (field.resolved_type, field.nullability)
        for name, field in semantic.model.relation_row_schemas[later].fields.items()
    } == {
        "id": (
            ResolvedType(name="Int", kind=TypeKind.BUILTIN),
            EffectiveNullability.NON_NULL,
        ),
        **{
            name: (
                ResolvedType(name="Int", kind=TypeKind.BUILTIN),
                EffectiveNullability.NULLABLE,
            )
            for name in ("previous", "following", "first", "last", "nth")
        },
    }


@pytest.mark.parametrize("case", range(2, 6))
def test_unbound_null_only_T_cases_fail_closed(case: int) -> None:
    identity = IDENTITIES[case % 2]
    call = f"{identity}(None, 0)" if case < 4 else f"{identity}(None, 2, None)"
    _failure(call, "PIE-S2104")


@pytest.mark.parametrize("case", range(4))
def test_omitted_offset_and_default_boundary_is_nullable(case: int) -> None:
    identity = IDENTITIES[case // 2]
    value = ("id", "nullable_id")[case % 2]
    assert _result_nullability(f"{identity}({value})") is EffectiveNullability.NULLABLE


@pytest.mark.parametrize("case", range(4))
def test_positive_offset_and_omitted_default_boundary_is_nullable(case: int) -> None:
    identity = IDENTITIES[case // 2]
    value = ("id", "nullable_id")[case % 2]
    assert (
        _result_nullability(f"{identity}({value}, 2)") is EffectiveNullability.NULLABLE
    )


@pytest.mark.parametrize("case", range(2))
def test_positional_syntax_cannot_omit_offset_while_supplying_default(
    case: int,
) -> None:
    _failure(f"{IDENTITIES[case]}(id, nullable_id)", "PIE-S2104")


@pytest.mark.parametrize("case", range(16))
def test_positive_offset_explicit_default_joins_value_default_nullability(
    case: int,
) -> None:
    identity = IDENTITIES[case // 8]
    pairs = (
        ("id", "id", EffectiveNullability.NON_NULL),
        ("id", "nullable_id", EffectiveNullability.NULLABLE),
        ("id", "None", EffectiveNullability.NULLABLE),
        ("nullable_id", "id", EffectiveNullability.NULLABLE),
        ("nullable_id", "nullable_id", EffectiveNullability.NULLABLE),
        ("nullable_id", "None", EffectiveNullability.NULLABLE),
        ("None", "id", EffectiveNullability.NULLABLE),
        ("None", "nullable_id", EffectiveNullability.NULLABLE),
    )
    value, default, expected = pairs[case % 8]
    assert _result_nullability(f"{identity}({value}, 2, {default})") is expected


@pytest.mark.parametrize("case", (*range(6), *range(8, 14)))
def test_zero_offset_concrete_value_follows_value_nullability(case: int) -> None:
    identity = IDENTITIES[case // 8]
    pairs = (
        ("id", "id", EffectiveNullability.NON_NULL),
        ("id", "nullable_id", EffectiveNullability.NON_NULL),
        ("id", "None", EffectiveNullability.NON_NULL),
        ("nullable_id", "id", EffectiveNullability.NULLABLE),
        ("nullable_id", "nullable_id", EffectiveNullability.NULLABLE),
        ("nullable_id", "None", EffectiveNullability.NULLABLE),
    )
    value, default, expected = pairs[case % 8]
    assert _result_nullability(f"{identity}({value}, 0, {default})") is expected


@pytest.mark.parametrize("case", range(4))
def test_zero_offset_null_value_preserves_always_nullable_provenance(case: int) -> None:
    identity = IDENTITIES[case // 2]
    default = ("id", "nullable_id")[case % 2]
    result, _, _ = _success(f"{identity}(None, 0, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.value_always_null
    assert (
        fact.nullability_match.evidence.kind is NullabilityFormulaKind.ALWAYS_NULLABLE
    )
    assert (
        _result_nullability(f"{identity}(None, 0, {default})")
        is EffectiveNullability.NULLABLE
    )


@pytest.mark.parametrize("case", range(4))
def test_navigation_requires_nonempty_local_order(case: int) -> None:
    identity = IDENTITIES[case // 2]
    partition = ("id",) if case % 2 == 0 else ("nullable_id",)
    _failure(f"{identity}(id)", "PIE-S2103", partition=partition, order=())


@pytest.mark.parametrize("case", range(8))
def test_partition_and_multi_key_order_reuse_existing_binders(case: int) -> None:
    identity = IDENTITIES[case // 4]
    result, _, _ = _success(
        f"{identity}(id)",
        partition=("id", "nullable_id")[: 1 + case % 2],
        order=(("id", None), ("nullable_id", "desc"))[: 1 + (case // 2) % 2],
    )
    assert isinstance(result.partition_binding_fact, WindowPartitionBindingFact)
    assert isinstance(result.order_binding_fact, WindowOrderBindingFact)


@pytest.mark.parametrize("case", range(8))
def test_order_direction_explicitness_and_mixed_directions_are_preserved(
    case: int,
) -> None:
    identity = IDENTITIES[case // 4]
    orders = (
        (("id", None),),
        (("id", "asc"),),
        (("id", "desc"),),
        (("id", "desc"), ("nullable_id", "asc")),
    )[case % 4]
    result, _, _ = _success(f"{identity}(id)", order=orders)
    assert tuple(
        item.source_direction for item in result.order_binding_fact.bindings
    ) == tuple(direction for _, direction in orders)


@pytest.mark.parametrize("case", range(4))
def test_duplicate_order_keys_preserve_source_order_and_occurrences(case: int) -> None:
    identity = IDENTITIES[case // 2]
    order = (("id", None), ("id", "desc"), ("nullable_id", None))
    result, _, _ = _success(f"{identity}(id)", order=order)
    assert tuple(
        cast(NameExpr, item.expression).name
        for item in result.order_binding_fact.bindings
    ) == (
        "id",
        "id",
        "nullable_id",
    )


@pytest.mark.parametrize("case", range(4))
def test_nullable_order_fields_are_accepted_without_runtime_claims(case: int) -> None:
    identity = IDENTITIES[case // 2]
    order = (("nullable_id", None),) if case % 2 == 0 else (("label", "desc"),)
    result, _, _ = _success(f"{identity}(id)", order=order)
    assert (
        result.order_binding_fact.bindings[0].value_type.nullability
        is EffectiveNullability.NULLABLE
    )


@pytest.mark.parametrize("case", range(2))
def test_navigation_is_peer_insensitive_and_adds_no_total_order_proof(
    case: int,
) -> None:
    result, _, _ = _success(f"{IDENTITIES[case]}(id)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert not fact.peer_sensitive
    assert fact.peer_key == ()


def test_validation_first_error_sequence_is_exact() -> None:
    _failure("UnknownNavigation(id)", "PIE-S2103")


@pytest.mark.parametrize("case", (0, 1, 2, 4, 5, 6, 7, 8, 10, 11))
def test_navigation_diagnostic_codes_messages_and_spans_are_exact(case: int) -> None:
    identity = IDENTITIES[case // 6]
    calls = {
        0: f"{identity}()",
        1: f"{identity}(id, -1)",
        2: f"{identity}(id, 1, score)",
        4: f"{identity}(id + 1)",
        5: f"{identity}(None)",
    }
    result, diagnostics, _, _, relation = _analysis(calls[case % 6])
    assert type(result) is WindowExpressionUnsupported
    assert len(diagnostics) == 1
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert diagnostics[0].location.column == expression.call.span.column
    assert identity in diagnostics[0].message


@pytest.mark.parametrize("case", range(4))
def test_navigation_carriers_are_private_frozen_slotted_kw_only_hashable(
    case: int,
) -> None:
    result, _, _ = _success(f"{IDENTITIES[case % 2]}(id, 1, nullable_id)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert type(fact.direction) is NavigationDirection
    assert type(fact.offset_fact) is NavigationOffsetFact
    assert type(fact.default_fact) is NavigationDefaultFact
    assert type(fact.nullability_match) is NullabilityEvaluationMatch
    values: tuple[object, ...] = (
        fact.offset_fact,
        fact.default_fact,
        fact,
        fact.direction,
    )
    value = values[case]
    assert hash(value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        carrier_fields = dataclasses.fields(value)
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(
                value,
                carrier_fields[0].name,
                getattr(value, carrier_fields[0].name),
            )
        assert not hasattr(value, "__dict__")
    assert "Navigation" not in getattr(pietto, "__all__", ())


@pytest.mark.parametrize("case", range(2))
def test_composite_analysis_reuses_identical_common_and_navigation_facts(
    case: int,
) -> None:
    result, _, _ = _success(f"{IDENTITIES[case]}(id, 1, nullable_id)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.semantic_fact is result.semantic_fact
    assert result.partition_binding_fact.semantic_fact is result.semantic_fact
    assert result.order_binding_fact.semantic_fact is result.semantic_fact


@pytest.mark.parametrize("case", range(8))
def test_project_dependency_role_order_and_ordinals_are_exact(case: int) -> None:
    identity = IDENTITIES[case // 4]
    calls = (
        f"{identity}(id)",
        f"{identity}(id, 1, nullable_id)",
        f"{identity}(1)",
        f"{identity}(1, 0, 2)",
    )
    fact = _project_fact(calls[case % 4], partition=("nullable_id",))
    roles = tuple(item.role for item in fact.dependency_occurrences)
    assert tuple(item.global_ordinal for item in fact.dependency_occurrences) == tuple(
        range(len(roles))
    )
    assert tuple(WindowDependencyRole).index(roles[0]) <= tuple(
        WindowDependencyRole
    ).index(roles[-1])


@pytest.mark.parametrize("case", range(8))
def test_project_value_and_default_occurrences_use_argument_and_default_roles(
    case: int,
) -> None:
    identity = IDENTITIES[case // 4]
    value, default = (
        ("id", "nullable_id"),
        ("rows.id", "rows.nullable_id"),
        ("id", "id"),
        ("nullable_id", "nullable_id"),
    )[case % 4]
    fact = _project_fact(f"{identity}({value}, 1, {default})")
    assert tuple(item.role for item in fact.dependency_occurrences[:2]) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_DEFAULT,
    )


@pytest.mark.parametrize("case", range(8))
def test_project_literals_offsets_and_null_create_no_dependency_occurrence(
    case: int,
) -> None:
    identity = IDENTITIES[case // 4]
    call = (
        f"{identity}(1)",
        f"{identity}(1, 0)",
        f"{identity}(1, 2, None)",
        f"{identity}(None, 2, 1)",
    )[case % 4]
    fact = _project_fact(call)
    assert all(
        item.role
        not in {
            WindowDependencyRole.WINDOW_ARGUMENT,
            WindowDependencyRole.WINDOW_DEFAULT,
        }
        for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize("case", range(6))
def test_project_edges_dedupe_first_role_target_and_preserve_occurrences(
    case: int,
) -> None:
    identity = IDENTITIES[case % 2]
    fact = _project_fact(
        f"{identity}(id, 1, id)",
        partition=("id", "id"),
        order=(("id", None), ("id", "desc")),
    )
    assert len(fact.dependency_occurrences) == 6
    assert len(fact.dependency_edges) == 4
    assert tuple(edge.role for edge in fact.dependency_edges) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_DEFAULT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )


@pytest.mark.parametrize("case", range(4))
def test_relation_input_fallback_is_exact_for_dependency_free_arguments(
    case: int,
) -> None:
    identity = IDENTITIES[case // 2]
    call = f"{identity}(1)" if case % 2 == 0 else f"{identity}(None, 1, 1)"
    fact = _project_fact(call)
    relation_occurrences = tuple(
        item
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.RELATION_INPUT
    )
    assert len(relation_occurrences) == 1
    assert (
        relation_occurrences[0].target.kind
        is ProjectRowDependencyNodeKind.RELATION_INPUT
    )


@pytest.mark.parametrize("case", range(4))
def test_project_result_identity_provenance_and_row_schema_boundaries_hold(
    case: int,
) -> None:
    identity = IDENTITIES[case // 2]
    fact = _project_fact(f"{identity}(id)")
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.result_identity.output_name == "navigation_value"


def test_semantic_model_persists_validated_analysis_but_project_model_does_not() -> (
    None
):
    script, relation = _parsed_relation(_program("lag(id)"))
    semantic = analyze(script)
    assert semantic.diagnostics == ()
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert "window_expression_analyses" in {
        field.name for field in dataclasses.fields(SemanticModel)
    }
    assert (
        semantic.model.window_expression_analyses[expression].navigation_fact
        is not None
    )
    assert "navigation" not in _read("src/pietto/_project/model.py")


@pytest.mark.parametrize("case", (0, 2))
def test_navigation_ir_lowering_reaches_window_call_ir(case: int) -> None:
    identity = IDENTITIES[case // 2]
    script, relation = _parsed_relation(_program(f"{identity}(id)"))
    semantic = analyze(script)
    expression = relation.select_items[-1].expression
    lowered = lower_expr(expression, semantic.model)
    assert lowered.diagnostics == ()
    assert type(lowered.expression) is WindowCallIR
    assert lowered.expression.identity.name == identity
    assert len(lowered.expression.arguments) == 1
    assert "WindowExpr" not in _read("src/pietto/sql/postgres.py")


# Phase 53 Slice 13 reader migration.


def test_unknown_bounded_navigation_expression_fails_closed() -> None:
    from pietto import ast_nodes as ast
    from pietto.semantic.window_navigation_analysis import _is_bounded_value_expression

    class UnknownExpression(ast.Expression):
        pass

    with pytest.raises(ValueError, match="Unsupported"):
        _is_bounded_value_expression(
            UnknownExpression(
                span=ast.Span(path=None, line=1, column=1, end_line=1, end_column=2)
            ),
            "rows",
            allow_qualified_fields=False,
        )
