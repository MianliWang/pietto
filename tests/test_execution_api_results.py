"""Public result-schema export and bounded-consumption documentation."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

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


def _wide(directory, fields):
    """The documented query with `fields` selected columns."""
    project = api.write_example(directory)
    main = project / "main.pietto"
    head = main.read_text(encoding="utf-8").split("table active_items")[0]
    main.write_text(
        head
        + "table active_items:\n    from items\n    select:\n"
        + "".join(f"        v{i} = id\n" for i in range(fields)),
        encoding="utf-8",
    )
    return execution.compile_query(
        project,
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


def _refusal(action):
    with pytest.raises(execution.RequestRejected) as refused:
        action()
    return refused.value.code, refused.value.detail


WIDE_ACCESS: dict[str, Any] = dict(
    route="postgres_rows",
    access=execution.PostgresAccess("127.0.0.1", 9, "app", "reader", "pw"),
    premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
)


def test_a_result_wider_than_one_batch_is_refused_before_it_runs(tmp_path):
    """A batch holds at most 64 Arrow fields: a query whose result needs more
    is refused while it is prepared, before a workspace or connection."""
    fits = _wide(tmp_path / "fits", 64)
    handle = execution.execute(fits, **WIDE_ACCESS)
    assert handle.outcome.end == "NOT_STARTED"
    handle.close()
    wide = _wide(tmp_path / "wide", 65)
    assert _refusal(lambda: execution.execute(wide, **WIDE_ACCESS)) == (
        "PIE-R1004",
        "LIMIT",
    )
    # The width is checked before a premise that does not cover the source.
    premise = execution.PostgresDeploymentPremise(("public", "pg_catalog"))
    narrow = dict(WIDE_ACCESS, premise=premise)
    assert _refusal(lambda: execution.execute(fits, **narrow)) == (
        "PIE-R1002",
        "POSTGRES_DEPLOYMENT_PREMISE_SCOPE",
    )
    assert _refusal(lambda: execution.execute(wide, **narrow)) == (
        "PIE-R1004",
        "LIMIT",
    )
    # The workspace does not exist: opening it first would be PIE-R1009.
    workspace = execution.WorkspaceRef(str(tmp_path / "never"), "ws-" + "0" * 32)
    assert _refusal(
        lambda: execution.save(
            workspace, wide, operation="op-" + "0" * 32, **WIDE_ACCESS
        )
    ) == ("PIE-R1004", "LIMIT")


def test_a_collected_field_counts_each_child_field_against_the_batch(tmp_path):
    import _pietto_results_nested as nested
    import _pietto_results_product as product

    def query(fields):
        project = tmp_path / f"collect{fields}"
        children = tuple((f"c{k}", "Int8", False) for k in range(fields))
        output = nested.collected(product, project, children, alone=True)
        contract = output.artifact.request.accepted_bytes
        (project / "contract.json").write_bytes(contract)
        return execution.compile_query(
            project,
            module="main.pietto",
            kind="query",
            name="result",
            dialect="postgres",
            emission_contract="contract.json",
        )

    premise = execution.PostgresDeploymentPremise(("public", "pg_catalog"))
    arguments = dict(WIDE_ACCESS, premise=premise)
    # One list field and its 63 child fields: 64 Arrow fields fit a batch.
    handle = execution.execute(query(63), **arguments)
    assert handle.outcome.end == "NOT_STARTED"
    handle.close()
    # One list field and its 64 child fields: 65 Arrow fields.
    wide = query(64)
    assert _refusal(lambda: execution.execute(wide, **arguments)) == (
        "PIE-R1004",
        "LIMIT",
    )


def test_schema_failures_have_the_fixed_public_code():
    refusal = errors.schema_failure(ex.ExecutionError("ARROW_DEPENDENCY_VERSION"))
    assert (refusal.code, refusal.category, refusal.detail) == (
        "PIE-R4004",
        "SCHEMA_EXPORT",
        "ARROW_DEPENDENCY_VERSION",
    )
