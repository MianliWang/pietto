from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    region: Text nullable\n"
    "    customer_id: Text not null\n"
    "    amount: Int not null\n"
    "    score: Float not null\n"
    "    price: Decimal not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_grouped_semantic_schema_for_bare_key_and_aggregates() -> None:
    script = _parse(
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "        revenue = sum(amount)\n"
        "        average_score = avg(score)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["status", "total", "revenue", "average_score"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["revenue"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(
        schema.fields["average_score"],
        "Float",
        EffectiveNullability.NULLABLE,
    )


def test_grouped_semantic_schema_for_qualified_key_and_alias() -> None:
    script = _parse(
        SOURCE_PREFIX + "query grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        orders.region\n"
        "    select:\n"
        "        bucket = orders.region\n"
        "        score_total = sum(score)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["bucket", "score_total"]
    _assert_field(schema.fields["bucket"], "Text", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["score_total"], "Float", EffectiveNullability.NULLABLE)


def test_equivalent_bare_and_qualified_group_keys_diagnose_later_duplicate() -> None:
    script = _parse(
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "        orders.status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == [
        ("PIE-S2317", "Duplicate GROUP BY key: orders.status"),
    ]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)


def test_unknown_group_key_suppresses_dependent_projection_cascade() -> None:
    script = _parse(
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        missing\n"
        "    select:\n"
        "        missing\n"
        "        total = count()\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == [
        ("PIE-S2102", "Unknown field: missing"),
    ]
    assert "PIE-S2318" not in _error_codes(result)
    assert schema.fields["missing"].resolved_type.kind is TypeKind.UNKNOWN
    assert schema.fields["missing"].nullability is EffectiveNullability.UNKNOWN
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)


def test_non_grouped_plain_projection_is_rejected_with_unknown_schema_field() -> None:
    script = _parse(
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        customer_id\n"
        "        total = count()\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == [
        ("PIE-S2318", "Grouped projection is not a GROUP BY key: customer_id"),
    ]
    assert schema.fields["customer_id"].resolved_type.kind is TypeKind.UNKNOWN
    assert schema.fields["customer_id"].nullability is EffectiveNullability.UNKNOWN
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)


def test_scalar_group_key_expression_projection_is_deferred() -> None:
    script = _parse(
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        label = lower(status)\n"
        "        total = count()\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == [
        ("PIE-S2319", "Grouped scalar projection expressions are deferred"),
    ]
    assert schema.fields["label"].resolved_type.kind is TypeKind.UNKNOWN
    assert schema.fields["label"].nullability is EffectiveNullability.UNKNOWN
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)


def test_unaliased_grouped_aggregate_projection_is_rejected_and_suppressed() -> None:
    script = _parse(
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        count()\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == [
        ("PIE-S2313", "Aggregate count() projection requires an explicit alias"),
    ]
    assert list(schema.fields) == ["status"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)


def test_pure_grouping_without_aggregate_is_deferred_but_schema_is_known() -> None:
    script = _parse(
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == [
        ("PIE-S2320", "Pure grouped output without an aggregate is deferred"),
    ]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)


@pytest.mark.parametrize("order_item", ["sum(amount) desc", "orders.status"])
def test_unsupported_grouped_order_by_items_emit_s2321(order_item: str) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table grouped_orders:\n"
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    order by:\n"
            f"        {order_item}\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2321",
            "Unsupported grouped ORDER BY item; expected a supported select output name",
        ),
    ]


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "revenue = sum(status)",
            (
                "PIE-S2314",
                "Aggregate function sum expects Int, Float, or Decimal field "
                "argument, got Text",
            ),
        ),
        (
            "revenue = sum(1)",
            (
                "PIE-S2315",
                "Aggregate function sum requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
        (
            "revenue = sum(avg(amount))",
            ("PIE-S2311", "Nested aggregate avg() is not supported"),
        ),
        (
            "revenue = sum(amount) + 1",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around sum() is deferred",
            ),
        ),
    ],
)
def test_grouped_aggregate_invalid_shapes_match_phase20_behavior(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table grouped_orders:\n"
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


def test_cli_check_succeeds_for_valid_grouped_relation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "grouped.pietto", _valid_grouped_source())

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


def test_emit_sql_json_succeeds_for_valid_grouped_relation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "grouped.pietto", _valid_grouped_source())

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    assert result["ok"] is True
    assert result["diagnostics"] == []
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert diagnostics == []
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert len(artifacts) == 1
    assert artifacts[0]["name"] == "grouped_orders"
    assert "GROUP BY" in cast(str, artifacts[0]["sql"])


def test_downstream_relation_from_grouped_relation_emits_by_relation_name(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "downstream-grouped.pietto",
        _valid_grouped_source() + "query downstream:\n"
        "    from grouped_orders\n"
        "    select:\n"
        "        status\n"
        "        total\n",
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    assert result["ok"] is True
    assert result["diagnostics"] == []
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert [artifact["name"] for artifact in artifacts] == [
        "grouped_orders",
        "downstream",
    ]
    assert 'FROM "grouped_orders"' in cast(str, artifacts[1]["sql"])


def _valid_grouped_source() -> str:
    return (
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _error_codes(result: SemanticResult) -> list[str]:
    return [code for code, _message in _errors(result)]


def _assert_field(
    field: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    typed_field = cast("object", field)
    assert getattr(typed_field, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(typed_field, "resolved_type").name == expected_type
    assert getattr(typed_field, "nullability") is expected_nullability


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return cast(dict[str, object], json.loads(captured.out))
