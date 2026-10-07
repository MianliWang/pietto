"""S19 independent checker; import acquires nothing.

The required matrix is derived here from the lower-level case owners (S05
CASES, S06 additions, the S10 bound/row-domain extras and the S07 manifest)
plus literal target restrictions and totals, and cross-checked against the
producers' `native_manifest`/`r2_families`; a shortened producer manifest
cannot pass. Joint-history laws read raw facts (store backups, sink rows,
process cut/reap records, runtime events) and recompute; they never trust a
producer PASS field. Every coordinated damage names the law that rejects it.
The bounded model is a design check over abstract states, not a proof.
"""

from __future__ import annotations

from collections import deque
import copy
from typing import Any

ROUTES = {"postgres": ("postgres_rows", "postgres_adbc"), "mysql": ("mysql_rows",)}
CELLS = (
    ("source", "live"),
    ("source", "bundle"),
    ("installed", "live"),
    ("installed", "bundle"),
)
# Original target restrictions and the owner that refuses each of them.
_FULL = "S05/S06 original(): no FULL JOIN on MySQL"
_GROUPS = "S05/S06 original(): no GROUPS frame EXCLUDE on MySQL"
EXCLUSIONS: dict[str, dict[tuple, str]] = {
    "postgres": {},
    "mysql": {
        ("ordinary", "V_join_full", "null_keys"): _FULL,
        ("refined", "V_join_full", "null_keys"): _FULL,
        ("ordinary", "A_window_groups", "exclude"): _GROUPS,
        ("refined", "A_window_groups", "exclude"): _GROUPS,
        ("guarded", "full_unmatched", None): "S07 manifest option postgres_only",
    },
}
# Declared cases, named exclusions and admitted R2 families (incl. excluded).
TOTALS = {"postgres": (166, 0, 62), "mysql": (164, 5, 62)}
# J01/J09 repeated-recovery, drift and revision histories per route (S14 names).
J01_HISTORIES = (
    "B_holes",
    "B_damage_value",
    "B_damage_coordinate",
    "C_reply_lost",
    "D_second_crash",
    "G_source_drift",
    "H_version_replaced",
)
# The accepted B19 product wheel (S18 dist-final), the archived predecessor role.
B19_SHA256 = "cf81718b12dfcc9161719063b7f171d65299eb662507cdf37467d64a75543979"
# Evidence classes stay distinct; each needs its own backing observation.
EVIDENCE = ("MODEL", "INJECTED", "REAL_COMPONENT", "SIGKILL", "NATIVE")


class CheckError(AssertionError):
    """One named law failed; the name is the designated rejecting control."""


def need(ok, law: str) -> None:
    if not ok:
        raise CheckError(law)


def declared(target: str) -> list[tuple]:
    """(target, group, case, variant, excluded, r2) from the lower-level owners."""
    from _pietto_phase68_slice5_cases import CASES as s05
    from _pietto_phase68_slice6_cases import CASES as s06
    from _pietto_phase68_slice7_cases import manifest

    seven = tuple(
        ("R2_seven", f"{p}_{s}") for p in (39, 65) for s in ("values", "empty", "null")
    )
    rows = (
        (("G_scan_row_domains", v) for v in ("inherited_parent", "view_rows"))
        if target == "postgres"
        else ()
    )
    guards = manifest()
    refined_guards = {c["name"] for c in guards if c["options"].get("refined")}
    groups = (
        ("ordinary", (*s05, *seven, *rows)),
        ("refined", (*s06, *(("R2_bound", v) for v in ("A", "B", "A_again")))),
        ("guarded", tuple((c["name"], None) for c in guards)),
    )
    found = []
    for group, items in groups:
        for case, variant in items:
            r2 = group == "refined" or (group == "guarded" and case in refined_guards)
            excluded = (group, case, variant) in EXCLUSIONS[target]
            found.append((target, group, case, variant, excluded, r2))
    return found


def required(target: str) -> tuple[frozenset, dict]:
    """Exact cell identities and named exclusions of the whole S19 matrix."""
    cells, excluded = set(), {}
    for t, group, case, variant, is_excluded, r2 in declared(target):
        if is_excluded:
            excluded[(t, group, case, variant)] = EXCLUSIONS[t][(group, case, variant)]
            continue
        for route in ROUTES[t]:
            for origin, entry in CELLS:
                obligation = "R2" if r2 else "MATRIX"
                cells.add((t, route, group, case, variant, entry, origin, obligation))
    return frozenset(cells), excluded


def cross_check(target: str, manifest: list, r2: list) -> dict:
    """The producer owners must resolve exactly the independently derived set."""
    mine = declared(target)
    need(len({m[1:4] for m in mine}) == len(mine), "INVENTORY_DUPLICATE")
    need(
        sorted((g, c, v, e) for _t, g, c, v, e, _r in mine)
        == sorted(
            (m["group"], m["case"], m["variant"], m["excluded"]) for m in manifest
        ),
        "INVENTORY_MANIFEST",
    )
    need(
        sorted((g, c, v) for _t, g, c, v, _e, r in mine if r)
        == sorted((m["group"], m["case"], m["variant"]) for m in r2),
        "INVENTORY_R2",
    )
    total = (len(mine), sum(1 for m in mine if m[4]), sum(1 for m in mine if m[5]))
    need(total == TOTALS[target], "INVENTORY_TOTALS")
    cells, excluded = required(target)
    return {
        "declared": total[0],
        "excluded": total[1],
        "r2": total[2],
        "cells": len(cells),
        "r2_cells": sum(1 for c in cells if c[7] == "R2"),
        "exclusions": len(excluded),
    }


def refusal(key) -> dict:
    """The owner and observed refusal a named exclusion's record must carry: the
    S07 guard preparation refuses a postgres_only case with its typed error; the
    S05/S06 original() returns no reference for an unsupported MySQL shape."""
    if key[1] == "guarded":
        return {"owner": "case_preparation", "observed": "GuardPreparationError"}
    return {"owner": "original", "observed": "NONE"}


def check_inventory(target: str, records: list[dict]) -> dict:
    """Producer records: {"cell": [...8 fields...]} or {"excluded": [target,
    group, case, variant], "owner": ..., "observed": ...}; the restriction texts
    are this checker's own (EXCLUSIONS). Producer totals are ignored."""
    cells, excluded = required(target)
    seen = [tuple(r["cell"]) for r in records if "cell" in r]
    dropped = [tuple(r["excluded"]) for r in records if "excluded" in r]
    need(len(seen) == len(set(seen)), "INVENTORY_DUPLICATE")
    need(len(dropped) == len(set(dropped)), "INVENTORY_DUPLICATE")
    supported = {c[:1] + c[2:5] for c in cells}
    need(not supported & set(dropped), "INVENTORY_RECAST")
    need(set(seen) <= cells, "INVENTORY_FOREIGN")
    need(set(seen) == cells, "INVENTORY_OMITTED")
    need(set(dropped) == set(excluded), "INVENTORY_EXCLUSION")
    for key, r in zip(dropped, (r for r in records if "excluded" in r)):
        need(
            (r.get("owner"), r.get("observed")) == tuple(refusal(key).values()),
            "INVENTORY_EXCLUSION",
        )
    return {"cells": len(seen), "exclusions": len(dropped)}


def check_evidence(record: dict) -> str:
    """A claimed class needs its own backing observation from the raw."""
    kind = record["evidence"]
    need(kind in EVIDENCE, "EVIDENCE_CLASS")
    if kind == "SIGKILL":
        need(
            record.get("returncode") == -9 and record.get("reaped") is True,
            "EVIDENCE_CLASS",
        )
    if kind == "NATIVE":
        need(
            bool(record.get("session"))
            and record.get("route") in {r for rs in ROUTES.values() for r in rs}
            and bool(record.get("loaded_drivers")),
            "EVIDENCE_CLASS",
        )
    if kind in ("MODEL", "INJECTED"):
        need(
            not record.get("returncode") and not record.get("session"), "EVIDENCE_CLASS"
        )
    return kind


def joint_model(chunks: int = 2) -> int:
    """Exhaustive interleavings for one generation of `chunks` occurrences:
    chunk commit (file then reference), sink send (effect) and local confirm per
    occurrence, publication, consumer ACK, retirement and collection, with a
    crash (loss of uncommitted local state) allowed before every step. Laws: a
    confirmation names a committed effect; at most one effect per occurrence; a
    published or referenced member is never collected; publication needs every
    member; an ACK never exceeds what was issued. Returns explored states."""
    # state: (committed, effects, confirmed, issued, acked, published, retired,
    #         collected, crashes)
    start = (0, frozenset(), frozenset(), 0, 0, False, False, False, 0)
    seen = {start}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        committed, effects, confirmed, issued, acked, published, retired = state[:7]
        collected, crashes = state[7], state[8]
        need(confirmed <= effects, "MODEL_CONFIRM_WITHOUT_EFFECT")
        need(all(p < committed for p in effects), "MODEL_EFFECT_BEYOND_COMMIT")
        need(
            not (collected and (published or not retired)), "MODEL_PROTECTED_COLLECTED"
        )
        need(not published or committed == chunks, "MODEL_PARTIAL_PUBLICATION")
        need(acked <= issued <= committed, "MODEL_ACK_BEYOND_ISSUE")
        successors = []
        if committed < chunks and not retired:
            successors.append((committed + 1, *state[1:]))
        for p in range(committed):
            if p not in effects and not collected:
                successors.append((committed, effects | {p}, *state[2:]))
            if p in effects and p not in confirmed:
                successors.append((committed, effects, confirmed | {p}, *state[3:]))
        if issued < committed and not collected:
            successors.append((*state[:3], issued + 1, *state[4:]))
        if acked < issued:
            successors.append((*state[:4], acked + 1, *state[5:]))
        if committed == chunks and not published and not retired:
            successors.append((*state[:5], True, *state[6:]))
        if not published and not retired:
            successors.append((*state[:6], True, *state[7:]))
        if retired and not published and not collected:
            successors.append((*state[:7], True, crashes))
        if crashes < 1:
            # A crash loses the unacknowledged issuance (it may be issued again
            # under the same occurrences); committed and sink facts survive.
            successors.append((*state[:3], acked, acked, *state[5:8], crashes + 1))
        for item in successors:
            if item not in seen:
                seen.add(item)
                queue.append(item)
    return len(seen)


