"""Pure checks for the separately invoked native AVG(Int) witness runner."""

from types import SimpleNamespace
import json

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
