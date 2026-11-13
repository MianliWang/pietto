from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_verification as verification
from pietto._project.project_sql_emission import serialize_project_sql_emission
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


def _physical_integer(family: str, kind: str) -> rows.Realization:
    bounds = rows.signed_range({"kind": kind})
    assert bounds is not None
    low, high = bounds
    return rows.Realization(
        "Int",
        {"kind": kind},
        False,
        {"kind": "int_range", "min": str(low), "max": str(high)},
        (low, high),
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
    if family == "postgres":
        # Q2: the checked bigint `+` keeps the doubled physical range inside
        # signed 64 bits; the declared 0..1 never narrows it.
        assert problem is None and realized is not None
        assert rows.proven_int_bounds(realized) == physical
    else:
        assert realized is None
        assert problem == ("PIE-B1002", "arithmetic_outside_physical_range")

    realized, problem = rows.resolved_binary_realization(
        family, "+", "Int", False, source, _literal_integer(family, 0)
    )
    assert problem is None
    assert realized is not None
    assert rows.proven_int_bounds(realized) == physical

    if family == "postgres":
        negated = verification.resolved_row_realization(
            family, "unary", "-", "Int", False, (source,)
        )
        assert rows.proven_int_bounds(negated) == (-physical[1], physical[1])
        return
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
    let alias = id
    let plus_zero = alias + 0
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

    doubled = (
        header
        + """table result:
    from rows
    let alias = id
    select:
        result = alias + alias
"""
    )
    # The int4 sum is computed in bigint over the whole storage range: the
    # declared 0..1 never narrows it.
    _, outcome = probe.build_case(
        tmp_path / "widened", doubled, encoded, "preserve_literals"
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert public["columns"][0]["representation"] == {
        "storage": {"kind": "pg_int8"},
        "nullable": "unknown",
        "domain": {"kind": "int_range", "min": "-4294967296", "max": "4294967294"},
    }
    assert public["sql"].endswith(
        'SELECT (CAST("t1"."c5" AS pg_catalog.int8) + "t1"."c5") AS "result" '
        'FROM "p0" AS "t1"'
    )
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).rendered.sql == outcome.artifact.rendered.sql

    contract["sources"][0]["fields"][0]["representation"]["storage"] = {
        "kind": "pg_int8"
    }
    _, outcome = probe.build_case(
        tmp_path / "checked",
        doubled,
        probe.encoded(contract).decode(),
        "preserve_literals",
    )
    # Q2: over bigint the declared 0..1 still never narrows the range; the
    # target's checked operator bounds it to signed 64 bits instead.
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert public["columns"][0]["representation"]["domain"] == {
        "kind": "int_range",
        "min": str(-(2**63)),
        "max": str(2**63 - 1),
    }
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).rendered.sql == outcome.artifact.rendered.sql


def test_int_proofs_drive_avg_range_and_set_consumers() -> None:
    from pietto._project import project_sql_emission_aggregation as aggregation
    from pietto._project import project_sql_emission_sets as sets
    from pietto._project import project_sql_emission_windows as windows
    from pietto.ast_nodes import SetOperationKind, SetOperationQuantifier

    source = _source_integer("postgres")
    declared_only = _integer("postgres")
    assert aggregation.resolved_argument_problem(
        "avg", True, declared_only, "postgres"
    ) == (
        "PIE-B1004",
        "avg_int_range_evidence_missing",
    )
    assert (
        aggregation.resolved_argument_problem("avg", True, source, "postgres") is None
    )
    # Lane F: stddev needs no range evidence on PostgreSQL, whose VAR_SAMP of
    # any signed 64-bit input is finite; MySQL computes it in DOUBLE.
    assert (
        aggregation.resolved_argument_problem("stddev", True, declared_only, "postgres")
        is None
    )
    assert aggregation.resolved_argument_problem(
        "stddev", True, _integer("mysql"), "mysql"
    ) == ("PIE-B1003", "stddev_int_not_admitted_on_target")

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
    # Q2: one past the window value's bigint top is PostgreSQL's checked `+`;
    # the result keeps only the values inside signed 64 bits.
    bumped = rows.resolved_binary_realization(
        "postgres", "+", "Int", True, window_value, _literal_integer("postgres", 1)
    )[0]
    window_bounds = rows.proven_int_bounds(window_value)
    assert bumped is not None and window_bounds is not None
    assert rows.proven_int_bounds(bumped) == (window_bounds[0] + 1, 2**63 - 1)

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


