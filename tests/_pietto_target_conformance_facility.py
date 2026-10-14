"""Offline fixture/observer/receipt controls; these tests never run a database."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import _pietto_target_conformance as facility
import _pietto_target_conformance_resources as resources


class InjectedServerError(Exception):
    sqlstate = "22012"
    errno = None


class FakeCursor:
    def __init__(self, connection: Any, fault: str = ""):
        self.connection, self.fault = connection, fault
        self.description: Any = [("id", 20, None, 8, None, None, None)]
        self.remaining = [[(1,)]]
        self.fetches = 0
        self.calls: list[tuple[str, Any]] = []

    def execute(self, sql: str, parameters: Any = None) -> None:
        self.calls.append((sql, parameters))
        if sql == "BEGIN":
            self.connection.info.transaction_status = 2
            self.description = None
        elif sql == "SELECT 1/0":
            self.connection.info.transaction_status = 3
            raise InjectedServerError("division by zero")
        elif sql == "SELECT 2 AS v":
            self.remaining = [[(2,)]]
        if self.fault == "metadata":
            self.description = None
        if self.fault == "timeout":
            raise TimeoutError("injected deadline")

    def fetchmany(self, size: int) -> list[tuple[int]]:
        self.fetches += 1
        if self.fault == "late_fetch" and self.fetches == 2:
            raise RuntimeError("injected late fetch")
        return self.remaining.pop(0) if self.remaining else []

    def close(self) -> None:
        if self.fault in {"close", "primary_close"}:
            raise RuntimeError("injected close")


class FakeConnection:
    def __init__(self, fault: str = ""):
        self.fault = fault
        self.info = SimpleNamespace(backend_pid=41, transaction_status=0)
        self.last: FakeCursor | None = None

    def add_notice_handler(self, callback: Any) -> None:
        self.callback = callback

    def cursor(self, **kwargs: Any) -> FakeCursor:
        self.last = FakeCursor(self, self.fault)
        return self.last

    def rollback(self) -> None:
        if self.fault == "recovery":
            raise RuntimeError("injected rollback failure")
        self.info.transaction_status = 0

    def close(self) -> None:
        if self.fault == "connection_close":
            raise RuntimeError("injected connection close")


class FakeResources(resources.Resources):
    fail_stop = False
    foreign = False

    def __init__(self, target: str, pin: dict[str, Any], directory: Path):
        super().__init__(target, pin, directory)
        self.container_id, self.network_id = "a" * 64, "b" * 64
        self.runtime_image_id = pin["platform_digest"]
        self.live = {"container": True, "network": True}
        self.commands: list[tuple[str, ...]] = []
        self.event("network_acquired", id=self.network_id)
        self.event("container_acquired", id=self.container_id)

    def inspect_resource(
        self, kind: str, reference: str, *, timeout: float = 30
    ) -> dict[str, Any]:
        return {
            "id": reference,
            "name": self.name if kind == "container" else self.network_name,
            "image": self.runtime_image_id,
            "labels": {
                "pietto.phase66.invocation": "foreign" if self.foreign else self.nonce
            },
        }

    def docker(
        self, *args: str, timeout: float = 30, extra_env: dict[str, str] | None = None
    ) -> str:
        self.commands.append(args)
        if args[:2] == ("container", "stop") and self.fail_stop:
            raise RuntimeError("injected stop failure")
        if args[1] == "rm":
            self.live[args[0]] = False
        if args[1] == "ls":
            return ""
        return "owned"

    def acquire(self) -> None:
        raise RuntimeError("injected setup failure after acquisition")


def _injected_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    pins, pins_digest = facility.load_pins(facility.PINS)
    monkeypatch.setattr(
        facility,
        "sys",
        SimpleNamespace(
            implementation=SimpleNamespace(name="cpython"), version_info=(3, 13)
        ),
    )
    args = argparse.Namespace(
        target="postgres",
        evidence_dir=tmp_path / "run",
        case=None,
        expected_commit=None,
        run_id="injected",
        run_attempt=1,
    )
    assert facility.run_target(args, pins, pins_digest) == 1
    receipt, _ = facility.read_json(
        args.evidence_dir / "phase66-postgres-injected-1.json"
    )
    return receipt
