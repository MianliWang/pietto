"""Independent S14 checks over raw worker records and saved stores.

The checker never calls a product mutation or reconciliation function. Complete
fresh enumerations and values are judged by S10's raw checker and the S06/S07
literal oracles; this module checks the R2 laws on top: the abandoned original
prefix, the frozen predecessor and bounds, the barrier, old members unchanged,
new members as the exact complement, gap-free coverage and layered outcomes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ABANDONED = "S14_EXTRACTION_ABANDONED_WITHOUT_TERMINAL"


def need(condition, category):
    if not condition:
        raise AssertionError("S14_CHECK_" + category)


def frontier(ranges) -> int:
    position = 0
    for start, stop in sorted(ranges):
        if start != position:
            break
        position = stop
    return position


def check_capture(record: dict[str, Any], cell, case) -> None:
    """At most three pages of two, published by the fixed plan, then abandoned."""
    facts, failure = record["s14"], record["failure"]
    if facts is None:
        # A guard outside the page fails the attempt before any R2 basis.
        need(
            case is not None
            and cell["case"] == "refined_violation_outside_page"
            and failure is not None
            and failure["kind"] != "S14Abandoned"
            and not record["rows"],
            "CAPTURE_WITHOUT_BASIS",
        )
        return
    need(
        failure is not None
        and failure["kind"] == "S14Abandoned"
        and failure["message"] == ABANDONED
        and not record["rows"],
        "CAPTURE_ABANDONED",
    )
    staged, position = facts["staged"], 0
    for start, stop, batches, _chunk in staged:
        need(
            start == position and stop - start <= 2 and batches == (stop > start),
            "CAPTURE_PAGES",
        )
        position = stop
    need(
        len(staged) <= 3
        and facts["observed"] == position
        and len(record["pages"]) <= 3,
        "CAPTURE_BOUND",
    )
    plan = [0, 2] if len(staged) >= 3 else [0] if staged else []
    need(
        [p[0] for p in facts["published"]] == [staged[i][3] for i in plan],
        "CAPTURE_PLAN",
    )
    members = sorted((m[0], m[1], m[3]) for m in facts["members"])
    need(
        members == sorted((staged[i][0], staged[i][1], staged[i][3]) for i in plan)
        and all(m[2] == facts["attempt"] for m in facts["members"])
        and facts["frontier"] == frontier([(m[0], m[1]) for m in members]),
        "CAPTURE_MEMBERS",
    )


def check_recovery(record: dict[str, Any], capture: dict[str, Any]) -> None:
    """The R2 laws of one fresh recovery against its own abandoned original."""
    f = record["s14"]
    if record["failure"] is not None or f is None:
        raise AssertionError("S14_CHECK_RECOVERY_FAILED")
    old = sorted((m[0], m[1], m[3], m[2]) for m in capture["members"])
    ranges = [(a, b) for a, b, _chunk, _attempt in old]
    first, reach, rows, _known, frozen = f["frozen"]
    need(
        f["predecessor"] == capture["checkpoint"]
        and sorted((m[0], m[1], m[3], m[2]) for m in frozen) == old,
        "FROZEN_PREDECESSOR",
    )
    need(
        (first, reach, rows)
        == (
            frontier(ranges),
            max((b for _a, b in ranges), default=0),
            sum(b - a for a, b in ranges),
        ),
        "FROZEN_BOUNDS",
    )
    count = len(record["rows"])
    need(
        f["observed"] == count == f["end"]["observed"] == f["observed_end"]
        and f["frontier"] == count
        and f["holes"] == []
        and f["state"][:2] == [count, True]
        and f["end"]["checkpoint"] == f["checkpoint"],
        "COMPLETE_COVERAGE",
    )
    need(
        f["reconciled"]["position"] >= reach and f["matched"] == rows,
        "BARRIER",
    )
    final = sorted((m[0], m[1], m[3], m[2]) for m in f["members"])
    kept = [m for m in final if m[3] != f["attempt"]]
    added = [m for m in final if m[3] == f["attempt"]]
    need(kept == old, "OLD_MEMBERS_PRESERVED")
    saved = {p for a, b in ranges for p in range(a, b)}
    need(
        sorted(p for a, b, _c, _t in added for p in range(a, b))
        == sorted(set(range(count)) - saved)
        and sorted(tuple(x) for x in f["materialized"])
        == sorted((a, b) for a, b, _c, _t in added),
        "NEW_EXACT_COMPLEMENT",
    )
    if count == 0:
        need(len(final) == 1 and final[0][:2] == (0, 0), "EMPTY_SCHEMA_MEMBER")
    layers = dict(f["layers"])
    need(
        layers["attempt_terminal"] == "INTERRUPTED"
        and all(
            layers[n] == "UNKNOWN"
            for n in ("source", "transaction", "delivery", "cleanup")
        ),
        "PRIOR_UNKNOWN_PRESERVED",
    )
    current = layers["continuations"][-1]
    current_layers = dict(current[2])
    need(
        current[:2] == [f["attempt"], "OUTCOME"]
        and current_layers["source"] == "EOF"
        and current_layers["transaction"] == "COMMIT_ACK",
        "CURRENT_LAYERS",
    )
    need(
        f["verify_store"]["continuation_ends"] >= 1
        and f["verify_store"]["extractions"] >= 1,
        "STORE_VERIFIED",
    )


def _attempts(members):
    return {m[2] for m in members}


def check_history(record: dict[str, Any], route: str, oracle: dict) -> None:
    """Per-route SIGKILL histories over the seven-scalar retained result."""
    from collections import Counter
    import json

    name, capture, steps = record["history"], record["capture"], record["steps"]
    original, count = capture["attempt"], len(oracle["rows"])
    need(
        capture["session_gone"][-1] == 0
        and all(m[2] == original for m in capture["members"])
        and [m[:2] for m in capture["members"]]
        == ([[0, 2]] if len(capture["staged"]) == 1 else [[0, 2], [4, 6]])
        and count > 6,
        "HISTORY_CAPTURE",
    )
    saved = sorted(tuple(m) for m in capture["members"])
    last = steps[-1]
    refused = [s for s in steps if s.get("status") == "REFUSED"]
    for step in refused:
        if step.get("reconciled"):
            continue  # a late failure may leave a valid provisional prefix
        # A refusal before the barrier never changes or extends the membership.
        need(
            sorted(tuple(m) for m in step["final_members"])
            == sorted(tuple(m) for m in step["before"])
            and step["final_checkpoint"] == step["predecessor"]
            and not step.get("reconciled"),
            "HISTORY_REFUSAL_PRESERVES",
        )
    expected_refusal = {
        "B_damage_value": "RECONCILIATION_MISMATCH",
        "B_damage_coordinate": "RECONCILIATION_MISMATCH",
        "G_source_drift": "RECONCILIATION_MISMATCH",
        "H_version_replaced": "SOURCE_VERSION_OR_RETENTION",
        "I_cancel": "CANCELED",
        "L_cancel_before_qualification": "CANCELED",
    }.get(name)
    if expected_refusal is not None:
        need(
            len(refused) == 1 and expected_refusal in refused[0]["error"],
            "HISTORY_EXPECTED_REFUSAL",
        )
    if name == "E_end_reply_lost":
        kind, observation, result = last["queried"]
        need(
            kind == "end_continuation"
            and observation == "QUERIED"
            and result["observed"] == count
            and last["state"][1:3] == [count, True]
            and result["checkpoint"] == last["state"][0],
            "HISTORY_END_QUERIED",
        )
        return
    if name.startswith("B_damage"):
        need(len(steps) == 1, "HISTORY_DAMAGE_STEPS")
        return
    need(last["status"] == "COMPLETE", "HISTORY_FINAL_COMPLETE")
    final = sorted(tuple(m) for m in last["members"])
    need(
        [m for m in final if m[2] == original] == [m for m in saved],
        "HISTORY_ORIGINAL_MEMBERS",
    )
    need(
        frontier([(m[0], m[1]) for m in final]) == count
        and sum(m[1] - m[0] for m in final) == count
        and last["holes"] == []
        and last["end"]["observed"] == count
        and last["known"] == count
        and last["coverage"] is True,
        "HISTORY_COMPLETE_COVERAGE",
    )

    def key(row):
        return json.dumps(row, sort_keys=True)

    need(
        Counter(map(key, last["rows"])) == Counter(map(key, oracle["rows"]))
        and (not oracle["ordered"] or last["rows"] == oracle["rows"]),
        "HISTORY_ORACLE_VALUES",
    )
    layers = dict(last["layers"])
    continuations = layers["continuations"]
    need(
        layers["attempt_terminal"] == "INTERRUPTED"
        and layers["source"] == layers["transaction"] == "UNKNOWN"
        and continuations[-1][0] == last["attempt"]
        and continuations[-1][1] == "OUTCOME"
        and dict(continuations[-1][2])["source"] == "EOF",
        "HISTORY_LAYERS",
    )
    producers = _attempts(final)
    if name == "C_reply_lost":
        kind, observation, result = steps[0]["queried"]
        need(
            kind == "publish_chunk"
            and observation == "QUERIED"
            and last["predecessor"] == result["checkpoint"]
            and steps[0]["attempt"] in producers,
            "HISTORY_REPLY_QUERIED",
        )
    if name == "D_second_crash":
        need(
            producers == {original, steps[0]["attempt"], last["attempt"]},
            "HISTORY_THREE_PRODUCERS",
        )
    if name == "F_barrier_crash":
        need(
            steps[0]["attempt"] not in producers
            and last["predecessor"] == capture["checkpoint"],
            "HISTORY_BARRIER_NOT_PROGRESS",
        )
    # Every attempt that froze a predecessor keeps its own layers; an attempt
    # refused before that (e.g. at native qualification) is no continuation.
    need(
        all(dict(c[2]).get("source") for c in continuations)
        and [c[0] for c in continuations]
        == [s["attempt"] for s in steps if s.get("continued")],
        "HISTORY_ATTEMPT_LAYERS",
    )


def r1_expected(report: dict[str, Any], origin: str) -> dict[str, dict]:
    """The oracle-checked recoveries of one origin, rebuilt from digest-checked raw."""
    expected = {}
    for index, item in enumerate(report["records"]):
        if (
            item.get("origin") != origin
            or not isinstance(item.get("recover"), dict)
            or "drift" in item
        ):
            continue
        for role in ("capture", "recover"):
            raw = Path(item[role]["raw"]).read_bytes()
            need(hashlib.sha256(raw).hexdigest() == item[role]["sha256"], "RAW_DIGEST")
        capture = {r["route"]: r["s14"] for r in item["capture"]["results"]}
        for record in json.loads(Path(item["recover"]["raw"]).read_text())["results"]:
            expected["%d:%s:%s" % (index, item["entry"], record["route"])] = {
                "rows": record["rows"],
                "generation": capture[record["route"]]["generation"],
                "attempts": sorted({m[2] for m in record["s14"]["members"]}),
                "checkpoint": record["s14"]["checkpoint"],
            }
    return expected


def check_r1(data: dict[str, Any], expected: dict[str, dict]) -> None:
    """Source-offline Arrow-only R1 of recovered checkpoints: same rows, stable
    (generation, position) labels, multi-attempt members and saved-scope end."""
    need(
        data["connections"] == []
        and data["installed_drivers"] == []
        and data["loaded_drivers"] == []
        and data["forbidden_calls"] == []
        and sorted(r["key"] for r in data["results"]) == sorted(expected),
        "R1_SOURCE_OFFLINE",
    )
    for result in data["results"]:
        want = expected[result["key"]]
        count = len(want["rows"])
        need("error" not in result, "R1_READ:" + result.get("error", ""))
        need(
            result["rows"] == want["rows"]
            and result["occurrences"] == [[want["generation"], p] for p in range(count)]
            and result["attempts"] == want["attempts"]
            and result["checkpoint"] == want["checkpoint"]
            and result["end"]
            == ["SAVED_SCOPE_EXHAUSTED", "complete_capture", count, count, []],
            "R1_RECOVERED_RESULT",
        )


def check_refused_recovery(record: dict[str, Any], capture: dict[str, Any]) -> None:
    """A fresh guard over changed source data refuses the recovery at native
    qualification: no continuation, no rows, the saved prefix untouched."""
    failure = record["failure"]
    need(
        failure is not None
        and record["s14"] is None
        and not record["rows"]
        and "VIOLATED" in (record.get("guard_states") or ())
        and capture is not None
        and capture["members"],
        "REFUSED_BY_FRESH_GUARD",
    )


# Discriminating mechanism set: extra entry/origin combinations beyond the
# main live/source and bundle/installed matrix (values, ties/SET/window, bound
# literals, JOIN, DISTINCT, global aggregate).
DISCRIMINATING = (
    ("refined", "R2_seven", "39_values"),
    ("refined", "R2_seven", "65_values"),
    ("refined", "R2_repeated", "tied_limit"),
    ("refined", "R2_mixed", "joint"),
    ("refined", "R2_bound", "A"),
    ("refined", "W_join_values", "left_marker"),
    ("refined", "O_result_distinct", "hidden_group"),
    ("refined", "X_aggregate_global", "bag"),
)
MAIN = (("source", "live"), ("installed", "bundle"))
EXTRA = (("source", "bundle"), ("installed", "live"))


def r2_denominator(target):
    """Independently derived from S10's native manifest and S07's guard cases."""
    from _pietto_phase68_slice10_probe import native_manifest
    from _pietto_phase68_slice7_cases import manifest

    refined = {c["name"] for c in manifest() if c["options"].get("refined")}
    return [
        c
        for c in native_manifest(target)
        if c["group"] == "refined" or (c["group"] == "guarded" and c["case"] in refined)
    ]


def check_campaign(matrix, histories, old_runtime, damage):
    """Every denominator entry has its checked records; nothing missing or extra."""
    from _pietto_phase68_slice14_probe import HISTORIES

    seen: dict[tuple, set] = {}
    drifts: dict[str, list] = {}
    for report in matrix:
        need(
            report["status"] == "PASS" and report["cleanup"]["status"] == "success",
            "CAMPAIGN_GROUP",
        )
        target = report["target"]
        routes = (
            ["mysql_rows"] if target == "mysql" else ["postgres_rows", "postgres_adbc"]
        )
        for item in report["records"]:
            cell = item["cell"]
            key = (target, cell["group"], cell["case"], cell["variant"])
            if "drift" in item:
                need(
                    cell["case"] == "refined_pages"
                    and item.get("checked") is True
                    and all(a == b for a, b in item["after_refusal"].values()),
                    "CAMPAIGN_GUARD_DRIFT_ITEM",
                )
                drifts.setdefault(target, []).append((item["origin"], item["entry"]))
                continue
            if item.get("status") == "ORIGINAL_TARGET_EXCLUSION":
                need(cell["excluded"], "CAMPAIGN_EXCLUSION")
                seen.setdefault(key, set()).add("EXCLUDED")
                continue
            need(item.get("checked") is True, "CAMPAIGN_UNCHECKED")
            need(
                [r["route"] for r in item["capture"]["results"]] == routes,
                "CAMPAIGN_ROUTES",
            )
            if item.get("recover") == "NO_R2_BASIS":
                need(
                    cell["case"] == "refined_violation_outside_page",
                    "CAMPAIGN_NO_BASIS",
                )
            else:
                need(
                    [r["route"] for r in item["recover"]["results"]] == routes,
                    "CAMPAIGN_RECOVERY_ROUTES",
                )
            combo = (item["origin"], item["entry"])
            need(combo not in seen.get(key, set()), "CAMPAIGN_DUPLICATE")
            seen.setdefault(key, set()).add(combo)
        # Every recovered store's source-offline R1, re-judged from its raw.
        directory = Path(
            next(i["capture"]["raw"] for i in report["records"] if "capture" in i)
        ).parent
        for origin in ("source", "installed"):
            expected = r1_expected(report, origin)
            need(bool(expected), "CAMPAIGN_R1_DENOMINATOR")
            raw = directory / ("pietto-phase68-slice14-r1-" + origin + "-raw.json")
            check_r1(json.loads(raw.read_text()), expected)
    for target in ("postgres", "mysql"):
        for cell in r2_denominator(target):
            key = (target, cell["group"], cell["case"], cell["variant"])
            if cell["excluded"]:
                need(seen.get(key) == {"EXCLUDED"}, "CAMPAIGN_EXCLUSION_MISSING")
                continue
            want = set(MAIN)
            if (cell["group"], cell["case"], cell["variant"]) in DISCRIMINATING or (
                cell["group"] == "guarded"
            ):
                want |= set(EXTRA)
            need(seen.get(key) == want, "CAMPAIGN_MISSING:" + repr(key))
    need(
        len(seen) == sum(len(r2_denominator(t)) for t in ("postgres", "mysql")),
        "CAMPAIGN_EXTRA_ENTRY",
    )
    for report in histories:
        routes = (
            ["mysql_rows"]
            if report["target"] == "mysql"
            else ["postgres_rows", "postgres_adbc"]
        )
        need(
            report["status"] == "PASS"
            and sorted(
                (h["route"], h["history"])
                for h in report["histories"]
                if h.get("checked")
            )
            == sorted((r, n) for r in routes for n in HISTORIES),
            "CAMPAIGN_HISTORIES",
        )
    need(sorted(drifts) == ["mysql", "postgres"], "CAMPAIGN_GUARD_DRIFT")
    need(
        old_runtime
        == {
            "outcome": "WORKSPACE_FORMAT",
            "unchanged": True,
            "s11_format": "pietto.job-workspace.v1",
        },
        "CAMPAIGN_OLD_RUNTIME",
    )
    need(len(damage) >= 9, "CAMPAIGN_CHECKER_DAMAGE")