def damaged(evidence: Any, change) -> Any:
    """A deep copy with one coordinated change applied."""
    copied = copy.deepcopy(evidence)
    change(copied)
    return copied


def rejects(check, evidence: Any, change, law: str) -> str:
    """Apply one coordinated damage; only the designated law may reject it."""
    try:
        check(damaged(evidence, change))
    except CheckError as error:
        need(str(error) == law, "DAMAGE_WRONG_CONTROL:" + law + ":" + str(error))
        return law
    raise CheckError("DAMAGE_ACCEPTED:" + law)


def inventory_damages(target: str, records: list[dict]) -> dict[str, str]:
    """Omitted / duplicated / foreign / relabeled cells and a supported cell
    recast as an exclusion, each with a producer total adjusted to match."""
    records = [dict(r) for r in records]
    cell = next(i for i, r in enumerate(records) if "cell" in r)

    def omitted(rs):
        rs.pop(cell)

    def duplicated(rs):
        rs.append(dict(rs[cell]))

    def foreign(rs):
        rs[cell] = {"cell": ["sqlite", *rs[cell]["cell"][1:]]}

    def relabeled(rs):
        c = list(rs[cell]["cell"])
        c[3] = c[3] + "_relabeled"
        rs[cell] = {"cell": c}

    def recast(rs):
        c = rs.pop(cell)["cell"]
        key = [c[0], *c[2:5]]
        rs.append({"excluded": key, **refusal(key)})

    def check(rs):
        check_inventory(target, rs)

    return {
        name: rejects(check, records, change, law)
        for name, change, law in (
            ("omitted", omitted, "INVENTORY_OMITTED"),
            ("duplicated", duplicated, "INVENTORY_DUPLICATE"),
            ("foreign", foreign, "INVENTORY_FOREIGN"),
            ("relabeled", relabeled, "INVENTORY_FOREIGN"),
            ("recast", recast, "INVENTORY_RECAST"),
        )
    }


def as_records(target: str) -> list[dict[str, Any]]:
    """The required set rendered as producer-shaped records (tests/damages)."""
    cells, excluded = required(target)
    return [{"cell": list(c)} for c in sorted(cells, key=repr)] + [
        {"excluded": list(k), **refusal(k)} for k in sorted(excluded, key=repr)
    ]


def check_compat(evidence: dict) -> dict:
    """Current vs archived B19 formats, envelopes before SQLite, recognized
    schema damage, archived S16 refusal, and the B19/current code outcome that
    follows from identities recomputed from the actual wheel bytes."""
    import _pietto_phase68_slice18_check as s18

    current, previous = evidence["formats"]["current"], evidence["formats"]["b19"]
    try:
        s18.check_formats(current)
        s18.check_formats(previous)
    except s18.Rejected as error:
        raise CheckError(error.law) from None
    need(current == previous, "FORMAT_UNCHANGED")
    need(
        sorted(e["damage"] for e in evidence["envelopes"])
        == ["future_format", "relabeled_v6", "reordered_features", "unknown_feature"]
        and all(
            e["outcome"] == "WORKSPACE_FORMAT" and e["unchanged"]
            for e in evidence["envelopes"]
        ),
        "ENVELOPE_BEFORE_SQLITE",
    )
    need(evidence["schema"]["outcome"] == "WORKSPACE_SCHEMA", "RECOGNIZED_SCHEMA")
    need(
        evidence["s16"]
        == {
            "outcome": "WORKSPACE_FORMAT",
            "unchanged": True,
            "format": "pietto.job-workspace.v1",
        },
        "ARCHIVED_REFUSAL",
    )
    code = evidence["code"]
    b19 = s18.compatibility_identity(evidence["b19_wheel"], evidence["antlr_wheel"])
    now = s18.compatibility_identity(evidence["current_wheel"], evidence["antlr_wheel"])
    need(
        code["b19_identity"] == b19
        and code["current_identity"] == now
        and code["source_identity"] == now,
        "CODE_IDENTITY",
    )
    expected = (
        ("LOADED", "BOUND", "BOUND")
        if b19 == now
        else ("COMPILED_COMPATIBILITY", "JOB_COMPATIBILITY", "JOB_COMPATIBILITY")
    )
    need(
        code["b19_self"] == "LOADED"
        and code["b19_binding"] == "BOUND"
        and code["open"] == "OPENED"
        and (code["load"], code["binding_b19"], code["binding_current"]) == expected
        and code["fresh"] == "ACCEPTED",
        "CODE_COMPATIBILITY",
    )
    return {"b19_identity": b19, "current_identity": now, "same_code": b19 == now}


def compat_damages(evidence: dict) -> dict[str, str]:
    """Coordinated compatibility damages, each with its designated law."""

    def feature(e):
        for matrix in e["formats"].values():
            matrix["pietto.job-workspace.v7"]["features"].append("gc")
            matrix["pietto.job-workspace.v7"]["gates"]["gc"] = "PASSED"

    def laundered(e):
        # A different archived identity relabeled compatible with matching claims.
        e["code"].update(b19_identity="0" * 64, load="LOADED", binding_b19="BOUND")

    def envelope(e):
        e["envelopes"][0].update(outcome="ACCEPTED")

    def old_runtime(e):
        e["s16"].update(outcome="OPENED")

    return {
        name: rejects(check_compat, evidence, change, law)
        for name, change, law in (
            ("unknown_feature", feature, "FORMAT_FEATURES"),
            ("laundered_identity", laundered, "CODE_IDENTITY"),
            ("envelope_accepted", envelope, "ENVELOPE_BEFORE_SQLITE"),
            ("archived_accepts_v7", old_runtime, "ARCHIVED_REFUSAL"),
        )
    }


# --- storage joint history (J03-J10 without a source database) ----------------

J07_RESUME = {
    "K1_decision_uncommitted": ("decided", "UNLINKED"),
    "K2_committed_before_unlink": ("resumed", "UNLINKED"),
    "K3_unlinked_before_sync": ("resumed", "ABSENT"),
    "K4_synced_before_observation": ("resumed", "ABSENT"),
    "K5_observed_before_reply": ("none", None),
}
J10_REFUSALS = {
    "E_ack": None,
    "E_unknown": "PUBLICATION_TRANSACTION",
    "E_source": "PUBLICATION_SOURCE",
    "E_cleanup": "PUBLICATION_CLEANUP",
}
SEVEN_A = (0, 1, 2, 3, 4, 0, 1, 2)


def _rows(connection, sql, parameters=()):
    return [tuple(r) for r in connection.execute(sql, parameters)]


