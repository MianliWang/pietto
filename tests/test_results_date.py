"""Date result carriers remain derived, exact, and Arrow-lazy."""

from datetime import date, datetime
import json
from types import SimpleNamespace

import pytest

import _pietto_results_product as probe
from pietto._project import project_arrow_result as arrow
from pietto._project import project_result_binding as binding
from pietto._project import project_result_contract as contract
from pietto._project import project_scalar_meaning as meaning
from pietto._project.project_execution_reader import check_native_column
from pietto._project.project_result_output import prepare_output
from pietto._project.project_result_contract_correspondence import verify_bound_export
from pietto._project.project_result_contract_portable import export_result_contract
from pietto._project.project_sql_emission import emit_project_sql


def _source(target):
    return f"""shape Row:
    occurred_at: Timestamp | None
source rows: Row = {target}.table("opaque.result.fixture")
table result:
    from rows
    select:
        event_date = date_of(occurred_at)
"""


def _input(target):
    document = json.loads(probe.temporal_input(target))
    (field,) = document["sources"][0]["fields"][:1]
    field.update(name="occurred_at", column="occurred_at")
    field["representation"]["nullable"] = True
    document["sources"][0]["fields"] = [field]
    return json.dumps(document).encode()


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_derived_date_result_uses_exact_carrier_and_lazy_date32(tmp_path, target):
    checked = probe.build_neutral(tmp_path / target, {"main.pietto": _source(target)})
    scalar_meaning = meaning.acquire_scalar_meaning(checked)
    outcome = emit_project_sql(checked, _input(target), scalar_meaning=scalar_meaning)
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    output = prepare_output(outcome.artifact)
    assert [field.shape.canonical.name for field in output.contract.shape.fields] == [
        "Date"
    ]
    assert output.contract.shape.fields[0].meaning is None
    exported = export_result_contract(output.contract, checked)
    assert exported.view.document["fields"][0]["canonical"]["name"] == "Date"
    verify_bound_export(exported, checked)
    producer = binding.bind_producer(
        output.contract,
        outcome.artifact,
        (
            binding.ProducerObservation(
                0,
                "event_date",
                target,
                "pg_date" if target == "postgres" else "my_date",
                domain="date",
                carrier="date",
            ),
        ),
        output=output,
    )
    assert arrow._value(None, producer.fields[0]) is None
    fake_arrow = type("Arrow", (), {"date32": staticmethod(lambda: "date32[day]")})
    assert (
        arrow._arrow_type(fake_arrow, producer.fields[0], None, None, None, None)
        == "date32[day]"
    )
    assert arrow._value(date(1000, 1, 1), producer.fields[0]) == date(1000, 1, 1)
    assert arrow._value(date(9999, 12, 31), producer.fields[0]) == date(9999, 12, 31)

    class DateSubclass(date):
        pass

    for value in (
        DateSubclass(2026, 10, 13),
        datetime(2026, 10, 13),
        "2026-10-13",
        0,
    ):
        with pytest.raises(contract.ResultError, match="VALUE_DOMAIN"):
            arrow._value(value, producer.fields[0])
    real = output.columns[0].realization
    if target == "postgres":
        assert (
            check_native_column(
                real,
                "postgres_rows",
                SimpleNamespace(name="event_date", type_code=1082, null_ok=True),
                label="event_date",
                ordinal=0,
                source_field=output.columns[0].source_field,
            )
            is True
        )
        assert (
            check_native_column(
                real,
                "postgres_adbc",
                {
                    "ordinal": 0,
                    "name": "event_date",
                    "type": "date32[day]",
                    "metadata": {b"ADBC:postgresql:typname".hex(): b"date".hex()},
                    "nullable": True,
                },
                label="event_date",
                ordinal=0,
                source_field=output.columns[0].source_field,
            )
            is True
        )
        assert (
            check_native_column(
                real,
                "postgres_adbc",
                {
                    "ordinal": 0,
                    "name": "event_date",
                    "type": "date32[day]",
                    "metadata": {},
                    "nullable": True,
                },
                label="event_date",
                ordinal=0,
                source_field=output.columns[0].source_field,
            )
            is True
        )
        with pytest.raises(contract.ResultError, match="EXECUTION_METADATA"):
            check_native_column(
                real,
                "postgres_adbc",
                {
                    "ordinal": 0,
                    "name": "event_date",
                    "type": "date32[day]",
                    "metadata": {b"ADBC:postgresql:typname".hex(): b"timestamp".hex()},
                    "nullable": True,
                },
                label="event_date",
                ordinal=0,
                source_field=output.columns[0].source_field,
            )
    else:
        assert (
            check_native_column(
                real,
                "mysql_rows",
                ("event_date", 10, None, None, None, None, 1, 0, 63),
                label="event_date",
                ordinal=0,
                source_field=output.columns[0].source_field,
            )
            is True
        )
    with pytest.raises(contract.ResultError, match="ARROW_DEPENDENCY_MISSING"):
        arrow.bind_arrow(producer)
