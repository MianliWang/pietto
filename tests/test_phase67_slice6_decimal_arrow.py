"""Retained Decimal authority and context-free fixed-scale ingress without Arrow."""

from dataclasses import replace
from decimal import Decimal, localcontext, ROUND_DOWN, ROUND_UP
from typing import cast
import importlib.util
import json

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_arrow_result as arrow
from pietto._project import project_result_binding as binding
from pietto._project.project_result_contract import ResultError
from pietto._project.project_sql_emission import emit_project_sql
from pietto._project.project_result_contract_portable import export_result_contract
from pietto._project.project_result_contract_correspondence import verify_bound_export


@pytest.fixture(scope="module")
def roots(tmp_path_factory):
    root = tmp_path_factory.mktemp("decimal-roots")
    return {
        (t, p, s): probe.decimal_fixture(root / f"{t}-{p}-{s}", t, p, s)
        for t in ("postgres", "mysql")
        for p, s in probe.DECIMAL_PAIRS
    }


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("precision,scale", probe.DECIMAL_PAIRS)
def test_real_retained_parameters_defaults_exact_edges_and_codec(
    roots, target, precision, scale
):
    checked, artifact, neutral, producer = roots[target, precision, scale]
    binding.verify_producer_binding(producer, neutral, artifact)
    assert (
        arrow._decimal_widths(producer, None)
        == ((128 if precision <= 38 else 256),) * 2
    )
    for field in producer.fields:
        assert field.column.source_field.decimal.precision == precision
        assert field.column.source_field.decimal.scale == scale
        assert field.observation.decimal == binding.DecimalObservation(precision, scale)
        assert (
            field.observation.lower
            is field.observation.upper
            is field.observation.text
            is None
        )
    for k in (10**precision - 1, 1 - 10**precision, 0, 1, -1):
        value = probe.decimal_literal(k, scale, trailing=4, negative_zero=k == 0)
        assert (
            cast(Decimal, arrow._value(value, producer.fields[0])).as_tuple()
            == probe.decimal_literal(k, scale).as_tuple()
        )
    for k in (10**precision, -(10**precision)):
        with pytest.raises(ResultError, match="VALUE_DOMAIN"):
            arrow._value(probe.decimal_literal(k, scale), producer.fields[0])
    exported = export_result_contract(neutral, checked)
    verify_bound_export(exported, checked)
    assert [
        [a["value"]["value"] for a in f["declared"]["arguments"]]
        for f in exported.view.fields
    ] == [[str(precision), str(scale)]] * 2
    assert importlib.util.find_spec("pyarrow") is None


@pytest.mark.parametrize(
    "changes",
    (
        {"precision": 8},
        {"scale": 1},
        {"precision": True},
        {"scale": False},
        {"precision": 9.0},
        {"scale": "2"},
    ),
)
def test_observation_parameters_are_exact_and_source_bound(roots, changes, monkeypatch):
    _, artifact, neutral, producer = roots["postgres", 9, 2]
    obs = list(probe.decimal_observations("postgres", 9, 2))
    fact = obs[0].decimal
    assert fact is not None
    obs[0] = replace(obs[0], decimal=replace(fact, **changes))

    def forbidden():
        raise AssertionError("producer lie reached Arrow")

    monkeypatch.setattr(arrow, "_arrow", forbidden)
    with pytest.raises(ResultError, match="PRODUCER_OBSERVATION"):
        arrow.bind_arrow(binding.bind_producer(neutral, artifact, tuple(obs)))


class DecimalSubclass(Decimal):
    pass


class Coercible:
    def __float__(self):
        raise AssertionError("implicit float")

    def __str__(self):
        raise AssertionError("implicit text")


@pytest.mark.parametrize(
    "value",
    (
        1,
        True,
        1.0,
        "1",
        b"1",
        DecimalSubclass("1"),
        Coercible(),
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("1E+1000000"),
        Decimal("1E-1000000"),
        Decimal("1.234"),
    ),
)
def test_exact_finite_carrier_and_no_lossy_scale(roots, value):
    with pytest.raises(ResultError, match="VALUE_DOMAIN"):
        arrow._value(value, roots["postgres", 9, 2][3].fields[0])


