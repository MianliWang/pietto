"""S19 cross-layer laws on controlled raw-shaped facts: each law accepts a
valid connected history and the coordinated damages are rejected by their
designated laws. Pure; the real histories run in the explicit families."""

import copy

import pytest

import _pietto_phase68_slice19_check as check

G = "gen-" + "a" * 32
CK2 = "ckp-" + "2" * 32
CK4 = "ckp-" + "4" * 32
OP = "op-" + "1" * 32


def _collect(decided=(), removed=(), resumed=(), busy=(), charged=(0, 0)):
    return {
        "decided": [list(d) for d in decided],
        "removed": [list(x) for x in removed],
        "resumed": [list(x) for x in resumed],
        "busy": list(busy),
        "blocked": [],
        "refused": [],
        "charged": [{"removed": charged[0]}, {"removed": charged[1]}],
    }


def storage_view():
    occurrences = [[G, 2], [G, 3]]
    later = [[CK2, 4, [[0, 2], [2, 4]]] for _ in range(3)]
    j07 = {}
    removed = 0
    for i, (cut, (where, basis)) in enumerate(check.J07_RESUME.items(), start=1):
        gen = "gen-g%031d" % i
        two = [["chk-%d-a" % i, basis], ["chk-%d-b" % i, basis]]
        if where == "decided":
            resume = _collect(
                [["gcd-%d" % i, gen, 2, 10]],
                removed=two,
                charged=(removed, removed + 10),
            )
        elif where == "resumed":
            resume = _collect(resumed=two, charged=(removed, removed + 10))
        else:
            resume = _collect(charged=(removed + 10, removed + 10))
        removed += 10
        j07[cut] = {"generation": gen, "resume": resume, "repeat": _collect()}
    published = {
        "observed": ["PUBLISHED", "COMMITTED_THIS_CALL"],
        "eligible": True,
        "published": True,
        "effects": [0, 1, 2, 3],
    }
    j10 = {"E_ack": published}
    for name, refusal in list(check.J10_REFUSALS.items())[1:]:
        j10[name] = {
            "observed": ["REFUSED", refusal],
            "eligible": False,
            "published": False,
            "effects": [0, 1, 2, 3],
        }
    row = [{"kind": "int", "value": "1"}]
    return {
        "steps": [
            {
                "step": "setup",
                "evidence": "REAL_COMPONENT",
                "returncode": 0,
                "reaped": None,
            },
            {
                "step": "j03-first",
                "evidence": "SIGKILL",
                "returncode": -9,
                "reaped": True,
            },
        ],
        "j03": {
            "cut": {"acked": [0, 2], "issued": [2, 4], "occurrences": occurrences},
            "second": {
                "before": [[0, 2]],
                "deliveries": [[2, 4, occurrences]],
                "end": ["SAVED_SCOPE_EXHAUSTED", 4, 4],
                "acknowledged": [[0, 2], [2, 4]],
            },
            "ck2": CK2,
            "generation": G,
            "consumer_row": (CK2, "committed_prefix", 4),
            "acks": [(0, 2), (2, 4)],
            "issued": [(0, 2), (2, 4), (2, 4)],
            "later": later,
        },
        "j04": {
            "pre": {"publication": None, "query": None},
            "post": {
                "publication": [CK4, 8, 4, "att", "ret", OP],
                "query": ["publish_generation", "QUERIED", {"checkpoint": CK4}],
                "protected": ["chk-1", "chk-2"],
            },
            "operation": OP,
            "A": (CK4, 8, OP, "ret"),
            "A_latest": CK4,
            "A_members": ["chk-1", "chk-2"],
            "notify": {
                "observation": "COMMITTED_THIS_CALL",
                "notification": "BrokenPipeError",
            },
            "N": True,
        },
        "j05": {
            "busy": {"claim": "PUBLISHER_BUSY"},
            "holder": {"returncode": -9, "epoch": 2},
            "cancel": {"claim": "CLAIMED", "epoch": 3},
            "resume": {"refused": "JOB_STATE"},
            "publish": {"observation": "COMMITTED_THIS_CALL", "retention": "ret-b2"},
            "cancel_after": {"claim": "CLAIMED"},
            "B1": [False, "CANCELLED", False],
            "B2": [("ck", 3, "op", "ret-b2"), "CANCELLED", False],
        },
        "j07": j07,
        "j06": {
            "G6": "gen-6",
            "G7": "gen-7",
            "busy": _collect(busy=["gen-6"]),
            "won": _collect(
                [["gcd-6", "gen-6", 2, 10]],
                removed=[["c1", "UNLINKED"], ["c2", "UNLINKED"]],
            ),
            "first": {"collector": -9, "late": {"outcome": "CHUNK_COLLECTED"}},
            "resume": _collect(resumed=[["c3", "UNLINKED"], ["c4", "UNLINKED"]]),
        },
        "decided": ["gen-6", "gen-7"],
        "retired": ["gen-6", "gen-7"],
        "published": ["gen-a"],
        "protected": ["gen-a", "gen-b"],
        "j08": {
            "cut": {
                "stalled": ["WAITING_FOR_DOWNSTREAM", {}],
                "saturated": ["WAITING_FOR_ADMISSION", "connections"],
                "cancelled": ["CANCELLED_QUEUED", "COMMITTED"],
                "progressed": ["COMPLETED", None],
                "deadline": ["adm", "STOPPED", "NONE", ["DEADLINE"]],
                "open_admissions": 1,
                "slow": ["adm-slow"],
            },
            "reconcile": {
                "first": [["adm-slow", "RECONCILED"]],
                "second": [],
                "attempts_before": 5,
                "attempts_after": 5,
            },
        },
        "settlements": [("adm-slow", "RECONCILED"), ("adm-x", "RELEASED")],
        "j09": {
            "expired": "REGISTERED:ACCEPTANCE_EXPIRED",
            "compiled": "CompiledError:X",
        },
        "j10": j10,
        "values": {"A": [list(row), list(row)], "oracle": [list(row), list(row)]},
    }


