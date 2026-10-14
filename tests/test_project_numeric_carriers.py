from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_verification as verification
from pietto.semantic.expressions import resolved_binary_value_type
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
)


def _decimal(family: str, precision: int, scale: int) -> rows.Realization:
    return rows.Realization(
        "Decimal",
        {
            "kind": "pg_numeric" if family == "postgres" else "my_decimal",
            "precision": precision,
            "scale": scale,
        },
        False,
        {"kind": "decimal", "precision": precision, "scale": scale},
    )


def _float(family: str) -> rows.Realization:
    return rows.Realization(
        "Float",
        {"kind": "pg_float8" if family == "postgres" else "my_double"},
        False,
        {"kind": "finite_float", "format": "binary64"},
    )


def _integer(family: str) -> rows.Realization:
    return rows.Realization(
        "Int",
        {"kind": "pg_int8" if family == "postgres" else "my_signed_int"},
        False,
        {"kind": "int_range", "min": "0", "max": "1"},
    )


def _source_integer(family: str) -> rows.Realization:
    realized = rows.source_realization(_integer(family))
    assert realized is not None
    return realized


def _literal_integer(family: str, value: int) -> rows.Realization:
    return rows.Realization(
        "Int",
        {"kind": "pg_int8" if family == "postgres" else "my_signed_int"},
        False,
        {"kind": "int_range", "min": str(value), "max": str(value)},
        (value, value),
    )


@pytest.mark.parametrize("family", ("postgres", "mysql"))
def test_int_source_arithmetic_uses_physical_proof_not_declared_json_range(
    family: str,
) -> None:
    source = _source_integer(family)
    physical = rows.signed_range(source.storage)
    assert physical is not None
    assert rows.int_bounds(source) == (0, 1)
    assert rows.proven_int_bounds(source) == physical

    realized, problem = rows.resolved_binary_realization(
        family, "+", "Int", False, source, source
    )
    assert realized is None
    assert problem == ("PIE-B1002", "arithmetic_outside_physical_range")

    realized, problem = rows.resolved_binary_realization(
        family, "+", "Int", False, source, _literal_integer(family, 0)
    )
    assert problem is None
    assert realized is not None
    assert rows.proven_int_bounds(realized) == physical

    with pytest.raises(ValueError, match="integer result outside its physical range"):
        verification.resolved_row_realization(
            family, "unary", "-", "Int", False, (source,)
        )


def test_narrow_source_range_cannot_bypass_alias_let_or_compiled_replay(
    tmp_path,
) -> None:
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    item = probe.fixture("postgres", "T_row_direct", "table_preserve")
    header = item["source"].split("table result:", 1)[0]
    contract = json.loads(item["contract"])
    contract["sources"][0]["fields"][0]["representation"]["domain"] = {
        "kind": "int_range",
        "min": "0",
        "max": "1",
    }
    encoded = probe.encoded(contract).decode()

    safe = (
        header
        + """table result:
    from rows
    let:
        alias = id
        plus_zero = alias + 0
    select:
        result = plus_zero + 0
"""
    )
    _, outcome = probe.build_case(tmp_path / "safe", safe, encoded, "preserve_literals")
    assert outcome.status == "VERIFIED"
    assert outcome.artifact is not None

    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replayed = emit_compiled(loaded, ())
    assert replayed.request.family == "postgres"

    rejected = (
        header
        + """table result:
    from rows
    let:
        alias = id
    select:
        result = alias + alias
"""
    )
    _, outcome = probe.build_case(
        tmp_path / "rejected", rejected, encoded, "preserve_literals"
    )
    assert outcome.status == "BLOCKED"