@pytest.mark.parametrize("rounding", (ROUND_DOWN, ROUND_UP))
def test_context_flags_extreme_exponents_and_zero_do_not_change(roots, rounding):
    bound = roots["postgres", 65, 30][3].fields[0]
    value = probe.decimal_literal(10**65 - 1, 30, trailing=6)
    expected = probe.decimal_literal(10**65 - 1, 30).as_tuple()
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.rounding = rounding
        ctx.Emin = -2
        ctx.Emax = 2
        for signal in ctx.traps:
            ctx.traps[signal] = True
        for signal in ctx.flags:
            ctx.flags[signal] = True
        before = probe.decimal_context_snapshot(ctx)
        assert cast(Decimal, arrow._value(value, bound)).as_tuple() == expected
        for zero in (Decimal("0E+1000000"), Decimal("-0E-1000000")):
            assert cast(Decimal, arrow._value(zero, bound)).as_tuple() == (0, (0,), -30)
        for bad in (Decimal("1E+1000000"), Decimal("1E-1000000"), Decimal("sNaN")):
            with pytest.raises(ResultError, match="VALUE_DOMAIN"):
                arrow._value(bad, bound)
        assert probe.decimal_context_snapshot(ctx) == before


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_explicit_width_identity_and_no_sample_cures_128_at_39(
    roots, target, monkeypatch
):
    producer = roots[target, 39, 4][3]
    fields = producer.fields

    def forbidden():
        raise AssertionError("invalid request reached Arrow")

    monkeypatch.setattr(arrow, "_arrow", forbidden)
    r0, r1 = (arrow.DecimalWidthRequest(f.field, 256) for f in fields)
    for req in (
        (),
        [],
        (r0,),
        (r0, r1, None),
        (r0, r0),
        (r1, r0),
        (arrow.DecimalWidthRequest(replace(r0.field), 256), r1),
        (arrow.DecimalWidthRequest(r0.field, True), r1),
        (arrow.DecimalWidthRequest(r0.field, 64), r1),
        (arrow.DecimalWidthRequest(r0.field, 128), r1),
        (arrow.IntegerWidthRequest(r0.field, 64), r1),
    ):
        with pytest.raises(ResultError, match="ARROW_ADAPTATION"):
            arrow.bind_arrow(producer, decimal_widths=req)
    low = roots[target, 9, 2][3]
    assert arrow._decimal_widths(
        low, tuple(arrow.DecimalWidthRequest(f.field, 256) for f in low.fields)
    ) == (256, 256)


