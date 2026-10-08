"""Independent S18 judgement over raw installation, compatibility and handoff
records; import acquires nothing.

The expectations below are this checker's own literal statement of the S18
selections, artifact declarations, workspace formats and route modules. They
are not derived from pyproject, the lock, package_smoke or any producer, and no
producer field named status/PASS is ever read as a verdict. Archive members and
compatibility identities are recomputed from the actual wheel bytes.
"""

from __future__ import annotations

import base64
import copy
import csv
import hashlib
import io
import json
import re
import tarfile
import zipfile
from email import policy
from email.parser import BytesParser

CORE = {"pietto": "0.1.0", "antlr4-python3-runtime": "4.13.2"}
ARROW = {**CORE, "pyarrow": "25.0.1"}
POSTGRES = {**ARROW, "psycopg": "3.3.5", "psycopg-binary": "3.3.5"}
MYSQL = {**ARROW, "mysql-connector-python": "26.7.0"}
ADBC = {
    **ARROW,
    "adbc-driver-postgresql": "1.12.0",
    "adbc-driver-manager": "1.12.0",
    "importlib-resources": "7.1.0",
    "typing-extensions": "4.16.0",
}
# Installed closure of each selection on CPython 3.13 Linux x86-64.
SELECTIONS = {
    "core": CORE,
    "arrow": ARROW,
    "execute-postgres": POSTGRES,
    "execute-mysql": MYSQL,
    "execute-postgres-adbc": ADBC,
    "union": {**POSTGRES, **MYSQL, **ADBC},
}
EXTRAS = {
    "core": (),
    "arrow": ("arrow",),
    "execute-postgres": ("execute-postgres",),
    "execute-mysql": ("execute-mysql",),
    "execute-postgres-adbc": ("execute-postgres-adbc",),
    "union": ("execute-postgres", "execute-mysql", "execute-postgres-adbc"),
}
# Artifact Requires-Dist: (name, requirement extras, specifier, extra marker).
REQUIRES = frozenset(
    {
        ("antlr4-python3-runtime", (), ">=4.13.2", None),
        ("pyarrow", (), "==25.0.1", "arrow"),
        ("pyarrow", (), "==25.0.1", "execute-postgres"),
        ("psycopg", ("binary",), "==3.3.5", "execute-postgres"),
        ("pyarrow", (), "==25.0.1", "execute-mysql"),
        ("mysql-connector-python", (), "==26.7.0", "execute-mysql"),
        ("pyarrow", (), "==25.0.1", "execute-postgres-adbc"),
        ("adbc-driver-postgresql", (), "==1.12.0", "execute-postgres-adbc"),
        ("adbc-driver-manager", (), "==1.12.0", "execute-postgres-adbc"),
    }
)
PROVIDES = ("arrow", "execute-postgres", "execute-mysql", "execute-postgres-adbc")
ROUTES = ("postgres_rows", "postgres_adbc", "mysql_rows")
ROUTE_SELECTION = {
    "postgres_rows": "execute-postgres",
    "postgres_adbc": "execute-postgres-adbc",
    "mysql_rows": "execute-mysql",
}
# Top-level modules each route's own driver check may load.
ROUTE_MODULES = {
    "postgres_rows": frozenset({"psycopg", "psycopg_binary"}),
    "postgres_adbc": frozenset(
        {"adbc_driver_postgresql", "adbc_driver_manager", "pyarrow"}
    ),
    # mysql-connector-python also ships its optional C extension module.
    "mysql_rows": frozenset({"mysql", "_mysql_connector"}),
}
# Owners that must be wheel members and must have run from the wheel.
OWNERS = tuple(
    "pietto/_project/" + name + ".py"
    for name in (
        "project_compiled_loading",
        "project_compiled_build",
        "project_execution",
        "project_execution_postgres",
        "project_execution_postgres_adbc_native",
        "project_execution_mysql_native",
        "project_job_workspace",
        "project_job_store",
        "project_job_store_verification",
        "project_job_chunks",
        "project_job_capture",
        "project_job_replay",
        "project_job_extraction",
        "project_job_delivery",
        "project_job_sink",
        "project_job_publication",
        "project_job_runtime",
        "project_job_collection",
        "project_arrow_result",
        "project_result_contract",
    )
) + ("pietto/cli.py", "pietto/generated/PiettoParser.py")
FEATURES = {
    "pietto.job-workspace.v1": (),
    "pietto.job-workspace.v2": ("result-chunks",),
    "pietto.job-workspace.v3": ("result-chunks", "saved-replay"),
    "pietto.job-workspace.v4": ("result-chunks", "saved-replay", "extraction-resume"),
    "pietto.job-workspace.v5": (
        "result-chunks",
        "saved-replay",
        "extraction-resume",
        "cooperative-delivery",
    ),
    "pietto.job-workspace.v6": (
        "result-chunks",
        "saved-replay",
        "extraction-resume",
        "cooperative-delivery",
        "complete-publication",
    ),
    "pietto.job-workspace.v7": (
        "result-chunks",
        "saved-replay",
        "extraction-resume",
        "cooperative-delivery",
        "complete-publication",
        "bounded-job-runtime",
        "concurrent-gc",
    ),
}
GATES = {
    "result-chunks": "WORKSPACE_CAPTURE_FORMAT",
    "saved-replay": "WORKSPACE_REPLAY_FORMAT",
    "extraction-resume": "WORKSPACE_EXTRACTION_FORMAT",
    "cooperative-delivery": "WORKSPACE_DELIVERY_FORMAT",
    "complete-publication": "WORKSPACE_PUBLICATION_FORMAT",
    "bounded-job-runtime": "WORKSPACE_RUNTIME_FORMAT",
    "concurrent-gc": "WORKSPACE_COLLECTION_FORMAT",
}
NATIVE_CELLS = frozenset(
    (route, entry, origin)
    for route in ROUTES
    for entry in ("live", "bundle")
    for origin in ("source", "installed")
)