def test_int_proofs_drive_avg_range_and_set_consumers() -> None:
    from pietto._project import project_sql_emission_aggregation as aggregation
    from pietto._project import project_sql_emission_sets as sets
    from pietto._project import project_sql_emission_windows as windows
    from pietto.ast_nodes import SetOperationKind, SetOperationQuantifier

    source = _source_integer("postgres")
    declared_only = _integer("postgres")
    assert aggregation.resolved_argument_problem("avg", True, declared_only) == (
        "PIE-B1004",
        "avg_int_range_evidence_missing",
    )
    assert aggregation.resolved_argument_problem("avg", True, source) is None

    order = SimpleNamespace(direction="asc", read=SimpleNamespace(realization=source))
    assert windows.range_arithmetic_problem(
        SimpleNamespace(unit="range"), (("offset_following", 1),), (order,)
    ) == ("PIE-B1002", "window_range_boundary_out_of_signed64_range")

    window_value, problem = windows.resolved_value_result(
        "postgres", source, "field", None, ("Int", True)
    )
    assert problem is None
    assert window_value is not None
    assert rows.proven_int_bounds(window_value) == rows.proven_int_bounds(source)
    assert (
        rows.resolved_binary_realization(
            "postgres", "+", "Int", True, window_value, _literal_integer("postgres", 0)
        )[0]
        is not None
    )
    assert (
        rows.resolved_binary_realization(
            "postgres", "+", "Int", True, window_value, _literal_integer("postgres", 1)
        )[0]
        is None
    )

    realized, problem = sets.resolved_column_realization(
        SetOperationKind.UNION,
        SetOperationQuantifier.ALL,
        False,
        (SimpleNamespace(realization=source),) * 2,
        (None, None),
    )
    assert problem is None
    assert realized is not None
    assert rows.proven_int_bounds(realized) == rows.proven_int_bounds(source)


def test_int_cast_and_substr_controls_require_proven_ranges() -> None:
    from pietto.ir.model import SymbolId, SymbolNamespace

    literal = _literal_integer("postgres", 1)
    source_forged = _integer("postgres")
    cast, problem = rows.resolved_cast_realization("postgres", "Float", False, literal)
    assert cast is not None and problem is None
    cast, problem = rows.resolved_cast_realization(
        "postgres", "Float", False, source_forged
    )
    assert cast is None
    assert problem == ("PIE-B1003", "cast_realization_not_admitted")

    text = rows.Realization(
        "Text",
        {"kind": "pg_text"},
        False,
        {
            "kind": "text",
            "max_characters": 4,
            "encoding": "UTF8",
            "collation": "C",
            "padding": "NO PAD",
        },
    )
    value, problem = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "substr"),
        "Text",
        False,
        (text, literal, _literal_integer("postgres", 2)),
    )
    assert value is not None and problem is None
    value, problem = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "substr"),
        "Text",
        False,
        (text, source_forged, _literal_integer("postgres", 2)),
    )
    assert value is None
    assert problem == ("PIE-B1004", "substring_result_bound_missing")


def test_narrow_text_length_domain_cannot_prove_arithmetic_safety(tmp_path) -> None:
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    item = probe.fixture("postgres", "T_row_direct", "table_preserve")
    header = item["source"].split("table result:", 1)[0]
    contract = json.loads(item["contract"])
    contract["sources"][0]["fields"][2]["representation"]["domain"] = {
        "kind": "text",
        "max_characters": 1,
        "encoding": "UTF8",
        "collation": "C",
        "padding": "NO PAD",
    }
    encoded = probe.encoded(contract).decode()

    direct = (
        header
        + """table result:
    from rows
    select:
        result = len(text)
"""
    )
    _, outcome = probe.build_case(
        tmp_path / "direct", direct, encoded, "preserve_literals"
    )
    assert outcome.status == "VERIFIED"

    safe = (
        header
        + """table result:
    from rows
    select:
        result = len(text) + 0
"""
    )
    _, outcome = probe.build_case(tmp_path / "safe", safe, encoded, "preserve_literals")
    assert outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).request.family == "postgres"

    rejected = (
        header
        + """table result:
    from rows
    select:
        result = len(text) * 4611686018427387904
"""
    )
    _, outcome = probe.build_case(
        tmp_path / "rejected", rejected, encoded, "preserve_literals"
    )
    assert outcome.status == "BLOCKED"


