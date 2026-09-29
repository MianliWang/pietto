"""Offline S03 control and observation checker, with no driver or DB discovery."""

import importlib.util
from pathlib import Path
import sys
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "s03_entry", ROOT / "scripts/phase68_slice3_probe.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
p = cast(Any, MODULE).load_probe()
c = p.load("s03_cases", ROOT / "tests/_pietto_phase68_slice3_cases.py")


def test_actual_s03_pipe_serializer_timeout_and_reap(tmp_path):
    result = p.child({"op": "echo", "value": "雪\nS03"}, tmp_path)
    assert (
        result["data"] == {"value": "雪\nS03"}
        and result["reaped"]
        and result["exit"] == 0
    )
    with pytest.raises(TimeoutError, match="control timeout"):
        p.child({"op": "stall"}, tmp_path, seconds=0.2)
    import json

    journal = [
        json.loads(s)
        for s in (tmp_path / (p.PREFIX + "children.jsonl")).read_text().splitlines()
    ]
    assert journal[-1]["event"] == "reaped" and journal[-1]["exit"] is not None


def test_actual_operation_drift_is_not_a_report_pass():
    query = {
        "parameters": [],
        "api_calls": [{"method": "execute", "sql": "SELECT 2", "values": []}],
        "sql": "SELECT 1",
    }
    with pytest.raises(ValueError, match="actual native SQL"):
        c.check_query(query, "postgres_rows")
