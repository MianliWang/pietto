from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, ValueTypeKind, analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    region: Text\n"
    "    status: Text\n"
    "    active: Bool\n"
    "    amount: Int\n"
    "    tax: Int\n"
    "    score: Float\n"
    'source orders: Order = postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_grouped_satisfying_over_aggregate_alias_is_accepted(
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

    assert _errors(result) == []


def test_grouped_satisfying_over_group_key_alias_is_accepted() -> None:
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

    assert _errors(result) == []


def test_no_group_satisfying_is_rejected() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table high_value_orders:\n"
            "    from orders\n"
            "    select:\n"
            "        amount\n"
            "    having:\n"
            "        amount > 1000\n"
        )
    )

    assert _errors(result) == [
        ("PIE-S2323", "`having` requires GROUP BY"),
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
            "    having:\n"
            "        sum(amount) > 1000\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate sum() is not allowed in having clause; "
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
        ("PIE-S2324", "Unknown select output in having: missing"),
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
            "Having reference must use select output name, not input field: amount",
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

    assert _errors(valid) == []
    assert _errors(invalid) == [
        (
            "PIE-S2325",
            "Having reference must use select output name, not input field: region",
        ),
    ]


@pytest.mark.parametrize(
    ("satisfying", "form", "column"),
    (
        ("None", "null literal", 9),
        ("n > None", "null literal", 13),
    ),
)
def test_satisfying_that_cannot_be_validated_reports_s2327(
    satisfying: str, form: str, column: int
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table rates:\n"
            "    from orders\n"
            "    select:\n"
            "        per = amount / None\n"
            "table buckets:\n"
            "    from rates\n"
            "    group by:\n"
            "        per\n"
            "    select:\n"
            "        per\n"
            "        n = count()\n"
            "    having:\n"
            f"        {satisfying}\n"
        )
    )

    assert [
        (
            diagnostic.code,
            diagnostic.severity,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
        )
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2327",
            Severity.ERROR,
            f"Unsupported having expression form: {form}",
            21,
            column,
        ),
    ]


@pytest.mark.parametrize(
    ("satisfying", "form"),
    (
        ('upper(r) == "A"', "function call"),
        ('high_value_regions.r == "A"', "qualified name"),
        ("total_amount + 1 > 1000", "operator `+`"),
    ),
)
def test_unsupported_satisfying_forms_are_named_in_plain_words(
    satisfying: str, form: str
) -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=("r = region", "total_amount = sum(amount)"),
                satisfying=satisfying,
            )
        )
    )

    assert _errors(result) == [
        ("PIE-S2327", f"Unsupported having expression form: {form}")
    ]


def test_satisfying_over_an_output_of_unknown_type_is_not_refused_at_check() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table rates:\n"
            "    from orders\n"
            "    select:\n"
            "        per = amount / None\n"
            "table buckets:\n"
            "    from rates\n"
            "    group by:\n"
            "        per\n"
            "    select:\n"
            "        per\n"
            "        n = count()\n"
            "    having:\n"
            "        per >= 0\n"
        )
    )

    assert result.diagnostics == ()
    # Kept for lowering, so that emission refuses it (PIE-B1000) deterministically.
    assert result.model.relation_symbols["buckets"] in result.model.result_predicates


def test_satisfying_over_an_unknown_row_reads_a_count_output_as_an_int() -> None:
    """Over a source without a shape a `count()` output is an `Int` to
    `satisfying`, as over a source with a shape, whatever the row: alone it is
    PIE-S2202, beside an operand of unknown type an `and` operand that is not
    a Bool is PIE-S2105, and it compares only with numbers (before: each
    accepted). A predicate that passes keeps the facts it had."""

    def relation(name: str, satisfying: str) -> str:
        return (
            f"table {name}:\n    from raw\n    group by t\n    select:\n"
            "        c = count()\n        m = max(n)\n"
            f"    having {satisfying}\n"
        )

    result = analyze(
        _parse(
            'source raw = postgres.table("raw")\n'
            + relation("a", "c")
            + relation("b", "c and m > 1")
            + relation("d", "c > 'x'")
            + relation("e", "c > 1 and m > 1")
        )
    )

    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in result.diagnostics
        if d.severity is Severity.ERROR
    ] == [
        ("PIE-S2202", 8, 12, "Expected Bool expression in having clause"),
        (
            "PIE-S2105",
            15,
            12,
            "Invalid operands for operator and: expected Bool operands",
        ),
        (
            "PIE-S2105",
            22,
            12,
            "Invalid operands for operator >: expected comparable operands",
        ),
    ]
    (definition, predicate), *rest = result.model.result_predicates.items()
    assert (definition.name, rest) == ("e", [])
    # Typed as before, so that emission refuses it as before (PIE-B1000).
    assert (
        predicate.expression_value_types[predicate.clause.expression].kind
        is ValueTypeKind.UNKNOWN
    )


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
        ("PIE-S2319", "Grouped scalar projection expressions are not supported yet"),
        (
            "PIE-S2326",
            "Having output is not a group-key or direct aggregate projection: doubled",
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
            "Aggregate sum() is not allowed in having clause; "
            "use it only as a direct aliased select projection",
        ),
    ]