def storage_view(report: dict, backup, sink_backup) -> dict:
    """Raw facts of one storage history: the steps' own emitted observations and
    named-column reads of the static backups (supported backup API copies)."""
    import json as _json
    import sqlite3

    import _pietto_phase68_slice12_probe as s12
    import _pietto_phase68_slice16_check as s16

    steps = {s["step"]: s for s in report["steps"]}
    cap = report["setup"]["captured"]
    emitted = {k: s.get("emitted") for k, s in steps.items()}
    store = sqlite3.connect(f"file:{backup}?mode=ro", uri=True)
    sink = sqlite3.connect(f"file:{sink_backup}?mode=ro", uri=True)
    try:
        a = cap["A"]
        consumer = report["j03_cut"]["consumer"]
        published = {
            g: (c, e, o, r)
            for g, c, e, o, r in _rows(
                store,
                "SELECT generation, checkpoint, extent, operation, retention FROM publication",
            )
        }
        released = {
            r for (r,) in _rows(store, "SELECT retention FROM retention_release")
        }
        states = dict(_rows(store, "SELECT identity, state FROM job"))
        # Every committed decision, including those of killed collectors.
        decided = sorted(
            {g for (g,) in _rows(store, "SELECT DISTINCT generation FROM tombstone")}
        )
        retired = sorted(
            {g for (g,) in _rows(store, "SELECT generation FROM generation_retirement")}
        )
        j10 = {}
        for name in J10_REFUSALS:
            item = cap[name]
            (outcome,) = _rows(
                store,
                "SELECT outcome FROM attempt_terminal WHERE attempt = ?",
                (item["closing"],),
            )[0]
            row = _rows(
                store,
                "SELECT * FROM closing_observation WHERE attempt = ?",
                (item["closing"],),
            )[0]
            (reference,) = _rows(
                store,
                "SELECT binding_reference FROM attempt WHERE identity = ?",
                (item["closing"],),
            )[0]
            j10[name] = {
                "observed": item["publication"],
                "eligible": s16._eligible(
                    _json.loads(outcome),
                    row,
                    "postgres_rows",
                    reference,
                    item["frontier"],
                ),
                "published": item["generation"] in published,
                "effects": [
                    p
                    for (p,) in _rows(
                        sink,
                        "SELECT position FROM effect WHERE generation = ? ORDER BY position",
                        (item["generation"],),
                    )
                ],
            }
        rows = s16.published_rows(
            s16.load(backup), report["setup"]["workspace"], a["generation"]
        )
        view = {
            "steps": [
                {k: s.get(k) for k in ("step", "evidence", "returncode", "reaped")}
                for s in report["steps"]
            ],
            "j03": {
                "cut": report["j03_cut"],
                "second": emitted["j03-second"],
                "ck2": next(ck for ck, f in a["checkpoints"] if f == 4),
                "generation": a["generation"],
                "consumer_row": _rows(
                    store,
                    "SELECT checkpoint, scope, extent FROM consumer WHERE identity = ?",
                    (consumer,),
                )[0],
                "acks": sorted(
                    _rows(
                        store,
                        "SELECT start, stop FROM acknowledgement WHERE consumer = ?",
                        (consumer,),
                    )
                ),
                "issued": sorted(
                    _rows(
                        store,
                        "SELECT start, stop FROM issuance WHERE consumer = ?",
                        (consumer,),
                    )
                ),
                "later": [
                    [
                        emitted[k]["checkpoint"],
                        emitted[k]["extent"],
                        emitted[k]["acknowledged"],
                    ]
                    for k in (
                        "j04-query-precommit",
                        "j04-query-postcommit",
                        "j04-query-notify",
                    )
                ],
            },
            "j04": {
                "pre": emitted["j04-query-precommit"],
                "post": emitted["j04-query-postcommit"],
                "operation": steps["j04-P4_committed_before_response"]
                .get("config", {})
                .get("operation"),
                "A": published.get(a["generation"]),
                "A_latest": a["checkpoint"],
                "A_members": sorted(m[3] for m in a["members"]),
                "notify": report["j04_notify"],
                "N": cap["N"]["generation"] in published,
            },
            "j05": {
                "busy": emitted["j05-busy"],
                "holder": report["j05_holder"],
                "cancel": emitted["j05-cancel"],
                "resume": emitted["j05-resume"],
                "publish": emitted["j05-publish"],
                "cancel_after": emitted["j05-cancel-after"],
                "B1": [
                    cap["B1"]["generation"] in published,
                    states[cap["B1"]["job"]],
                    report["j05_holder"]["retention"] in released,
                ],
                "B2": [
                    published.get(cap["B2"]["generation"]),
                    states[cap["B2"]["job"]],
                    emitted["j05-publish"]["retention"] in released,
                ],
            },
            "j07": {
                cut: {
                    "generation": cap["G%d" % i]["generation"],
                    "resume": emitted["j07-resume-G%d" % i],
                    "repeat": emitted["j07-repeat-G%d" % i],
                }
                for i, cut in enumerate(J07_RESUME, start=1)
            },
            "j06": {
                "G6": cap["G6"]["generation"],
                "G7": cap["G7"]["generation"],
                "busy": emitted["j06-collect-busy"],
                "won": emitted["j06-collect-won"],
                "first": report["j06_decision_first"],
                "resume": emitted["j06-collect-resume"],
            },
            "decided": decided,
            "retired": retired,
            "published": sorted(published),
            "protected": sorted(
                cap[n]["generation"] for n in ("A", "B1", "B2", "N", "R", *J10_REFUSALS)
            ),
            "j08": {"cut": report["j08_cut"], "reconcile": emitted["j08-reconcile"]},
            "settlements": _rows(
                store, "SELECT admission, kind FROM admission_settlement"
            ),
            "j09": emitted["j09-refusals"],
            "j10": j10,
            "values": {
                "A": s16.encoded(rows),
                "oracle": s16.encoded([s12.SEVEN_ROWS[i] for i in SEVEN_A]),
            },
        }
    finally:
        store.close()
        sink.close()
    return view


def check_storage(view: dict) -> dict:
    """Every storage-history law over one view; returns compact facts."""
    from collections import Counter
    import json as _json

    for step in view["steps"]:
        check_evidence(step)
        need(step["evidence"] == "SIGKILL" or step["returncode"] == 0, "EVIDENCE_CLASS")
    j = view["j03"]
    occurrences = [[j["generation"], 2], [j["generation"], 3]]
    need(
        j["cut"]["acked"] == [0, 2]
        and j["cut"]["issued"] == [2, 4]
        and j["cut"]["occurrences"] == occurrences
        and j["second"]["before"] == [[0, 2]]
        and j["second"]["deliveries"] == [[2, 4, occurrences]]
        and j["second"]["end"] == ["SAVED_SCOPE_EXHAUSTED", 4, 4]
        and j["second"]["acknowledged"] == [[0, 2], [2, 4]]
        and j["acks"] == [(0, 2), (2, 4)]
        and j["issued"] == [(0, 2), (2, 4), (2, 4)]
        and j["consumer_row"] == (j["ck2"], "committed_prefix", 4)
        and all(x == [j["ck2"], 4, [[0, 2], [2, 4]]] for x in j["later"]),
        "J03_R1",
    )
    p = view["j04"]
    need(
        p["pre"]["publication"] is None
        and p["pre"]["query"] is None
        and p["A"] is not None
        and p["post"]["publication"] is not None
        and p["post"]["publication"][0] == p["A"][0] == p["A_latest"]
        and p["post"]["publication"][1] == p["A"][1] == 8
        and p["post"]["publication"][5] == p["A"][2] == p["operation"]
        and p["post"]["query"][0] == "publish_generation"
        and p["post"]["query"][2]["checkpoint"] == p["A_latest"]
        and set(p["A_members"]) <= set(p["post"]["protected"])
        and p["notify"]
        == {"observation": "COMMITTED_THIS_CALL", "notification": "BrokenPipeError"}
        and p["N"],
        "J04_PUBLICATION",
    )
    c = view["j05"]
    need(
        c["busy"] == {"claim": "PUBLISHER_BUSY"}
        and c["holder"]["returncode"] == -9
        and c["cancel"] == {"claim": "CLAIMED", "epoch": c["holder"]["epoch"] + 1}
        and c["resume"] == {"refused": "JOB_STATE"}
        and c["B1"] == [False, "CANCELLED", False]
        and c["publish"]["observation"] == "COMMITTED_THIS_CALL"
        and c["cancel_after"]["claim"] == "CLAIMED"
        and c["B2"][0] is not None
        and c["B2"][0][3] == c["publish"]["retention"]
        and c["B2"][1:] == ["CANCELLED", False],
        "J05_ORDER",
    )
    for cut, (where, basis) in J07_RESUME.items():
        item = view["j07"][cut]
        resume, repeat = item["resume"], item["repeat"]
        need(
            not repeat["decided"] and not repeat["removed"] and not repeat["resumed"],
            "J07_COLLECTION",
        )
        before, after = resume["charged"]
        if where == "decided":
            need(
                [d[1] for d in resume["decided"]] == [item["generation"]]
                and sorted(b for _c, b in resume["removed"]) == [basis, basis]
                and after["removed"] - before["removed"] == resume["decided"][0][3],
                "J07_COLLECTION",
            )
        elif where == "resumed":
            need(
                not resume["decided"]
                and sorted(b for _c, b in resume["resumed"]) == [basis, basis]
                and after["removed"] > before["removed"],
                "J07_COLLECTION",
            )
        else:
            need(
                not resume["decided"]
                and not resume["resumed"]
                and after["removed"] == before["removed"],
                "J07_COLLECTION",
            )
    g = view["j06"]
    need(
        g["busy"]["busy"] == [g["G6"]]
        and not g["busy"]["decided"]
        and [d[1] for d in g["won"]["decided"]] == [g["G6"]]
        and sorted(b for _c, b in g["won"]["removed"]) == ["UNLINKED", "UNLINKED"]
        and g["first"]["collector"] == -9
        and g["first"]["late"]["outcome"] == "CHUNK_COLLECTED"
        and sorted(b for _c, b in g["resume"]["resumed"]) == ["UNLINKED", "UNLINKED"],
        "J06_LIFETIME",
    )
    need(
        set(view["decided"]) <= set(view["retired"])
        and not set(view["decided"])
        & (set(view["protected"]) | set(view["published"])),
        "PROTECTED_COLLECTED",
    )
    h = view["j08"]
    cut, rec = h["cut"], h["reconcile"]
    need(
        cut["stalled"][0] == "WAITING_FOR_DOWNSTREAM"
        and cut["saturated"] == ["WAITING_FOR_ADMISSION", "connections"]
        and cut["cancelled"] == ["CANCELLED_QUEUED", "COMMITTED"]
        and cut["progressed"] == ["COMPLETED", None]
        and cut["deadline"][1] == "STOPPED"
        and "DEADLINE" in cut["deadline"][3]
        and cut["deadline"][2] != "COMMITTED"
        and cut["open_admissions"] >= 1
        and len(rec["first"]) == cut["open_admissions"]
        and cut["slow"][0] in {x[0] for x in rec["first"]}
        and rec["second"] == []
        and rec["attempts_before"] == rec["attempts_after"],
        "J08_RECONCILE",
    )
    keys = Counter(a for a, _k in view["settlements"])
    need(all(n == 1 for n in keys.values()), "J08_RECONCILE")
    r9 = view["j09"]
    need(
        r9["expired"] != "ACCEPTED"
        and "EXPIRED" in r9["expired"]
        and not r9["compiled"].startswith("ACCEPTED"),
        "J09_REFUSAL",
    )
    for name, refusal in J10_REFUSALS.items():
        item = view["j10"][name]
        need(item["eligible"] is (refusal is None), "J10_ELIGIBILITY")
        need(
            item["observed"]
            == (
                ["PUBLISHED", "COMMITTED_THIS_CALL"]
                if refusal is None
                else ["REFUSED", refusal]
            )
            and item["published"] is (refusal is None)
            and item["effects"] == [0, 1, 2, 3],
            "J10_ELIGIBILITY",
        )

    def bag(rows):
        return Counter(_json.dumps(r, sort_keys=True) for r in rows)

    need(bag(view["values"]["A"]) == bag(view["values"]["oracle"]), "VALUES")
    return {
        "steps": len(view["steps"]),
        "sigkill": sum(1 for s in view["steps"] if s["evidence"] == "SIGKILL"),
        "decided": len(view["decided"]),
        "settlements": len(view["settlements"]),
        "values": len(view["values"]["A"]),
    }


