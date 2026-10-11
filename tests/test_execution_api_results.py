"""Public result-schema export and bounded-consumption documentation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import _pietto_execution_api as api
import pietto.execution as execution
from pietto._project import project_arrow_result as arrow
from pietto._project import project_execution as ex
from pietto._project import project_execution_reader as reader
from pietto._project import project_public_execution as composition
from pietto.execution import _errors as errors


def _handle():
    handle = object.__new__(execution.ResultHandle)
    handle._owner = SimpleNamespace(attempt="result-schema-attempt")
    handle._route = "postgres_rows"
    handle._finalizer = None
    handle._recorded = None
    return handle


def test_a_schema_export_does_not_open_or_consume_the_attempt(monkeypatch):
    handle = _handle()
    calls = []

    class Schema:
        def __arrow_c_schema__(self):
            calls.append("capsule")
            return "schema-capsule"

    monkeypatch.setattr(composition, "result_schema", lambda owner: Schema())
    assert handle.__arrow_c_schema__() == "schema-capsule"
    assert calls == ["capsule"]


def test_a_schema_export_failure_is_unchained_handle_misuse(monkeypatch):
    handle = _handle()

    def missing(owner):
        raise ex.ExecutionError("EXECUTION_DEPENDENCY_MISSING")

    monkeypatch.setattr(composition, "result_schema", missing)
    with pytest.raises(execution.HandleMisuse) as raised:
        handle.__arrow_c_schema__()
    assert (raised.value.code, raised.value.detail, raised.value.attempt) == (
        "PIE-R4004",
        "EXECUTION_DEPENDENCY_MISSING",
        "result-schema-attempt",
    )
    assert raised.value.__cause__ is None and raised.value.__context__ is None


def test_the_schema_path_reuses_the_stored_output_and_arrow_owners(monkeypatch):
    output, route, producer, schema = object(), "postgres_rows", object(), object()
    owner = SimpleNamespace(request=SimpleNamespace(output=output, route=route))
    calls = []
    monkeypatch.setattr(arrow, "pinned", lambda: calls.append("pinned"))
    monkeypatch.setattr(
        reader,
        "bind_stored_output",
        lambda actual_output, actual_route: (
            calls.append((actual_output, actual_route)) or producer
        ),
    )
    monkeypatch.setattr(
        arrow,
        "bind_arrow",
        lambda actual_producer: (
            calls.append(actual_producer) or SimpleNamespace(schema=schema)
        ),
    )
    assert composition.result_schema(owner) is schema
    assert calls == ["pinned", (output, route), producer]


def test_pinned_arrow_uses_the_existing_pinned_module_bridge(monkeypatch):
    calls = []
    package = object()

    def pinned_modules(pins, code):
        calls.append((pins, code))
        return [package]

    monkeypatch.setattr(ex, "pinned_modules", pinned_modules)
    assert arrow.pinned() is package
    assert calls == [((arrow.PYARROW,), "ARROW_DEPENDENCY_VERSION")]


def test_schema_export_is_the_only_new_handle_arrow_surface():
    assert "__arrow_c_schema__" in vars(execution.ResultHandle)
    assert (
        not {
            "__arrow_c_array__",
            "__arrow_c_stream__",
            "fetchall",
            "read_all",
            "to_pandas",
            "to_table",
        }
        & vars(execution.ResultHandle).keys()
    )


def test_results_documentation_has_the_consumption_script_and_output(tmp_path):
    blocks = api.results_blocks()
    assert "pa.schema(result)" in blocks["python"]
    assert blocks["text"].splitlines() == [
        "id: int64 not null",
        "label: string not null",
        "COMPLETE 4 [2, 2, 3, 5]",
        "PIE-R3004 FAILED 2",
    ]
    api.write_example(tmp_path)
    assert (tmp_path / "consume_query.py").read_text(encoding="utf-8") == blocks[
        "python"
    ]


def test_schema_failures_have_the_fixed_public_code():
    refusal = errors.schema_failure(ex.ExecutionError("ARROW_DEPENDENCY_VERSION"))
    assert (refusal.code, refusal.category, refusal.detail) == (
        "PIE-R4004",
        "SCHEMA_EXPORT",
        "ARROW_DEPENDENCY_VERSION",
    )