@pytest.mark.parametrize("bits,expected", ((128, 34), (256, 66)))
def test_decimal_charge_uses_checked_width(roots, bits, expected):
    producer = roots["postgres", 9, 2][3]
    requests = tuple(arrow.DecimalWidthRequest(f.field, bits) for f in producer.fields)
    bound = arrow.ArrowResultBinding(producer, None, decimal_widths=requests)
    assert arrow._base_charge(bound, 1, arrow.BatchLimits(bytes=expected)) == expected
    assert arrow._base_charge(bound, 0, arrow.BatchLimits(bytes=0)) == 0
    with pytest.raises(ResultError, match="LIMIT"):
        arrow._base_charge(bound, 1, arrow.BatchLimits(bytes=expected - 1))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_upstream_parameters_cannot_be_replaced_by_storage_domain_agreement(
    roots, target
):
    checked = roots[target, 9, 2][0]
    for p, s in ((8, 2), (9, 1), (66, 2), (9, 3)):
        result = emit_project_sql(checked, probe.decimal_input(target, p, s))
        assert result.status == "BLOCKED" and result.artifact is None
    bad = json.loads(probe.decimal_input(target, 9, 2))
    bad["sources"][0]["fields"][0]["representation"]["storage"]["extra"] = 0
    result = emit_project_sql(checked, json.dumps(bad).encode())
    assert result.status == "INPUT_REJECTED"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "declaration,pair,admitted",
    (
        ("Decimal(38, 0)", (38, 0), True),
        ("Decimal(39, 4)", (39, 4), True),
        ("Decimal(65, 30)", (65, 30), True),
        ("Decimal(38, 38)", (38, 38), False),
        ("Decimal(65, 31)", (65, 31), False),
        ("Decimal(65, 65)", (65, 65), False),
        ("Decimal(66, 0)", None, False),
        ("Decimal(0, 0)", None, False),
        ("Decimal(9, 12)", None, False),
        ("Decimal", None, False),
        ("Decimal()", None, False),
        ("Decimal(precision = 9, scale = 2)", None, False),
    ),
)
def test_shared_fact_and_producer_admission_are_distinct(
    tmp_path, target, declaration, pair, admitted
):
    from pietto._project.project_sql_emission_contract import (
        prepare_project_sql_emission,
        PreparedEmission,
    )

    source = probe.decimal_source(target, 38, 0).replace("Decimal(38, 0)", declaration)
    checked = probe.build_neutral(tmp_path / "source", {"main.pietto": source})
    raw = probe.decimal_input(target, *(pair or (38, 0)))
    prepared = prepare_project_sql_emission(checked, raw)
    assert isinstance(prepared, PreparedEmission)
    assert [
        None if f.decimal is None else (f.decimal.precision, f.decimal.scale)
        for f in prepared.sources[0].fields
    ] == [pair, pair]
    result = emit_project_sql(checked, raw)
    assert result.status == ("VERIFIED" if admitted else "BLOCKED")
    if not admitted:
        assert result.artifact is None
        assert [b.code for b in result.blockers] == [
            "PIE-B1004" if pair is None else "PIE-B1002"
        ] * 2


def test_existing_row_equivalence_uses_exact_high_precision_facts(tmp_path):
    from test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin import (
        _completed,
        _source,
        _entry,
    )
    from pietto._project.project_row_equivalence import compatible_row_types

    source = (
        _source("Decimal(39, 4)")
        .replace(
            "    hidden: Float nullable",
            "    same: Decimal(39, 4) not null\n    wider: Decimal(65, 4) nullable\n    scale: Decimal(39, 5) nullable",
        )
        .replace(
            "        value\n",
            "        value\n        same\n        wider\n        scale\n",
        )
    )
    result = _completed(tmp_path, source)
    assert result.ok and result.diagnostics == ()
    entry = _entry(result)
    distinct = entry.row_domain.distinct
    assert distinct is not None and distinct.equivalence.supported
    first, same, wider, scale = distinct.equivalence.evidence
    assert [
        (f.decimal.precision, f.decimal.scale)
        for f in (first, same, wider, scale)
        if f.decimal is not None
    ] == [(39, 4), (39, 4), (65, 4), (39, 5)]
    assert compatible_row_types(first, same)
    assert not compatible_row_types(first, wider) and not compatible_row_types(
        first, scale
    )
    assert all(
        e.selected is f
        for e, f in zip(distinct.equivalence.evidence, entry.fields, strict=True)
    )
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(first, decimal=wider.decimal)


@pytest.mark.parametrize("computed", (False, True))
def test_missing_or_computed_decimal_facts_stay_unavailable(tmp_path, computed):
    from test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin import (
        _completed,
        _source,
    )
    from pietto._project.project_final_outputs import (
        ProjectEffectiveOutputCompletionTerminal,
        ProjectDistinctUnsupported,
    )
    from pietto._project.project_row_equivalence import ProjectRowEquivalenceReason

    source = _source("Decimal(65, 30)" if computed else "Decimal")
    if computed:
        source = source.replace("        value\n", "        computed = value + value\n")
    result = _completed(tmp_path, source)
    assert [d.code for d in result.diagnostics] == ["PIE-S2339"]
    terminal = result.effective_outputs.entries[-1]
    assert isinstance(terminal, ProjectEffectiveOutputCompletionTerminal)
    assert isinstance(terminal.blocker, ProjectDistinctUnsupported)
    assert (
        terminal.blocker.equivalence.evidence[0].reason
        is ProjectRowEquivalenceReason.DECIMAL_PARAMETERS_MISSING
    )