def storage_damages(view: dict) -> dict[str, str]:
    """Coordinated damages over a real storage view, each with its law."""

    def invented_ack(v):
        v["j03"]["acks"].append((4, 6))
        v["j03"]["second"]["acknowledged"].append([4, 6])

    def enlarged_scope(v):
        v["j03"]["consumer_row"] = (v["j03"]["ck2"], "committed_prefix", 8)
        for x in v["j03"]["later"]:
            x[1] = 8

    def relabeled_redelivery(v):
        new = [[v["j03"]["generation"], 4], [v["j03"]["generation"], 5]]
        v["j03"]["second"]["deliveries"][0][2] = new

    def notification_as_commit(v):
        v["j04"]["pre"]["publication"] = v["j04"]["post"]["publication"]

    def reversed_order(v):
        v["j05"]["B1"][0] = True

    def released_protection(v):
        v["j05"]["B2"][2] = True

    def stale_read(v):
        v["j06"]["first"]["late"]["outcome"] = "READ"

    def protected_tombstone(v):
        v["decided"].append(v["protected"][0])

    def observed_absence(v):
        resumed = v["j07"]["K3_unlinked_before_sync"]["resume"]["resumed"]
        for item in resumed:
            item[1] = "UNLINKED"

    def credit_before_removal(v):
        resume = v["j07"]["K2_committed_before_unlink"]["resume"]
        resume["charged"][0]["removed"] = resume["charged"][1]["removed"]

    def double_settlement(v):
        v["settlements"].append(v["settlements"][0])

    def cancel_as_success(v):
        v["j08"]["cut"]["cancelled"] = ["COMPLETED", "NONE"]

    def unknown_published(v):
        v["j10"]["E_unknown"].update(
            observed=["PUBLISHED", "COMMITTED_THIS_CALL"], published=True
        )

    def changed_value(v):
        row = v["values"]["A"][0]
        row[0] = (
            {"kind": "text", "value": "changed"}
            if isinstance(row[0], dict)
            else "changed"
        )

    def collapsed_duplicate(v):
        v["values"]["A"].pop()

    def injected_as_kill(v):
        step = next(s for s in v["steps"] if s["evidence"] == "SIGKILL")
        step["returncode"] = 0

    return {
        name: rejects(check_storage, view, change, law)
        for name, change, law in (
            ("invented_ack", invented_ack, "J03_R1"),
            ("enlarged_scope", enlarged_scope, "J03_R1"),
            ("relabeled_redelivery", relabeled_redelivery, "J03_R1"),
            ("notification_as_commit", notification_as_commit, "J04_PUBLICATION"),
            ("reversed_order", reversed_order, "J05_ORDER"),
            ("released_protection", released_protection, "J05_ORDER"),
            ("stale_read", stale_read, "J06_LIFETIME"),
            ("protected_tombstone", protected_tombstone, "PROTECTED_COLLECTED"),
            ("observed_absence", observed_absence, "J07_COLLECTION"),
            ("credit_before_removal", credit_before_removal, "J07_COLLECTION"),
            ("double_settlement", double_settlement, "J08_RECONCILE"),
            ("cancel_as_success", cancel_as_success, "J08_RECONCILE"),
            ("unknown_published", unknown_published, "J10_ELIGIBILITY"),
            ("changed_value", changed_value, "VALUES"),
            ("collapsed_duplicate", collapsed_duplicate, "VALUES"),
            ("injected_as_kill", injected_as_kill, "EVIDENCE_CLASS"),
        )
    }


# --- native joint histories, the whole matrix and the equal-guarantee pairs ----


def _cover(members) -> list:
    """The occurrence positions of member ranges; duplicates stay visible."""
    return sorted(p for m in members for p in range(m[0], m[1]))


def check_j01(record: dict, rows: int = 12) -> dict:
    """A checked S14 repeated-recovery history: exact gap-free final coverage
    without duplicates; every member known before a recovery (including what a
    killed attempt committed) keeps its producing attempt through every later
    reconciliation; a recovery starts from the previous step's last observed
    checkpoint (a killed step has only its queried one); C and D end with three
    producing attempts."""
    need(record.get("checked") is True, "J01_LINEAGE")
    steps = record["steps"]
    final = steps[-1]
    if record["history"].startswith("B_damage"):
        # A coherently damaged saved member: the one recovery refuses at
        # reconciliation and leaves the saved membership and checkpoint as is.
        need(
            len(steps) == 1
            and final.get("status") == "REFUSED"
            and "RECONCILIATION_MISMATCH" in final["error"]
            and sorted(map(tuple, final["final_members"]))
            == sorted(map(tuple, final["before"]))
            == sorted(map(tuple, record["capture"]["members"]))
            and final["final_checkpoint"] == final["predecessor"],
            "J01_LINEAGE",
        )
        return {"history": record["history"], "attempts": 1, "members": 0}
    need(final.get("status") == "COMPLETE", "J01_LINEAGE")
    members = final["final_members"]
    need(_cover(members) == list(range(rows)), "J01_LINEAGE")
    attempts = {m[2] for m in members}
    need(
        record["capture"]["attempt"] in attempts and final["attempt"] in attempts,
        "J01_LINEAGE",
    )
    known = [record["capture"]["members"], *(s["before"] for s in steps), members]
    for earlier, later in zip(known, known[1:]):
        need({tuple(m) for m in earlier} <= {tuple(m) for m in later}, "J01_LINEAGE")
    for earlier, later in zip(steps, steps[1:]):
        # What a killed step committed (the reply-lost chunk, the extension)
        # is reconciled by the next recovery under its own producing attempt.
        committed: list = list(earlier.get("extended") or ())
        if earlier.get("lost"):
            start, stop, chunk = earlier["lost"]
            committed.append([start, stop, earlier["attempt"], chunk])
        need(all(m in later["before"] for m in committed), "J01_LINEAGE")
        queried = earlier.get("queried")
        last = earlier.get(
            "final_checkpoint", queried[2].get("checkpoint") if queried else None
        )
        need(last is None or later["predecessor"] == last, "J01_LINEAGE")
    if record["history"] in ("C_reply_lost", "D_second_crash"):
        need(len(attempts) == 3 and steps[0]["attempt"] in attempts, "J01_LINEAGE")
    return {
        "history": record["history"],
        "attempts": len(attempts),
        "members": len(members),
    }


def _wire_values(row) -> list:
    """One row of typed wires, decoded by the independent S15 wire decoder and
    encoded like the literal oracle."""
    from _pietto_phase68_slice4_probe import s01
    from _pietto_phase68_slice15_check import decode_wire

    return [s01.scalar(decode_wire(w)) for w in row]


def _payload_values(effect) -> list:
    """One sink effect's public values (its refinement coordinates excluded)."""
    import json

    return _wire_values(json.loads(effect[4])["values"])


def check_j02(j02: dict, target: str) -> dict:
    """Lost sink reply before EOF: the sink kept one effect per occurrence; the
    restart resent by the same identity (no second effect), adopted the
    recovered checkpoint and delivered only the rest; the effects carry the
    literal oracle's exact values with multiplicity (its equal-valued
    occurrences stay separate effects); a same-key different payload
    conflicted; the adopter had no driver or connection."""
    from collections import Counter
    import json

    from _pietto_phase68_slice6_check import expected

    literal, _ordered = expected(target, "R2_seven", "39_values", None)
    rows = len(literal)
    relay, recover, adopt = j02["relay"], j02["recover"], j02["adopt"]
    process = j02["adopt_process"]
    need(relay["returncode"] == -9 and relay["reaped"] is True, "EVIDENCE_CLASS")
    need(
        relay["lost"] == [2, 4]
        and relay["confirms"] == [[0, 2], [2, 4]]
        and [r[0] for r in relay["sink_rows"]] == [0, 1, 2, 3]
        and relay["position"] == 2
        and relay["terminal"] is None
        and relay["observed"] < rows,
        "J02_EFFECT",
    )
    need(
        recover.get("status") == "COMPLETE"
        and recover["coverage"] is True
        and _cover(recover["members"]) == list(range(rows))
        and {m[3] for m in relay["members"]} <= {m[3] for m in recover["members"]},
        "J02_EFFECT",
    )
    statuses = set(adopt["first"][3].values())
    before = {r[0]: r for r in adopt["before"]}
    final = {r[0]: r for r in adopt["final"]}
    need(
        adopt["reopened"] == 2
        and adopt["first"][:2] == [2, 4]
        and statuses <= {"DUPLICATE", "PRESENT_MATCHING"}
        and sorted(r[0] for r in adopt["final"]) == list(range(rows))
        and len({r[2] for r in adopt["final"]}) == rows
        and all(final[p][:3] == before[p][:3] for p in before)
        and [x[0] for x in adopt["issued"]][0] == 4
        and all(set(s) == {"COMMITTED"} for _a, _b, s in adopt["issued"])
        and _cover([x[:2] for x in adopt["issued"]]) == list(range(4, rows))
        and adopt["conflict"] == "CONFLICT"
        and final[0][1] == before[0][1],
        "J02_EFFECT",
    )
    wanted = Counter(json.dumps(r) for r in literal)
    need(
        Counter(json.dumps(_payload_values(r)) for r in adopt["final"]) == wanted
        and max(wanted.values()) > 1,
        "J02_EFFECT",
    )
    need(
        process == {"connections": [], "installed_drivers": [], "loaded_drivers": []},
        "SAVED_SOURCE_ACCESS",
    )
    return {"effects": len(final), "resent": sorted(statuses)}