def test_storage_laws_accept_a_valid_history_and_reject_each_damage():
    view = storage_view()
    assert check.check_storage(copy.deepcopy(view))["sigkill"] == 1
    assert check.storage_damages(view) == {
        "invented_ack": "J03_R1",
        "enlarged_scope": "J03_R1",
        "relabeled_redelivery": "J03_R1",
        "notification_as_commit": "J04_PUBLICATION",
        "reversed_order": "J05_ORDER",
        "released_protection": "J05_ORDER",
        "stale_read": "J06_LIFETIME",
        "protected_tombstone": "PROTECTED_COLLECTED",
        "observed_absence": "J07_COLLECTION",
        "credit_before_removal": "J07_COLLECTION",
        "double_settlement": "J08_RECONCILE",
        "cancel_as_success": "J08_RECONCILE",
        "unknown_published": "J10_ELIGIBILITY",
        "changed_value": "VALUES",
        "collapsed_duplicate": "VALUES",
        "injected_as_kill": "EVIDENCE_CLASS",
    }


def j01_record():
    """The real C_reply_lost shape: the killed reply-cut step has no final
    membership, only its queried checkpoint and what it reconciled from."""
    first = [[0, 2, "att-0", "chk-0"], [4, 6, "att-0", "chk-2"]]
    middle = first + [[2, 4, "att-1", "chk-1"]]
    final = middle + [[6, 12, "att-2", "chk-3"]]
    return {
        "history": "C_reply_lost",
        "checked": True,
        "capture": {"attempt": "att-0", "members": [list(m) for m in first]},
        "steps": [
            {
                "attempt": "att-1",
                "predecessor": "ckp-0",
                "before": [list(m) for m in first],
                "lost": [2, 4, "chk-1"],
                "queried": ["publish_chunk", "QUERIED", {"checkpoint": "ckp-1"}],
            },
            {
                "attempt": "att-2",
                "predecessor": "ckp-1",
                "before": [list(m) for m in middle],
                "final_members": [list(m) for m in final],
                "final_checkpoint": "ckp-2",
                "status": "COMPLETE",
            },
        ],
    }