@pytest.mark.parametrize("family", ("postgres", "mysql"))
@pytest.mark.parametrize(
    ("operator", "left", "right", "expected"),
    (
        ("+", (10, 2), (12, 2), (13, 2)),
        ("-", (10, 2), (12, 2), (13, 2)),
        ("*", (10, 2), (12, 2), (22, 4)),
    ),
)
def test_direct_decimal_carriers_are_reconstructed_for_both_targets(
    family: str,
    operator: str,
    left: tuple[int, int],
    right: tuple[int, int],
    expected: tuple[int, int],
) -> None:
    operands = (_decimal(family, *left), _decimal(family, *right))
    realized, problem = rows.resolved_binary_realization(
        family,
        operator,
        "Decimal",
        False,
        *operands,
        direct_decimal_sources=True,
    )

    assert problem is None
    assert realized is not None
    assert (realized.storage["precision"], realized.storage["scale"]) == expected
    independently_reconstructed = verification.resolved_row_realization(
        family,
        "binary",
        operator,
        "Decimal",
        False,
        operands,
        direct_decimal_sources=True,
    )
    assert independently_reconstructed.storage == realized.storage
    assert independently_reconstructed.domain == realized.domain


@pytest.mark.parametrize("family", ("postgres", "mysql"))
def test_decimal_carrier_boundaries_fail_closed(family: str) -> None:
    left = _decimal(family, 10, 2)
    mismatched_scale = _decimal(family, 12, 3)
    realized, problem = rows.resolved_binary_realization(
        family,
        "+",
        "Decimal",
        False,
        left,
        mismatched_scale,
        direct_decimal_sources=True,
    )
    assert realized is None
    assert problem == ("PIE-B1003", "decimal_scale_mismatch")

    too_wide = (_decimal(family, 65, 0), _decimal(family, 1, 0))
    realized, problem = rows.resolved_binary_realization(
        family,
        "*",
        "Decimal",
        False,
        *too_wide,
        direct_decimal_sources=True,
    )
    assert realized is None
    assert problem == ("PIE-B1002", "decimal_result_outside_physical_range")

    too_scaled = (_decimal(family, 35, 15), _decimal(family, 30, 16))
    realized, problem = rows.resolved_binary_realization(
        family,
        "*",
        "Decimal",
        False,
        *too_scaled,
        direct_decimal_sources=True,
    )
    assert realized is None
    assert problem == ("PIE-B1002", "decimal_result_outside_physical_range")

    with pytest.raises(ValueError, match="decimal direct source operands"):
        verification.resolved_row_realization(
            family,
            "binary",
            "+",
            "Decimal",
            False,
            (left, left),
            direct_decimal_sources=False,
        )

    realized, problem = rows.resolved_binary_realization(
        family,
        "+",
        "Decimal",
        False,
        left,
        _integer(family),
        direct_decimal_sources=True,
    )
    assert realized is None
    assert problem == ("PIE-B1003", "arithmetic_requires_signed_int_operands")


@pytest.mark.parametrize("family", ("postgres", "mysql"))
@pytest.mark.parametrize("operator", ("+", "-", "*"))
def test_finite_float_literal_carriers_are_reconstructed_and_overflow_refused(
    family: str, operator: str
) -> None:
    operands = (_float(family), _float(family))
    realized, problem = rows.resolved_binary_realization(
        family,
        operator,
        "Float",
        False,
        *operands,
        float_values=(1.5, 2.0),
    )
    assert problem is None
    assert realized is not None
    assert (
        verification.resolved_row_realization(
            family,
            "binary",
            operator,
            "Float",
            False,
            operands,
            float_values=(1.5, 2.0),
        ).domain
        == realized.domain
    )

    realized, problem = rows.resolved_binary_realization(
        family,
        "*",
        "Float",
        False,
        *operands,
        float_values=(1e308, 1e308),
    )
    assert realized is None
    assert problem == ("PIE-B1002", "float_result_not_finite")

    with pytest.raises(ValueError, match="float literal operands"):
        verification.resolved_row_realization(
            family,
            "binary",
            "+",
            "Float",
            False,
            operands,
        )


def test_decimal_multiplication_has_the_closed_semantic_signature() -> None:
    decimal = ValueType(
        ResolvedType("Decimal", TypeKind.BUILTIN), EffectiveNullability.NON_NULL
    )

    result, problem = resolved_binary_value_type("*", decimal, decimal)

    assert problem is None
    assert result.resolved_type.name == "Decimal"
