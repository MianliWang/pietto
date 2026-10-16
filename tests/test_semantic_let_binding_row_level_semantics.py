from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import (
    BinaryExpr,
    ComparisonExpr,
    IsNullExpr,
    NameExpr,
    QueryDef,
    TableDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, ValueTypeKind, analyze


SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int nullable\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("keyword", ["table", "query"])
def test_valid_table_and_query_let_validate_row_scope_and_succeed(
    keyword: str,
) -> None:
    relation, semantic = _analyze_relation(
        f"{keyword} enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    where gross > 0\n"
        "    select:\n"
        "        gross_value = gross\n"
        "    order by:\n"
        "        gross\n"
    )

    assert isinstance(relation, (TableDef, QueryDef))
    assert _error_codes(semantic) == []
    assert "PIE-S2102" not in _error_codes(semantic)

    assert relation.where_clause is not None
    assert relation.order_by_clause is not None
    select_expr = relation.select_items[0].expression
    order_expr = relation.order_by_clause.items[0].expression
    assert isinstance(select_expr, NameExpr)
    assert isinstance(order_expr, NameExpr)

    assert _value_type_name(semantic, select_expr) == "Int"
    assert _value_type_name(semantic, order_expr) == "Int"
    assert _value_type_name(semantic, relation.where_clause.expression) == "Bool"


def test_source_qualified_input_fields_work_inside_let_expression() -> None:
    relation, semantic = _analyze_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = orders.amount + orders.tax\n"
        "    select:\n"
        "        gross_value = gross\n"
    )

    assert _error_codes(semantic) == []
    assert "PIE-S2102" not in _error_codes(semantic)
    assert relation.let_clause is not None
    binding_expr = relation.let_clause.bindings[0].expression
    assert isinstance(binding_expr, BinaryExpr)
    assert _value_type_name(semantic, binding_expr) == "Int"


def test_function_calls_and_earlier_let_references_type_in_binding_order() -> None:
    relation, semantic = _analyze_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        normalized = lower(trim(status))\n"
        "        status_len = len(normalized)\n"
        "    select:\n"
        "        normalized_value = normalized\n"
        "        status_length = status_len\n"
    )

    assert _error_codes(semantic) == []
    assert relation.let_clause is not None
    normalized, status_len = relation.let_clause.bindings
    assert _value_type_name(semantic, normalized.expression) == "Text"
    assert _value_type_name(semantic, status_len.expression) == "Int"
    assert _value_type_name(semantic, relation.select_items[0].expression) == "Text"
    assert _value_type_name(semantic, relation.select_items[1].expression) == "Int"


def test_unary_binary_comparison_and_is_null_value_types_are_preserved() -> None:
    relation, semantic = _analyze_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        negative = -amount\n"
        "        gross = amount + tax\n"
        "        is_large = gross > 10\n"
        "        tax_missing = tax is null\n"
        "    select:\n"
        "        negative_value = negative\n"
        "        gross_value = gross\n"
        "        large_value = is_large\n"
        "        missing_value = tax_missing\n"
    )

    assert _error_codes(semantic) == []
    assert relation.let_clause is not None
    negative, gross, is_large, tax_missing = relation.let_clause.bindings

    assert _value_type_name(semantic, negative.expression) == "Int"
    assert _value_type_name(semantic, gross.expression) == "Int"
    assert isinstance(is_large.expression, ComparisonExpr)
    assert _value_type_name(semantic, is_large.expression) == "Bool"
    assert isinstance(tax_missing.expression, IsNullExpr)
    assert _value_type_name(semantic, tax_missing.expression) == "Bool"


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "        gross = amount - tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        amount = tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        orders = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        gross\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        gross = amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = net + tax\n"
            "        net = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount if true else net\n"
            "        net = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount in (net,)\n"
            "        net = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = cast(net as Float)\n"
            "        net = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = gross + tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = net\n"
            "        net = gross\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = sum(amount)\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2308",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "        net = orders.gross\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        flagged = total > 0\n"
            "    select:\n"
            "        total = amount\n",
            "PIE-S2102",
        ),
    ],
)
def test_invalid_let_binding_cases_fail_closed(
    body: str,
    expected_code: str,
) -> None:
    _, semantic = _analyze_relation("query enriched_orders:\n" + body)

    codes = _error_codes(semantic)
    assert expected_code in codes


@pytest.mark.parametrize(
    "body",
    [
        (
            "    let:\n"
            "        gross = amount + tax\n"
            "    where gross > 0\n"
            "    select:\n"
            "        id\n"
            "        gross\n"
            "        twice = gross * 2\n"
            "    order by:\n"
            "        gross asc\n"
        ),
        (
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        id\n"
            "        gross\n"
            "        n = count()\n"
        ),
    ],
)
def test_reads_of_a_refused_let_name_report_only_the_refusal(body: str) -> None:
    relation, semantic = _analyze_relation(
        "query enriched_orders:\n    from orders\n" + body
    )
    assert relation.let_clause is not None
    binding = relation.let_clause.bindings[0]

    assert [(d.code, d.message) for d in semantic.diagnostics] == [
        ("PIE-S2329", "Let binding conflicts with projection output name: gross")
    ]
    location = semantic.diagnostics[0].location
    assert (location.line, location.column) == (binding.span.line, binding.span.column)


