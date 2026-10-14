"""Private MySQL packet premise for verified growing Text expressions."""

from types import SimpleNamespace

import pytest

from pietto._project.project_execution import ExecutionError
from pietto._project.project_execution_mysql_context import (
    native_context,
    verify_mysql_text_packet_capacity,
)
from pietto._project.project_sql_emission_rows import Realization, SQLOperation
from pietto.ir.model import SymbolId, SymbolNamespace


def _owner(capacity=None):
    access = SimpleNamespace(account="reader@%", roles="NONE", database="phase66")
    request = SimpleNamespace(
        access=access,
        artifact=SimpleNamespace(
            request=SimpleNamespace(release="8.4.12"), ast=object()
        ),
        isolation="stable",
    )
    return SimpleNamespace(
        request=request,
        session_id=7,
        _mysql_packet_capacity=capacity,
        _mysql_text_packet_requirements=None,
    )


def _context(capacity):
    return (
        "8.4.12",
        "reader@%",
        "NONE",
        7,
        "phase66",
        "REPEATABLE-READ",
        "utf8mb4",
        "utf8mb4",
        "utf8mb4",
        "utf8mb4_0900_bin",
        "ONLY_FULL_GROUP_BY,STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION",
        "+00:00",
        0,
        1000,
        "server-a",
        capacity,
    )


def test_native_context_binds_packet_capacity_and_rejects_retry_mutation(monkeypatch):
    from pietto._project import project_execution_mysql_context as context

    owner = _owner()
    row = _context(64)
    monkeypatch.setattr(context, "read_control", lambda *_: ((), (row,)))
    assert native_context(owner) == row[:15]
    assert owner._mysql_packet_capacity == 64

    changed = _context(63)
    monkeypatch.setattr(context, "read_control", lambda *_: ((), (changed,)))
    with pytest.raises(ExecutionError, match="MYSQL_PACKET_CAPACITY_CHANGED"):
        native_context(owner)


def test_packet_premise_rejects_tiny_capacity_and_retains_exact_operation_identity(
    monkeypatch,
):
    from pietto._project import project_sql_emission_ast as ast

    operation_ref = object()
    original = SimpleNamespace(
        ref=operation_ref,
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "upper"),
    )
    operation = SQLOperation(
        original,
        "scalar_call",
        (),
        Realization(
            "Text",
            {"kind": "my_varchar", "length": 2},
            False,
            {
                "kind": "text",
                "max_characters": 2,
                "encoding": "utf8mb4",
                "collation": "utf8mb4_0900_bin",
                "padding": "NO PAD",
            },
        ),
    )
    monkeypatch.setattr(ast, "row_value_roots", lambda _: (operation,))
    owner = _owner(capacity=7)
    with pytest.raises(ExecutionError, match="MYSQL_TEXT_PACKET_CAPACITY"):
        verify_mysql_text_packet_capacity(owner)

    owner._mysql_packet_capacity = 8
    verify_mysql_text_packet_capacity(owner)
    assert owner._mysql_text_packet_requirements == ((operation_ref, 8),)

    changed = SQLOperation(
        SimpleNamespace(
            ref=object(),
            callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "upper"),
        ),
        "scalar_call",
        (),
        operation.realization,
    )
    monkeypatch.setattr(ast, "row_value_roots", lambda _: (changed,))
    with pytest.raises(ExecutionError, match="MYSQL_TEXT_PACKET_IDENTITY"):
        verify_mysql_text_packet_capacity(owner)