def j01_damages(record: dict) -> dict[str, str]:
    """Coordinated lineage damages of one C_reply_lost history."""

    def duplicated(r):
        final = r["steps"][-1]["final_members"]
        final.append(list(final[0]))

    def dropped(r):
        r["steps"][-1]["final_members"].pop(0)

    def foreign_predecessor(r):
        r["steps"][-1]["predecessor"] = "ckp-" + "f" * 32

    def laundered(r):
        for m in r["steps"][-1]["final_members"]:
            m[2] = r["steps"][-1]["attempt"]

    def relabeled_lost(r):
        # The reply-lost chunk re-attributed to the recovering attempt in both
        # the reconciled and the final membership.
        chunk = r["steps"][0]["lost"][2]
        for m in r["steps"][-1]["before"] + r["steps"][-1]["final_members"]:
            if m[3] == chunk:
                m[2] = r["steps"][-1]["attempt"]

    return {
        name: rejects(check_j01, record, change, "J01_LINEAGE")
        for name, change in (
            ("duplicated_occurrence", duplicated),
            ("dropped_member", dropped),
            ("foreign_predecessor", foreign_predecessor),
            ("laundered_attempts", laundered),
            ("relabeled_lost_reply", relabeled_lost),
        )
    }


def _twin(final) -> tuple[int, int]:
    """Two positions carrying equal public values."""
    seen: dict = {}
    for effect in final:
        key = repr(_payload_values(effect))
        if key in seen:
            return seen[key], effect[0]
        seen[key] = effect[0]
    raise CheckError("J02_NO_EQUAL_VALUED_OCCURRENCES")


def j02_damages(value: dict, target: str) -> dict[str, str]:
    """Coordinated effect damages of one lost-reply delivery history."""
    import json

    def collapsed(v):
        # Two equal-valued occurrences delivered as one effect (positions kept):
        # the twin now carries another occurrence's payload.
        final = v["adopt"]["final"]
        first, second = _twin(final)
        donor = next(e for e in final if e[0] not in (first, second))
        index = next(i for i, e in enumerate(final) if e[0] == second)
        final[index][4] = donor[4]

    def changed_value(v):
        for effect in v["adopt"]["final"]:
            payload = json.loads(effect[4])
            wire = next((w for w in payload["values"] if w[0] == "int"), None)
            if wire is not None:
                wire[1] += 1
                effect[4] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
                return

    def second_effect(v):
        v["adopt"]["first"][3]["2"] = "COMMITTED"

    def duplicated(v):
        v["adopt"]["final"].append(list(v["adopt"]["final"][0]))

    def conflict_accepted(v):
        v["adopt"]["conflict"] = "DUPLICATE"

    def identity_changed(v):
        v["adopt"]["final"][0][2] = "skc-" + "0" * 32

    def driver_loaded(v):
        v["adopt_process"]["loaded_drivers"] = ["psycopg"]

    def not_killed(v):
        v["relay"]["returncode"] = 0

    return {
        name: rejects(lambda v: check_j02(v, target), value, change, law)
        for name, change, law in (
            ("collapsed_duplicate", collapsed, "J02_EFFECT"),
            ("changed_value", changed_value, "J02_EFFECT"),
            ("second_effect_on_resend", second_effect, "J02_EFFECT"),
            ("duplicated_effect", duplicated, "J02_EFFECT"),
            ("conflict_accepted", conflict_accepted, "J02_EFFECT"),
            ("effect_identity_changed", identity_changed, "J02_EFFECT"),
            ("driver_in_adopter", driver_loaded, "SAVED_SOURCE_ACCESS"),
            ("injected_as_kill", not_killed, "EVIDENCE_CLASS"),
        )
    }


def check_matrix(target: str, reports: list[dict]) -> dict:
    """The union of every matrix part is exactly the required inventory; each
    checked cell keeps unique fresh attempts; R2 cells are recovered (or the
    original guard refused before any basis); every recovered store was read
    source-offline by a driver-free process."""
    records = [r for report in reports for r in report["records"]]
    cells = [r for r in records if "cell" in r]
    check_inventory(target, cells + [r for r in records if "excluded" in r])
    _cells, excluded = required(target)
    attempts = []
    recovered = {"source": 0, "installed": 0}
    for r in cells:
        need(r.get("checked") is True, "MATRIX_CELL")
        if r["cell"][7] == "MATRIX":
            attempts += r["attempt"]["attempts"]
        elif r.get("basis") == "NO_R2_BASIS":
            need(r["cell"][3] == "refined_violation_outside_page", "MATRIX_CELL")
            attempts += r["capture"]["attempts"]
        else:
            attempts += r["capture"]["attempts"] + r["recover"]["attempts"]
            recovered[r["cell"][6]] += 1
    need(len(attempts) == len(set(attempts)), "MATRIX_FRESH_ATTEMPTS")
    tails = {"source": 0, "installed": 0}
    for report in reports:
        for origin, tail in report.get("r1", {}).items():
            need(
                tail["loaded_drivers"] == []
                and tail["installed_drivers"] == []
                and tail["connections"] == [],
                "R1_SOURCE_OFFLINE",
            )
            tails[origin] += tail["stores"]
    need(tails == recovered, "R1_SOURCE_OFFLINE")
    drifts = [r for r in records if "drift" in r]
    need(
        len(drifts) == len(ROUTES[target])
        and all(
            d.get("checked")
            and "recover" in d
            and d["after_refusal"][0] == d["after_refusal"][1]
            for d in drifts
        ),
        "MATRIX_DRIFT",
    )
    return {
        "cells": len(cells),
        "exclusions": len(excluded),
        "attempts": len(attempts),
        "recovered": recovered,
        "drift": len(drifts),
    }


def matrix_report_damages(target: str, reports: list[dict]) -> dict[str, str]:
    """Coordinated damages of a target's real matrix reports (union level)."""

    def reused_attempt(rs):
        cells = [r for rp in rs for r in rp["records"] if "attempt" in r]
        cells[1]["attempt"]["attempts"] = list(cells[0]["attempt"]["attempts"])

    def driver_in_tail(rs):
        tail = next(rp["r1"] for rp in rs if rp.get("r1"))
        next(iter(tail.values()))["loaded_drivers"] = ["psycopg"]

    def moved_checkpoint(rs):
        drift = next(r for rp in rs for r in rp["records"] if "drift" in r)
        drift["after_refusal"][1] = "ckp-" + "f" * 32

    def missing_drift(rs):
        for rp in rs:
            rp["records"] = [r for r in rp["records"] if "drift" not in r]

    return {
        name: rejects(lambda rs: check_matrix(target, rs), reports, change, law)
        for name, change, law in (
            ("reused_attempt", reused_attempt, "MATRIX_FRESH_ATTEMPTS"),
            ("driver_in_saved_tail", driver_in_tail, "R1_SOURCE_OFFLINE"),
            ("refusal_moved_checkpoint", moved_checkpoint, "MATRIX_DRIFT"),
            ("missing_drift", missing_drift, "MATRIX_DRIFT"),
        )
    }


def check_tuning(report: dict) -> dict:
    """Equal guarantees under both policies (terminals, the literal oracle's
    exact values with multiplicity, equal work, the S17 runtime laws); admitted
    units overlap only under the concurrent policy; elapsed time is reported,
    never required to improve."""
    from collections import Counter
    import json

    import _pietto_phase68_slice6_check as s6check
    import _pietto_phase68_slice17_check as k17

    literal, _ordered = s6check.expected(
        report["target"], "R2_seven", "39_values", None
    )
    wanted = Counter(json.dumps(r) for r in literal)
    found = {}
    for route, pair in report["pairs"].items():
        runs = pair["tuning"]
        serial, concurrent = runs["serial"], runs["concurrent"]
        for run in (serial, concurrent):
            # The slow sink really applied backpressure under both policies.
            need(run["blocked"] == "WAITING_FOR_DOWNSTREAM", "TUNING_BACKPRESSURE")
            terminals = run["terminals"]
            need(
                all(terminals[k][0] == "COMPLETED" for k in ("small", "larger", "slow"))
                and terminals["cancelled"][0] in ("CANCELLED", "CANCELLED_QUEUED")
                and terminals["cancelled"][2] == "COMMITTED",
                "TUNING_TERMINALS",
            )
        need(
            serial["values"] == concurrent["values"]
            and all(
                Counter(json.dumps(_wire_values(r)) for r in serial["values"][k])
                == wanted
                for k in ("small", "larger", "slow")
            ),
            "TUNING_VALUES",
        )
        need(
            serial["chunks"] == concurrent["chunks"]
            and serial["admissions"] == concurrent["admissions"],
            "TUNING_EQUAL_WORK",
        )
        peaks = {}
        for label, run in (("serial", serial), ("concurrent", concurrent)):
            units = {h: u for h, u in run["units"].items() if u["vector"] is not None}
            policy = {
                "connections": run["workers"],
                "workers": run["workers"],
                "memory": 512 * 1024 * 1024,
                "durable": 128 * 1024 * 1024,
                "operations": 65536,
            }
            try:
                peaks[label] = k17.check_events(units, policy)
            except k17.CheckError as error:
                raise CheckError("TUNING_RUNTIME:" + str(error)) from None
        need(
            peaks["serial"]["workers"] == 1
            and peaks["concurrent"]["workers"] > 1
            # Physical native connections open at the backpressure moment.
            and len(serial["open_sessions"]) == 1
            and len(concurrent["open_sessions"]) > 1,
            "TUNING_OVERLAP",
        )
        found[route] = {
            "order": pair["order"],
            "serial_seconds": serial["elapsed"],
            "concurrent_seconds": concurrent["elapsed"],
            "outcome": "MEASURED_SPEEDUP"
            if concurrent["elapsed"] < serial["elapsed"]
            else "NO_MEASURED_SPEEDUP",
            "peaks": peaks,
            "open_sessions": [
                len(serial["open_sessions"]),
                len(concurrent["open_sessions"]),
            ],
        }
    return found