def test_postgres_scalar_carriers_have_their_own_physical_laws() -> None:
    from pietto.ir.model import SymbolId, SymbolNamespace

    integer = _literal_integer("postgres", -(1 << 63))
    text, problem = rows.resolved_cast_realization("postgres", "Text", False, integer)
    assert problem is None
    assert text is not None
    assert text.domain["max_characters"] == 20
    assert rows.resolved_cast_realization("mysql", "Text", False, integer)[0] is None

    decimal = _decimal("postgres", 4, 2)
    rounded, problem = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "round"),
        "Decimal",
        False,
        (decimal, _literal_integer("postgres", 0)),
        static_values=(None, ("Int", 0)),
    )
    assert problem is None and rounded is not None
    assert rounded.domain == {"kind": "decimal", "precision": 3, "scale": 0}

    decimal_65_30 = _decimal("postgres", 65, 30)
    default, problem = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "round"),
        "Decimal",
        False,
        (decimal_65_30,),
    )
    explicit_zero, problem_zero = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "round"),
        "Decimal",
        False,
        (decimal_65_30, _literal_integer("postgres", 0)),
        static_values=(None, ("Int", 0)),
    )
    assert problem is problem_zero is None
    assert default is not None and explicit_zero is not None
    assert (
        default.domain
        == explicit_zero.domain
        == {
            "kind": "decimal",
            "precision": 36,
            "scale": 0,
        }
    )

    decimal_65_0 = _decimal("postgres", 65, 0)
    default_zero, problem = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "round"),
        "Decimal",
        False,
        (decimal_65_0,),
    )
    explicit_zero, problem_zero = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "round"),
        "Decimal",
        False,
        (decimal_65_0, _literal_integer("postgres", 0)),
        static_values=(None, ("Int", 0)),
    )
    assert problem is problem_zero is None
    assert default_zero is not None and explicit_zero is not None
    assert (
        default_zero.domain
        == explicit_zero.domain
        == {
            "kind": "decimal",
            "precision": 65,
            "scale": 0,
        }
    )

    for source, digits, expected in (
        (decimal_65_0, 0, {"kind": "decimal", "precision": 65, "scale": 0}),
        (decimal_65_30, 30, {"kind": "decimal", "precision": 65, "scale": 30}),
    ):
        rounded, problem = rows.resolved_scalar_call_realization(
            "postgres",
            SymbolId(SymbolNamespace.CALLABLE, "round"),
            "Decimal",
            False,
            (source, _literal_integer("postgres", digits)),
            static_values=(None, ("Int", digits)),
        )
        assert problem is None and rounded is not None
        assert rounded.domain == expected

    rejected, problem = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "round"),
        "Decimal",
        False,
        (decimal_65_0, _literal_integer("postgres", -1)),
        static_values=(None, ("Int", -1)),
    )
    assert rejected is None
    assert problem == ("PIE-B1002", "round_result_outside_physical_range")

    floating = _float("postgres")
    rounded, problem = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "round"),
        "Float",
        False,
        (floating,),
    )
    assert problem is None and rounded is not None
    assert (rounded.tag, rounded.storage, rounded.domain) == (
        floating.tag,
        floating.storage,
        floating.domain,
    )
    assert (
        rows.resolved_scalar_call_realization(
            "mysql",
            SymbolId(SymbolNamespace.CALLABLE, "round"),
            "Float",
            False,
            (floating,),
        )[0]
        is None
    )

    timestamp = rows.Realization(
        "Timestamp",
        {"kind": "pg_timestamp", "fractional_seconds": 6},
        False,
        {"kind": "timestamp"},
    )
    unit = rows.Realization(
        "Text",
        {"kind": "pg_text"},
        False,
        {
            "kind": "text",
            "max_characters": 6,
            "encoding": "UTF8",
            "collation": "C",
            "padding": "NO PAD",
        },
    )
    truncated, problem = rows.resolved_scalar_call_realization(
        "postgres",
        SymbolId(SymbolNamespace.CALLABLE, "date_trunc"),
        "Timestamp",
        False,
        (unit, timestamp),
        static_values=(("Text", "year"), None),
    )
    assert problem is None and truncated is not None
    assert (truncated.tag, truncated.storage, truncated.domain) == (
        timestamp.tag,
        timestamp.storage,
        timestamp.domain,
    )


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

    # The one-character Text domain never bounds `len(text)`: its product with
    # 2**62 stays outside a static proof. PostgreSQL's checked bigint `*`
    # bounds it (Q2), with its evidence; it is never proved statically.
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
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    assert [
        r.evidence for r in outcome.artifact.generated_requirements if r.evidence
    ] == [("target_checked_signed64_narrowing",)]


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
    if family == "postgres":
        assert problem is None and realized is not None
        assert realized.domain == {"kind": "decimal", "precision": 13, "scale": 3}
    else:
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
    assert problem == ("PIE-B1004", "decimal_source_carrier_missing")