class Rejected(ValueError):
    """A named law rejected the evidence."""

    def __init__(self, law: str):
        super().__init__(law)
        self.law = law


def need(condition, law: str) -> None:
    if not condition:
        raise Rejected(law)


def normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement(text: str):
    """This checker's own parse of one Requires-Dist value."""
    body, _, marker = text.partition(";")
    found = re.fullmatch(
        r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[([^\]]*)\])?\s*\(?\s*([<>=!~]=?)\s*"
        r"([0-9][0-9.]*)\s*\)?\s*",
        body,
    )
    need(found is not None, "METADATA_REQUIRES")
    assert found is not None
    name, extras, operator, version = found.groups()
    names = tuple(sorted({normal(e) for e in (extras or "").split(",") if e.strip()}))
    extra = None
    if marker.strip():
        selected = re.fullmatch(
            r"\s*\(?\s*extra\s*==\s*['\"]([^'\"]+)['\"]\s*\)?\s*", marker
        )
        need(selected is not None, "METADATA_REQUIRES")
        assert selected is not None
        extra = selected[1]
    return normal(name), names, operator + version, extra


def _declarations(metadata: bytes) -> dict:
    message = BytesParser(policy=policy.default).parsebytes(metadata)
    return {
        "name": message.get_all("Name"),
        "version": message.get_all("Version"),
        "requires_python": message.get_all("Requires-Python"),
        "requires": [requirement(str(v)) for v in message.get_all("Requires-Dist", ())],
        "provides": message.get_all("Provides-Extra", []),
    }


def _same_declarations(found: dict) -> None:
    need(
        (found["name"], found["version"], found["requires_python"])
        == (["pietto"], ["0.1.0"], [">=3.12"]),
        "METADATA_IDENTITY",
    )
    need(
        len(found["requires"]) == len(set(found["requires"]))
        and frozenset(found["requires"]) == REQUIRES,
        "METADATA_REQUIRES",
    )
    need(
        sorted(found["provides"]) == sorted(PROVIDES)
        and len(found["provides"]) == len(PROVIDES),
        "METADATA_PROVIDES",
    )


