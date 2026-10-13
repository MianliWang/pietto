"""The S19 matrix's shared claim queue (an R2-first walk, each declaration claimed
exactly once), the narrowed S14 no-basis law, the campaign check's matrix, tuning
and consumer sections, and the consumer family's explicit archived receipts (a
receipts directory, that run's minimal audit record and its identity, bound
before anything is written). Pure; no database or Arrow."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import threading
from typing import Any

import pytest

import _pietto_execution_compiled_probe as s10
import _pietto_execution_recovery_probe as s14
from _pietto_execution_recovery_check import check_capture
from _pietto_execution_matrix_probe import claim, consumer, queue_work, receipt_inputs
from _pietto_execution_guard_cases import manifest as guard_manifest


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
    from _pietto_execution_matrix_check import matrix_verdict

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
    from _pietto_execution_matrix_check import ROUTES, tuning_pairs

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


IDENTITY = ("a" * 40, "123", 1)
STEPS = (
    "package_smoke",
    "arrow_readiness",
    "check_arrow",
    "result_product",
    "check_product",
    "consumer_prepare",
    "consumer_replay",
    "consumer_verify",
)


def _archive(tmp_path, **audit):
    """IDENTITY's two receipts and that run's minimal audit record."""
    bodies = {"postgres": b'{"pg": 1}\n', "mysql": b'{"my": 1}\n'}
    names = {t: "phase66-%s-123-1.json" % t for t in bodies}
    for target, body in bodies.items():
        (tmp_path / names[target]).write_bytes(body)
    record = {
        "status": "PASS_EXACT_HEAD_ALL_CONSUMERS",
        "head": IDENTITY[0],
        "run": 123,
        "attempt": 1,
        "artifacts": [
            {"name": names[t], "digest": "sha256:" + hashlib.sha256(b).hexdigest()}
            for t, b in bodies.items()
        ],
        **audit,
    }
    (tmp_path / "audit.json").write_text(json.dumps(record))
    return names, bodies


def test_receipts_bind_to_the_audit_record_of_their_identity(tmp_path, monkeypatch):
    names, bodies = _archive(tmp_path)
    status, found = receipt_inputs(tmp_path, tmp_path / "audit.json", IDENTITY)
    assert status == {"status": "PASS_EXACT_HEAD_ALL_CONSUMERS"}
    assert found == {names[t]: bodies[t] for t in ("postgres", "mysql")}

    def spawn(*_args, **_kwargs):
        raise AssertionError("SPAWNED")

    # The consumer family binds them before it writes or spawns anything.
    monkeypatch.setattr(subprocess, "run", spawn)
    monkeypatch.setattr(subprocess, "check_output", spawn)
    for identity in (
        ("b" * 40, "123", 1),
        ("a" * 40, "124", 1),
        ("a" * 40, "123", 2),
    ):
        with pytest.raises(ValueError, match="^S19_RECEIPT_AUDIT:identity$"):
            receipt_inputs(tmp_path, tmp_path / "audit.json", identity)
        with pytest.raises(ValueError, match="^S19_RECEIPT_AUDIT:identity$"):
            consumer(
                tmp_path / "run",
                tmp_path / "ledger.json",
                label="local-x",
                receipt_dir=tmp_path,
                audit=tmp_path / "audit.json",
                identity=identity,
            )
        assert not (tmp_path / "run").exists()


def test_a_receipt_the_audit_record_does_not_vouch_for_is_refused(tmp_path):
    names, _bodies = _archive(tmp_path)
    (tmp_path / names["mysql"]).write_bytes(b'{"my": 2}\n')
    with pytest.raises(ValueError, match="^S19_RECEIPT_AUDIT:" + names["mysql"]):
        receipt_inputs(tmp_path, tmp_path / "audit.json", IDENTITY)
    names, _bodies = _archive(tmp_path, artifacts=[])
    with pytest.raises(ValueError, match="^S19_RECEIPT_AUDIT:" + names["postgres"]):
        receipt_inputs(tmp_path, tmp_path / "audit.json", IDENTITY)
    names, _bodies = _archive(tmp_path)
    vouched = json.loads((tmp_path / "audit.json").read_text())["artifacts"]
    stray = {"name": names["mysql"], "digest": "sha256:" + "0" * 64}
    # A name the record lists twice has no winner, whichever entry comes first.
    for artifacts in ([stray, *vouched], [*vouched, stray]):
        _archive(tmp_path, artifacts=artifacts)
        with pytest.raises(ValueError, match="^S19_RECEIPT_AUDIT:duplicate$"):
            receipt_inputs(tmp_path, tmp_path / "audit.json", IDENTITY)
    names, _bodies = _archive(tmp_path)
    (tmp_path / names["postgres"]).unlink()
    with pytest.raises(FileNotFoundError):
        receipt_inputs(tmp_path, tmp_path / "audit.json", IDENTITY)


def _consumer(identity=IDENTITY, **changes):
    """A consumer family report as `consumer` writes it for `identity`."""
    _commit, run_id, attempt = identity
    report = {
        "provenance": "LOCAL",
        "label": "local-x",
        "receipts": {
            "phase66-%s-%s-%d.json" % (t, run_id, attempt): {"bytes": 1}
            for t in ("postgres", "mysql")
        },
        "receipt_audit": {"status": "PASS_EXACT_HEAD_ALL_CONSUMERS"},
        "head": identity[0],
        "steps": [{"step": s, "returncode": 0} for s in STEPS],
        "wheels": {"result": "c" * 64, "consumer": "c" * 64},
    }
    report.update(changes)
    return report


def test_the_consumer_law_judges_the_explicit_identity():
    from _pietto_execution_matrix_check import consumer_verdict

    expected = {"label": "local-x", "wheel": "c" * 64}
    assert consumer_verdict(_consumer(), IDENTITY, "c" * 64) == expected
    # Any explicit identity, not one literal head.
    other = ("e" * 40, "9", 3)
    assert consumer_verdict(_consumer(other), other, "c" * 64) == expected
    failed = _consumer()
    failed["steps"][6]["returncode"] = 1
    one_receipt = _consumer()
    one_receipt["receipts"].pop("phase66-mysql-123-1.json")
    for report, identity, wheel in (
        (_consumer(), ("b" * 40, "123", 1), "c" * 64),
        (_consumer(), ("a" * 40, "124", 1), "c" * 64),
        (_consumer(), ("a" * 40, "123", 2), "c" * 64),
        (_consumer(head="b" * 40), IDENTITY, "c" * 64),
        (one_receipt, IDENTITY, "c" * 64),
        (_consumer(provenance="CI"), IDENTITY, "c" * 64),
        (_consumer(), IDENTITY, "d" * 64),
        (failed, IDENTITY, "c" * 64),
    ):
        with pytest.raises(AssertionError, match="^CONSUMER$"):
            consumer_verdict(report, identity, wheel)


# The inputs each family requires, in the order its refusal names them.
NEEDS = {
    "consumer": ("--label", "--receipts", "--receipt-audit", "--receipt-identity"),
    "check": ("--receipt-identity",),
}


@pytest.mark.parametrize(
    "family,omitted", [(f, o) for f, needed in NEEDS.items() for o in needed]
)
def test_the_families_refuse_each_missing_receipt_input(
    tmp_path, monkeypatch, capsys, family, omitted
):
    path = Path(__file__).resolve().parents[1] / "scripts/phase68_slice19_probe.py"
    spec = importlib.util.spec_from_file_location("s19_entry", path)
    assert spec is not None and spec.loader is not None
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    values = {
        "--label": ["local-x"],
        "--receipts": [str(tmp_path / "receipts")],
        "--receipt-audit": [str(tmp_path / "audit.json")],
        "--receipt-identity": [IDENTITY[0], IDENTITY[1], str(IDENTITY[2])],
    }
    given = [t for o in NEEDS[family] if o != omitted for t in (o, *values[o])]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            path.name,
            family,
            *given,
            "--directory",
            str(tmp_path / "d"),
            "--ledger",
            str(tmp_path / "l.json"),
        ],
    )
    with pytest.raises(SystemExit) as exit_:
        entry.main()
    assert exit_.value.code == 2
    assert capsys.readouterr().err.splitlines()[-1] == "%s: error: %s needs %s" % (
        path.name,
        family,
        " ".join(NEEDS[family]),
    )
    assert not (tmp_path / "d").exists()