def test_postgres_decimal_int_and_scale_mismatch_use_exact_carriers() -> None:
    decimal = _decimal("postgres", 3, 2)
    int2 = _physical_integer("postgres", "pg_int2")
    literal = _literal_integer("postgres", 1)

    realized, problem = rows.resolved_binary_realization(
        "postgres",
        "+",
        "Decimal",
        False,
        decimal,
        int2,
        decimal_operand_origins=("decimal", "int"),
    )
    assert problem is None and realized is not None
    assert realized.domain == {"kind": "decimal", "precision": 8, "scale": 2}
    independently_reconstructed = verification.resolved_row_realization(
        "postgres",
        "binary",
        "+",
        "Decimal",
        False,
        (decimal, int2),
        decimal_operand_origins=("decimal", "int"),
    )
    assert independently_reconstructed.storage == realized.storage

    realized, problem = rows.resolved_binary_realization(
        "postgres",
        "+",
        "Decimal",
        False,
        decimal,
        literal,
        decimal_operand_origins=("decimal", "int_literal"),
    )
    assert problem is None and realized is not None
    assert realized.domain == {"kind": "decimal", "precision": 4, "scale": 2}

    mixed = _decimal("postgres", 5, 3)
    realized, problem = rows.resolved_binary_realization(
        "postgres",
        "-",
        "Decimal",
        False,
        decimal,
        mixed,
        decimal_operand_origins=("decimal", "decimal"),
    )
    assert problem is None and realized is not None
    assert realized.domain == {"kind": "decimal", "precision": 6, "scale": 3}


def test_postgres_decimal_sum_uses_checked_wide_result() -> None:
    source = _decimal("postgres", 46, 30)
    result = rows.decimal_sum_realization("postgres", source, True)
    assert result is not None
    assert result.storage == {"kind": "pg_numeric", "precision": 65, "scale": 30}
    assert (
        rows.decimal_sum_realization("postgres", _decimal("postgres", 47, 30), True)
        is None
    )


def test_same_scale_decimal_parameters_stay_refused_in_both_realizers() -> None:
    left = _decimal("postgres", 9, 2)
    right = _decimal("postgres", 9, 2)
    realized, problem = rows.resolved_binary_realization(
        "postgres",
        "+",
        "Decimal",
        False,
        left,
        right,
        decimal_operand_origins=("decimal", "decimal_parameter"),
    )
    assert realized is None
    assert problem == ("PIE-B1003", "decimal_direct_source_operands_required")
    with pytest.raises(ValueError, match="decimal direct source operands"):
        verification.resolved_row_realization(
            "postgres",
            "binary",
            "+",
            "Decimal",
            False,
            (left, right),
            decimal_operand_origins=("decimal", "decimal_parameter"),
        )


