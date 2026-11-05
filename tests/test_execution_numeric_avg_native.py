"""Pure checks for the separately invoked native AVG(Int) witness runner."""

from types import SimpleNamespace
import json
import math
import statistics

import pytest

import _pietto_execution_numeric_avg_native as witness


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_avg_int_witness_sql_casts_the_input_and_not_the_aggregate(target):
    statement = witness.sql(target)[3]
    assert "AVG(CAST(" in statement
    assert "CAST(AVG(" not in statement


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("name, _values, expected", witness.CASES)
def test_avg_int_witness_checks_each_carrier_and_value(target, name, _values, expected):
    carrier = 701 if target == "postgres" else 5
    description = (
        (SimpleNamespace(type_code=carrier),)
        if target == "postgres"
        else ((None, carrier),)
    )
    rows = ((expected,),)
    observed = witness.validate_case(target, name, expected, rows, description)
    assert observed["carrier"] == carrier


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_avg_int_witness_refuses_the_wrong_native_carrier(target):
    description = (
        (SimpleNamespace(type_code=20),) if target == "postgres" else ((None, 8),)
    )
    with pytest.raises(ValueError, match="carrier"):
        witness.validate_case(target, "wrong", 1.0, ((1.0,),), description)


def test_avg_int_witness_does_not_accept_failed_resource_cleanup(tmp_path, monkeypatch):
    resource = SimpleNamespace(
        manager=None,
        acquire=lambda: None,
        role_statements=lambda: (),
        connect=lambda **_: None,
        cleanup=lambda: {"status": "failed", "failures": ["container remains"]},
    )
    monkeypatch.setattr(witness, "Resources", lambda *_: resource)
    monkeypatch.setattr(witness, "CASES", ())
    monkeypatch.setattr(witness, "_run", lambda *_: None)
    directory = tmp_path / "native"

    with pytest.raises(RuntimeError, match="resource cleanup failed"):
        witness.run("postgres", directory)

    report = json.loads((directory / "report.json").read_text())
    assert report["status"] == "FAILED"
    assert report["cleanup"]["failures"] == ["container remains"]


_STDDEV = {(name, tag): values for name, tag, values in witness.STDDEV_CASES}


@pytest.mark.parametrize("name, tag, values", witness.STDDEV_CASES)
def test_stddev_tolerance_passes_the_oracle_and_refuses_a_null_mismatch(
    name, tag, values
):
    if name == "O2":
        with pytest.raises(ValueError, match="unrepresentable"):
            witness.tolerance(tag, values, 1.0)
        return
    oracle = witness.stddev_oracle(values)
    assert witness.tolerance(tag, values, oracle) == 0.0
    with pytest.raises(ValueError, match="NULL mismatch"):
        witness.tolerance(tag, values, 1.0 if oracle is None else None)


@pytest.mark.parametrize("observed", (-1.0, math.inf, math.nan))
def test_stddev_tolerance_refuses_a_negative_or_non_finite_value(observed):
    with pytest.raises(ValueError, match="finite non-negative"):
        witness.tolerance("Float", _STDDEV["N2", "Float"], observed)


def test_stddev_tolerance_has_the_two_tiers():
    """Within the Int tier 2*eps*s passes and twice it fails; IS is exact."""
    values = _STDDEV["IS", "Int"]
    oracle = witness.stddev_oracle(values)
    assert oracle is not None and oracle == 70710678.11865476
    step = 2 * witness.EPSILON * oracle
    # oracle + step rounds to the nearest binary64, a little below the tier.
    assert 0.9 < witness.tolerance("Int", values, oracle + step) <= 1
    assert witness.tolerance("Int", values, oracle + 2 * step) > 1
    # Equal Int values deviate by exactly 0, so any other value fails.
    assert witness.tolerance("Int", _STDDEV["R3", "Int"], 1e-300) == math.inf


@pytest.mark.parametrize(
    "name, tag, discriminates",
    (
        ("M8", "Int", True),
        ("N2", "Int", True),
        ("F1", "Float", True),
        ("IN", "Int", True),
        # FN is an accuracy cell only: its population deviation is inside B.
        ("FN", "Float", False),
    ),
)
def test_stddev_tolerance_tells_the_population_deviation_apart(
    name, tag, discriminates
):
    values = _STDDEV[name, tag]
    population = statistics.pstdev([value for value in values if value is not None])
    assert (witness.tolerance(tag, values, population) > 1) is discriminates