# --- coordinated damages over REAL matrix raw (original S10/S14 checkers) ------


def tuning_damages(report: dict) -> dict[str, str]:
    """Coordinated damages of one target's real equal-guarantee pairs."""
    route = next(iter(report["pairs"]))

    def runs(r):
        return r["pairs"][route]["tuning"]

    def dropped_value(r):
        runs(r)["concurrent"]["values"]["small"].pop()

    def equal_but_wrong(r):
        # Equal under both policies, yet not the literal oracle's bag.
        for run in runs(r).values():
            run["values"]["slow"].append(run["values"]["slow"][0])

    def serialized(r):
        # The concurrent run's admitted intervals shifted apart (no overlap).
        units = [u for u in runs(r)["concurrent"]["units"].values() if u["vector"]]
        span = 1 + max(n for u in units for n, _k in u["events"])
        for index, unit in enumerate(units):
            unit["events"] = [[n + index * span, k] for n, k in unit["events"]]

    def one_connection(r):
        # Reserved units overlapped, yet a single native connection was open.
        runs(r)["concurrent"]["open_sessions"] = runs(r)["concurrent"]["open_sessions"][
            :1
        ]

    def never_blocked(r):
        runs(r)["serial"]["blocked"] = "STEPPING"

    def cancel_completed(r):
        runs(r)["serial"]["terminals"]["cancelled"] = ["COMPLETED", None, "NONE"]

    def less_work(r):
        runs(r)["concurrent"]["chunks"] -= 1

    return {
        name: rejects(check_tuning, report, change, law)
        for name, change, law in (
            ("dropped_value", dropped_value, "TUNING_VALUES"),
            ("equal_but_wrong", equal_but_wrong, "TUNING_VALUES"),
            ("serialized_concurrent", serialized, "TUNING_OVERLAP"),
            ("one_connection", one_connection, "TUNING_OVERLAP"),
            ("never_blocked", never_blocked, "TUNING_BACKPRESSURE"),
            ("cancel_completed", cancel_completed, "TUNING_TERMINALS"),
            ("less_work", less_work, "TUNING_EQUAL_WORK"),
        )
    }


# S14's own damage family (its checker_damage) and the laws it designated.
R2_DAMAGES = {
    "producing_attempt": "S14_CHECK_OLD_MEMBERS_PRESERVED",
    "hole": "S14_CHECK_NEW_EXACT_COMPLEMENT",
    "frontier": "S14_CHECK_FROZEN_BOUNDS",
    "barrier": "S14_CHECK_BARRIER",
    "prior_unknown": "S14_CHECK_PRIOR_UNKNOWN_PRESERVED",
    "eof": "S14_CHECK_COMPLETE_COVERAGE",
    "capture_plan": "S14_CHECK_CAPTURE_PLAN",
    "history_payload_bit": "S14_CHECK_HISTORY_ORACLE_VALUES",
    "history_saved_membership": "S14_CHECK_HISTORY_CAPTURE",
}


def r2_damages(parts, target: str, histories) -> dict[str, str]:
    """S14's checker_damage, unchanged, over this campaign's own raw: an installed
    bundle R2_seven 39_values recovery on the target's rows route (presented in
    S14's group layout) and the route's B_holes history."""
    import json as _json
    from pathlib import Path
    import tempfile

    import _pietto_phase68_slice14_probe as s14

    route = ROUTES[target][0]
    wanted = [target, route, "refined", "R2_seven", "39_values", "bundle", "installed"]
    item = next(
        r
        for part in parts
        for r in _json.loads(
            (Path(part) / "pietto-phase68-slice19-matrix.json").read_text()
        )["records"]
        if r.get("cell", [])[:7] == wanted
    )
    _data, handoff = _raw(item["capture"]["raw"])
    with tempfile.TemporaryDirectory(prefix="pietto-s19-r2-damage-") as scratch:
        group = {
            "records": [
                {
                    "checked": True,
                    "cell": handoff["cell"],
                    "capture": {"raw": item["capture"]["raw"]},
                    "recover": {"raw": item["recover"]["raw"]},
                }
            ]
        }
        (Path(scratch) / (s14.PREFIX + "r2-group.json")).write_text(_json.dumps(group))
        found = s14.checker_damage(Path(scratch), Path(histories))
    return {name: law.split(":", 1)[0] for name, law in found.items()}


def _rejection(check, value) -> str:
    """Run an original layer checker over a damaged copy; its category."""
    try:
        check(value)
    except Exception as error:  # the original checkers' own failure types
        return str(error).split(":", 1)[0]
    return "ACCEPTED"


def _raw(path) -> tuple[dict, dict]:
    """A matrix worker's raw and public handoff; the parent's own server-session
    observations (persisted beside the raw, never inside it) are attached."""
    import json as _json
    from pathlib import Path

    stem = str(path)[: -len("-raw.json")]
    handoff = _json.loads(Path(stem + "-handoff.json").read_text())
    data = _json.loads(Path(path).read_text())
    sessions = Path(stem + "-sessions.json")
    need(sessions.exists(), "MATRIX_SESSIONS")
    observed = {s["attempt"]: s for s in _json.loads(sessions.read_text())}
    for record in data["results"]:
        seen = observed[record["outcome"]["attempt"]]
        record["session_gone"] = seen["session_gone"]
        record["sessions_gone"] = seen["sessions_gone"]
    return data, handoff


def matrix_recheck(parts, target: str, wheel, install) -> dict:
    """Every cell's raw re-judged here by the original checkers (the parent's
    own verdict is not read): raw digest, origin against the route's own
    installation or the checkout, S10's matrix record against a reference
    rebuilt from the recorded public inputs, S14 capture/recovery/refusal, and
    each origin's driver-free R1 tail against the recovered results."""
    import hashlib
    import json as _json
    from pathlib import Path
    import tempfile

    import _pietto_phase68_slice10_probe as s10
    import _pietto_phase68_slice13_probe as s13
    import _pietto_phase68_slice18_probe as s18
    from _pietto_phase68_slice7_cases import manifest
    from _pietto_phase68_slice10_check import check_matrix_origin, check_matrix_record
    from _pietto_phase68_slice14_check import (
        check_capture,
        check_r1,
        check_recovery,
        check_refused_recovery,
    )

    guards = {c["name"]: c for c in manifest()}
    references: dict = {}
    counts = {"MATRIX": 0, "R2": 0, "NO_R2_BASIS": 0, "DRIFT": 0, "R1": 0}
    with tempfile.TemporaryDirectory(prefix="pietto-s19-recheck-") as scratch:

        def judged(facts):
            raw = Path(facts["raw"])
            need(
                hashlib.sha256(raw.read_bytes()).hexdigest() == facts["sha256"],
                "MATRIX_RAW_DIGEST",
            )
            data, handoff = _raw(raw)
            (route,) = handoff["routes"]
            prefix = Path(install) / (s18.PREFIX + "env-" + s18.ROUTE_RECIPE[route])
            check_matrix_origin(data, handoff, prefix / "bin/python", wheel)
            (record,) = data["results"]
            return record, handoff

        def reference(handoff):
            cell = handoff["cell"]
            key = (cell["group"], cell["case"], cell["variant"])
            if key not in references:
                references[key] = s10.build_native_reference(
                    Path(scratch) / str(len(references)),
                    target,
                    cell,
                    handoff["providers"],
                )
            return references[key]

        for part in parts:
            part = Path(part)
            report = _json.loads(
                (part / "pietto-phase68-slice19-matrix.json").read_text()
            )
            expected: dict = {"source": {}, "installed": {}}
            for item in report["records"]:
                if "excluded" in item:
                    continue
                if "attempt" in item:
                    record, handoff = judged(item["attempt"])
                    cell = handoff["cell"]
                    case = (
                        guards.get(cell["case"]) if cell["group"] == "guarded" else None
                    )
                    check_matrix_record(record, cell, reference(handoff), case=case)
                    counts["MATRIX"] += 1
                    continue
                capture, handoff = judged(item["capture"])
                cell = handoff["cell"]
                case = guards.get(cell["case"]) if cell["group"] == "guarded" else None
                check_capture(capture, cell, case)
                if item.get("basis") == "NO_R2_BASIS":
                    need(
                        capture["s14"] is None and "recover" not in item, "MATRIX_CELL"
                    )
                    counts["NO_R2_BASIS"] += 1
                    continue
                recovered, _handoff = judged(item["recover"])
                if "drift" in item:
                    check_refused_recovery(recovered, capture["s14"])
                    counts["DRIFT"] += 1
                    continue
                check_matrix_record(recovered, cell, reference(handoff), case=case)
                check_recovery(recovered, capture["s14"])
                counts["R2"] += 1
                label = Path(item["recover"]["raw"]).name[: -len("-recover-raw.json")]
                expected[handoff["origin"]][label[len("pietto-phase68-slice19-") :]] = {
                    "rows": recovered["rows"],
                    "generation": capture["s14"]["generation"],
                    "attempts": sorted({m[2] for m in recovered["s14"]["members"]}),
                    "checkpoint": recovered["s14"]["checkpoint"],
                }
            for origin, want in expected.items():
                if not want:
                    continue
                data = _json.loads(
                    (
                        part / ("pietto-phase68-slice14-r1-" + origin + "-raw.json")
                    ).read_text()
                )
                if origin == "installed":
                    s13.installed_members(data, wheel)
                check_r1(data, want)
                counts["R1"] += len(want)
    return counts