def _let_chain(count: int, step: str) -> str:
    lines = [
        f"        v{i} = {step.format(previous=f'v{i - 1}')}" for i in range(1, count)
    ]
    return "\n".join(("    let:", "        v0 = amount", *lines)) + "\n"


@pytest.mark.parametrize(
    ("count", "step", "select", "culprit", "limit"),
    [
        (256, "{previous} + 1", "y = v255", None, None),
        (257, "{previous} + 1", "y = v256", "v256", "256 nested levels"),
        (500, "{previous} + 1", "y = v499", "v256", "256 nested levels"),
        # Emission inlines only what a relation expression reads.
        (500, "{previous} + 1", "y = v100", None, None),
        (16, "{previous} + {previous}", "y = v15", None, None),
        (17, "{previous} + {previous}", "y = v16", "v16", "100000 expression nodes"),
        (24, "{previous} + {previous}", "y = v23", "v16", "100000 expression nodes"),
        (16, "{previous} + {previous}", "y = v15 + v15", "", "100000 expression nodes"),
    ],
)
def test_let_inline_expansion_is_bounded_on_read_paths(
    count: int, step: str, select: str, culprit: str | None, limit: str | None
) -> None:
    relation, semantic = _analyze_relation(
        "query chained:\n    from orders\n"
        + _let_chain(count, step)
        + f"    select:\n        {select}\n"
    )

    messages = [(d.code, d.message) for d in semantic.diagnostics]
    if culprit is None:
        assert messages == []
        return
    suffix = f" (first at let binding {culprit})" if culprit else ""
    assert messages == [
        (
            "PIE-S2328",
            "Expression exceeds the single-file let inline expansion limit of "
            f"{limit} after inlining the let bindings it reads{suffix}",
        )
    ]
    node = relation.select_items[0].expression
    location = semantic.diagnostics[0].location
    assert (location.line, location.column) == (node.span.line, node.span.column)


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        gross\n"
            "    select:\n"
            "        status\n"
            "        total_amount = sum(amount)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        total_amount = min(gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total_amount = sum(amount)\n"
            "    satisfying:\n"
            "        gross > 0\n",
            "PIE-S2324",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total_amount = sum(amount)\n"
            "    order by:\n"
            "        gross\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        amount\n"
            "    limit gross\n",
            "PIE-S2307",
        ),
    ],
)
def test_non_row_level_consumers_do_not_see_let_names(
    body: str,
    expected_code: str,
) -> None:
    _, semantic = _analyze_relation("query enriched_orders:\n" + body)

    codes = _error_codes(semantic)
    assert expected_code in codes


def test_cli_check_succeeds_for_supported_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(tmp_path)

    exit_code = cli.main(["check", str(source_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert f"OK: {source_path}" in captured.out


def test_emit_sql_json_succeeds_for_supported_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(tmp_path)

    exit_code = cli.main(
        [
            "emit-sql",
            str(source_path),
            "--dialect",
            "postgres",
            "--format=json",
        ]
    )
    captured = capsys.readouterr()
    document = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert document["ok"] is True
    assert len(document["artifacts"]) == 1
    assert document["diagnostics"] == []
    assert "let_scopes" not in json.dumps(document)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert diagnostics == []


def test_explain_succeeds_for_supported_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(tmp_path)

    exit_code = cli.main(["explain", str(source_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert "Semantic Metadata Artifact v1" in captured.out


def _analyze_relation(source: str) -> tuple[TableDef | QueryDef, SemanticResult]:
    result = parse_source(SOURCE_PREFIX + source, path="let_semantics.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(TableDef | QueryDef, result.ast.definitions[-1])
    return relation, analyze(result.ast)


def _error_codes(semantic: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _value_type_name(semantic: SemanticResult, expression: object) -> str:
    value_type = semantic.model.expression_value_types[cast(NameExpr, expression)]
    assert value_type.kind is ValueTypeKind.KNOWN
    return value_type.resolved_type.name


def _write_source(tmp_path: Path) -> Path:
    path = tmp_path / "with_let.pietto"
    path.write_text(
        SOURCE_PREFIX
        + "query enriched_orders:\n"
        + "    from orders\n"
        + "    let:\n"
        + "        gross = amount + tax\n"
        + "    select:\n"
        + "        gross_value = gross\n",
        encoding="utf-8",
    )
    return path