def test_j01_lineage_keeps_every_attempt_and_exact_coverage():
    assert check.check_j01(j01_record())["attempts"] == 3
    assert set(check.j01_damages(j01_record()).values()) == {"J01_LINEAGE"}


def test_a_damaged_saved_member_is_refused_without_adoption():
    saved = [[0, 2, "att-0", "chk-0"]]
    record = {
        "history": "B_damage_value",
        "checked": True,
        "capture": {"attempt": "att-0", "members": [list(m) for m in saved]},
        "steps": [
            {
                "attempt": "att-1",
                "status": "REFUSED",
                "error": "JobStoreError:RECONCILIATION_MISMATCH",
                "predecessor": "ckp-0",
                "before": [list(m) for m in saved],
                "final_members": [list(m) for m in saved],
                "final_checkpoint": "ckp-0",
            }
        ],
    }
    assert check.check_j01(record)["attempts"] == 1
    for change in (
        lambda r: r["steps"][0]["final_members"].append([2, 4, "att-1", "chk-1"]),
        lambda r: r["steps"][0].update(final_checkpoint="ckp-1"),
        lambda r: r["steps"][0].update(status="COMPLETE"),
    ):
        assert check.rejects(check.check_j01, record, change, "J01_LINEAGE")


def _effect(position, row):
    """A sink effect row in the reference sink's real payload shape."""
    import json

    from pietto._project.project_job_chunks import coordinate_wire

    payload = json.dumps(
        {
            "coordinates": [["int", position]],
            "values": [coordinate_wire(v) for v in row],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return [position, "dig-%d" % position, "skc-%d" % position, position + 1, payload]


def j02_value():
    import _pietto_phase68_slice6_check as s6check

    rows = s6check.seven_rows("postgres", 39)
    # Independent rows, as in the JSON raw (no shared list objects).
    before = [_effect(p, rows[p]) for p in range(4)]
    final = [_effect(p, rows[p]) for p in range(12)]
    return {
        "relay": {
            "returncode": -9,
            "reaped": True,
            "lost": [2, 4],
            "confirms": [[0, 2], [2, 4]],
            "sink_rows": [[p] for p in range(4)],
            "position": 2,
            "terminal": None,
            "observed": 4,
            "members": [[0, 2, "a", "c0"], [2, 4, "a", "c1"]],
        },
        "recover": {
            "status": "COMPLETE",
            "coverage": True,
            "members": [[0, 2, "a", "c0"], [2, 4, "a", "c1"], [4, 12, "b", "c2"]],
        },
        "adopt": {
            "reopened": 2,
            "first": [2, 4, [], {"2": "DUPLICATE", "3": "DUPLICATE"}],
            "before": before,
            "final": final,
            "issued": [
                [4, 7, ["COMMITTED"] * 3],
                [7, 10, ["COMMITTED"] * 3],
                [10, 12, ["COMMITTED"] * 2],
            ],
            "conflict": "CONFLICT",
        },
        "adopt_process": {
            "connections": [],
            "installed_drivers": [],
            "loaded_drivers": [],
        },
    }


def test_j02_one_effect_per_occurrence_across_a_lost_reply():
    assert check.check_j02(j02_value(), "postgres")["effects"] == 12
    found = check.j02_damages(j02_value(), "postgres")
    assert found["collapsed_duplicate"] == found["changed_value"] == "J02_EFFECT"
    assert found["driver_in_adopter"] == "SAVED_SOURCE_ACCESS"
    assert found["injected_as_kill"] == "EVIDENCE_CLASS"


def tuning_report():
    import _pietto_phase68_slice6_check as s6check
    from pietto._project.project_job_chunks import coordinate_wire

    def wires():
        rows = s6check.seven_rows("postgres", 39)
        return [[coordinate_wire(v) for v in row] for row in rows]

    def run(workers, elapsed):
        vector = dict.fromkeys(
            ("connections", "workers", "memory", "durable", "operations"), 1
        )
        # Serial units follow one another; concurrent ones overlap.
        spans = (
            [(1, 2), (3, 4), (5, 6)] if workers == 1 else [(1, 10), (2, 11), (3, 12)]
        )
        units = {
            "u%d" % i: {
                "vector": vector,
                "events": [[a, "ADMITTED"], [b, "TERMINAL:COMPLETED"]],
            }
            for i, (a, b) in enumerate(spans)
        }
        units["queued"] = {"vector": None, "events": [[1, "QUEUED"]]}
        return {
            "elapsed": elapsed,
            "workers": workers,
            "terminals": {
                "small": ["COMPLETED", None, "NONE"],
                "larger": ["COMPLETED", None, "NONE"],
                "slow": ["COMPLETED", None, "NONE"],
                "cancelled": ["CANCELLED_QUEUED", None, "COMMITTED"],
            },
            "values": {"small": wires(), "larger": wires(), "slow": wires()},
            "units": units,
            "open_sessions": ["1"] if workers == 1 else ["1", "2", "3"],
            "blocked": "WAITING_FOR_DOWNSTREAM",
            "chunks": 4,
            "admissions": 4,
        }

    return {
        "target": "postgres",
        "pairs": {
            "postgres_rows": {
                "order": ["serial", "concurrent"],
                "tuning": {"serial": run(1, 2.0), "concurrent": run(3, 2.5)},
            }
        },
    }


def test_equal_guarantee_pair_compares_values_not_speed():
    found = check.check_tuning(tuning_report())
    assert found["postgres_rows"]["outcome"] == "NO_MEASURED_SPEEDUP"
    assert check.tuning_damages(tuning_report()) == {
        "dropped_value": "TUNING_VALUES",
        "equal_but_wrong": "TUNING_VALUES",
        "serialized_concurrent": "TUNING_OVERLAP",
        "one_connection": "TUNING_OVERLAP",
        "never_blocked": "TUNING_BACKPRESSURE",
        "cancel_completed": "TUNING_TERMINALS",
        "less_work": "TUNING_EQUAL_WORK",
    }


def test_matrix_union_must_equal_the_required_inventory():
    records = check.as_records("mysql")
    cells = [r for r in records if "cell" in r]
    reports = []
    for index, record in enumerate(cells):
        cell = record["cell"]
        item = {"cell": cell, "checked": True}
        if cell[7] == "MATRIX":
            item["attempt"] = {"attempts": ["att-%d" % index]}
        else:
            item["capture"] = {"attempts": ["cap-%d" % index]}
            item["recover"] = {"attempts": ["rec-%d" % index]}
        reports.append(item)
    excluded = [r for r in records if "excluded" in r]
    recovered = {
        o: sum(1 for r in reports if "recover" in r and r["cell"][6] == o)
        for o in ("source", "installed")
    }
    report = {
        "records": reports
        + excluded
        + [
            {
                "drift": ["mysql", "mysql_rows"],
                "checked": True,
                "recover": {"attempts": ["drift-rec"]},
                "after_refusal": ["ckp-1", "ckp-1"],
            }
        ],
        "r1": {
            o: {
                "stores": n,
                "loaded_drivers": [],
                "installed_drivers": [],
                "connections": [],
            }
            for o, n in recovered.items()
        },
    }
    assert check.check_matrix("mysql", [report])["cells"] == 636
    assert check.matrix_report_damages("mysql", [report]) == {
        "reused_attempt": "MATRIX_FRESH_ATTEMPTS",
        "driver_in_saved_tail": "R1_SOURCE_OFFLINE",
        "refusal_moved_checkpoint": "MATRIX_DRIFT",
        "missing_drift": "MATRIX_DRIFT",
    }


@pytest.mark.parametrize("damaged", [False, True])
def test_damage_harness_names_only_the_designated_law(damaged):
    def law(value):
        check.need(value["ok"], "SOME_LAW")

    if damaged:
        with pytest.raises(check.CheckError, match="DAMAGE_WRONG_CONTROL"):
            check.rejects(law, {"ok": True}, lambda v: v.update(ok=False), "OTHER_LAW")
    else:
        with pytest.raises(check.CheckError, match="DAMAGE_ACCEPTED"):
            check.rejects(law, {"ok": True}, lambda v: None, "SOME_LAW")
