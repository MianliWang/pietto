"""Old-flat regression harness: comparator sensitivity and a bounded real run."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import _pietto_harness_flat_regression as harness

# Child processes over the checkout only: no storage, native, Arrow, Git or package premise.
pytestmark = pytest.mark.ci_workload("general-runtime")

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "_pietto_harness_flat_regression.py"
READ_BY_HARNESS = ("src/pietto", "tests/fixtures", "examples")
READ_FILES = (
    "README.md",
    "docs/language.md",
    "docs/style.md",
    "tests/_pietto_sql_emission.py",
    "tests/_pietto_project_explain_differential_probe.py",
    "tests/_pietto_project_explain_scenarios.py",
)


def _record(stdout: str = "", stderr: str = "", exit_code: int = 0) -> dict:
    return {"exit": exit_code, "stdout": {"text": stdout}, "stderr": {"text": stderr}}


def _check_json(code: str, message: str, suggestion: str | None = None, **extra) -> str:
    diagnostic = {
        "code": code,
        "severity": "error",
        "message": message,
        "location": {"path": "a.pietto", "line": 2, "column": 5},
        "suggestion": suggestion,
        **extra,
    }
    return json.dumps({"ok": False, "diagnostics": [diagnostic]}) + "\n"


def test_classification_is_byte_strict_except_for_approved_message_text():
    approved = frozenset({"PIE-P1000"})
    sql = _record('{"sql": "SELECT 1"}\n')
    assert harness.classify(sql, sql, approved)[0] == "IDENTICAL"
    assert (
        harness.classify(sql, _record('{"sql": "SELECT  1"}\n'), approved)[0] == "DRIFT"
    )
    base = _record(_check_json("PIE-P1000", "expected one of: a"), exit_code=1)
    reworded = _record(
        _check_json("PIE-P1000", "expected one of: a, b", "Write b."), exit_code=1
    )
    assert harness.classify(base, reworded, approved)[0] == "APPROVED_MESSAGE_DELTA"
    assert harness.classify(base, reworded, frozenset())[0] == "DRIFT"
    other = _record(_check_json("PIE-S2301", "Unknown relation: x"), exit_code=1)
    other_reworded = _record(_check_json("PIE-S2301", "Unknown table: x"), exit_code=1)
    assert harness.classify(other, other_reworded, approved)[0] == "DRIFT"
    recoded = _record(_check_json("PIE-P1001", "expected one of: a"), exit_code=1)
    assert harness.classify(base, recoded, approved)[0] == "DRIFT"
    moved = _record(
        _check_json("PIE-P1000", "expected one of: a").replace(
            '"line": 2', '"line": 3'
        ),
        exit_code=1,
    )
    assert harness.classify(base, moved, approved)[0] == "DRIFT"
    with_sql = _record(_check_json("PIE-P1000", "m", sql="SELECT 1"))
    sql_changed = _record(_check_json("PIE-P1000", "n", sql="SELECT 2"))
    assert harness.classify(with_sql, sql_changed, approved)[0] == "DRIFT"
    exit_changed = dict(reworded, exit=2)
    assert harness.classify(base, exit_changed, approved)[0] == "DRIFT"


def test_text_lines_may_differ_only_for_approved_codes():
    approved = frozenset({"PIE-S2103"})
    base = _record("a.pietto:2:5 PIE-S2103 error: Old text\nOK\n", exit_code=1)
    hinted = _record("a.pietto:2:5 PIE-S2103 error: Old text. Hint\nOK\n", exit_code=1)
    assert harness.classify(base, hinted, approved)[0] == "APPROVED_MESSAGE_DELTA"
    for changed in (
        "a.pietto:2:6 PIE-S2103 error: Old text. Hint\nOK\n",  # location
        "a.pietto:2:5 PIE-S2104 error: Old text\nOK\n",  # code
        "a.pietto:2:5 PIE-S2103 error: Old text\nOK!\n",  # another line
        "a.pietto:2:5 PIE-S2103 error: Old text\n",  # a line fewer
    ):
        verdict, detail = harness.classify(
            base, _record(changed, exit_code=1), approved
        )
        assert verdict == "DRIFT" and detail["first_difference"], changed


def test_allow_entries_must_name_actual_differences():
    records = [
        {"class": "DRIFT", "input": "file:a", "argv": ["check", "a"]},
        {"class": "IDENTICAL", "input": "file:b", "argv": ["check", "b"]},
        *harness.compare_frozen({"x": "1", "y": "2"}, {"x": "1", "y": "3", "z": "4"}),
    ]
    stale = harness.apply_allow(
        records,
        [
            {"input": "file:a", "argv": ["check", "a"], "decision": "D71.01"},
            {"input": "file:b", "argv": ["check", "b"], "decision": "D71.01"},
            {"path": "y", "decision": "D71.06"},
        ],
    )
    assert [r["class"] for r in records] == [
        "ALLOWED",
        "IDENTICAL",
        "IDENTICAL",
        "ALLOWED",
        "ADDED",
    ]
    assert [entry["allow"]["input"] for entry in stale] == ["file:b"]
    assert harness.compare_frozen({"x": "1"}, {})[0]["class"] == "DRIFT"
    with pytest.raises(SystemExit):
        harness.apply_allow(records, [{"path": "y"}])


def _tree_digest() -> str:
    digest = hashlib.sha256()
    paths = [ROOT / name for name in READ_FILES]
    for name in READ_BY_HARNESS:
        paths += sorted((ROOT / name).rglob("*"))
    for path in paths:
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _run(tmp_path: Path, name: str, *extra: str) -> tuple[int, dict, bytes]:
    no_tools = tmp_path / "empty-path"
    no_tools.mkdir(exist_ok=True)
    env = {**os.environ, "PATH": str(no_tools), "PYTHONDONTWRITEBYTECODE": "1"}
    report = tmp_path / f"{name}.json"
    done = subprocess.run(
        [
            sys.executable,
            "-P",
            str(HARNESS),
            "--baseline",
            str(ROOT),
            "--candidate",
            str(ROOT),
            "--baseline-id",
            "same",
            "--candidate-id",
            "same",
            "--scratch",
            str(tmp_path / name),
            "--report",
            str(report),
            "--limit",
            "4",
            *extra,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        timeout=300,
        check=False,
    )
    assert done.stderr == b"", done.stderr
    data = report.read_bytes()
    return done.returncode, json.loads(data), data


def test_bounded_self_comparison_is_identical_deterministic_and_read_only(tmp_path):
    before = _tree_digest()
    code, first, first_bytes = _run(tmp_path, "first")
    assert code == 0 and first["ok"]
    assert first["inputs"] == {"docs": 1, "explain": 1, "files": 1, "projects": 1}
    assert first["commands"] == 16 and first["differences"] == []
    assert first["counts"]["IDENTICAL"] == 16 + first["frozen_files"]
    assert first_bytes == (json.dumps(first, indent=1, sort_keys=True) + "\n").encode()
    plan = json.loads((tmp_path / "first" / "plan.json").read_text())
    records = json.loads((tmp_path / "first" / "candidate.json").read_text())
    explained = [
        (item["input"], json.loads(record["stdout"]["text"]))
        for item, record in zip(plan, records, strict=True)
        if item["argv"][0] == "explain" and "json" in item["argv"]
    ]
    # Explain runs only on its v4 scenarios, and they reach real explain output.
    assert [(name, doc["ok"], doc["diagnostics"]) for name, doc in explained] == [
        ("explain:matrix", True, [])
    ]
    allow = tmp_path / "allow.json"
    entry = {"path": "absent.pietto", "decision": "D71.01"}
    allow.write_text(json.dumps([entry]))
    code, second, second_bytes = _run(tmp_path, "second", "--allow", str(allow))
    assert code == 1 and not second["ok"]
    assert second["counts"] == {**first["counts"], "STALE": 1}
    assert second["differences"] == [{"class": "STALE", "allow": entry}]
    assert {**second, "counts": first["counts"], "differences": [], "ok": True} == first
    assert (
        second_bytes == (json.dumps(second, indent=1, sort_keys=True) + "\n").encode()
    )
    assert _tree_digest() == before
    with pytest.raises(SystemExit):
        harness.main(
            ["--baseline", str(ROOT), "--candidate", str(ROOT), "--baseline-id", "x"]
            + ["--candidate-id", "x", "--scratch", str(ROOT / "tests" / "scratch")]
            + ["--report", str(tmp_path / "r.json")]
        )
    assert not (ROOT / "tests" / "scratch").exists()