def _record_digest(data: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(
        b"="
    ).decode("ascii")


def wheel_members(wheel: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
        return {n: archive.read(n) for n in archive.namelist() if not n.endswith("/")}


def check_artifacts(wheel: bytes, sdist: bytes) -> dict:
    """Wheel METADATA/entry/RECORD and sdist PKG-INFO/members from the bytes."""
    members = wheel_members(wheel)
    info = "pietto-0.1.0.dist-info/"
    need(all(o in members for o in OWNERS), "WHEEL_MEMBERS")
    _same_declarations(_declarations(members[info + "METADATA"]))
    entry = members[info + "entry_points.txt"].decode()
    need(
        re.search(
            r"^\[console_scripts\]\s*\npietto = pietto\.cli:main\s*$", entry, re.M
        )
        is not None,
        "WHEEL_ENTRY",
    )
    rows = list(csv.reader(io.StringIO(members[info + "RECORD"].decode())))
    listed = {row[0]: row for row in rows}
    need(set(listed) == set(members), "WHEEL_RECORD")
    for name, data in members.items():
        if name == info + "RECORD":
            continue
        need(
            listed[name][1] == _record_digest(data)
            and listed[name][2] == str(len(data)),
            "WHEEL_RECORD",
        )
    with tarfile.open(fileobj=io.BytesIO(sdist), mode="r:gz") as archive:
        names = archive.getnames()
        prefix = "pietto-0.1.0/"
        pkg = archive.extractfile(prefix + "PKG-INFO")
        need(pkg is not None, "SDIST_MEMBERS")
        assert pkg is not None
        _same_declarations(_declarations(pkg.read()))
        for name, data in members.items():
            if name.endswith(".py") and name.startswith("pietto/"):
                handle = archive.extractfile(prefix + "src/" + name)
                need(handle is not None and handle.read() == data, "SDIST_MEMBERS")
        need(prefix + "pyproject.toml" in names, "SDIST_MEMBERS")
    modules = sorted(
        n for n in members if n.startswith("pietto/") and n.endswith(".py")
    )
    return {"members": len(members), "modules": len(modules)}


def compatibility_identity(wheel: bytes, antlr_wheel: bytes) -> str:
    """Recompute `semantic_build_identity` of an installation of these exact
    wheels (all `.py` of the pietto and antlr4 packages, in path order)."""
    digest = hashlib.sha256(b"pietto.compiled-semantic-code.v1\0")
    for name, data, package, release in (
        ("pietto", wheel, "pietto/", "resolved-code"),
        ("antlr4-python3-runtime", antlr_wheel, "antlr4/", "4.13.2"),
    ):
        label = (name + "\0" + release).encode("utf-8")
        digest.update(len(label).to_bytes(8, "big"))
        digest.update(label)
        members = wheel_members(data)
        for member in sorted(
            (m for m in members if m.startswith(package) and m.endswith(".py")),
            key=lambda m: tuple(m[len(package) :].split("/")),
        ):
            relative = member[len(package) :].encode("utf-8")
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(len(members[member]).to_bytes(8, "big"))
            digest.update(members[member])
    return digest.hexdigest()


def check_wheelhouse(entries: list, lock: dict) -> None:
    """Every wheelhouse file is the lock's exact artifact (URL, size, hash)."""
    recorded = {}
    for package in lock["package"]:
        for wheel in package.get("wheels", ()):
            recorded[wheel["url"]] = (
                normal(package["name"]),
                package["version"],
                wheel,
            )
    names = set()
    for entry in entries:
        need(entry["url"] in recorded, "WHEELHOUSE_ARTIFACT")
        name, version, wheel = recorded[entry["url"]]
        need(
            entry["url"].startswith("https://files.pythonhosted.org/")
            and entry["bytes"] == wheel["size"]
            and "sha256:" + entry["sha256"] == wheel["hash"]
            and entry["file"] == entry["url"].rsplit("/", 1)[1],
            "WHEELHOUSE_ARTIFACT",
        )
        names.add((name, version))
    expected = {(n, v) for n, v in SELECTIONS["union"].items() if n != "pietto"}
    need(names == expected and len(entries) == len(expected), "WHEELHOUSE_SET")


def check_origins(facts: dict, members: dict[str, bytes], prefix: str) -> None:
    """Every loaded pietto module ran from this prefix with the wheel's bytes,
    and every wheel module was loaded."""
    modules = {
        n[:-3].replace("/", ".").removesuffix(".__init__"): n
        for n in members
        if n.startswith("pietto/") and n.endswith(".py")
    }
    origins = facts["origins"]
    need(set(origins) == set(modules), "ORIGIN_SET")
    for name, item in origins.items():
        need(item["path"].startswith(prefix + "/lib/"), "ORIGIN_PREFIX")
        need(
            item["path"].endswith("/site-packages/" + modules[name])
            and item["sha256"] == hashlib.sha256(members[modules[name]]).hexdigest(),
            "ORIGIN_BYTES",
        )


def check_cell(cell: dict, wheel: bytes) -> dict:
    """One clean resolver materialization and its installed facts."""
    recipe = cell["recipe"]
    members = wheel_members(wheel)
    need(EXTRAS[recipe] == tuple(cell["extras"]), "CELL_SELECTION")
    install = cell["install"]
    argv = install["argv"]
    target = argv[-1]
    requested = target.partition("[")[2].rstrip("]")
    need(
        install["returncode"] == 0
        and "--no-deps" not in argv
        and "--no-index" in argv
        and "--find-links" in argv
        and "--constraint" in argv
        and argv[argv.index("--python") + 1] == cell["prefix"] + "/bin/python"
        and target.partition("[")[0] == cell["wheel"]
        and tuple(e for e in requested.split(",") if e) == EXTRAS[recipe],
        "RESOLVER_COMMAND",
    )
    need(cell["check"]["returncode"] == 0, "RESOLVER_CHECK")
    facts = cell["facts"]
    need(facts["prefix"] == cell["prefix"], "ORIGIN_PREFIX")
    installed = {normal(n): v for n, v in facts["distributions"].items()}
    need(installed == SELECTIONS[recipe], "CELL_CLOSURE")
    direct = facts["direct_url"]
    need(
        direct["url"] == "file://" + cell["wheel"]
        and set(direct) <= {"url", "archive_info"},
        "ORIGIN_WHEEL",
    )
    need(facts["wheel_sha256"] == hashlib.sha256(wheel).hexdigest(), "ORIGIN_WHEEL")
    check_origins(facts, members, cell["prefix"])
    need(facts["lazy"] == [], "LAZY_IMPORT")
    need(
        facts["arrow"]
        == ("ARROW_DEPENDENCY_MISSING" if recipe == "core" else "25.0.1"),
        "ARROW_BOUNDARY",
    )
    selected = set(EXTRAS[recipe])
    for route in ROUTES:
        outcome = facts["routes"][route]
        if ROUTE_SELECTION[route] in selected:
            need(outcome["result"] == "OK", "ROUTE_AVAILABLE")
            need(set(outcome["loaded"]) <= ROUTE_MODULES[route], "ROUTE_FALLBACK")
        else:
            need(outcome["result"] == "EXECUTION_DEPENDENCY_MISSING", "ROUTE_MISSING")
            need(outcome["loaded"] == [], "ROUTE_FALLBACK")
    if recipe == "union":
        for blocked in facts["no_fallback"]:
            need(blocked["result"] == "EXECUTION_DEPENDENCY_MISSING", "ROUTE_MISSING")
            need(blocked["loaded"] == [], "ROUTE_FALLBACK")
    return {
        "recipe": recipe,
        "distributions": len(installed),
        "modules": len(facts["origins"]),
    }


def check_install(evidence: dict) -> dict:
    """The six cells, their shared wheel, CLI agreement and the negatives."""
    wheel, sdist = evidence["wheel_bytes"], evidence["sdist_bytes"]
    artifacts = check_artifacts(wheel, sdist)
    check_wheelhouse(evidence["wheelhouse"], evidence["lock"])
    cells = evidence["cells"]
    need(
        sorted(c["recipe"] for c in cells) == sorted(SELECTIONS)
        and len({c["prefix"] for c in cells}) == len(SELECTIONS),
        "INVENTORY",
    )
    need(len({c["wheel"] for c in cells}) == 1, "SAME_WHEEL")
    outputs = {json.dumps(c["facts"]["cli"], sort_keys=True) for c in cells}
    need(len(outputs) == 1 and json.loads(outputs.pop())["check"] == 0, "CLI_AGREEMENT")
    checked = [check_cell(c, wheel) for c in cells]
    negatives = {n["kind"]: n for n in evidence["negatives"]}
    need(set(negatives) == {"conflicting_constraint", "missing_artifact"}, "INVENTORY")
    for item in negatives.values():
        need(
            item["returncode"] != 0 and item["distributions"] == {}, "RESOLVER_NEGATIVE"
        )
    damaged = {d["kind"]: d for d in evidence["damaged"]}
    unforced = damaged.get("psycopg_binary_unforced", {})
    need(
        set(damaged)
        == {
            "driver_version",
            "adbc_library",
            "psycopg_binary",
            "psycopg_binary_unforced",
        }
        and damaged["driver_version"]["result"] == "EXECUTION_DRIVER_VERSION"
        and damaged["adbc_library"]["result"] == "POSTGRES_ADBC_DRIVER_LIBRARY"
        # The forced binary implementation fails to import: never "missing".
        and damaged["psycopg_binary"]["result"] == "ImportError"
        and damaged["psycopg_binary"]["psycopg_impl_env"] == "binary"
        # Unforced, psycopg would load a system libpq: the route refuses it.
        and unforced["psycopg_impl_env"] is None
        and unforced["result"]
        == ("POSTGRES_DRIVER_LIBRARY" if unforced["libpq"] else "ImportError"),
        "DAMAGED_INSTALLATION",
    )
    return {
        "artifacts": artifacts,
        "cells": checked,
        "damaged": {k: d["result"] for k, d in damaged.items()},
    }


def check_formats(matrix: dict) -> None:
    need(set(matrix) == set(FEATURES), "FORMAT_SET")
    for version, (fmt, features) in enumerate(FEATURES.items(), start=1):
        row = matrix[fmt]
        need(tuple(row["features"]) == features, "FORMAT_FEATURES")
        need(row["user_version"] == version and row["unchanged"], "FORMAT_FEATURES")
        for feature, code in GATES.items():
            outcome = row["gates"][feature]
            if feature in features:
                need(not outcome.startswith("WORKSPACE_"), "FORMAT_GATE")
            else:
                need(outcome == code, "FORMAT_GATE")
        need(
            row["runtime"]
            == (
                "OPENED"
                if "bounded-job-runtime" in features
                else GATES["bounded-job-runtime"]
            ),
            "FORMAT_GATE",
        )


def check_compat(evidence: dict) -> dict:
    current, previous = evidence["formats"]["current"], evidence["formats"]["s17"]
    check_formats(current)
    check_formats(previous)
    need(current == previous, "FORMAT_UNCHANGED")
    for item in evidence["envelopes"]:
        need(
            item["outcome"] == "WORKSPACE_FORMAT" and item["unchanged"],
            "ENVELOPE_BEFORE_SQLITE",
        )
    need(
        sorted(e["damage"] for e in evidence["envelopes"])
        == ["future_format", "relabeled_v6", "reordered_features", "unknown_feature"],
        "INVENTORY",
    )
    old = evidence["s16"]
    need(
        old
        == {
            "outcome": "WORKSPACE_FORMAT",
            "unchanged": True,
            "format": "pietto.job-workspace.v1",
        },
        "ARCHIVED_REFUSAL",
    )
    need(evidence["schema"]["outcome"] == "WORKSPACE_SCHEMA", "RECOGNIZED_SCHEMA")
    code = evidence["code"]
    s17 = compatibility_identity(evidence["s17_wheel"], evidence["antlr_wheel"])
    now = compatibility_identity(evidence["current_wheel"], evidence["antlr_wheel"])
    need(
        code["s17_identity"] == s17
        and code["current_identity"] == now
        and code["source_identity"] == now,
        "CODE_IDENTITY",
    )
    need(s17 != now, "CODE_IDENTITY")
    need(
        code["s17_self"] == "LOADED"
        and code["s17_binding"] == "BOUND"
        and code["load"] == "COMPILED_COMPATIBILITY"
        and code["open"] == "OPENED"
        and code["binding_s17"] == "JOB_COMPATIBILITY"
        and code["binding_current"] == "JOB_COMPATIBILITY"
        and code["fresh"] == "ACCEPTED",
        "CODE_COMPATIBILITY",
    )
    return {"s17_identity": s17, "current_identity": now}


def check_saved(saved: dict) -> dict:
    """Driver-free saved tail: observations, not configuration."""
    need(
        saved["installed_drivers"] == []
        and saved["loaded_drivers"] == []
        and saved["connections"] == [],
        "SAVED_SOURCE_ACCESS",
    )
    for refusal in saved["refusals"]:
        need(refusal["result"] == "EXECUTION_DEPENDENCY_MISSING", "ARROW_ONLY_REFUSAL")
        if refusal["kind"] == "submit":
            need(
                refusal["admissions_before"] == refusal["admissions_after"]
                and refusal["records"] == 0,
                "ARROW_ONLY_REFUSAL",
            )
        else:
            need(
                refusal["kind"] == "owner"
                and refusal["socket_attempts"] == 0
                and refusal["connected"] is False,
                "ARROW_ONLY_REFUSAL",
            )
    need({r["kind"] for r in saved["refusals"]} == {"submit", "owner"}, "INVENTORY")
    window = saved["restart"]
    need(
        window["first"] == window["reissued"]
        and window["acknowledged_before_restart"] == []
        and window["acknowledged_after"] == [window["first"]],
        "SAVED_RESTART_WINDOW",
    )
    need(
        saved["query"]["published"] and saved["query"]["read_terminal"] == "COMPLETED",
        "PUBLICATION_QUERY",
    )
    retained = saved["retained"]
    if retained is not None:
        need(
            retained["protected"]
            and retained["removed"] == []
            and retained["root"] == "CONSUMER"
            and retained["released_removed"] > 0,
            "RETAINED_CONSUMER",
        )
    need(saved["reclaimed"] > 0, "RECLAIMED")
    reply = saved["lost_reply"]
    if reply is not None:
        need(
            reply["issued"] > 0
            and reply["sink_effects_after_cut"] == reply["issued"]
            and reply["confirmed_after_cut"] == 0
            and set(reply["statuses"].values()) == {"PRESENT_MATCHING"}
            and len(reply["statuses"]) == reply["issued"]
            and reply["sink_effects_final"] == reply["rows"]
            and reply["commits_final"] == reply["rows"]
            and reply["positions_final"] == list(range(reply["rows"])),
            "SINK_LOST_REPLY",
        )
    return {"refusals": len(saved["refusals"]), "reclaimed": saved["reclaimed"]}


def check_inventory(report: dict, requested) -> None:
    """Exactly the caller's requested cells for this family's routes, each once;
    `requested` is the orchestrator's (origin, entry) set, never the producer's."""
    cells = [(h["route"], h["entry"], h["origin"]) for h in report["histories"]]
    need(len(cells) == len(set(cells)), "INVENTORY")
    need(
        frozenset(cells)
        == frozenset(
            (route, entry, origin)
            for route in report["routes"]
            for origin, entry in requested
        ),
        "INVENTORY",
    )
    need(report["cell_count"] == len(cells), "INVENTORY")


def _rewrite_wheel(wheel: bytes, metadata_edit) -> bytes:
    """A coordinated damage: METADATA changed and RECORD recomputed to match."""
    members = wheel_members(wheel)
    info = "pietto-0.1.0.dist-info/"
    members[info + "METADATA"] = metadata_edit(members[info + "METADATA"])
    rows = []
    for name, data in members.items():
        if name == info + "RECORD":
            continue
        rows.append([name, _record_digest(data), str(len(data))])
    rows.append([info + "RECORD", "", ""])
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    members[info + "RECORD"] = out.getvalue().encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _optional_into_core(e):
    def edit(data):
        return re.sub(
            rb"(Requires-Dist: pyarrow ?==25\.0\.1) ?; ?extra ?== ?['\"]execute-mysql['\"]",
            rb"\1",
            data,
            count=1,
        )

    e["wheel_bytes"] = _rewrite_wheel(e["wheel_bytes"], edit)


def _route_dependency_removed(e):
    def edit(data):
        return re.sub(rb"Requires-Dist: mysql-connector-python[^\n]*\n", b"", data)

    e["wheel_bytes"] = _rewrite_wheel(e["wheel_bytes"], edit)


def _foreign_origin(e):
    # Same-version module bytes of another installation, recorded consistently
    # in the cell's own origin map and its duplicate summary.
    cell = e["cells"][0]
    name = "pietto._project.project_job_runtime"
    cell["facts"]["origins"][name]["sha256"] = e["foreign_sha256"]
    cell["summary"] = {"origins": "MATCH"}


def _altered_member(e):
    cell = e["cells"][-1]
    name = "pietto._project.project_execution"
    item = cell["facts"]["origins"][name]
    item["sha256"] = hashlib.sha256(b"altered" + item["sha256"].encode()).hexdigest()
    cell["record_recomputed"] = True


def _unknown_feature(e):
    for matrix in e["formats"].values():
        matrix["pietto.job-workspace.v7"]["features"].append("gc")
        matrix["pietto.job-workspace.v7"]["gates"]["gc"] = "PASSED"


def _laundered(e):
    e["code"].update(
        s17_identity=e["code"]["current_identity"],
        s17_self="LOADED",
        load="LOADED",
        binding_s17="BOUND",
        binding_current="BOUND",
        package_versions=["0.1.0", "0.1.0"],
    )


def _hidden_source_access(e):
    e["saved"]["loaded_drivers"] = ["psycopg"]
    e["saved"]["summary"] = {"source_access": "NONE"}


def _cell_removed(e):
    e["report"]["histories"].pop()
    e["report"]["cell_count"] -= 1


# Each coordinated damage and the law that must reject it.
DAMAGES = {
    "D1_optional_into_core": (_optional_into_core, "install", "METADATA_REQUIRES"),
    "D2_route_dependency_removed": (
        _route_dependency_removed,
        "install",
        "METADATA_REQUIRES",
    ),
    "D3_foreign_origin": (_foreign_origin, "install", "ORIGIN_BYTES"),
    "D4_altered_member": (_altered_member, "install", "ORIGIN_BYTES"),
    "D5_unknown_feature": (_unknown_feature, "compat", "FORMAT_FEATURES"),
    "D6_laundered_compatibility": (_laundered, "compat", "CODE_IDENTITY"),
    "D7_hidden_source_access": (_hidden_source_access, "saved", "SAVED_SOURCE_ACCESS"),
    "D8_cell_removed": (_cell_removed, "inventory", "INVENTORY"),
}
CHECKS = {
    "install": check_install,
    "compat": check_compat,
    "saved": lambda e: check_saved(e["saved"]),
    "inventory": lambda e: check_inventory(e["report"], e["requested"]),
}


def rejects(kind: str, evidence: dict) -> str:
    """Apply one damage to a deep copy; the designated law must reject it."""
    damage, family, law = DAMAGES[kind]
    copied = copy.deepcopy(evidence)
    damage(copied)
    try:
        CHECKS[family](copied)
    except Rejected as error:
        need(error.law == law, "DAMAGE_LAW:" + kind + ":" + error.law)
        return error.law
    raise Rejected("DAMAGE_ACCEPTED:" + kind)
