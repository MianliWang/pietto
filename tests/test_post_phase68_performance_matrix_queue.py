"""The S19 matrix's shared claim queue (an R2-first walk, each declaration claimed
exactly once) and the narrowed S14 no-basis law. Pure; no database or Arrow."""

from __future__ import annotations

import threading
from typing import Any

import pytest

import _pietto_phase68_slice10_probe as s10
import _pietto_phase68_slice14_probe as s14
from _pietto_phase68_slice14_check import check_capture
from _pietto_phase68_slice19_probe import claim, queue_work
from _pietto_phase68_slice7_cases import manifest as guard_manifest


def _key(cell):
    return (cell["group"], cell["case"], cell["variant"])


def _admitted(target):
    return {_key(c) for c in s14.r2_families(target)}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_the_walk_is_r2_first_and_each_class_keeps_manifest_order(target):
    declarations = s10.native_manifest(target)
    admitted = _admitted(target)
    walk = queue_work(declarations, admitted, joint=False)
    assert sorted(i for i, _ in walk) == list(range(len(declarations)))
    assert all(declarations[i] is cell for i, cell in walk)
    r2 = sum(_key(cell) in admitted for cell in declarations)
    assert r2 == len(admitted)
    assert [_key(cell) in admitted for _, cell in walk] == [True] * r2 + [False] * (
        len(declarations) - r2
    )
    for walked in (walk[:r2], walk[r2:]):
        assert [i for i, _ in walked] == sorted(i for i, _ in walked)
    assert queue_work(declarations, admitted, joint=True) == walk[:r2]


def test_concurrent_parts_claim_each_declaration_exactly_once(tmp_path):
    declarations = s10.native_manifest("postgres")
    admitted = _admitted("postgres")
    parts = 5
    start = threading.Barrier(parts)
    taken: list[list[int]] = [[] for _ in range(parts)]

    def part(n):
        start.wait()
        for index, _cell in queue_work(declarations, admitted, joint=n == 0):
            if claim(tmp_path, "postgres", index):
                taken[n].append(index)

    threads = [threading.Thread(target=part, args=(n,)) for n in range(parts)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(i for t in taken for i in t) == list(range(len(declarations)))
    assert all(_key(declarations[i]) in admitted for i in taken[0])
    assert not any(claim(tmp_path, "postgres", i) for i in range(len(declarations)))
    assert claim(tmp_path, "mysql", 0)
    with pytest.raises(FileNotFoundError):
        claim(tmp_path / "missing", "postgres", 0)


def _no_basis() -> tuple[dict[str, Any], dict, dict]:
    """The fields the no-basis law reads, as the S19 campaign04 raw holds them
    for the designated guard refusal (eight admission-phase, four guard-phase)."""
    cell = next(
        c
        for c in s10.native_manifest("postgres")
        if c["case"] == "refined_violation_outside_page"
    )
    case = next(c for c in guard_manifest() if c["name"] == cell["case"])
    record = {
        "s14": None,
        "failure": {
            "kind": "ValueError",
            "category": "SINGLE_MATCH_VIOLATED",
            "message": "SINGLE_MATCH_VIOLATED",
            "sqlstate": None,
        },
        "guard_states": ["VIOLATED"],
        "rows": [],
        "post_close_rows": [],
        "outcome": {
            "transaction": "ROLLBACK_ACK",
            "delivery": "FAILED",
            "rows": 0,
            "batches": 0,
            "bytes": 0,
            "primary": {"phase": "admission", "kind": "ValueError"},
            "cleanup_failures": [],
        },
    }
    return record, cell, case


@pytest.mark.parametrize("phase", ("admission", "guard"))
def test_the_designated_guard_refusal_has_no_basis(phase):
    record, cell, case = _no_basis()
    record["outcome"]["primary"]["phase"] = phase
    check_capture(record, cell, case)


@pytest.mark.parametrize(
    "damage",
    (
        lambda r, c: r["failure"].update(category="QUERY_TIMEOUT"),
        lambda r, c: r["failure"].update(message="QUERY_TIMEOUT"),
        lambda r, c: r["failure"].update(kind="OperationalError"),
        lambda r, c: r.update(failure=None),
        lambda r, c: r.update(guard_states=["FULFILLED"]),
        lambda r, c: r["rows"].append([1]),
        lambda r, c: r["post_close_rows"].append([1]),
        lambda r, c: r["outcome"].update(rows=1),
        lambda r, c: r["outcome"].update(batches=1),
        lambda r, c: r["outcome"].update(bytes=8),
        lambda r, c: r["outcome"].update(transaction="COMMIT_ACK"),
        lambda r, c: r["outcome"].update(delivery="COMPLETE"),
        lambda r, c: r["outcome"]["primary"].update(phase="fetch"),
        lambda r, c: r["outcome"]["primary"].update(kind="OperationalError"),
        lambda r, c: r["outcome"].update(cleanup_failures=["close"]),
        lambda r, c: c.update(case="refined_pages"),
    ),
    ids=(
        "unrelated_category",
        "unrelated_message",
        "other_kind",
        "no_failure",
        "guard_fulfilled",
        "rows_captured",
        "post_close_rows",
        "outcome_rows",
        "outcome_batches",
        "outcome_bytes",
        "committed",
        "delivered",
        "other_phase",
        "other_primary",
        "cleanup_failed",
        "other_case",
    ),
)
def test_a_substituted_failure_is_not_a_guard_refusal(damage):
    record, cell, case = _no_basis()
    cell = dict(cell)
    damage(record, cell)
    with pytest.raises(AssertionError, match="S14_CHECK_CAPTURE_WITHOUT_BASIS"):
        check_capture(record, cell, case)


def test_a_cell_without_its_guard_case_is_not_a_guard_refusal():
    record, cell, _case = _no_basis()
    with pytest.raises(AssertionError, match="S14_CHECK_CAPTURE_WITHOUT_BASIS"):
        check_capture(record, cell, None)


def _write_report(directory, name, report):
    import json

    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(report))


