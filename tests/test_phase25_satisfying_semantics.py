from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_grouped_satisfying_over_aggregate_alias_fails_closed(
    relation_kind: str,
) -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                relation_kind=relation_kind,
                projections=(
                    "region",
                    "total_amount = sum(amount)",
                ),
                satisfying="total_amount > 1000",
            )
        )
    )

    assert _errors(result) == [
        ("PIE-S2322", "`satisfying` IR/SQL lowering is deferred"),
    ]


def test_grouped_satisfying_over_group_key_alias_fails_closed() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "r = region",
                    "total_orders = count()",
                ),
                satisfying='r != "test"',
            )
        )
    )

    assert _errors(result) == [
        ("PIE-S2322", "`satisfying` IR/SQL lowering is deferred"),
    ]


def test_no_group_satisfying_is_rejected() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table high_value_orders:\n"
            "    from orders\n"
            "    select:\n"
            "        amount\n"
            "    satisfying:\n"
            "        amount > 1000\n"
        )
    )

    assert _errors(result) == [
        ("PIE-S2323", "`satisfying` requires GROUP BY in the Phase 25 MVP"),
    ]


def test_no_group_direct_aggregate_call_in_satisfying_uses_aggregate_context_diagnostic() -> (
    None
):
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table high_value_orders:\n"
            "    from orders\n"
            "    select:\n"
            "        amount\n"
            "    satisfying:\n"
            "        sum(amount) > 1000\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate sum() is not allowed in satisfying clause; "
            "use it only as a direct aliased select projection",
        ),
    ]


def test_unknown_select_output_name_in_satisfying_is_rejected() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "total_orders = count()",
                ),
                satisfying="missing > 0",
            )
        )
    )

    assert _errors(result) == [
        ("PIE-S2324", "Unknown select output in satisfying: missing"),
    ]


def test_input_field_reference_in_satisfying_must_use_select_output() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "total_orders = count()",
                ),
                satisfying="amount > 1000",
            )
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2325",
            "Satisfying reference must use select output name, not input field: amount",
        ),
    ]


def test_renamed_group_key_exposes_only_alias_to_satisfying() -> None:
    valid = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "r = region",
                    "total_orders = count()",
                ),
                satisfying='r == "east"',
            )
        )
    )
    invalid = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "r = region",
                    "total_orders = count()",
                ),
                satisfying='region == "east"',
            )
        )
    )

    assert _errors(valid) == [
        ("PIE-S2322", "`satisfying` IR/SQL lowering is deferred"),
    ]
    assert _errors(invalid) == [
        (
            "PIE-S2325",
            "Satisfying reference must use select output name, not input field: region",
        ),
    ]


def test_computed_projection_output_in_satisfying_is_deferred() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "doubled = amount + amount",
                    "total_orders = count()",
                ),
                satisfying="doubled > 1000",
            )
        )
    )

    assert _errors(result) == [
        ("PIE-S2319", "Grouped scalar projection expressions are deferred"),
        (
            "PIE-S2326",
            "Satisfying output is not a group-key or direct aggregate projection: doubled",
        ),
    ]


@pytest.mark.parametrize(
    "satisfying",
    [
        "sum(amount) > 1000",
        "sum(amount + tax) > 1000",
        "sum(avg(amount)) > 1000",
        "sum() > 1000",
    ],
)
def test_aggregate_calls_inside_satisfying_use_invalid_context_diagnostic(
    satisfying: str,
) -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "total_orders = count()",
                ),
                satisfying=satisfying,
            )
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate sum() is not allowed in satisfying clause; "
            "use it only as a direct aliased select projection",
        ),
    ]


def test_select_projection_aggregate_expression_argument_still_uses_pie_s2315() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "total_amount = sum(amount + tax)",
                ),
                satisfying="total_amount > 1000",
            )
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2315",
            "Aggregate function sum requires a direct field argument; "
            "expression arguments are deferred",
        ),
    ]


@pytest.mark.parametrize(
    "satisfying",
    [
        "orders.region == region",
        'lower(region) == "east"',
        "total_amount + 1 > 1000",
        "-total_amount > 1000",
        'region like "e%"',
        "total_amount between 1 and 1000",
        "region is null",
        "region is not null",
    ],
)
def test_unsupported_satisfying_expression_forms_are_deferred(
    satisfying: str,
) -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "total_amount = sum(amount)",
                ),
                satisfying=satisfying,
            )
        )
    )

    assert _error_codes(result) == ["PIE-S2327"]


def test_non_bool_satisfying_predicate_reuses_predicate_diagnostic() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "total_amount = sum(amount)",
                ),
                satisfying="total_amount",
            )
        )
    )

    assert _errors(result) == [
        ("PIE-S2202", "Expected Bool expression in satisfying clause"),
    ]


def test_and_or_bool_composition_is_accepted_subject_to_lowering_gate() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "total_amount = sum(amount)",
                ),
                satisfying='total_amount > 1000 and region != "test" or total_amount < 10',
            )
        )
    )

    assert _errors(result) == [
        ("PIE-S2322", "`satisfying` IR/SQL lowering is deferred"),
    ]


def test_invalid_and_or_operands_reuse_operator_diagnostic() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "total_amount = sum(amount)",
                ),
                satisfying='total_amount and region != "test"',
            )
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2105",
            "Invalid operands for operator and: expected Bool operands",
        ),
    ]


def test_emit_sql_text_fails_closed_before_ir_and_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())
    _forbid_ir_and_sql(monkeypatch)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2322 error: `satisfying` IR/SQL lowering is deferred" in captured.err
    assert "SELECT" not in captured.out


def test_emit_sql_json_fails_closed_without_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())
    _forbid_ir_and_sql(monkeypatch)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    result = cast(dict[str, object], json.loads(captured.out))
    assert result["ok"] is False
    assert result["artifacts"] == []
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2322"]


def _grouped_relation(
    *,
    projections: tuple[str, ...],
    satisfying: str,
    relation_kind: str = "table",
) -> str:
    select_body = "".join(f"        {projection}\n" for projection in projections)
    return (
        SOURCE_PREFIX + f"{relation_kind} high_value_regions:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        f"{select_body}"
        "    satisfying:\n"
        f"        {satisfying}\n"
    )


def _valid_satisfying_source() -> str:
    return _grouped_relation(
        projections=(
            "region",
            "total_amount = sum(amount)",
        ),
        satisfying="total_amount > 1000",
    )


def _parse(source: str):
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _error_codes(result: SemanticResult) -> list[str]:
    return [code for code, _message in _errors(result)]


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _forbid_ir_and_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("satisfying semantic errors must stop IR and SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