@pytest.mark.parametrize(
    ("operator", "left", "right", "origins", "accepted"),
    (
        ("+", (9, 2), (19, 0), ("decimal_parameter", "int"), True),
        ("+", (19, 0), (9, 2), ("int", "decimal_parameter"), True),
        ("+", (9, 2), (19, 0), ("decimal", "int_parameter"), True),
        ("+", (19, 0), (9, 2), ("int_parameter", "decimal"), True),
        ("+", (9, 2), (19, 0), ("decimal_parameter", "int_parameter"), True),
        ("-", (9, 2), (19, 0), ("decimal_parameter", "int"), True),
        ("-", (19, 0), (9, 2), ("int", "decimal_parameter"), True),
        ("-", (9, 2), (19, 0), ("decimal", "int_parameter"), True),
        ("-", (19, 0), (9, 2), ("int_parameter", "decimal"), True),
        ("-", (9, 2), (19, 0), ("decimal_parameter", "int_parameter"), True),
        ("+", (9, 2), (8, 3), ("decimal_parameter", "decimal"), True),
        ("+", (8, 3), (9, 2), ("decimal", "decimal_parameter"), True),
        ("-", (9, 2), (8, 3), ("decimal_parameter", "decimal_parameter"), True),
        ("+", (9, 2), (8, 2), ("decimal_parameter", "decimal"), False),
        ("-", (9, 2), (8, 2), ("decimal", "decimal_parameter"), False),
        ("+", (9, 2), (9, 2), ("decimal_parameter", "decimal_parameter"), False),
        ("*", (9, 2), (8, 3), ("decimal_parameter", "decimal"), False),
        ("*", (9, 2), (8, 3), ("decimal", "decimal_parameter"), False),
        ("*", (9, 2), (8, 3), ("decimal_parameter", "decimal_parameter"), False),
    ),
)
def test_parameter_e9_matrix_has_one_live_and_independent_boundary(
    operator: str,
    left: tuple[int, int],
    right: tuple[int, int],
    origins: tuple[str, str],
    accepted: bool,
) -> None:
    def operand(parameters: tuple[int, int], origin: str) -> rows.Realization:
        if origin.startswith("decimal"):
            return _decimal("postgres", *parameters)
        return _physical_integer("postgres", "pg_int8")

    left_value, right_value = (
        operand(left, origins[0]),
        operand(right, origins[1]),
    )
    realized, problem = rows.resolved_binary_realization(
        "postgres",
        operator,
        "Decimal",
        False,
        left_value,
        right_value,
        decimal_operand_origins=origins,
    )
    if not accepted:
        assert realized is None
        assert problem == ("PIE-B1003", "decimal_direct_source_operands_required")
        with pytest.raises(ValueError, match="decimal direct source operands"):
            verification.resolved_row_realization(
                "postgres",
                "binary",
                operator,
                "Decimal",
                False,
                (left_value, right_value),
                decimal_operand_origins=origins,
            )
        return
    assert problem is None and realized is not None
    reconstructed = verification.resolved_row_realization(
        "postgres",
        "binary",
        operator,
        "Decimal",
        False,
        (left_value, right_value),
        decimal_operand_origins=origins,
    )
    assert reconstructed.storage == realized.storage
    assert reconstructed.domain == realized.domain


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

    if family == "postgres":
        assert (
            verification.resolved_row_realization(
                family,
                "binary",
                "+",
                "Float",
                False,
                operands,
            ).domain
            == operands[0].domain
        )
    else:
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


def _narrow(kind: str) -> rows.Realization:
    realized = rows.source_realization(
        rows.Realization(
            "Int", {"kind": kind}, False, {"kind": "int_range", "min": "0", "max": "1"}
        )
    )
    assert realized is not None
    return realized


@pytest.mark.parametrize("kind", ("pg_int2", "pg_int4"))
@pytest.mark.parametrize("operator", ("+", "-", "*"))
def test_narrow_postgres_arithmetic_leaving_its_type_is_computed_in_bigint(
    kind: str, operator: str
) -> None:
    narrow = _narrow(kind)
    limit = 1 << (16 if kind == "pg_int2" else 32) - 1
    low, high = {
        "+": (-2 * limit, 2 * limit - 2),
        "-": (-2 * limit + 1, 2 * limit - 1),
        "*": (-limit * (limit - 1), limit * limit),
    }[operator]
    expected = (
        "Int",
        {"kind": "pg_int8"},
        False,
        {"kind": "int_range", "min": str(low), "max": str(high)},
        (low, high),
        False,
        None,
    )

    def fields(value):
        return (
            value.tag,
            value.storage,
            value.nullable,
            value.domain,
            value.proven_int_range,
            value.binding,
            value.obligation,
        )

    realized, problem = rows.resolved_binary_realization(
        "postgres", operator, "Int", False, narrow, narrow
    )
    assert problem is None and realized is not None
    assert fields(realized) == expected
    assert (
        fields(
            verification.resolved_row_realization(
                "postgres", "binary", operator, "Int", False, (narrow, narrow)
            )
        )
        == expected
    )
    negated = rows._unary_int("postgres", narrow, -limit + 1, limit, False)
    assert negated is not None and negated.storage == {"kind": "pg_int8"}
    assert verification.resolved_row_realization(
        "postgres", "unary", "-", "Int", False, (narrow,)
    ).storage == {"kind": "pg_int8"}