@pytest.mark.parametrize(
    "damage",
    (
        {"source_cleanup": {"status": "failed"}},
        {"status": "FAILED"},
    ),
    ids=("leaked_database", "unfinished_part"),
)
def test_a_matrix_part_that_did_not_finish_cleanly_is_refused(tmp_path, damage):
    from _pietto_phase68_slice19_check import matrix_verdict

    dirs = []
    for index in range(2):
        report = {
            "part": [index, 2],
            "status": "CHECKED",
            "source_cleanup": {"status": "success"},
        }
        if index == 1:
            report.update(damage)
        dirs.append(tmp_path / ("matrix-pg-%d" % index))
        _write_report(dirs[-1], "pietto-phase68-slice19-matrix.json", report)
    with pytest.raises(AssertionError, match="^MATRIX_PART_CLEANUP$"):
        matrix_verdict("postgres", dirs, {}, None)


def test_tuning_pairs_come_only_from_runs_that_cleaned_up(tmp_path):
    from _pietto_phase68_slice19_check import ROUTES, tuning_pairs

    name = "pietto-phase68-slice19-tuning.json"
    good = {
        "status": "ACQUIRED",
        "source_cleanup": {"status": "success"},
        "pairs": {route: {"route": route} for route in ROUTES["postgres"]},
    }
    _write_report(tmp_path / "ok/tuning/postgres", name, good)
    assert sorted(tuning_pairs(tmp_path / "ok", "postgres")) == sorted(
        ROUTES["postgres"]
    )
    for label, damage in (
        ("leaked", {"source_cleanup": {"status": "failed"}}),
        ("failed", {"status": "FAILED"}),
    ):
        _write_report(tmp_path / label / "tuning/postgres", name, {**good, **damage})
        with pytest.raises(AssertionError, match="^TUNING_CLEANUP$"):
            tuning_pairs(tmp_path / label, "postgres")
    _write_report(tmp_path / "twice/tuning/postgres", name, good)
    _write_report(tmp_path / "twice/tuning-reused/postgres", name, good)
    with pytest.raises(AssertionError, match="^TUNING_ROUTES$"):
        tuning_pairs(tmp_path / "twice", "postgres")
