"""Offline S02 control/store checks; no optional drivers or source DBs."""

import importlib.util
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "p68_recovery", ROOT / "scripts/phase68_recovery_premise.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
p = cast(Any, MODULE)


def test_actual_pipe_serialization_and_reap(tmp_path):
    result = p.child({"op": "echo", "value": "雪\n9007199254740993"}, tmp_path)
    assert result["data"] == {"value": "雪\n9007199254740993"}
    assert result["exit"] == 0 and result["reaped"]
    with pytest.raises(TimeoutError, match="control timeout"):
        p.child({"op": "stall"}, tmp_path, seconds=0.2)
    events = [
        json.loads(line)
        for line in (tmp_path / "children.jsonl").read_text().splitlines()
    ]
    assert events[-1]["event"] == "reaped" and events[-1]["exit"] is not None


def test_actual_store_crashes_sink_and_reopen(tmp_path):
    records = json.loads(json.dumps(p.run_store(tmp_path / "store")))
    cases = p.load("p68_cases", ROOT / "tests/_pietto_phase68_recovery_cases.py")
    cases.check_store(records)
    for key, mutate in (
        ("store_committed", lambda r: r["reopen"]["data"].update(frontier=0)),
        (
            "store_orphan",
            lambda r: r["producer"]["data"].update(events=["metadata_commit_returned"]),
        ),
        ("holes", lambda r: r["reopen"]["data"].update(ack_frontier=3)),
        (
            "isolation",
            lambda r: r["history"]["waiting"]["profile"].update(in_transaction=True),
        ),
    ):
        damaged = deepcopy(records)
        mutate(damaged[key])
        with pytest.raises(ValueError):
            cases.check_store(damaged)
    assert records["store_committed"]["reopen"]["data"]["frontier"] == 2
    for cut in ("partial", "fsync_failure", "orphan", "uncommitted"):
        assert records["store_" + cut]["reopen"]["data"]["frontier"] == 1
    assert records["holes"]["reopen"]["data"]["frontier"] == 1
    assert records["holes"]["reopen"]["data"]["ack_frontier"] == 1
    assert all("rejected" in r["data"] for r in records["store_guards"].values())
    assert all("rejected" in r["data"] for r in records["sink_guards"].values())
    assert records["isolation"]["history"]["reader_same_view"] == "active"
    assert records["isolation"]["history"]["reader_new_view"] == "complete"


def test_checker_rejects_submitted_operation_even_when_declared_values_match():
    cases = p.load("p68_cases", ROOT / "tests/_pietto_phase68_recovery_cases.py")
    query = {
        "sql": "SELECT $1",
        "options": {},
        "parameters": [{"kind": "int", "value": "2"}],
        "api_calls": [
            {
                "method": "execute",
                "sql": "SELECT $1",
                "values": [{"kind": "int", "value": "3"}],
            }
        ],
    }
    with pytest.raises(ValueError, match="actual submitted parameters"):
        cases.submission(query, "SELECT $1", [2], "postgres_rows")


def test_checked_chunk_refuses_changed_type_and_overlap(tmp_path):
    job = tmp_path / "job"
    b = p.binding()
    p.store.initialize(job, b)
    with pytest.raises(ValueError, match="invalid checked scalar row"):
        p.store.persist(job, b, [[1, 7, "text", 9007199254740993.0]])
    p.store.persist(job, b, [[1, 7, "same", 1], [2, 7, "same", 1]])
    with pytest.raises(ValueError, match="overlapping chunk"):
        p.store.persist(job, b, [[2, 7, "same", 1], [3, 7, "same", 1]])
    assert p.store.reopen(job, b)["frontier"] == 2