def test_bigint_widening_never_applies_to_int8_or_mysql() -> None:
    wide = _narrow("pg_int8")
    # A bigint operand is never widened; an operation that may leave signed
    # 64 bits is PostgreSQL's checked bigint operation (Q2), clipped.
    for operator, left in (("+", wide), ("*", _narrow("pg_int4"))):
        realized, problem = rows.resolved_binary_realization(
            "postgres", operator, "Int", False, left, wide
        )
        assert problem is None and realized is not None
        assert (realized.storage, realized.proven_int_range) == (
            {"kind": "pg_int8"},
            rows.SIGNED64,
        )
    mysql = rows.source_realization(
        rows.Realization(
            "Int",
            {"kind": "my_int"},
            False,
            {"kind": "int_range", "min": "0", "max": "1"},
        )
    )
    assert mysql is not None
    realized, problem = rows.resolved_binary_realization(
        "mysql", "+", "Int", False, mysql, mysql
    )
    assert problem is None and realized is not None
    assert realized.storage == {"kind": "my_signed_int"}
    # A narrow sum that fits its own type keeps it: no redundant widening.
    small = rows.Realization(
        "Int",
        {"kind": "pg_int4"},
        False,
        {"kind": "int_range", "min": "0", "max": "1"},
        (0, 1),
    )
    realized, problem = rows.resolved_binary_realization(
        "postgres", "+", "Int", False, small, small
    )
    assert problem is None and realized is not None
    assert realized.storage == {"kind": "pg_int4"}


def _point(kind: str, value: int) -> rows.Realization:
    return rows.Realization(
        "Int",
        {"kind": kind},
        False,
        {"kind": "int_range", "min": str(value), "max": str(value)},
        (value, value),
    )


def _operation(kind, operator, operands, realization):
    """A realized operation over already realized operand values."""
    original = SimpleNamespace(
        expression=SimpleNamespace(operator=operator),
        callee_symbol=SimpleNamespace(name=operator),
    )
    values = tuple(
        rows.SQLOperation(original, "arithmetic", (), operand) for operand in operands
    )
    return rows.SQLOperation(original, kind, values, realization)


@pytest.mark.parametrize(
    "operator,left,right,low,high",
    (
        ("+", "wide", "one", -(2**63) + 1, 2**63 - 1),
        ("-", "one", "wide", -(2**63) + 2, 2**63 - 1),
        ("-", "wide", "one", -(2**63), 2**63 - 2),
        ("*", "wide", "wide", -(2**63), 2**63 - 1),
    ),
)
def test_bigint_arithmetic_meeting_signed_64_is_the_targets_checked_operation(
    operator, left, right, low, high
) -> None:
    """Q2: a bigint result whose exact range meets but leaves signed 64 bits
    keeps the part inside them, binding-free, and both the builder and the
    independent verifier mark it as relying on the target's check."""
    values = {"wide": _narrow("pg_int8"), "one": _point("pg_int8", 1)}
    operands = (values[left], values[right])
    realized, problem = rows.resolved_binary_realization(
        "postgres", operator, "Int", False, *operands
    )
    assert problem is None and realized is not None
    expected = (
        {"kind": "pg_int8"},
        {"kind": "int_range", "min": str(low), "max": str(high)},
        (low, high),
        False,
        None,
    )
    for value in (
        realized,
        verification.resolved_row_realization(
            "postgres", "binary", operator, "Int", False, operands
        ),
    ):
        assert (
            value.storage,
            value.domain,
            value.proven_int_range,
            value.binding,
            value.obligation,
        ) == expected
    operation = _operation("arithmetic", operator, operands, realized)
    assert rows.target_checked("postgres", operation)
    assert verification._target_checked("postgres", operation)
    # MySQL keeps the static signed 64-bit proof.
    mysql = tuple(
        rows.Realization(
            "Int", {"kind": "my_bigint"}, False, value.domain, value.proven_int_range
        )
        for value in operands
    )
    assert rows.resolved_binary_realization(
        "mysql", operator, "Int", False, *mysql
    ) == (None, ("PIE-B1002", "arithmetic_outside_physical_range"))


def test_a_bigint_range_wholly_outside_signed_64_stays_refused() -> None:
    """A disjoint range, as of a constant, is refused statically: PostgreSQL
    would otherwise raise 22003 while planning, even in a branch never run."""
    top, one = _point("pg_int8", 2**63 - 1), _point("pg_int8", 1)
    assert rows.resolved_binary_realization(
        "postgres", "+", "Int", False, top, one
    ) == (None, ("PIE-B1002", "arithmetic_outside_physical_range"))
    with pytest.raises(ValueError, match="outside its physical range"):
        verification.resolved_row_realization(
            "postgres", "binary", "+", "Int", False, (top, one)
        )
    bottom = _point("pg_int8", -(2**63))
    assert rows._unary_int("postgres", bottom, 2**63, 2**63, False) is None


