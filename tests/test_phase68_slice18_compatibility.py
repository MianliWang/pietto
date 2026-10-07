"""S18 compatibility laws and the independent checker.

Core (no Arrow, no database): the v1-v7 capability matrix and the envelope /
recognized-schema programs run in a fresh registered core interpreter on the
qualified local profile (elsewhere the profile refusal is the observation);
the checker's artifact, compatibility-identity, origin, cell, saved-tail and
inventory laws run on constructed evidence (MODEL), each coordinated damage
rejected by its designated law. Installed and archived observations come from
scripts/phase68_slice18_probe.py.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import zipfile

import pytest

import _pietto_phase68_slice18_check as check
import _pietto_phase68_slice18_probe as probe
from _pietto_phase68_slice11_probe import qualified
from test_phase11_packaging_smoke import _metadata_bytes

ROOT = Path(__file__).resolve().parents[1]
INFO = "pietto-0.1.0.dist-info/"
PREFIX = "/owned/prefix"
SITE = PREFIX + "/lib/python3.13/site-packages/"


def _zip(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _wheel(metadata: bytes | None = None, salt: bytes = b"") -> bytes:
    members = {name: b"# " + name.encode() + salt + b"\n" for name in check.OWNERS}
    members["pietto/__init__.py"] = b"# pietto" + salt + b"\n"
    members[INFO + "METADATA"] = metadata or _metadata_bytes()
    members[INFO + "WHEEL"] = b"Wheel-Version: 1.0\n"
    members[INFO + "entry_points.txt"] = (
        b"[console_scripts]\npietto = pietto.cli:main\n"
    )
    rows = [[n, check._record_digest(d), str(len(d))] for n, d in members.items()]
    rows.append([INFO + "RECORD", "", ""])
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    members[INFO + "RECORD"] = out.getvalue().encode()
    return _zip(members)


def _sdist(wheel: bytes) -> bytes:
    members = {
        "pietto-0.1.0/PKG-INFO": _metadata_bytes(),
        "pietto-0.1.0/pyproject.toml": (ROOT / "pyproject.toml").read_bytes(),
    }
    for name, data in check.wheel_members(wheel).items():
        if name.startswith("pietto/") and name.endswith(".py"):
            members["pietto-0.1.0/src/" + name] = data
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_artifact_law_accepts_exact_declarations_and_rejects_coordinated_damage():
    wheel = _wheel()
    sdist = _sdist(wheel)
    assert check.check_artifacts(wheel, sdist)["modules"] == len(check.OWNERS) + 1
    for kind in ("D1_optional_into_core", "D2_route_dependency_removed"):
        damage, family, law = check.DAMAGES[kind]
        evidence = {"wheel_bytes": wheel}
        damage(evidence)
        assert evidence["wheel_bytes"] != wheel
        with pytest.raises(check.Rejected) as raised:
            check.check_artifacts(evidence["wheel_bytes"], sdist)
        assert (family, raised.value.law) == ("install", law)
    members = check.wheel_members(wheel)
    members["pietto/cli.py"] += b"# changed without RECORD\n"
    with pytest.raises(check.Rejected, match="WHEEL_RECORD"):
        check.check_artifacts(_zip(members), sdist)
    with pytest.raises(check.Rejected, match="SDIST_MEMBERS"):
        check.check_artifacts(wheel, _sdist(_wheel(salt=b" other")))


def test_identity_recomputation_equals_the_running_compiler():
    import antlr4
    from pietto._project.project_compiled_loading import semantic_build_identity

    package = ROOT / "src/pietto"
    pietto = {
        "pietto/" + p.relative_to(package).as_posix(): p.read_bytes()
        for p in package.rglob("*.py")
    }
    library = Path(antlr4.__file__).resolve().parent
    runtime = {
        "antlr4/" + p.relative_to(library).as_posix(): p.read_bytes()
        for p in library.rglob("*.py")
    }
    assert check.compatibility_identity(_zip(pietto), _zip(runtime)) == (
        semantic_build_identity()
    )
    changed = {**pietto, "pietto/_project/project_execution.py": b"# other\n"}
    assert check.compatibility_identity(_zip(changed), _zip(runtime)) != (
        semantic_build_identity()
    )


def _facts(wheel: bytes) -> dict:
    origins = {}
    for name, data in check.wheel_members(wheel).items():
        if name.startswith("pietto/") and name.endswith(".py"):
            module = name[:-3].replace("/", ".").removesuffix(".__init__")
            origins[module] = {
                "path": SITE + name,
                "sha256": hashlib.sha256(data).hexdigest(),
            }
    return {
        "prefix": PREFIX,
        "distributions": {"pietto": "0.1.0", "antlr4_python3_runtime": "4.13.2"},
        "direct_url": {"url": "file:///owned/pietto-0.1.0-py3-none-any.whl"},
        "wheel_sha256": hashlib.sha256(wheel).hexdigest(),
        "origins": origins,
        "lazy": [],
        "arrow": "ARROW_DEPENDENCY_MISSING",
        "routes": {
            route: {"result": "EXECUTION_DEPENDENCY_MISSING", "loaded": []}
            for route in check.ROUTES
        },
        "cli": {"check": 0},
    }


def _cell(wheel: bytes) -> dict:
    path = "/owned/pietto-0.1.0-py3-none-any.whl"
    return {
        "recipe": "core",
        "extras": [],
        "prefix": PREFIX,
        "wheel": path,
        "install": {
            "argv": [
                "uv",
                "pip",
                "install",
                "--python",
                PREFIX + "/bin/python",
                "--no-index",
                "--find-links",
                "/owned/wheelhouse",
                "--constraint",
                "/owned/constraints.txt",
                "--link-mode",
                "copy",
                "--strict",
                path,
            ],
            "returncode": 0,
        },
        "check": {"returncode": 0},
        "facts": _facts(wheel),
    }


def test_cell_law_accepts_a_clean_core_cell_and_names_each_rejection():
    wheel = _wheel()
    cell = _cell(wheel)
    assert check.check_cell(cell, wheel)["distributions"] == 2
    foreign = hashlib.sha256(b"same-version module of another wheel").hexdigest()
    cases = {
        "D3_foreign_origin": lambda e: check.DAMAGES["D3_foreign_origin"][0](e),
        "D4_altered_member": lambda e: check.DAMAGES["D4_altered_member"][0](e),
    }
    for kind, damage in cases.items():
        evidence = {"cells": [copy.deepcopy(cell)], "foreign_sha256": foreign}
        damage(evidence)
        with pytest.raises(check.Rejected) as raised:
            check.check_cell(evidence["cells"][0], wheel)
        assert raised.value.law == check.DAMAGES[kind][2]
    variants = (
        ("RESOLVER_COMMAND", lambda c: c["install"]["argv"].insert(3, "--no-deps")),
        ("RESOLVER_COMMAND", lambda c: c["install"]["argv"].remove("--no-index")),
        ("RESOLVER_CHECK", lambda c: c["check"].update(returncode=1)),
        (
            "CELL_CLOSURE",
            lambda c: c["facts"]["distributions"].update(pyarrow="25.0.1"),
        ),
        ("ORIGIN_SET", lambda c: c["facts"]["origins"].pop("pietto.cli")),
        (
            "ORIGIN_PREFIX",
            lambda c: c["facts"]["origins"]["pietto.cli"].update(
                path="/checkout/src/pietto/cli.py"
            ),
        ),
        ("ORIGIN_WHEEL", lambda c: c["facts"].update(wheel_sha256="0" * 64)),
        ("LAZY_IMPORT", lambda c: c["facts"].update(lazy=["psycopg"])),
        ("ARROW_BOUNDARY", lambda c: c["facts"].update(arrow="25.0.1")),
        (
            "ROUTE_MISSING",
            lambda c: c["facts"]["routes"]["mysql_rows"].update(result="OK"),
        ),
        (
            "ROUTE_FALLBACK",
            lambda c: c["facts"]["routes"]["postgres_adbc"].update(loaded=["psycopg"]),
        ),
    )
    for law, damage in variants:
        damaged = copy.deepcopy(cell)
        damage(damaged)
        with pytest.raises(check.Rejected) as raised:
            check.check_cell(damaged, wheel)
        assert raised.value.law == law


def _matrix() -> dict:
    out = {}
    for version, (fmt, features) in enumerate(check.FEATURES.items(), start=1):
        gates = {
            feature: ("PASSED_GATE" if feature in features else code)
            for feature, code in check.GATES.items()
        }
        gates["bounded-job-runtime"] = (
            "OPENED"
            if "bounded-job-runtime" in features
            else gates["bounded-job-runtime"]
        )
        out[fmt] = {
            "features": list(features),
            "user_version": version,
            "gates": gates,
            "runtime": gates["bounded-job-runtime"],
            "unchanged": True,
        }
    return out


def _compat() -> dict:
    antlr = _zip({"antlr4/__init__.py": b"# runtime\n"})
    old, now = _wheel(salt=b" s17"), _wheel(salt=b" s18")
    return {
        "formats": {"current": _matrix(), "s17": _matrix()},
        "envelopes": [
            {"damage": d, "outcome": "WORKSPACE_FORMAT", "unchanged": True}
            for d in (
                "future_format",
                "unknown_feature",
                "relabeled_v6",
                "reordered_features",
            )
        ],
        "s16": {
            "outcome": "WORKSPACE_FORMAT",
            "unchanged": True,
            "format": "pietto.job-workspace.v1",
        },
        "schema": {"outcome": "WORKSPACE_SCHEMA"},
        "code": {
            "s17_identity": check.compatibility_identity(old, antlr),
            "current_identity": check.compatibility_identity(now, antlr),
            "source_identity": check.compatibility_identity(now, antlr),
            "s17_self": "LOADED",
            "s17_binding": "BOUND",
            "load": "COMPILED_COMPATIBILITY",
            "open": "OPENED",
            "binding_s17": "JOB_COMPATIBILITY",
            "binding_current": "JOB_COMPATIBILITY",
            "fresh": "ACCEPTED",
        },
        "s17_wheel": old,
        "current_wheel": now,
        "antlr_wheel": antlr,
    }


def test_compatibility_law_and_its_damages():
    evidence = _compat()
    verdict = check.check_compat(evidence)
    assert verdict["s17_identity"] != verdict["current_identity"]
    assert check.rejects("D5_unknown_feature", evidence) == "FORMAT_FEATURES"
    assert check.rejects("D6_laundered_compatibility", evidence) == "CODE_IDENTITY"
    variants = (
        (
            "FORMAT_UNCHANGED",
            lambda e: e["formats"]["s17"]["pietto.job-workspace.v3"].update(
                user_version=3, schema="x"
            ),
        ),
        (
            "FORMAT_GATE",
            lambda e: e["formats"]["current"]["pietto.job-workspace.v6"][
                "gates"
            ].update({"concurrent-gc": "PASSED_GATE"}),
        ),
        ("ENVELOPE_BEFORE_SQLITE", lambda e: e["envelopes"][1].update(unchanged=False)),
        ("ARCHIVED_REFUSAL", lambda e: e["s16"].update(outcome="ACCEPTED")),
        ("RECOGNIZED_SCHEMA", lambda e: e["schema"].update(outcome="ACCEPTED")),
        ("CODE_COMPATIBILITY", lambda e: e["code"].update(binding_s17="BOUND")),
        ("CODE_IDENTITY", lambda e: e.update(current_wheel=e["s17_wheel"])),
    )
    for law, damage in variants:
        damaged = copy.deepcopy(evidence)
        damage(damaged)
        with pytest.raises(check.Rejected) as raised:
            check.check_compat(damaged)
        assert raised.value.law == law


def _saved() -> dict:
    return {
        "installed_drivers": [],
        "loaded_drivers": [],
        "connections": [],
        "refusals": [
            {
                "kind": "submit",
                "mode": "RECOVER",
                "result": "EXECUTION_DEPENDENCY_MISSING",
                "admissions_before": 3,
                "admissions_after": 3,
                "records": 0,
            },
            {
                "kind": "owner",
                "route": "postgres_rows",
                "result": "EXECUTION_DEPENDENCY_MISSING",
                "socket_attempts": 0,
                "connected": False,
            },
        ],
        "restart": {
            "first": [0, 2],
            "reissued": [0, 2],
            "acknowledged_before_restart": [],
            "acknowledged_after": [[0, 2]],
        },
        "query": {"published": True, "read_terminal": "COMPLETED"},
        "reclaimed": 2,
        "retained": {
            "protected": True,
            "removed": [],
            "root": "CONSUMER",
            "released_removed": 2,
        },
        "lost_reply": {
            "issued": 2,
            "sink_effects_after_cut": 2,
            "confirmed_after_cut": 0,
            "statuses": {"0": "PRESENT_MATCHING", "1": "PRESENT_MATCHING"},
            "sink_effects_final": 3,
            "rows": 3,
            "positions_final": [0, 1, 2],
            "commits_final": 3,
        },
    }


def test_saved_tail_law_and_its_damages():
    saved = _saved()
    assert check.check_saved(saved)["reclaimed"] == 2
    assert check.check_saved({**saved, "retained": None, "lost_reply": None})
    assert check.rejects("D7_hidden_source_access", {"saved": saved}) == (
        "SAVED_SOURCE_ACCESS"
    )
    variants = (
        ("SAVED_SOURCE_ACCESS", lambda s: s["connections"].append("socket_connect")),
        ("ARROW_ONLY_REFUSAL", lambda s: s["refusals"][0].update(admissions_after=4)),
        ("ARROW_ONLY_REFUSAL", lambda s: s["refusals"][1].update(socket_attempts=1)),
        ("ARROW_ONLY_REFUSAL", lambda s: s["refusals"][1].update(result="OPENED")),
        ("INVENTORY", lambda s: s["refusals"].pop()),
        (
            "SAVED_RESTART_WINDOW",
            lambda s: s["restart"].update(acknowledged_before_restart=[[0, 2]]),
        ),
        ("SAVED_RESTART_WINDOW", lambda s: s["restart"].update(reissued=[2, 4])),
        ("PUBLICATION_QUERY", lambda s: s["query"].update(published=False)),
        (
            "RETAINED_CONSUMER",
            lambda s: s["retained"].update(removed=[["chk-1", "UNLINKED"]]),
        ),
        ("RETAINED_CONSUMER", lambda s: s["retained"].update(root="NONE")),
        ("RETAINED_CONSUMER", lambda s: s["retained"].update(released_removed=0)),
        ("RECLAIMED", lambda s: s.update(reclaimed=0)),
        (
            "SINK_LOST_REPLY",
            lambda s: s["lost_reply"].update(
                commits_final=4, sink_effects_final=4, positions_final=[0, 1, 1, 2]
            ),
        ),
        ("SINK_LOST_REPLY", lambda s: s["lost_reply"].update(confirmed_after_cut=2)),
        (
            "SINK_LOST_REPLY",
            lambda s: s["lost_reply"]["statuses"].update({"1": "COMMITTED"}),
        ),
    )
    for law, damage in variants:
        damaged = copy.deepcopy(saved)
        damage(damaged)
        with pytest.raises(check.Rejected) as raised:
            check.check_saved(damaged)
        assert raised.value.law == law


def test_inventory_law_and_a_removed_cell():
    requested = [(o, e) for o in ("source", "installed") for e in ("live", "bundle")]
    report = {
        "routes": ["postgres_rows", "postgres_adbc"],
        "histories": [
            {"route": r, "entry": e, "origin": o}
            for r in ("postgres_rows", "postgres_adbc")
            for o, e in requested
        ],
    }
    report["cell_count"] = len(report["histories"])
    check.check_inventory(report, requested)
    evidence = {"report": report, "requested": requested}
    assert check.rejects("D8_cell_removed", evidence) == "INVENTORY"
    duplicated = copy.deepcopy(report)
    duplicated["histories"][-1] = dict(duplicated["histories"][0])
    with pytest.raises(check.Rejected, match="INVENTORY"):
        check.check_inventory(duplicated, requested)
    with pytest.raises(check.Rejected, match="INVENTORY"):
        check.check_inventory(report, requested[:-1])


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"events": [], "owned_resources": []}))
    return ledger


def test_current_capability_matrix_envelopes_and_schema_in_a_fresh_process(tmp_path):
    if not qualified(tmp_path):
        return
    ledger = _ledger(tmp_path)
    run = tmp_path / "run"
    run.mkdir()

    def worker(program, name):
        return probe._worker(
            run,
            ledger,
            sys.executable,
            probe.HEADER + program,
            {"tests": str(ROOT / "tests")},
            probe.PREFIX + name,
            origin="source",
        )

    matrix = worker(probe.MATRIX, "matrix")["matrix"]
    check.check_formats(matrix)
    damaged = copy.deepcopy({"formats": {"current": matrix}})
    check.DAMAGES["D5_unknown_feature"][0](damaged)
    with pytest.raises(check.Rejected, match="FORMAT_FEATURES"):
        check.check_formats(damaged["formats"]["current"])
    observed = worker(probe.ENVELOPES, "envelopes")
    assert [
        (e["damage"], e["outcome"], e["unchanged"]) for e in observed["envelopes"]
    ] == [
        ("future_format", "WORKSPACE_FORMAT", True),
        ("unknown_feature", "WORKSPACE_FORMAT", True),
        ("relabeled_v6", "WORKSPACE_FORMAT", True),
        ("reordered_features", "WORKSPACE_FORMAT", True),
    ]
    assert observed["schema"] == {"outcome": "WORKSPACE_SCHEMA"}
    events = json.loads(ledger.read_text())["events"]
    assert [e["kind"] for e in events] == ["registered_worker", "worker_reaped"] * 2
    assert all(e["returncode"] == 0 for e in events if e["kind"] == "worker_reaped")
