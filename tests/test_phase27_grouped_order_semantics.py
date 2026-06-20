from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import NameExpr, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    customer_id: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize(
    ("projection", "order_item"),
    [
        ("region", "region"),
        ("r = region", "r"),
        ("r = orders.region", "r"),
        ("total = count()", "total"),
        ("total = sum(amount)", "total"),
        ("average_score = avg(score)", "average_score"),
        ("unique_statuses = count_distinct(status)", "unique_statuses"),
        ("total = sum(amount + tax)", "total"),
        ("weighted = avg(score * weight)", "weighted"),
        ("normalized = count_distinct(lower(trim(status)))", "normalized"),
    ],
)
def test_grouped_order_accepts_supported_selected_outputs(
    projection: str,
    order_item: str,
) -> None:
    projections = (
        ("region", "total_orders = count()")
        if projection == "region"
        else ("region", projection, "total_orders = count()")
    )
    result = analyze(
        _parse(
            _grouped_relation(
                projections=projections,
                order_items=(f"{order_item} desc",),
            )
        )
    )

    assert _errors(result) == []


@pytest.mark.parametrize("order_item", ["region", "region asc", "region desc"])
def test_grouped_order_accepts_existing_direction_syntax(order_item: str) -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=("region", "total_orders = count()"),
                order_items=(order_item,),
            )
        )
    )

    assert _errors(result) == []


def test_grouped_order_preserves_duplicate_items_and_source_order_in_ast() -> None:
    script = _parse(
        _grouped_relation(
            projections=("region", "total = count()"),
            order_items=("total desc", "region", "total asc"),
        )
    )
    relation = cast(TableDef, script.definitions[-1])
    assert relation.order_by_clause is not None

    assert [
        (
            cast(NameExpr, item.expression).name,
            item.direction,
        )
        for item in relation.order_by_clause.items
    ] == [
        ("total", "desc"),
        ("region", None),
        ("total", "asc"),
    ]
    assert _errors(analyze(script)) == []


def test_grouped_satisfying_and_accepted_order_by_are_semantically_valid() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=("region", "total = sum(amount + tax)"),
                satisfying="total > 1000",
                order_items=("total desc", "region asc"),
            )
        )
    )

    assert _errors(result) == []


@pytest.mark.parametrize(
    "order_item",
    [
        "missing",
        "orders.region",
        "amount",
        "lower(region)",
        '"east"',
        "sum(amount)",
        "total + 1",
        "total > 1",
        'total > 1 and region == "east"',
    ],
)
def test_grouped_order_rejects_unsupported_item_shapes(order_item: str) -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=("region", "total = count()"),
                order_items=(order_item,),
            )
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2321",
            "Unsupported grouped ORDER BY item; expected a supported select output name",
        )
    ]


def test_grouped_order_ordinal_remains_parser_owned() -> None:
    result = parse_source(
        _grouped_relation(
            projections=("region", "total = count()"),
            order_items=("1",),
        ),
        path="phase27-grouped-order.pietto",
    )

    assert result.ast is None
    assert result.diagnostics
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-P1000"]


def test_grouped_order_rejects_original_name_for_renamed_group_key() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=("r = region", "total = count()"),
                order_items=("region",),
            )
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2321",
            "Unsupported grouped ORDER BY item; expected a supported select output name",
        )
    ]


def test_grouped_order_preserves_duplicate_projection_primary_diagnostic() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=("region", "region = count()"),
                order_items=("region",),
            )
        )
    )

    assert _errors(result) == [
        ("PIE-S2305", "Duplicate projection field: region"),
    ]


def test_grouped_order_preserves_invalid_aggregate_primary_diagnostic() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=("region", "bad_total = sum(status)"),
                order_items=("bad_total",),
            )
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2314",
            "Aggregate function sum expects Int, Float, or Decimal field argument, "
            "got Text",
        ),
        (
            "PIE-S2321",
            "Unsupported grouped ORDER BY item; expected a supported select output name",
        ),
    ]


def test_grouped_order_rejects_unsupported_computed_projection_output() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=("region", "doubled = amount + amount", "total = count()"),
                order_items=("doubled",),
            )
        )
    )

    assert _errors(result) == [
        ("PIE-S2319", "Grouped scalar projection expressions are deferred"),
        (
            "PIE-S2321",
            "Unsupported grouped ORDER BY item; expected a supported select output name",
        ),
    ]


def test_pietto_check_accepts_grouped_order_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "grouped-order.pietto",
        _grouped_relation(
            projections=("region", "total = sum(amount + tax)"),
            satisfying="total > 1000",
            order_items=("total desc", "region asc"),
        ),
    )

    assert cli.main(["check", str(path)]) == 0
    checked = capsys.readouterr()
    assert checked.out == f"OK: {path}\n"
    assert checked.err == ""


def _grouped_relation(
    *,
    projections: tuple[str, ...],
    order_items: tuple[str, ...],
    satisfying: str | None = None,
) -> str:
    projection_block = "".join(f"        {projection}\n" for projection in projections)
    satisfying_block = (
        "" if satisfying is None else f"    satisfying:\n        {satisfying}\n"
    )
    order_block = "".join(f"        {item}\n" for item in order_items)
    return (
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        f"{projection_block}"
        f"{satisfying_block}"
        "    order by:\n"
        f"{order_block}"
    )


def _parse(source: str) -> Script:
    result = parse_source(source, path="phase27-grouped-order.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path