def test_satisfying_resolves_aggregate_expression_projection_alias() -> None:
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

    assert _errors(result) == []


@pytest.mark.parametrize(
    "satisfying",
    [
        "orders.region == region",
        'lower(region) == "east"',
        "total_amount + 1 > 1000",
        "-total_amount > 1000",
        'region like "e%"',
        "1 <= total_amount <= 1000",
        "region is None",
        "region is not None",
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
        ("PIE-S2202", "Expected Bool expression in having clause"),
    ]


def test_and_or_bool_composition_is_accepted() -> None:
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

    assert _errors(result) == []


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


def test_comparison_operands_of_different_families_reuse_operator_diagnostic() -> None:
    result = analyze(
        _parse(
            _grouped_relation(
                projections=(
                    "region",
                    "total_amount = sum(amount)",
                ),
                satisfying='total_amount > "1000" and region != 1',
            )
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2105",
            "Invalid operands for operator >: expected comparable operands",
        ),
        (
            "PIE-S2105",
            "Invalid operands for operator !=: expected comparable operands",
        ),
    ]


def test_satisfying_compares_an_enum_key_only_with_its_enum_and_labels() -> None:
    """Before: an enum operand was not checked, so `having status == 1`
    passed and emitted `HAVING "status" = 1`, which PostgreSQL rejects
    (operator does not exist: status = integer)."""
    predicates = (
        'status == "active"',
        'status == "gone"',
        "status == 1",
        "n == status",
        "status == status",
    )
    result = analyze(
        _parse(
            "enum Status:\n    active\n    suspended\n"
            "shape Account:\n    id: Int\n    status: Status\n"
            'source accounts: Account = postgres.table("accounts")\n'
            + "".join(
                f"query q{index}:\n    from accounts\n    group by status\n"
                "    select:\n        status\n        n = count()\n"
                f"    having {predicate}\n"
                for index, predicate in enumerate(predicates)
            )
        )
    )

    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
            line,
            12,
        )
        for line in (21, 28, 35)
    ]


def test_emit_sql_text_invalid_satisfying_fails_before_ir_and_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "satisfying.pietto",
        _grouped_relation(
            projections=("region", "total_amount = sum(amount)"),
            satisfying="missing > 1000",
        ),
    )
    _forbid_ir_and_sql(monkeypatch)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2324 error: Unknown select output in having: missing" in captured.err
    assert "SELECT" not in captured.out


def test_emit_sql_json_invalid_satisfying_fails_without_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "satisfying.pietto",
        _grouped_relation(
            projections=("region", "total_amount = sum(amount)"),
            satisfying="missing > 1000",
        ),
    )
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
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2324"]


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
        "    having:\n"
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


@pytest.mark.parametrize("predicate", ['peer_status != "test"', 'status != "test"'])
def test_join_satisfying_reads_grouped_outputs_and_recognizes_input_fields(
    predicate: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "query grouped_orders:\n"
            "    from orders\n"
            "    let peer = orders\n"
            "    cross join peer\n"
            "    group by:\n"
            "        peer.status\n"
            "    select:\n"
            "        peer_status = peer.status\n"
            "        total = count()\n"
            "    having:\n"
            f"        {predicate}\n"
        )
    )

    if predicate.startswith("peer_status"):
        assert result.diagnostics == ()
        assert len(result.model.result_predicates) == 1
    else:
        assert _errors(result) == [
            (
                "PIE-S2325",
                "Having reference must use select output name, not input field: status",
            )
        ]
        diagnostic = result.diagnostics[0]
        assert (diagnostic.location.line, diagnostic.location.column) == (19, 9)