def test_checked_sign_and_abs_and_a_fitting_bigint_result_carry_no_check() -> None:
    wide = _narrow("pg_int8")
    negated = rows._unary_int("postgres", wide, -(2**63) + 1, 2**63, False)
    magnitude = rows._unary_int("postgres", wide, 0, 2**63, False)
    assert negated is not None and magnitude is not None
    assert (negated.proven_int_range, magnitude.proven_int_range) == (
        (-(2**63) + 1, 2**63 - 1),
        (0, 2**63 - 1),
    )
    assert rows.target_checked("postgres", _operation("sign", "-", (wide,), negated))
    assert rows.target_checked(
        "postgres", _operation("scalar_call", "abs", (wide,), magnitude)
    )
    assert verification._target_checked(
        "postgres", _operation("scalar_call", "abs", (wide,), magnitude)
    )
    # A bigint result that fits needs no check, and neither does `+` on its
    # own constant nor any MySQL result.
    zero = _point("pg_int8", 0)
    fitted, problem = rows.resolved_binary_realization(
        "postgres", "+", "Int", False, wide, zero
    )
    assert problem is None and fitted is not None
    for family in ("postgres", "mysql"):
        operation = _operation("arithmetic", "+", (wide, zero), fitted)
        assert not rows.target_checked(family, operation)
        assert not verification._target_checked(family, operation)
    assert rows._unary_int("mysql", wide, -(2**63) + 1, 2**63, False) is None


def test_a_parameter_operand_keeps_its_binding_obligation() -> None:
    """A template keeps deferring a parameter-dependent range to each binding,
    whose bound range then follows the same checked rule."""
    parameter = rows.parameter_realization("postgres", "Int", False)
    realized, problem = rows.resolved_binary_realization(
        "postgres", "+", "Int", False, parameter, _point("pg_int8", 1)
    )
    assert problem is None and realized is not None
    assert (realized.binding, realized.obligation) == (
        True,
        rows.INT_RANGE_OBLIGATION,
    )
    assert not rows.target_checked(
        "postgres",
        _operation("arithmetic", "+", (parameter, _point("pg_int8", 1)), realized),
    )


def _float_carrier(storage: str, domain: dict) -> rows.Realization:
    return rows.Realization("Float", {"kind": storage}, False, domain)


DISTRIBUTION = {"kind": "float64"}
# Each Float arm reads one carrier predicate. A window distribution result
# compares (and BETWEENs) on both targets and, on PostgreSQL only, also
# groups, deduplicates, orders, sets and keys a window (E6).
FLOAT_CARRIERS = {
    "pg": _float_carrier("pg_float8", probe.FINITE_FLOAT),
    "my": _float_carrier("my_double", probe.FINITE_FLOAT),
    "pg_distribution": _float_carrier("pg_float8", DISTRIBUTION),
    "my_distribution": _float_carrier("my_double", DISTRIBUTION),
    "pg_unreviewed": _float_carrier("pg_float8", {"kind": "float32"}),
    "my_unreviewed": _float_carrier("my_double", {"kind": "float32"}),
}


def _compares(family, left, right, operator="<", *, rows_both_sides=False):
    built = rows.resolved_comparison_realization(
        family, "Bool", False, left, right, operator, rows_both_sides=rows_both_sides
    )
    try:
        verification.resolved_row_realization(
            family,
            "comparison",
            operator,
            "Bool",
            False,
            (left, right),
            rows_both_sides=rows_both_sides,
        )
    except ValueError:
        independent = False
    else:
        independent = True
    assert (built[1] is None) is independent, built
    return independent


def _betweens(family, values):
    built = rows.resolved_between_realization(family, "Bool", False, values)
    try:
        verification.resolved_row_realization(
            family, "between", None, "Bool", False, values
        )
    except ValueError:
        independent = False
    else:
        independent = True
    assert (built[1] is None) is independent, built
    return independent


@pytest.mark.parametrize("family", ("postgres", "mysql"))
@pytest.mark.parametrize("name", tuple(FLOAT_CARRIERS))
def test_float_comparison_and_between_admit_one_reviewed_carrier(family, name):
    """F2/L13: builder and independent verifier agree on every carrier; only the
    family's own finite or window distribution carrier compares."""
    value = FLOAT_CARRIERS[name]
    own = name.startswith("pg" if family == "postgres" else "my")
    admitted = own and not name.endswith("unreviewed")
    literal = FLOAT_CARRIERS["pg" if family == "postgres" else "my"]
    assert _compares(family, value, literal) is admitted
    assert _compares(family, literal, value, "==") is admitted
    assert _betweens(family, (value, literal, literal)) is admitted
    assert _betweens(family, (literal, value, literal)) is admitted
    # O2: Float against Int stays refused on both targets.
    assert not _compares(family, value, _integer(family))