# Each matrix damage and the original S10 law designated to reject it.
MATRIX_DAMAGES = {
    "changed_value": "S10_MATRIX_ORIGINAL_FULL_VALUES",
    "collapsed_duplicate": "S10_MATRIX_ORIGINAL_FULL_VALUES",
    "swapped_ordinal": "S10_MATRIX_ORIGINAL_FULL_VALUES",
    "reversed_order": "S10_MATRIX_ORIGINAL_FULL_VALUES",
    "origin_swap": "S10_MATRIX_INSTALLED_ORIGIN",
    "source_elaboration": "S10_MATRIX_SOURCE_FREE",
}


def matrix_damages(parts, target: str, wheel) -> dict[str, str]:
    """Value, multiplicity, field-ordinal, order and origin damages applied
    coherently to real records of a target's matrix parts (record rows,
    post-close rows, every native pull the original checkers re-decode and the
    counts changed together), each judged by the original S10 checkers against
    a reference rebuilt from the recorded public inputs. A damage whose
    precondition no record meets is not applied (the caller requires every
    one)."""
    import hashlib
    import json as _json
    from pathlib import Path
    import tempfile

    import _pietto_phase68_slice10_probe as s10
    from _pietto_phase68_slice6_check import value
    from _pietto_phase68_slice7_cases import manifest
    from _pietto_phase68_slice7_check import metadata
    from _pietto_phase68_slice10_check import check_matrix_origin, check_matrix_record
    from pietto._project.project_execution_reader import decode_native_rows

    records = [
        item
        for part in parts
        for item in _json.loads(
            (Path(part) / "pietto-phase68-slice19-matrix.json").read_text()
        )["records"]
    ]
    rows_route = "mysql_rows" if target == "mysql" else "postgres_rows"
    guards = {c["name"]: c for c in manifest()}
    found: dict[str, str] = {}

    def load(item):
        return _raw(item["attempt"]["raw"])

    def native_pulls(r):
        """The query's native pulls in delivery order: PostgreSQL fetches, or
        the MySQL binary get_rows returns the S08 checker re-decodes."""
        if rows_route != "mysql_rows":
            return next(s for s in r["statements"] if s["purpose"] == "query")[
                "fetches"
            ]
        pulls, binary = [], False
        for event in r["events"]:
            if event["connection"] != "data":
                continue
            if event["event"] == "get_rows.call":
                binary = event["value"]["binary"]
            elif event["event"] == "get_rows.return" and binary:
                pulls.append(event["value"])
        return pulls

    def copies(r):
        """Every stored copy of the rows, position-aligned: record, post-close
        and the native pulls flattened (the same row objects)."""
        return [
            r["rows"],
            r["post_close_rows"],
            [row for pull in native_pulls(r) for row in pull["rows"]],
        ]

    candidates = [
        i
        for i in records
        if "cell" in i
        and i["cell"][1] == rows_route
        and i["cell"][6] == "installed"
        and i["cell"][7] == "MATRIX"
        and i["cell"][2] == "ordinary"
    ]
    with tempfile.TemporaryDirectory(prefix="pietto-s19-damage-") as scratch:
        references: dict[str, Any] = {}

        def rebuilt(item):
            """The case's original reference, rebuilt once from public inputs."""
            handoff = load(item)[1]
            cell = handoff["cell"]
            key = cell["case"] + ":" + str(cell["variant"])
            if key not in references:
                references[key] = s10.build_native_reference(
                    Path(scratch) / str(len(references)),
                    target,
                    cell,
                    handoff["providers"],
                )
            return references[key]

        def decodes(item, r) -> bool:
            """The native rows still decode inside every declared column domain."""
            query = next(s for s in r["statements"] if s["purpose"] == "query")
            meta = (
                tuple(tuple(m) for m in query["metadata"])
                if rows_route == "mysql_rows"
                else metadata(query, rows_route)
            )
            rows = tuple(tuple(value(v) for v in row) for row in copies(r)[2])
            try:
                decode_native_rows(rebuilt(item)[3], rows_route, meta, rows)
            except Exception:  # the original scalar validator's own failure types
                return False
            return True

        def judge(name, item, change):
            data, handoff = load(item)
            cell = handoff["cell"]
            record = data["results"][0]
            case = guards.get(cell["case"])
            check_matrix_record(copy.deepcopy(record), cell, rebuilt(item), case=case)
            damaged_ = copy.deepcopy(record)
            change(damaged_)
            found[name] = _rejection(
                lambda v: check_matrix_record(v, cell, rebuilt(item), case=case),
                damaged_,
            )

        def first(predicate):
            for item in candidates:
                record = load(item)[0]["results"][0]
                if predicate(record):
                    return item
            return None

        def duplicated(r):
            rows = r["rows"]
            return len(rows) != len({_json.dumps(x, sort_keys=True) for x in rows})

        bag = first(
            lambda r: (
                duplicated(r) and any(v.get("kind") == "bool" for v in r["rows"][0])
            )
        )
        if bag is not None:

            def changed_value(r):
                # Overall row 0 of every copy, its first Bool flipped (the
                # MySQL binary carrier holds that Bool as the integer 0 or 1).
                k = next(
                    i for i, v in enumerate(r["rows"][0]) if v.get("kind") == "bool"
                )
                for rows in copies(r):
                    v = rows[0][k]
                    if v["kind"] == "bool":
                        v["value"] = not v["value"]
                    else:
                        v["value"] = {"0": "1", "1": "0"}[v["value"]]

            def collapsed(r):
                # A later occurrence of row 0 removed from the record and
                # post-close rows and, at the record's overall position, from
                # the native pulls; the counts lowered with it.
                target_row = _json.dumps(r["rows"][0], sort_keys=True)
                position = next(
                    i
                    for i in range(1, len(r["rows"]))
                    if _json.dumps(r["rows"][i], sort_keys=True) == target_row
                )
                for rows in [r["rows"], r["post_close_rows"]]:
                    rows.pop(
                        next(
                            i
                            for i in range(1, len(rows))
                            if _json.dumps(rows[i], sort_keys=True) == target_row
                        )
                    )
                for pull in native_pulls(r):
                    if position < len(pull["rows"]):
                        pull["rows"].pop(position)
                        break
                    position -= len(pull["rows"])
                if rows_route != "mysql_rows":
                    next(s for s in r["statements"] if s["purpose"] == "query")[
                        "native_rows"
                    ] -= 1
                r["outcome"]["rows"] -= 1

            judge("changed_value", bag, changed_value)
            judge("collapsed_duplicate", bag, collapsed)

        def exchange(r, i, j):
            for rows in copies(r):
                for x in rows:
                    x[i], x[j] = x[j], x[i]

        def exchangeable(item):
            """The first two row-0 fields of one kind and different values whose
            exchange in every row changes the row bag and keeps the native rows
            inside every declared domain (an ordinal damage, nothing else)."""
            record = load(item)[0]["results"][0]
            row = record["rows"][0] if record["rows"] else []
            before = sorted(_json.dumps(x, sort_keys=True) for x in record["rows"])
            for i in range(len(row)):
                for j in range(i + 1, len(row)):
                    if row[i].get("kind") != row[j].get("kind") or row[i] == row[j]:
                        continue
                    trial = copy.deepcopy(record)
                    exchange(trial, i, j)
                    if before != sorted(
                        _json.dumps(x, sort_keys=True) for x in trial["rows"]
                    ) and decodes(item, trial):
                        return i, j
            return None

        pair = next(
            ((item, p) for item in candidates if (p := exchangeable(item))), None
        )
        if pair is not None:
            (i, j) = pair[1]
            judge("swapped_ordinal", pair[0], lambda r: exchange(r, i, j))
        ordered = next(
            (i for i in candidates if i["cell"][3] == "O_result_order"), None
        )
        if ordered is not None:

            def reversed_order(r):
                for rows in (r["rows"], r["post_close_rows"]):
                    rows.reverse()
                flat = [x for p in native_pulls(r) for x in p["rows"]][::-1]
                for pull in native_pulls(r):
                    n = len(pull["rows"])
                    pull["rows"][:], flat = flat[:n], flat[n:]

            judge("reversed_order", ordered, reversed_order)
        if candidates:
            # Installed modules relabeled as checkout sources with their real
            # (apparently valid) digests.
            data, handoff = load(candidates[0])
            root = Path(__file__).resolve().parents[1]
            for name, entry in data["origins"].items():
                relative = "/".join(name.split(".")) + (
                    "/__init__.py" if entry["path"].endswith("__init__.py") else ".py"
                )
                source = root / "src" / relative
                entry["path"] = str(source)
                entry["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
            interpreter = Path(data["prefix"]) / "bin/python"
            found["origin_swap"] = _rejection(
                lambda v: check_matrix_origin(
                    v, {**handoff, "origin": "installed"}, interpreter, wheel
                ),
                data,
            )
            # A bundle-entry worker that elaborated query source anyway.
            data, handoff = load(
                next(i for i in candidates if i["cell"][5] == "bundle")
            )
            data["forbidden_calls"].append("source_elaboration")
            found["source_elaboration"] = _rejection(
                lambda v: check_matrix_origin(
                    v, handoff, Path(data["prefix"]) / "bin/python", wheel
                ),
                data,
            )
    return found


# --- the whole campaign, re-consumed from its raw ------------------------------


def _rechecks(parts: dict, wheel, install) -> dict:
    """matrix_recheck of every part in its own spawned process (at most four
    at once, the noncampaign heavy ceiling; no fork from this Arrow-loaded
    process); each target's counts are summed over its parts."""
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing

    totals: dict = {}
    with ProcessPoolExecutor(
        max_workers=4, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        futures = [
            (target, pool.submit(matrix_recheck, [d], target, wheel, install))
            for target, dirs in parts.items()
            for d in dirs
        ]
        for target, future in futures:
            found = future.result()
            into = totals.setdefault(target, dict.fromkeys(found, 0))
            for name, count in found.items():
                into[name] += count
    return totals


def campaign_check(directory, wheel, house, install) -> dict:
    """Re-consume every component of one campaign directory with the original
    layer checkers and the S19 laws; returns the per-component verdicts."""
    import hashlib
    import json as _json
    from pathlib import Path

    import _pietto_phase68_slice6_check as s6check
    import _pietto_phase68_slice14_check as s14check
    import _pietto_phase68_slice18_probe as s18

    c = Path(directory)
    verdict: dict[str, Any] = {}

    def report(name, file):
        return _json.loads((c / name / file).read_text())

    # Every part directory the campaign holds per target; the union must still
    # equal the required inventory (check_matrix).
    parts = {
        target: [
            d
            for d in sorted(c.glob("matrix-%s-*" % short), key=lambda d: d.name)
            if d.is_dir()
        ]
        for target, short in (("postgres", "pg"), ("mysql", "mysql"))
    }
    rechecks = _rechecks(parts, wheel, install)
    for target in ("postgres", "mysql"):
        dirs = parts[target]
        reports = [
            _json.loads((d / "pietto-phase68-slice19-matrix.json").read_text())
            for d in dirs
        ]
        need(
            sorted(tuple(r["part"]) for r in reports)
            == [(i, len(reports)) for i in range(len(reports))],
            "MATRIX_PARTS",
        )
        found = check_matrix(target, reports)
        found["recheck"] = rechecks[target]
        need(
            found["recheck"]["MATRIX"]
            + found["recheck"]["R2"]
            + found["recheck"]["NO_R2_BASIS"]
            == found["cells"]
            and found["recheck"]["DRIFT"] == found["drift"]
            and found["recheck"]["R1"] == sum(found["recovered"].values()),
            "MATRIX_RECHECK",
        )
        found["damages"] = matrix_damages(dirs, target, wheel)
        need(found["damages"] == MATRIX_DAMAGES, "MATRIX_DAMAGES")
        found["inventory_damages"] = inventory_damages(
            target,
            [
                r
                for rp in reports
                for r in rp["records"]
                if "cell" in r or "excluded" in r
            ],
        )
        found["report_damages"] = matrix_report_damages(target, reports)
        joint = reports[0]["joint"]
        need(
            sorted(joint["j01"]) == sorted(joint["j02"]) == sorted(ROUTES[target])
            and all(
                [h["history"] for h in item["histories"]] == list(J01_HISTORIES)
                for item in joint["j01"].values()
            ),
            "J01_LINEAGE",
        )
        literal, ordered = s6check.expected(target, "R2_seven", "39_values", None)
        for route, item in joint["j01"].items():
            for history in item["histories"]:
                # The original S14 law, re-run here outside the harness.
                s14check.check_history(
                    history, route, {"rows": literal, "ordered": ordered}
                )
        found["j01"] = {
            route: [check_j01(h) for h in item["histories"]]
            for route, item in joint["j01"].items()
        }
        found["j02"] = {
            route: check_j02(item, target) for route, item in joint["j02"].items()
        }
        rows_route = ROUTES[target][0]
        found["j01_damages"] = j01_damages(
            next(
                h
                for h in joint["j01"][rows_route]["histories"]
                if h["history"] == "C_reply_lost"
            )
        )
        found["j02_damages"] = {
            route: j02_damages(item, target) for route, item in joint["j02"].items()
        }
        found["r2_damages"] = r2_damages(
            dirs, target, dirs[0] / ("pietto-phase68-slice19-j01-" + rows_route)
        )
        need(found["r2_damages"] == R2_DAMAGES, "R2_DAMAGES")
        verdict["matrix-" + target] = found
    for origin in ("source", "installed"):
        raw = report("storage/" + origin, "pietto-phase68-slice19-storage.json")
        view = storage_view(raw, raw["backup"], raw["sink_backup"])
        verdict["storage-" + origin] = {
            "laws": check_storage(view),
            "damages": storage_damages(view),
        }
    for name, target in (("joint-pg", "postgres"), ("joint-mysql", "mysql")):
        raw = report(name, s18.PREFIX + "native.json")
        need(
            raw["status"] == "CHECKED" and raw["source_cleanup"]["status"] == "success",
            "JOINT",
        )
        s18.native_check(c / name, target, raw, list(CELLS))
        verdict[name] = {
            "histories": len(raw["histories"]),
            "lost_replies": len(raw["lost_replies"]),
        }
    raw = _json.loads(
        (c / "compat" / "pietto-phase68-slice19-compat-raw.json").read_text()
    )
    (antlr,) = sorted(Path(house).glob("antlr4_python3_runtime-*.whl"))
    # The archived predecessor the compat family installed, pinned here by digest.
    b19 = Path(raw["archived"]["b19"]["wheel"]).read_bytes()
    need(hashlib.sha256(b19).hexdigest() == B19_SHA256, "CODE_IDENTITY")
    evidence = {
        **{k: raw[k] for k in ("formats", "envelopes", "schema", "s16", "code")},
        "b19_wheel": b19,
        "current_wheel": Path(wheel).read_bytes(),
        "antlr_wheel": antlr.read_bytes(),
    }
    verdict["compat"] = {
        "laws": check_compat(evidence),
        "damages": compat_damages(evidence),
    }
    verdict["tuning"] = {}
    for target in ("postgres", "mysql"):
        # This campaign's pairs plus any complete pair reused under a recorded
        # producing-input bridge (tuning-reused/); each route exactly once.
        pairs: dict = {}
        for base in ("tuning", "tuning-reused"):
            path = c / base / target / "pietto-phase68-slice19-tuning.json"
            if path.exists():
                for route, pair in _json.loads(path.read_text())["pairs"].items():
                    need(route not in pairs, "TUNING_ROUTES")
                    pairs[route] = pair
        need(sorted(pairs) == sorted(ROUTES[target]), "TUNING_ROUTES")
        raw = {"target": target, "pairs": pairs}
        verdict["tuning"][target] = {
            "pairs": check_tuning(raw),
            "damages": tuning_damages(raw),
        }
    controls = {}
    for target in ("postgres", "mysql"):
        data = report("controls/" + target, "pietto-phase68-slice19-controls.json")
        need(all(f["returncode"] == 0 for f in data["families"].values()), "CONTROLS")
    # The original control checkers, re-run here over the families' own raw.
    from _pietto_phase68_slice3_cases import verify_product
    from _pietto_phase68_slice8_check import check_controls as check08
    from _pietto_phase68_slice9_check import check_controls, check_source_controls

    controls["s03"] = verify_product(
        report("controls/postgres", "s03/run/pietto-phase68-slice03-report.json")
    )
    worker = report(
        "controls/postgres",
        "s09/run/pietto-phase68-slice09-controls-source/pietto-phase68-slice09-worker.json",
    )
    check_controls(worker["controls"])
    check_source_controls(worker["source_controls"])
    controls["s09"] = [c["control"] for c in worker["controls"]]
    found08 = report("controls/mysql", "s08/run/pietto-phase68-slice08-controls.json")
    kinds = [r["kind"] for r in found08["controls"]]
    check08(found08["controls"], kinds)
    controls["s08"] = kinds
    verdict["controls"] = controls
    consumer = report("consumer", "pietto-phase68-slice19-consumer.json")
    need(
        consumer["provenance"] == "LOCAL"
        # The archived receipts replay under their original identity, which
        # the local checkout must still be at (before the S19 commit).
        and consumer["head"] == "35fb67afa3d12088de7571bfe313c296a68a2f0d"
        and [s["step"] for s in consumer["steps"]]
        == [
            "package_smoke",
            "arrow_readiness",
            "check_arrow",
            "result_product",
            "check_product",
            "consumer_prepare",
            "consumer_replay",
            "consumer_verify",
        ]
        and all(s["returncode"] == 0 for s in consumer["steps"]),
        "CONSUMER",
    )
    # Both CI-shaped builds reproduce the candidate wheel's exact bytes.
    current = hashlib.sha256(Path(wheel).read_bytes()).hexdigest()
    need(set(consumer["wheels"].values()) == {current}, "CONSUMER")
    verdict["consumer"] = {"label": consumer["label"], "wheel": current}
    return verdict