@pytest.mark.parametrize("family", ("postgres", "mysql"))
@pytest.mark.parametrize("operator", ("==", "!=", "<", "<=", ">", ">="))
def test_mysql_float_equality_between_two_row_reads_stays_refused(family, operator):
    """Branch B: MySQL kept -0.0 and 0.0 apart in a hash over a wide key, so a
    Float `==` whose operands both read rows (a join, semijoin or hash key) is
    refused there, and so is `!=`, which MySQL's parser negates into `=` under
    `not`; PostgreSQL and every ordering inequality stay admitted."""
    value = FLOAT_CARRIERS["pg" if family == "postgres" else "my"]
    refused = family == "mysql" and operator in {"==", "!="}
    assert _compares(family, value, value, operator, rows_both_sides=True) is (
        not refused
    )
    assert _compares(family, value, value, operator, rows_both_sides=False)


def test_the_comparison_row_read_fact_is_required():
    value = FLOAT_CARRIERS["my"]
    with pytest.raises(TypeError):
        rows.resolved_comparison_realization(  # type: ignore[call-arg]
            "mysql", "Bool", False, value, value, "=="
        )
    with pytest.raises(ValueError, match="comparison row reads"):
        verification.resolved_row_realization(
            "mysql", "comparison", "==", "Bool", False, (value, value)
        )


@pytest.mark.parametrize("name", tuple(FLOAT_CARRIERS))
def test_a_mysql_float_key_cell_admits_only_the_finite_double(name):
    """Phase77 S07: a reader's own S07 cell admits MySQL's finite DOUBLE as a
    GROUP BY key, nothing else: no MySQL distribution result or unreviewed
    carrier, and no other aggregate argument."""
    from pietto._project import project_sql_emission_aggregation as aggregation

    value = FLOAT_CARRIERS[name]
    keyed = name in {"pg", "pg_distribution", "my"}
    assert (aggregation.group_key_problem(value, float_key_cell=True) is None) is keyed
    assert (
        aggregation.resolved_argument_problem("count_distinct", True, value, "mysql")
        is not None
    )


@pytest.mark.parametrize("name", tuple(FLOAT_CARRIERS))
def test_float_equivalence_admits_postgres_keys_and_order_each_finite(name):
    """Group keys, DISTINCT, the equivalence set forms, window partition and
    order keys, string_agg order keys and FULL JOIN equalities admit only the
    PostgreSQL finite and distribution carriers (Branch B, E6); relation ORDER
    admits each target's own finite carrier (MySQL too); UNION ALL transports
    any matching Float carrier exactly as before. A counted or extreme
    aggregate argument stays finite only."""
    from pietto._project import project_sql_emission_aggregation as aggregation
    from pietto._project import project_sql_emission_joins as joins
    from pietto._project import project_sql_emission_results as results
    from pietto._project import project_sql_emission_sets as setting
    from pietto._project import project_sql_emission_windows as windows
    from pietto.ast_nodes import SetOperationKind as Kind
    from pietto.ast_nodes import SetOperationQuantifier as Quantifier

    value = FLOAT_CARRIERS[name]
    admitted = name in {"pg", "pg_distribution"}
    assert (aggregation.group_key_problem(value) is None) is admitted
    assert (aggregation.group_key_problem(value, distribution=False) is None) is (
        name == "pg"
    )
    for family in ("postgres", "mysql"):
        keyed = admitted and family == "postgres"
        assert (results.distinct_problem(family, value) is None) is keyed
        assert results.order_admitted(family, value) is (
            name == {"postgres": "pg", "mysql": "my"}[family] or keyed
        )
        assert windows.partition_key_admitted(value, family) is keyed
        assert windows.order_key_admitted(value, family) is keyed
        assert verification._order_key(value, family) is keyed
        assert (
            aggregation.order_key_problem("string_agg", family, value) is None
        ) is admitted
    full = rows.SQLOperation(
        SimpleNamespace(expression=SimpleNamespace(operator="==")),
        "comparison",
        (
            rows.SQLStageReference(
                None, None, rows.StageColumn(0, "left", None, value), value, "left"
            ),
            rows.SQLStageReference(
                None, None, rows.StageColumn(1, "right", None, value), value, "right"
            ),
        ),
        rows._bool("postgres", False),
    )
    assert (joins.full_admissible(None, (), full, "postgres") is None) is admitted
    assert joins.full_admissible(None, (), full, "mysql") == (
        "PIE-B1003",
        "mysql_full_join_approved_non_support",
    )
    assert verification._float_carrier(value, "postgres") is (name == "pg")
    reads = (SimpleNamespace(realization=value), SimpleNamespace(realization=value))
    for kind, quantifier in (
        (Kind.UNION, Quantifier.ALL),
        (Kind.UNION, Quantifier.DISTINCT),
        (Kind.INTERSECT, Quantifier.ALL),
        (Kind.EXCEPT, Quantifier.DISTINCT),
    ):
        expected = admitted or (kind, quantifier) == (Kind.UNION, Quantifier.ALL)
        realized, problem = setting.resolved_column_realization(
            kind, quantifier, False, reads, (None, None)
        )
        assert (problem is None) is expected, problem
        if not expected:
            assert problem == ("PIE-B1003", "set_row_equivalence_domain_unsupported")
            with pytest.raises(ValueError, match="set comparison domain"):
                verification.resolved_set_column_realization(
                    kind, quantifier, False, reads, (None, None)
                )
        else:
            assert realized is not None
            checked = verification.resolved_set_column_realization(
                kind, quantifier, False, reads, (None, None)
            )
            assert (checked.storage, checked.domain) == (
                realized.storage,
                realized.domain,
            )


@pytest.mark.parametrize("precision,scale", [(9, 2), (46, 30), (47, 30)])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "origins", [("decimal", "int"), ("decimal_parameter", "int_parameter")]
)
def test_decimal_int_product_uses_its_own_digits_bound(
    precision, scale, reverse, origins
):
    operands = (
        _decimal("postgres", precision, scale),
        _physical_integer("postgres", "pg_int8"),
    )
    if reverse:
        operands, origins = operands[::-1], origins[::-1]
    realized, problem = rows.resolved_binary_realization(
        "postgres", "*", "Decimal", True, *operands, decimal_operand_origins=origins
    )
    if precision > 46:
        assert realized is None
        assert problem == ("PIE-B1002", "decimal_result_outside_physical_range")
        with pytest.raises(ValueError, match="outside physical range"):
            verification.resolved_row_realization(
                "postgres",
                "binary",
                "*",
                "Decimal",
                True,
                operands,
                decimal_operand_origins=origins,
            )
        return
    assert problem is None and realized is not None
    assert realized.storage == {
        "kind": "pg_numeric",
        "precision": precision + 19,
        "scale": scale,
    }
    assert realized.nullable is True
    reconstructed = verification.resolved_row_realization(
        "postgres",
        "binary",
        "*",
        "Decimal",
        True,
        operands,
        decimal_operand_origins=origins,
    )
    assert reconstructed.storage == realized.storage
    assert reconstructed.domain == realized.domain
    assert reconstructed.nullable == realized.nullable


@pytest.mark.parametrize(
    "bounds",
    [
        rows.SIGNED64,
        (rows.SIGNED64[0], rows.SIGNED64[0]),
        (rows.SIGNED64[1], rows.SIGNED64[1]),
        (2**70, 2**70),
        (-(2**70), -(2**70)),
        (1, -1),
    ],
)
@pytest.mark.parametrize("origin", ["int", "int_literal", "int_parameter"])
def test_decimal_product_rejects_forged_integer_physical_bounds(bounds, origin):
    integer = rows.Realization(
        "Int",
        {"kind": "pg_int8"},
        False,
        {"kind": "int_range", "min": str(bounds[0]), "max": str(bounds[1])},
        bounds,
    )
    operands = (_decimal("postgres", 46, 30), integer)
    origins = ("decimal", origin)
    realized, problem = rows.resolved_binary_realization(
        "postgres", "*", "Decimal", False, *operands, decimal_operand_origins=origins
    )
    accepted = rows.SIGNED64[0] <= bounds[0] <= bounds[1] <= rows.SIGNED64[1] and (
        origin != "int_literal" or bounds[0] == bounds[1]
    )
    if not accepted:
        assert realized is None and problem == (
            "PIE-B1004",
            "decimal_source_carrier_missing",
        )
        with pytest.raises(ValueError, match="decimal source carrier"):
            verification.resolved_row_realization(
                "postgres",
                "binary",
                "*",
                "Decimal",
                False,
                operands,
                decimal_operand_origins=origins,
            )
    else:
        assert problem is None and realized is not None
        assert realized.storage == {"kind": "pg_numeric", "precision": 65, "scale": 30}
        checked = verification.resolved_row_realization(
            "postgres",
            "binary",
            "*",
            "Decimal",
            False,
            operands,
            decimal_operand_origins=origins,
        )
        assert checked.storage == realized.storage
