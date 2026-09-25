"""Import-only CI requirement, coverage-health and bounded history helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import html
import importlib
import json
import math
from pathlib import Path
import re
import statistics
import time
import tomllib
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HEALTH_FORMAT = "pietto.ci-workload-health.v1"
READINESS_FORMAT = "pietto.arrow-readiness.v1"
MAX_HEALTH_BYTES = 1024 * 1024
KINDS = ("shared-acquisition", "process-portability", "general-runtime")
FIELDS = ("kind", "family", "acquisition_group", "dependency_profile")
CASES = (
    "types",
    "carriers",
    "adaptation",
    "strings",
    "capsules",
    "alias",
    "finite",
    "ipc",
    "device",
)
ARROW_VERSION = "25.0.1"


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError("CI workload policy: " + message)


def exact(value: object, fields: set[str], label: str) -> dict[str, Any]:
    require(
        type(value) is dict and set(value) == fields, "invalid " + label + " fields"
    )
    return value  # type: ignore[return-value]


def finite(value: Any, label: str) -> float:
    require(
        type(value) in (int, float) and math.isfinite(value) and value >= 0,
        "invalid " + label,
    )
    return float(value)  # type: ignore[arg-type]


def integer(value: object, minimum: int, maximum: int, label: str) -> int:
    require(type(value) is int and minimum <= value <= maximum, "invalid " + label)
    return value  # type: ignore[return-value]


def json_bytes(data: bytes, limit: int = MAX_HEALTH_BYTES) -> dict[str, Any]:
    require(len(data) <= limit, "report exceeds byte limit")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    value = json.loads(
        data,
        object_pairs_hook=pairs,
        parse_constant=lambda _: require(False, "nonfinite JSON"),
    )
    require(type(value) is dict, "report must be an object")
    return value


def read_json(path: Path, limit: int = MAX_HEALTH_BYTES) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), "report must be a regular file")
    with path.open("rb") as stream:
        return json_bytes(stream.read(limit + 1), limit)


def write_json(path: Path, value: object, limit: int = MAX_HEALTH_BYTES) -> None:
    data = canonical(value)
    require(len(data) <= limit, "report exceeds byte limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    exact(
        policy,
        {
            "version",
            "topology_version",
            "thresholds",
            "requirements",
            "placements",
            "shards",
            "groups",
            "legacy_files",
            "legacy_nodes",
        },
        "registry",
    )
    integer(policy["version"], 1, 1, "registry version")
    integer(policy["topology_version"], 1, 1000, "topology version")
    thresholds = exact(
        policy["thresholds"],
        {
            "imbalance_watch",
            "imbalance_review",
            "finish_spread",
            "startup",
            "long_node_fraction",
            "long_node_seconds",
            "critical_path_growth",
            "runner_sum_growth",
            "minimum_wall_gain",
        },
        "thresholds",
    )
    for name, value in thresholds.items():
        require(finite(value, name) > 0, "threshold must be positive")
    require(
        thresholds["imbalance_watch"] < thresholds["imbalance_review"],
        "unordered imbalance thresholds",
    )
    for key in (
        "requirements",
        "placements",
        "shards",
        "groups",
        "legacy_files",
        "legacy_nodes",
    ):
        require(type(policy[key]) is list and policy[key], "empty or malformed " + key)
    requirements = {}
    for row in policy["requirements"]:
        exact(row, set(FIELDS), "requirement")
        require(
            all(type(row[k]) is str for k in FIELDS),
            "requirement values must be strings",
        )
        require(
            row["kind"] in KINDS
            and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", row["family"])
            and row["dependency_profile"] == "core",
            "unknown class/family or unsupported dependency profile",
        )
        key = (row["kind"], row["family"])
        require(key not in requirements, "duplicate registered family")
        requirements[key] = row
    require(("general-runtime", "default") in requirements, "missing ordinary default")
    groups = {}
    for row in policy["groups"]:
        exact(row, {"name", "observer", "purpose"}, "group")
        require(all(type(v) is str and v for v in row.values()), "malformed group")
        require(row["observer"] == "differential", "unsupported managed observer")
        require(row["name"] not in groups, "duplicate group")
        groups[row["name"]] = row
    require(
        len({g["observer"] for g in groups.values()}) == len(groups),
        "observer assigned to multiple groups",
    )
    for row in requirements.values():
        require(
            (row["kind"] == "shared-acquisition") == bool(row["acquisition_group"]),
            "invalid acquisition group requirement",
        )
        require(
            not row["acquisition_group"] or row["acquisition_group"] in groups,
            "unknown acquisition group",
        )
    shards = {}
    for row in policy["shards"]:
        exact(row, {"id", "scheduler", "dependency_profile"}, "shard")
        require(
            type(row["id"]) is str and re.fullmatch(r"[a-z][a-z0-9-]{0,63}", row["id"]),
            "invalid shard ID",
        )
        require(
            row["id"] not in shards
            and row["scheduler"] in ("loadfile", "load")
            and row["dependency_profile"] == "core",
            "duplicate shard, unsupported scheduler/profile",
        )
        shards[row["id"]] = row
    require(len(shards) <= 4, "runtime job ceiling exceeded")
    placements = {}
    group_owners: dict[str, set[str]] = {}
    for row in policy["placements"]:
        exact(row, {"kind", "family", "shard"}, "placement")
        require(all(type(v) is str for v in row.values()), "malformed placement")
        key = (row["kind"], row["family"])
        require(
            key in requirements and key not in placements and row["shard"] in shards,
            "unknown or duplicate placement",
        )
        req = requirements[key]
        require(
            req["dependency_profile"] == shards[row["shard"]]["dependency_profile"],
            "dependency profile mismatch",
        )
        if req["kind"] != "process-portability":
            require(
                shards[row["shard"]]["scheduler"] == "loadfile",
                "only independent portability may use load",
            )
        if req["acquisition_group"]:
            group_owners.setdefault(req["acquisition_group"], set()).add(row["shard"])
        placements[key] = row["shard"]
    require(
        all(len(owners) == 1 for owners in group_owners.values()),
        "acquisition group split across shards",
    )
    require(
        set(group_owners) == set(groups),
        "managed group has no approved owner placement",
    )
    files = {}
    for row in policy["legacy_files"]:
        exact(row, {"path", "kind", "family"}, "legacy file")
        require(
            all(type(v) is str and v for v in row.values()), "malformed legacy file"
        )
        require(
            row["path"].startswith("tests/")
            and row["path"].endswith(".py")
            and ".." not in row["path"].split("/"),
            "invalid legacy path",
        )
        require(
            row["path"] not in files and (row["kind"], row["family"]) in requirements,
            "duplicate or unknown legacy file rule",
        )
        files[row["path"]] = row
    functions = set()
    for row in policy["legacy_nodes"]:
        exact(
            row, {"function", "modes", "kind", "family", "exception_to"}, "legacy node"
        )
        require(
            all(
                type(row[k]) is str
                for k in ("function", "kind", "family", "exception_to")
            ),
            "malformed node rule",
        )
        require(
            row["function"] not in functions
            and row["function"].split("::", 1)[0] == row["exception_to"]
            and row["exception_to"] in files,
            "duplicate node rule or unapproved file exception",
        )
        require((row["kind"], row["family"]) in requirements, "unknown node family")
        modes = row["modes"]
        require(
            type(modes) is list
            and modes
            and all(type(m) is str and m for m in modes)
            and len(modes) == len(set(modes)),
            "malformed or duplicate required modes",
        )
        functions.add(row["function"])
    return policy


def load_policy(path: Path = ROOT / "ci/workloads.toml") -> dict[str, Any]:
    with path.open("rb") as stream:
        return validate_policy(tomllib.load(stream))


def policy_identity(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": policy["version"],
        "topology_version": policy["topology_version"],
        "sha256": digest(policy),
    }


def table(policy: dict[str, Any]) -> list[list[str]]:
    return sorted([[r[k] for k in FIELDS] for r in policy["requirements"]])


def declared(policy: dict[str, Any], kind: object, values: dict[str, Any]) -> list[str]:
    require(type(kind) is str and kind in KINDS, "unknown workload class")
    require(
        set(values) <= set(FIELDS) - {"kind"},
        "unknown marker arguments; placement is not a marker",
    )
    family = values.get("family", "default")
    require(
        type(family) is str and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", family),
        "malformed family",
    )
    rows = [
        r for r in policy["requirements"] if (r["kind"], r["family"]) == (kind, family)
    ]
    require(len(rows) == 1, "unregistered family: " + str(family))
    row = rows[0]
    require(
        all(type(v) is str and row[k] == v for k, v in values.items()),
        "marker group/profile contradicts registered requirement",
    )
    return [row[k] for k in FIELDS]


def resolve(
    policy: dict[str, Any], nodes: list[str], marks: dict[str, list[tuple[tuple, dict]]]
) -> list[int]:
    require(nodes == sorted(set(nodes)) and nodes, "invalid independent collection")
    files = {r["path"]: r for r in policy["legacy_files"]}
    require(
        set(files) <= {n.split("::", 1)[0] for n in nodes},
        "stale required file selector",
    )
    exceptions = {}
    for rule in policy["legacy_nodes"]:
        expected = {rule["function"] + "[" + mode + "]" for mode in rule["modes"]}
        actual = {n for n in nodes if n.split("[", 1)[0] == rule["function"]}
        require(actual == expected, "stale required mode selector")
        exceptions.update({n: rule for n in expected})
    descriptors = table(policy)
    indices = []
    for node in nodes:
        rule = exceptions.get(node) or files.get(node.split("::", 1)[0])
        legacy = (
            declared(policy, rule["kind"], {"family": rule["family"]}) if rule else None
        )
        effective = []
        for args, kwargs in marks.get(node, []):
            require(len(args) == 1, "ci_workload requires one positional class")
            effective.append(declared(policy, args[0], kwargs))
        require(
            not effective or all(r == effective[0] for r in effective),
            "conflicting effective marker declarations",
        )
        require(
            legacy is None or not effective or legacy == effective[0],
            "marker contradicts legacy requirement",
        )
        chosen = (
            effective[0]
            if effective
            else legacy or declared(policy, "general-runtime", {})
        )
        indices.append(descriptors.index(chosen))
    return indices


def place(
    policy: dict[str, Any], nodes: list[str], indices: list[int]
) -> dict[str, list[str]]:
    require(len(nodes) == len(indices), "missing resolved requirements")
    descriptors = table(policy)
    placements = {(r["kind"], r["family"]): r["shard"] for r in policy["placements"]}
    result: dict[str, list[str]] = {r["id"]: [] for r in policy["shards"]}
    for node, index in zip(nodes, indices, strict=True):
        row = descriptors[integer(index, 0, len(descriptors) - 1, "descriptor index")]
        key = (row[0], row[1])
        require(
            key in placements,
            "registered requirement has no approved placement: " + "/".join(key),
        )
        result[placements[key]].append(node)
    return result


def input_identity(root: Path = ROOT) -> str:
    support = importlib.import_module(
        "_pietto_differential_process_acquisition"
    ).RELOCATION_SUPPORT_MANIFEST

    source = root / "tests/_pietto_differential_process_acquisition.py"
    paths = [
        *sorted((root / "src/pietto").rglob("*.py")),
        source,
        *(root / "tests" / n for n in support),
        root / "pyproject.toml",
        root / "uv.lock",
    ]
    return digest(
        {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths
        }
    )


def group_members(nodes: list[str]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[str]] = {}
    for node in nodes:
        groups.setdefault(node.split("::", 1)[0], []).append(node)
    return {
        name: {"count": len(ids), "sha256": digest(sorted(ids))}
        for name, ids in sorted(groups.items())
    }


def managed_observations(
    policy, partition, context, domain, inputs, workers, properties
):
    require(
        workers
        and all(type(w) is dict and w.get("enabled") is True for w in workers.values()),
        "missing managed observer evidence",
    )
    group = policy["groups"][0]
    owner = next(
        p["shard"]
        for p in policy["placements"]
        if any(
            r["acquisition_group"] == group["name"]
            and (r["kind"], r["family"]) == (p["kind"], p["family"])
            for r in policy["requirements"]
        )
    )
    productions = []
    preparation = []
    seen = set()
    for worker, observation in workers.items():
        exact(observation, {"enabled", "events"}, "managed observer")
        require(type(observation["events"]) is list, "invalid observer events")
        for event in observation["events"]:
            exact(
                event,
                {"kind", "key", "start", "seconds", "success"},
                "production event",
            )
            finite(event["start"], "production start")
            finite(event["seconds"], "production seconds")
            require(event["success"] is True, "managed production failed")
            require(
                event["kind"] in ("cell", "preparation"), "unknown production event"
            )
            if event["kind"] == "preparation":
                require(
                    event["key"] in ("source-relocated", "installed-wheel"),
                    "unknown preparation",
                )
                preparation.append({"worker": worker, **event})
                continue
            key = event["key"]
            require(
                type(key) is list
                and len(key) == 3
                and type(key[0]) is list
                and key[0] in domain
                and key[1] in ("0", "1", "7", "4294967295")
                and key[2] in ("checkout", "relocated", "installed"),
                "invalid managed cell",
            )
            require(partition == owner, "managed production outside approved shard")
            identity = [
                context["python"],
                context["python_version"],
                domain,
                group["purpose"],
                group["name"],
                key,
                inputs,
            ]
            stamp = digest(identity)
            require(stamp not in seen, "duplicate managed production")
            seen.add(stamp)
            productions.append({"identity": identity, "worker": worker, **event})
    manifests = [
        json.loads(value) for _, name, value in properties if name == "cell_manifest"
    ]
    if partition == owner:
        require(len(manifests) == 1, "missing independent cell manifest")
        expected = {canonical(row[:3]) for row in manifests[0]}
        require(
            {canonical(p["key"]) for p in productions} == expected,
            "managed production differs from complete cell manifest",
        )
    else:
        require(not productions, "unexpected managed cell production")
    return {
        "complete": True,
        "worker_count": len(workers),
        "productions": productions,
        "preparation": preparation,
    }


def timing_summary(reports, started_wall, scheduler):
    nodes: dict[str, dict[str, Any]] = {}
    groups: dict[str, float] = {}
    workers: dict[str, dict[str, Any]] = {}
    for report in reports:
        worker = getattr(report, "worker_id", "local")
        row = nodes.setdefault(
            report.nodeid, {"node": report.nodeid, "worker": worker, "phases": {}}
        )
        row["phases"][report.when] = {
            "seconds": report.duration,
            "start": report.start,
            "finish": report.stop,
        }
        group = report.nodeid.split("::", 1)[0]
        groups[group] = groups.get(group, 0.0) + report.duration
        totals = workers.setdefault(
            worker,
            {"seconds": 0.0, "calls": 0, "start": report.start, "finish": report.stop},
        )
        totals["seconds"] += report.duration
        totals["calls"] += report.when == "call"
        totals["start"] = min(totals["start"], report.start)
        totals["finish"] = max(totals["finish"], report.stop)
    slowest = sorted(
        nodes.values(),
        key=lambda row: -sum(p["seconds"] for p in row["phases"].values()),
    )[:30]
    return {
        "scheduler": scheduler,
        "plugin_started": started_wall,
        "workers": workers,
        "slowest_groups_summed_seconds": [
            list(row) for row in sorted(groups.items(), key=lambda row: -row[1])[:10]
        ],
        "nodes": slowest,
    }


def shard_health(coverage, timing, managed, runner):
    values = list(timing["workers"].values())
    first = min((w["start"] for w in values), default=timing["plugin_started"])
    ends = [w["finish"] for w in values]
    return {
        "format": HEALTH_FORMAT,
        "kind": "partition",
        "context": coverage["context"],
        "policy": coverage["policy"],
        "domain": coverage["domain"],
        "inputs": coverage["inputs"],
        "partition": coverage["partition"],
        "collection": coverage["collection"],
        "selection": {
            "count": len(coverage["nodes"]),
            "sha256": digest(coverage["nodes"]),
        },
        "outcomes_sha256": digest(coverage["outcomes"]),
        "runner": runner,
        "worker_budget": coverage["workers"],
        "elapsed_seconds": coverage["elapsed_seconds"],
        "startup_seconds": max(0.0, first - timing["plugin_started"]),
        "finish_spread_seconds": max(ends) - min(ends) if ends else 0.0,
        "groups": group_members(coverage["nodes"]),
        "timing": timing,
        "managed": managed,
        "resources": {"cpu_seconds": None, "memory_peak_bytes": None},
        "evidence_complete": True,
    }


def health_shape(value):
    """Closed data-only shape shared by current evidence and historical inspection."""
    exact(
        value,
        {
            "format",
            "kind",
            "context",
            "policy",
            "domain",
            "inputs",
            "partition",
            "collection",
            "selection",
            "outcomes_sha256",
            "runner",
            "worker_budget",
            "elapsed_seconds",
            "startup_seconds",
            "finish_spread_seconds",
            "groups",
            "timing",
            "managed",
            "resources",
            "evidence_complete",
        },
        "partition health",
    )
    require(
        value["format"] == HEALTH_FORMAT
        and value["kind"] == "partition"
        and value["evidence_complete"] is True,
        "invalid partition health identity",
    )
    context = exact(
        value["context"],
        {"checkout", "run_id", "run_attempt", "python", "python_version"},
        "runtime context",
    )
    require(
        all(
            type(context[k]) is str
            for k in ("checkout", "run_id", "python", "python_version")
        ),
        "invalid context strings",
    )
    require(
        re.fullmatch(r"[0-9a-f]{40}", context["checkout"])
        and context["python"] in ("3.12", "3.13")
        and re.fullmatch(
            re.escape(context["python"]) + r"\.[0-9]+", context["python_version"]
        ),
        "invalid runtime context",
    )
    integer(context["run_attempt"], 1, 100, "runtime attempt")
    policy = exact(
        value["policy"], {"version", "topology_version", "sha256"}, "health policy"
    )
    integer(policy["version"], 1, 1, "policy version")
    integer(policy["topology_version"], 1, 1000, "topology version")
    for label, checksum in (
        ("policy", policy["sha256"]),
        ("inputs", value["inputs"]),
        ("outcomes", value["outcomes_sha256"]),
    ):
        require(
            type(checksum) is str and re.fullmatch(r"[0-9a-f]{64}", checksum),
            "invalid " + label + " digest",
        )
    domain = value["domain"]
    require(
        type(domain) is list
        and domain
        and all(
            type(v) is list
            and len(v) == 2
            and all(type(n) is int for n in v)
            and v in ([3, 12], [3, 13])
            for v in domain
        )
        and domain == sorted(domain)
        and len({tuple(v) for v in domain if type(v) is list}) == len(domain)
        and [int(v) for v in context["python"].split(".")] in domain,
        "invalid interpreter domain",
    )
    selection = exact(value["selection"], {"count", "sha256"}, "selection")
    count = integer(selection["count"], 1, 1000000, "selected count")
    require(
        type(selection["sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", selection["sha256"]),
        "invalid selection digest",
    )
    collection = exact(
        value["collection"], {"count", "sha256", "requirements_sha256"}, "collection"
    )
    integer(collection["count"], count, 1000000, "collection count")
    require(
        all(
            type(collection[k]) is str and re.fullmatch(r"[0-9a-f]{64}", collection[k])
            for k in ("sha256", "requirements_sha256")
        ),
        "invalid collection digest",
    )
    require(
        type(value["partition"]) is str
        and re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value["partition"]),
        "invalid health partition",
    )
    integer(value["worker_budget"], 1, 4, "worker budget")
    for key in ("elapsed_seconds", "startup_seconds", "finish_spread_seconds"):
        finite(value[key], key)
    runner = exact(value["runner"], {"image", "image_version", "os", "arch"}, "runner")
    require(
        all(v is None or type(v) is str for v in runner.values()),
        "invalid runner values",
    )
    resources = exact(
        value["resources"], {"cpu_seconds", "memory_peak_bytes"}, "optional resources"
    )
    for k, v in resources.items():
        if v is not None:
            finite(v, k)
    require(
        type(value["groups"]) is dict and 0 < len(value["groups"]) <= 10000,
        "invalid group inventory",
    )
    for name, group in value["groups"].items():
        require(type(name) is str and name, "invalid group label")
        group = exact(group, {"count", "sha256"}, "group membership")
        integer(group["count"], 1, count, "group count")
        require(
            type(group["sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", group["sha256"]),
            "invalid group digest",
        )
    require(
        sum(g["count"] for g in value["groups"].values()) == count,
        "group counts differ from selection",
    )
    timing = exact(
        value["timing"],
        {
            "scheduler",
            "plugin_started",
            "workers",
            "slowest_groups_summed_seconds",
            "nodes",
        },
        "timing",
    )
    require(
        timing["scheduler"] in ("load", "loadfile", "no")
        and (timing["scheduler"] != "no" or value["worker_budget"] == 1),
        "invalid scheduler",
    )
    finite(timing["plugin_started"], "plugin start")
    require(
        type(timing["workers"]) is dict
        and 0 < len(timing["workers"]) <= value["worker_budget"],
        "invalid worker timing inventory",
    )
    for worker, row in timing["workers"].items():
        require(type(worker) is str and worker, "invalid worker label")
        row = exact(row, {"seconds", "calls", "start", "finish"}, "worker timing")
        integer(row["calls"], 0, count, "worker calls")
        for key in ("seconds", "start", "finish"):
            finite(row[key], key)
        require(row["finish"] >= row["start"], "reversed worker interval")
    workers = list(timing["workers"].values())
    require(sum(w["calls"] for w in workers) <= count, "excess worker calls")
    expected_startup = max(
        0.0, min(w["start"] for w in workers) - timing["plugin_started"]
    )
    expected_spread = max(w["finish"] for w in workers) - min(
        w["finish"] for w in workers
    )
    require(
        abs(value["startup_seconds"] - expected_startup) < 1e-6
        and abs(value["finish_spread_seconds"] - expected_spread) < 1e-6,
        "forged startup or finish spread",
    )
    require(
        type(timing["nodes"]) is list and len(timing["nodes"]) <= 30,
        "unbounded slow nodes",
    )
    seen = set()
    for row in timing["nodes"]:
        row = exact(row, {"node", "worker", "phases"}, "node timing")
        require(
            type(row["node"]) is str
            and row["node"].split("::", 1)[0] in value["groups"]
            and row["node"] not in seen
            and type(row["worker"]) is str
            and row["worker"] in timing["workers"],
            "foreign/duplicate timed node",
        )
        seen.add(row["node"])
        require(
            type(row["phases"]) is dict
            and {"setup", "teardown"}
            <= set(row["phases"])
            <= {"setup", "call", "teardown"},
            "incomplete timing phases",
        )
        for phase in row["phases"].values():
            phase = exact(phase, {"seconds", "start", "finish"}, "phase timing")
            for k, v in phase.items():
                finite(v, k)
            require(phase["finish"] >= phase["start"], "reversed phase interval")
    require(
        type(timing["slowest_groups_summed_seconds"]) is list
        and len(timing["slowest_groups_summed_seconds"]) <= 10,
        "unbounded groups",
    )
    group_rows: list[Any] = timing["slowest_groups_summed_seconds"]
    group_names = set()
    for row in group_rows:
        require(
            type(row) is list
            and len(row) == 2
            and type(row[0]) is str
            and row[0] in value["groups"],
            "unknown timed group",
        )
        require(row[0] not in group_names, "duplicate timed group")
        group_names.add(row[0])
        finite(row[1], "group seconds")
    managed = exact(
        value["managed"],
        {"complete", "worker_count", "productions", "preparation"},
        "managed observations",
    )
    require(
        managed["complete"] is True
        and type(managed["worker_count"]) is int
        and managed["worker_count"] == value["worker_budget"],
        "missing complete worker observations",
    )
    seen = set()
    for kind, field in (("cell", "productions"), ("preparation", "preparation")):
        require(type(managed[field]) is list, "invalid managed event list")
        for event in managed[field]:
            event = exact(
                event,
                {"worker", "kind", "key", "start", "seconds", "success"}
                | ({"identity"} if kind == "cell" else set()),
                "managed event",
            )
            require(
                event["kind"] == kind
                and type(event["worker"]) is str
                and event["worker"] in timing["workers"]
                and event["success"] is True,
                "invalid managed event owner/status",
            )
            finite(event["start"], "production start")
            finite(event["seconds"], "production seconds")
            if kind == "cell":
                key = event["key"]
                require(
                    type(key) is list
                    and len(key) == 3
                    and type(key[0]) is list
                    and key[0] in domain
                    and key[1] in ("0", "1", "7", "4294967295")
                    and key[2] in ("checkout", "relocated", "installed"),
                    "invalid managed cell key",
                )
                identity = event["identity"]
                require(
                    type(identity) is list
                    and len(identity) == 7
                    and identity[:3]
                    == [context["python"], context["python_version"], domain]
                    and identity[5:] == [event["key"], value["inputs"]]
                    and all(type(v) is str and v for v in identity[3:5]),
                    "foreign production namespace",
                )
                stamp = digest(identity)
                require(stamp not in seen, "duplicate managed production")
                seen.add(stamp)
            else:
                require(
                    event["key"] in ("source-relocated", "installed-wheel"),
                    "invalid preparation resource",
                )
    return value


def verify_shard_health(value, policy, coverage):
    health_shape(value)
    for key in (
        "context",
        "policy",
        "domain",
        "inputs",
        "partition",
        "collection",
        "elapsed_seconds",
    ):
        require(value[key] == coverage[key], "health differs from coverage: " + key)
    require(
        value["selection"]
        == {"count": len(coverage["nodes"]), "sha256": digest(coverage["nodes"])}
        and value["outcomes_sha256"] == digest(coverage["outcomes"]),
        "health selection/terminal binding mismatch",
    )
    require(
        value["groups"] == group_members(coverage["nodes"])
        and value["worker_budget"] == coverage["workers"],
        "health group or worker drift",
    )
    expected_scheduler = next(
        r["scheduler"] for r in policy["shards"] if r["id"] == value["partition"]
    )
    require(
        value["timing"]["scheduler"] in (expected_scheduler, "no"), "scheduler mismatch"
    )
    require(
        all(row["node"] in coverage["nodes"] for row in value["timing"]["nodes"]),
        "foreign timed node",
    )
    reconstructed: dict[str, Any] = {
        str(i): {"enabled": True, "events": []} for i in range(coverage["workers"])
    }
    for event in [*value["managed"]["productions"], *value["managed"]["preparation"]]:
        reconstructed["0"]["events"].append(
            {k: event[k] for k in ("kind", "key", "start", "seconds", "success")}
        )
    normalized = managed_observations(
        policy,
        value["partition"],
        value["context"],
        value["domain"],
        value["inputs"],
        reconstructed,
        coverage["properties"],
    )
    require(
        [p["identity"] for p in normalized["productions"]]
        == [p["identity"] for p in value["managed"]["productions"]],
        "production namespace mismatch",
    )
    return value


def verify_readiness(value, context, script_sha, requirements_sha):
    exact(
        value,
        {
            "format",
            "context",
            "pyarrow",
            "platform",
            "script_sha256",
            "requirements_sha256",
            "cases",
            "limits",
            "exit_code",
        },
        "Arrow readiness",
    )
    require(
        type(value["context"]) is dict
        and set(value["context"]) == set(context)
        and all(type(value["context"][k]) is type(v) for k, v in context.items()),
        "wrong readiness context types",
    )
    require(
        value["format"] == READINESS_FORMAT
        and value["context"] == context
        and value["pyarrow"] == ARROW_VERSION,
        "wrong Arrow readiness context/pin",
    )
    require(
        value["script_sha256"] == script_sha
        and value["requirements_sha256"] == requirements_sha,
        "wrong readiness inputs",
    )
    require(
        value["platform"] == {"system": "Linux", "machine": "x86_64"},
        "untested Arrow platform",
    )
    require(
        type(value["exit_code"]) is int
        and value["exit_code"] == 0
        and type(value["cases"]) is dict
        and set(value["cases"]) == set(CASES),
        "incomplete or failed Arrow readiness",
    )
    for case in value["cases"].values():
        exact(case, {"passed", "observations"}, "Arrow case")
        require(
            case["passed"] is True
            and type(case["observations"]) is dict
            and case["observations"],
            "missing real Arrow case result",
        )
    observed: dict[str, Any] = {
        name: case["observations"] for name, case in value["cases"].items()
    }
    required_true = {
        "types": ("bool_and_nulls", "finite_float64_signed_zero", "unicode_exact"),
        "carriers": (
            "zero_rows",
            "typed_all_null",
            "duplicate_labels_positional",
            "schema_equal_without_metadata",
            "pietto_must_check_actual_nulls",
        ),
        "adaptation": ("narrowing_refused",),
        "strings": ("metadata_retained_and_removed",),
        "capsules": (
            "schema_protocol",
            "array_protocol",
            "stream_protocol",
            "retained_after_exporter_and_reader_release",
            "binary16_preserved",
        ),
        "alias": (
            "external_mutation_visible",
            "owned_copy_isolated",
            "backing_lifetime_retained",
        ),
        "finite": ("rechunk_order_and_multiplicity", "normal_finite_finalization"),
        "ipc": (
            "roundtrip",
            "mid_message_refused",
            "boundary_truncation_accepted",
            "explicit_result_completeness_required",
            "binary16_preserved",
        ),
        "device": ("observed_cpu", "c_array_api"),
    }
    for name, fields in required_true.items():
        require(
            all(observed[name].get(k) is True for k in fields),
            "incomplete required Arrow witness: " + name,
        )
    for name, key in (
        ("types", "upstream_meaning_proven"),
        ("adaptation", "product_adapter_implemented"),
        ("capsules", "independent_c_implementation"),
        ("alias", "whole_system_zero_copy"),
        ("finite", "empty_batch_is_eof"),
        ("finite", "executor_success_proven"),
        ("device", "gpu_executed"),
    ):
        require(
            observed[name].get(key) is False,
            "Arrow observation promoted beyond tested scope",
        )
    require(
        observed["types"].get("integer_types") == ["int16", "int32", "int64"]
        and observed["types"].get("decimal128") == [9, 2]
        and observed["types"].get("decimal256") == [65, 3]
        and observed["types"].get("timestamp_unit") == "us"
        and observed["types"].get("timestamp_timezone") is None,
        "wrong finite type parameters",
    )
    require(
        type(observed["carriers"].get("nullable_false_accepts_actual_null")) is bool
        and observed["carriers"].get("schema_equal_with_metadata") is False,
        "invalid nullability/metadata observation",
    )
    require(
        observed["adaptation"].get("original_type") == "int16"
        and observed["adaptation"].get("safe_widening") == "int64",
        "wrong adaptation witness",
    )
    require(
        observed["strings"].get("string_type") == "string"
        and observed["strings"].get("large_string_type") == "large_string"
        and type(observed["strings"].get("slice_offset")) is int
        and observed["strings"]["slice_offset"] == 1,
        "wrong string/offset witness",
    )
    require(
        observed["finite"].get("values") == [1, 1, None, 2, 3]
        and type(observed["ipc"].get("boundary_rows")) is int
        and observed["ipc"]["boundary_rows"] == 2
        and type(observed["ipc"].get("complete_rows")) is int
        and observed["ipc"]["complete_rows"] == 3,
        "wrong finite/completeness witness",
    )
    for name in ("capsules", "ipc"):
        require(
            type(observed[name].get("uuid_extension_preserved")) is bool,
            "missing UUID correspondence",
        )
    expected_uuid = (
        "canonical-extension"
        if all(observed[n]["uuid_extension_preserved"] for n in ("capsules", "ipc"))
        else "explicit-binary16-logical-binding"
    )
    require(
        observed["types"].get("uuid_choice") == expected_uuid,
        "unexplained UUID representation switch",
    )
    require(
        value["limits"]
        == {"rows_per_case": 32, "admitted_buffer_bytes": 8 * 1024 * 1024},
        "wrong Arrow experiment bounds",
    )
    return value


def screen(
    shards: list[dict[str, Any]], thresholds: dict[str, float]
) -> list[dict[str, Any]]:
    """Pure screening. Durations are observations, never processing-time weights."""
    signals = []
    if not shards:
        return [
            {
                "code": "NO_RUNTIME_SAMPLE",
                "action": "check_new_requirements",
                "scope": "runtime",
                "structural": False,
            }
        ]
    elapsed = [finite(s["elapsed_seconds"], "partition elapsed") for s in shards]
    median = statistics.median(elapsed)
    if median > 0 and max(elapsed) / median > thresholds["imbalance_watch"]:
        signals.append(
            {
                "code": "SHARD_IMBALANCE_REVIEW"
                if max(elapsed) / median > thresholds["imbalance_review"]
                else "SHARD_IMBALANCE_WATCH",
                "action": "split_independent_family",
                "scope": "runtime",
                "structural": False,
            }
        )
    for shard, duration in zip(shards, elapsed, strict=True):
        partition = shard["partition"]
        if duration == 0:
            continue
        if (
            finite(shard["finish_spread_seconds"], "finish spread") / duration
            > thresholds["finish_spread"]
        ):
            signals.append(
                {
                    "code": "WORKER_FINISH_SPREAD",
                    "action": "inspect_long_node",
                    "scope": partition,
                    "structural": False,
                }
            )
        if (
            finite(shard["startup_seconds"], "startup") / duration
            > thresholds["startup"]
        ):
            signals.append(
                {
                    "code": "STARTUP_FRAGMENTATION",
                    "action": "investigate_startup",
                    "scope": partition,
                    "structural": False,
                }
            )
        for row in shard["timing"]["nodes"]:
            seconds = sum(
                finite(p["seconds"], "node phase") for p in row["phases"].values()
            )
            if (
                seconds > thresholds["long_node_seconds"]
                and seconds / duration > thresholds["long_node_fraction"]
            ):
                signals.append(
                    {
                        "code": "LONG_INDIVISIBLE_NODE",
                        "action": "inspect_long_node",
                        "scope": partition,
                        "node": row["node"],
                        "structural": False,
                    }
                )
        count = shard["selection"]["count"]
        if 0 < count < shard["worker_budget"]:
            signals.append(
                {
                    "code": "FEWER_UNITS_THAN_WORKERS",
                    "action": "consider_merge",
                    "scope": partition,
                    "structural": True,
                }
            )
    return signals


def context_compatible(current, previous):
    differences = []
    if current["policy"] != previous["policy"]:
        differences.append("policy")
    if current["context"].get("repository") != previous["context"].get("repository"):
        differences.append("repository")
    for version, runtime in current["runtimes"].items():
        old = previous["runtimes"].get(version)
        if old is None:
            differences.append(version + ":missing-runtime")
            continue
        if runtime["domain"] != old["domain"]:
            differences.append(version + ":domain")
        if runtime["context"]["python_version"] != old["context"]["python_version"]:
            differences.append(version + ":python-patch")
        if [s["runner"] for s in runtime["shards"]] != [
            s["runner"] for s in old["shards"]
        ]:
            differences.append(version + ":runner")
        if [s["partition"] for s in runtime["shards"]] != [
            s["partition"] for s in old["shards"]
        ]:
            differences.append(version + ":topology")
        if runtime["collection"] != old["collection"]:
            differences.append(version + ":test-set")
    return differences


def analyze(
    current: dict[str, Any], history: list[dict[str, Any]], thresholds: dict[str, float]
):
    """Pure deterministic recommendations; newest-first history has verified provenance."""
    require(len(history) <= 3, "history exceeds three samples")
    identities = [
        (
            h["context"].get("repository"),
            h["context"]["run_id"],
            h["context"].get("run_attempt", 1),
        )
        for h in history
    ]
    require(
        len(identities) == len(set(identities)), "duplicate historical run identity"
    )
    signals = [
        {"python": py, **signal}
        for py, runtime in current["runtimes"].items()
        for signal in screen(runtime["shards"], thresholds)
    ]
    comparisons = []
    eligible = []
    for previous in history:
        differences = context_compatible(current, previous)
        drift = {}
        for py, runtime in current["runtimes"].items():
            older = previous["runtimes"].get(py)
            if older:
                before = {
                    name: group
                    for s in older["shards"]
                    for name, group in s["groups"].items()
                }
                after = {
                    name: group
                    for s in runtime["shards"]
                    for name, group in s["groups"].items()
                }
                drift[py] = {
                    "node_growth": runtime["coverage"]["collected"]
                    - older["coverage"]["collected"],
                    "changed_groups": sorted(
                        k
                        for k in before.keys() | after.keys()
                        if before.get(k) != after.get(k)
                    ),
                }
        comparisons.append(
            {
                "run_id": previous["context"]["run_id"],
                "checkout": previous["context"].get("checkout"),
                "previous_policy": previous["policy"],
                "previous_runtime_domains": {
                    py: {
                        "python_version": runtime["context"]["python_version"],
                        "domain": runtime["domain"],
                        "runner": [shard["runner"] for shard in runtime["shards"]],
                    }
                    for py, runtime in previous["runtimes"].items()
                },
                "differences": differences,
                "membership_drift": drift,
            }
        )
        if not differences:
            eligible.append(previous)
    repeat = []
    for signal in signals:
        hits = 0
        for previous in eligible:
            old = screen(previous["runtimes"][signal["python"]]["shards"], thresholds)
            hits += any(
                s["code"] == signal["code"] and s["scope"] == signal["scope"]
                for s in old
            )
        if len(eligible) == 3 and hits >= 2:
            repeat.append(
                {
                    "code": signal["code"],
                    "python": signal["python"],
                    "scope": signal["scope"],
                    "hits": hits,
                    "samples": 3,
                }
            )
    # Cost comparisons require complete, like-for-like runs. Partial is not zero.
    cost_signals = []
    for previous in eligible:
        new_cost, old_cost = current["cost"], previous["cost"]
        if not new_cost["complete"] or not old_cost["complete"]:
            continue
        new_wall, old_wall = (
            new_cost["workflow_elapsed_seconds"],
            old_cost["workflow_elapsed_seconds"],
        )
        new_sum, old_sum = new_cost["sum_job_seconds"], old_cost["sum_job_seconds"]
        if old_wall and new_wall / old_wall > 1 + thresholds["critical_path_growth"]:
            cost_signals.append(
                {
                    "code": "CRITICAL_PATH_REGRESSION",
                    "reference_run": previous["context"]["run_id"],
                }
            )
        if (
            old_sum
            and old_wall
            and new_sum / old_sum > 1 + thresholds["runner_sum_growth"]
            and 1 - new_wall / old_wall < thresholds["minimum_wall_gain"]
        ):
            cost_signals.append(
                {
                    "code": "RUNNER_COST_TRADEOFF",
                    "reference_run": previous["context"]["run_id"],
                }
            )
    repeated_cost = [
        code
        for code in ("CRITICAL_PATH_REGRESSION", "RUNNER_COST_TRADEOFF")
        if len(eligible) == 3 and sum(s["code"] == code for s in cost_signals) >= 2
    ]
    enough = len(eligible) == 3
    status = (
        "INSUFFICIENT_EVIDENCE"
        if not enough
        else "REVIEW_RECOMMENDED"
        if repeat or repeated_cost or any(s["structural"] for s in signals)
        else "WATCH"
        if signals or cost_signals
        else "HEALTHY"
    )
    actions = [
        {
            "action": s["action"],
            "python": s["python"],
            "scope": s["scope"],
            "reason": s["code"],
            "provisional": not enough and not s["structural"],
        }
        for s in signals
    ]
    actions.extend(
        {
            "action": "check_new_requirements"
            if signal["code"] == "CRITICAL_PATH_REGRESSION"
            else "consider_merge",
            "python": "all",
            "scope": "workflow",
            "reason": signal["code"],
            "provisional": signal["code"] not in repeated_cost,
        }
        for signal in cost_signals
    )
    return {
        "status": status,
        "current_screen": "WATCH" if signals else "HEALTHY",
        "signals": signals,
        "repeat_confirmations": repeat,
        "cost_signals": cost_signals,
        "repeated_cost_codes": repeated_cost,
        "history_comparisons": comparisons,
        "comparable_samples": len(eligible),
        "recommendations": actions,
        "note": "Review actions only; observations never select tests or reconfigure execution.",
    }


def run_cost(run: dict[str, Any], jobs: list[dict[str, Any]], policy):
    """Separate actual wall, job sum, dependency-path job time and queue observations."""

    def seconds(start, end):
        return finite(
            (
                datetime.fromisoformat(end) - datetime.fromisoformat(start)
            ).total_seconds(),
            "job timestamp interval",
        )

    durations = {
        j["name"]: seconds(j["started_at"], j["completed_at"])
        for j in jobs
        if j.get("started_at")
        and j.get("completed_at")
        and j.get("status") == "completed"
    }
    expected = {
        *(f"Compiler / Package {p}" for p in ("3.12", "3.13")),
        *(
            f"Runtime {p} / {s['id']}"
            for p in ("3.12", "3.13")
            for s in policy["shards"]
        ),
        "Python 3.12",
        "Python 3.13",
        "Target postgres",
        "Target mysql",
        "Target conformance aggregate",
    }
    complete = (
        run.get("status") == "completed"
        and len(jobs) == len(expected)
        and set(durations) == expected
    )
    critical = None
    if complete:
        branches = [
            max(
                durations[f"Compiler / Package {p}"],
                *(durations[f"Runtime {p} / {s['id']}"] for s in policy["shards"]),
            )
            + durations["Python " + p]
            for p in ("3.12", "3.13")
        ]
        critical = (
            max(*branches, durations["Target postgres"], durations["Target mysql"])
            + durations["Target conformance aggregate"]
        )
    return {
        "complete": complete,
        "workflow_elapsed_seconds": seconds(run["created_at"], run["updated_at"])
        if complete
        else None,
        "sum_job_seconds": sum(durations.values()) if complete else None,
        "longest_dependency_path_job_seconds": critical,
        "completed_job_seconds": durations,
        "queue_seconds": {
            j["name"]: seconds(j["created_at"], j["started_at"])
            if j.get("created_at") and j.get("started_at")
            else None
            for j in jobs
        },
        "missing_jobs": sorted(expected - set(durations)),
        "error": None,
    }


def unavailable_cost(reason):
    return {
        "complete": False,
        "workflow_elapsed_seconds": None,
        "sum_job_seconds": None,
        "longest_dependency_path_job_seconds": None,
        "completed_job_seconds": {},
        "queue_seconds": {},
        "missing_jobs": [],
        "error": reason,
    }


def verify_workflow_health(value, expected_context=None):
    exact(
        value,
        {
            "format",
            "kind",
            "context",
            "policy",
            "runtimes",
            "cost",
            "assessment",
            "history",
            "reference",
        },
        "workflow health",
    )
    require(
        value["format"] == HEALTH_FORMAT and value["kind"] == "workflow",
        "wrong workflow health schema",
    )
    context = exact(
        value["context"],
        {"repository", "checkout", "run_id", "run_attempt", "event", "branch"},
        "workflow context",
    )
    require(
        all(
            type(context[k]) is str
            for k in ("repository", "checkout", "run_id", "event", "branch")
        )
        and re.fullmatch(r"[0-9a-f]{40}", context["checkout"]),
        "invalid workflow context",
    )
    integer(context["run_attempt"], 1, 100, "run attempt")
    if expected_context is not None:
        require(context == expected_context, "foreign workflow health context")
    exact(value["policy"], {"version", "topology_version", "sha256"}, "health policy")
    integer(value["policy"]["version"], 1, 1, "health policy version")
    integer(value["policy"]["topology_version"], 1, 1000, "health topology")
    require(
        type(value["policy"]["sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", value["policy"]["sha256"]),
        "invalid policy digest",
    )
    require(
        type(value["runtimes"]) is dict and set(value["runtimes"]) == {"3.12", "3.13"},
        "missing runtime health",
    )
    partition_ids = None
    for py, runtime in value["runtimes"].items():
        exact(
            runtime,
            {
                "format",
                "kind",
                "context",
                "policy",
                "domain",
                "collection",
                "coverage",
                "shards",
                "readiness",
            },
            "runtime summary",
        )
        require(
            runtime["format"] == HEALTH_FORMAT
            and runtime["kind"] == "runtime"
            and runtime["policy"] == value["policy"],
            "runtime summary identity drift",
        )
        require(
            runtime["context"]["python"] == py
            and all(
                runtime["context"][k] == context[k]
                for k in ("checkout", "run_id", "run_attempt")
            ),
            "foreign runtime summary",
        )
        require(
            type(runtime["shards"]) is list and 1 <= len(runtime["shards"]) <= 4,
            "invalid runtime shard inventory",
        )
        require(
            len({s["partition"] for s in runtime["shards"]}) == len(runtime["shards"]),
            "duplicate runtime shard",
        )
        current_ids = [shard["partition"] for shard in runtime["shards"]]
        require(
            partition_ids is None or partition_ids == current_ids,
            "runtime topology disagreement",
        )
        partition_ids = current_ids
        count = integer(
            runtime["coverage"]["collected"], 1, 1000000, "full collection count"
        )
        require(
            count
            == runtime["coverage"]["selected"]
            == runtime["coverage"]["executed_terminal"]
            == sum(s["selection"]["count"] for s in runtime["shards"]),
            "partial health coverage",
        )
        coverage = exact(
            runtime["coverage"],
            {
                "python",
                "collected",
                "selected",
                "executed_terminal",
                "passed",
                "skipped",
                "partitions",
            },
            "runtime coverage",
        )
        for name in ("collected", "selected", "executed_terminal", "passed", "skipped"):
            integer(coverage[name], 0, 1000000, name)
        require(
            coverage["python"] == py
            and coverage["passed"] + coverage["skipped"] == count
            and coverage["partitions"]
            == {s["partition"]: s["selection"]["count"] for s in runtime["shards"]},
            "forged runtime counters",
        )
        readiness = runtime["readiness"]
        for name in ("script_sha256", "requirements_sha256"):
            require(
                type(readiness.get(name)) is str
                and re.fullmatch(r"[0-9a-f]{64}", readiness[name]),
                "invalid readiness digest",
            )
        verify_readiness(
            readiness,
            runtime["context"],
            readiness["script_sha256"],
            readiness["requirements_sha256"],
        )
        for shard in runtime["shards"]:
            health_shape(shard)
            require(
                shard["format"] == HEALTH_FORMAT
                and shard["kind"] == "partition"
                and shard["context"] == runtime["context"]
                and shard["collection"] == runtime["collection"]
                and shard["domain"] == runtime["domain"]
                and shard["policy"] == runtime["policy"]
                and shard["evidence_complete"] is True
                and shard["managed"]["complete"] is True,
                "incomplete shard health",
            )
    cost = exact(
        value["cost"],
        {
            "complete",
            "workflow_elapsed_seconds",
            "sum_job_seconds",
            "longest_dependency_path_job_seconds",
            "completed_job_seconds",
            "queue_seconds",
            "missing_jobs",
            "error",
        },
        "cost",
    )
    require(type(cost["complete"]) is bool, "invalid cost completeness")
    for key in (
        "workflow_elapsed_seconds",
        "sum_job_seconds",
        "longest_dependency_path_job_seconds",
    ):
        require(cost[key] is not None or not cost["complete"], "missing complete cost")
        if cost[key] is not None:
            finite(cost[key], key)
    for key in ("completed_job_seconds", "queue_seconds"):
        require(type(cost[key]) is dict, "invalid job timing map")
        for name, seconds in cost[key].items():
            require(type(name) is str, "invalid job label")
            if seconds is not None:
                finite(seconds, key)
    require(
        type(value["assessment"]) is dict
        and value["assessment"].get("status")
        in ("HEALTHY", "WATCH", "REVIEW_RECOMMENDED", "INSUFFICIENT_EVIDENCE"),
        "invalid health assessment",
    )
    assessment = exact(
        value["assessment"],
        {
            "status",
            "current_screen",
            "signals",
            "repeat_confirmations",
            "cost_signals",
            "repeated_cost_codes",
            "history_comparisons",
            "comparable_samples",
            "recommendations",
            "note",
        },
        "assessment",
    )
    require(
        assessment["current_screen"] in ("HEALTHY", "WATCH")
        and type(assessment["note"]) is str,
        "invalid current screening",
    )
    integer(assessment["comparable_samples"], 0, 3, "comparable history samples")
    for field in (
        "signals",
        "repeat_confirmations",
        "cost_signals",
        "repeated_cost_codes",
        "history_comparisons",
        "recommendations",
    ):
        require(
            type(assessment[field]) is list and len(assessment[field]) <= 1000,
            "unbounded assessment",
        )
    for action in assessment["recommendations"]:
        action = exact(
            action,
            {"action", "python", "scope", "reason", "provisional"},
            "review action",
        )
        require(
            action["action"]
            in (
                "split_independent_family",
                "inspect_long_node",
                "consider_merge",
                "investigate_startup",
                "check_new_requirements",
            )
            and type(action["provisional"]) is bool
            and all(type(action[k]) is str for k in ("python", "scope", "reason")),
            "invalid advisory action",
        )
    provenance = exact(
        value["history"],
        {"availability", "candidates", "accepted", "rejected"},
        "history provenance",
    )
    require(
        provenance["availability"]
        in ("AVAILABLE", "INSUFFICIENT_EVIDENCE", "EXPLICIT_LOCAL_FILES"),
        "unknown history availability",
    )
    integer(provenance["candidates"], 0, 10, "history candidates")
    require(
        type(provenance["accepted"]) is list
        and len(provenance["accepted"]) <= 3
        and type(provenance["rejected"]) is list
        and len(provenance["rejected"]) <= 11,
        "unbounded history provenance",
    )
    reference = exact(
        value["reference"],
        {"label", "run_id", "workflow_seconds", "sum_job_seconds", "realized_jobs"},
        "historical reference",
    )
    require(
        type(reference["label"]) is str and type(reference["run_id"]) is str,
        "invalid reference label",
    )
    finite(reference["workflow_seconds"], "reference wall")
    finite(reference["sum_job_seconds"], "reference sum")
    integer(reference["realized_jobs"], 1, 100, "reference job count")
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def github_bytes(path, token, limit, deadline):
    """GET only; redirect credentials never leave api.github.com."""
    url = "https://api.github.com/" + path
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "pietto-ci-health",
    }
    opener = urllib.request.build_opener(_NoRedirect())
    for _ in range(4):
        require(time.monotonic() < deadline, "history deadline exceeded")
        try:
            response = opener.open(
                urllib.request.Request(url, headers=headers),
                timeout=min(10, max(0.1, deadline - time.monotonic())),
            )
        except urllib.error.HTTPError as error:
            if error.code not in (301, 302, 303, 307, 308):
                raise ValueError(
                    "CI workload policy: HTTP acquisition unavailable"
                ) from None
            url = urllib.parse.urljoin(url, error.headers["Location"])
            require(
                urllib.parse.urlsplit(url).scheme == "https", "unsafe artifact redirect"
            )
            headers = {"User-Agent": "pietto-ci-health"}
            continue
        with response:
            data = bytearray()
            while block := response.read(min(65536, limit + 1 - len(data))):
                data.extend(block)
                require(
                    len(data) <= limit and time.monotonic() < deadline,
                    "HTTP byte/time limit exceeded",
                )
            return bytes(data)
    raise ValueError("CI workload policy: too many redirects")


def fetch_history(context, token, policy):
    """Bounded read-only adapter. Unavailable history never removes required work."""
    records = []
    provenance = {
        "availability": "INSUFFICIENT_EVIDENCE",
        "candidates": 0,
        "accepted": [],
        "rejected": [],
    }
    current_cost = unavailable_cost("API_UNAVAILABLE")
    if context["event"] != "push" or context["branch"] != "main" or not token:
        provenance["rejected"].append({"reason": "NOT_TRUSTED_MAIN_OR_NO_TOKEN"})
        return records, provenance, current_cost
    require(
        re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", context["repository"]),
        "invalid repository identity",
    )
    prefix = "repos/" + context["repository"] + "/actions/runs/"
    deadline = time.monotonic() + 60
    workflow_id = None

    def api(path):
        return json_bytes(
            github_bytes(path, token, 2 * MAX_HEALTH_BYTES, deadline),
            2 * MAX_HEALTH_BYTES,
        )

    try:
        current = api(prefix + context["run_id"])
        workflow_id = current.get("workflow_id")
        jobs = api(prefix + context["run_id"] + "/jobs?per_page=100")
        require(
            current["head_sha"] == context["checkout"]
            and current["run_attempt"] == context["run_attempt"]
            and current["repository"]["full_name"] == context["repository"],
            "current API context mismatch",
        )
        current_cost = run_cost(current, jobs["jobs"], policy)
    except (ValueError, OSError, KeyError, TypeError):
        current_cost = unavailable_cost("CURRENT_API_UNAVAILABLE")
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        candidates = api(
            prefix.rstrip("/")
            + "?branch=main&event=push&per_page=10&created=%3E%3D"
            + cutoff.strftime("%Y-%m-%d")
        )["workflow_runs"]
        for run in candidates[:10]:
            provenance["candidates"] += 1
            if (
                str(run["id"]) == context["run_id"]
                or run["event"] != "push"
                or run["head_branch"] != "main"
                or type(run["run_attempt"]) is not int
                or run["run_attempt"] != 1
                or type(run["id"]) is not int
                or run["status"] != "completed"
                or run["conclusion"] != "success"
                or run["repository"]["full_name"] != context["repository"]
                or workflow_id is None
                or run.get("workflow_id") != workflow_id
                or datetime.fromisoformat(run["created_at"]) < cutoff
            ):
                continue
            metadata = api(prefix + str(run["id"]) + "/artifacts?per_page=100")
            name = f"ci-health-{run['id']}-1-summary.json"
            artifacts = [a for a in metadata["artifacts"] if a["name"] == name]
            if len(artifacts) != 1 or artifacts[0]["expired"]:
                provenance["rejected"].append(
                    {"run_id": str(run["id"]), "reason": "MISSING_OR_EXPIRED_HEALTH"}
                )
                continue
            artifact = artifacts[0]
            integer(artifact["id"], 1, 2**63 - 1, "artifact ID")
            integer(artifact["size_in_bytes"], 1, MAX_HEALTH_BYTES, "artifact size")
            require(
                artifact["workflow_run"]["id"] == run["id"]
                and artifact["workflow_run"]["head_sha"] == run["head_sha"]
                and artifact["workflow_run"].get("head_branch") == "main",
                "foreign history artifact",
            )
            raw = github_bytes(
                "repos/"
                + context["repository"]
                + f"/actions/artifacts/{artifact['id']}/zip",
                token,
                MAX_HEALTH_BYTES,
                deadline,
            )
            require(
                len(raw) == artifact["size_in_bytes"]
                and "sha256:" + hashlib.sha256(raw).hexdigest() == artifact["digest"],
                "history raw identity mismatch",
            )
            expected = {
                **context,
                "checkout": run["head_sha"],
                "run_id": str(run["id"]),
                "run_attempt": 1,
            }
            value = verify_workflow_health(json_bytes(raw), expected)
            # The completed run's actual API jobs can now fill its formerly partial cost.
            old_jobs = api(prefix + str(run["id"]) + "/jobs?per_page=100")
            require(
                old_jobs["jobs"]
                and all(
                    job.get("status") == "completed"
                    and job.get("conclusion") == "success"
                    for job in old_jobs["jobs"]
                ),
                "history has missing or non-successful constituent jobs",
            )
            historical_topology = {
                "shards": [
                    {"id": shard["partition"]}
                    for shard in value["runtimes"]["3.12"]["shards"]
                ]
            }
            value["cost"] = run_cost(run, old_jobs["jobs"], historical_topology)
            require(value["cost"]["complete"], "missing historical constituent jobs")
            require(
                all(
                    old["context"]["run_id"] != value["context"]["run_id"]
                    for old in records
                ),
                "duplicate historical run identity",
            )
            records.append(value)
            provenance["accepted"].append(
                {
                    "run_id": str(run["id"]),
                    "artifact_id": artifact["id"],
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "source": "natural-successful-main-attempt1",
                }
            )
            if len(records) == 3:
                break
        provenance["availability"] = "AVAILABLE" if records else "INSUFFICIENT_EVIDENCE"
    except (ValueError, OSError, KeyError, TypeError, RecursionError):
        provenance["rejected"].append(
            {"reason": "HISTORY_READ_OR_VALIDATION_UNAVAILABLE"}
        )
        provenance["availability"] = "INSUFFICIENT_EVIDENCE"
    return records, provenance, current_cost


def summary_markdown(health):
    def safe(value):
        return (
            html.escape(str(value), quote=True)
            .replace("|", "&#124;")
            .replace("`", "&#96;")
            .replace("\n", "<br>")
            .replace("\r", "")
        )

    lines = [
        "## CI workload health",
        "",
        "Status: **"
        + safe(health["assessment"]["status"])
        + "**; current screen: "
        + safe(health["assessment"]["current_screen"]),
        "",
        "| Runtime | Work | Nodes | Workers | Test seconds | Startup seconds | Finish spread |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for py, runtime in health["runtimes"].items():
        for shard in runtime["shards"]:
            cells = [
                py,
                shard["partition"],
                shard["selection"]["count"],
                shard["worker_budget"],
                round(shard["elapsed_seconds"], 3),
                round(shard["startup_seconds"], 3),
                round(shard["finish_spread_seconds"], 3),
            ]
            lines.append("| " + " | ".join(safe(v) for v in cells) + " |")
    lines += [
        "",
        "Policy/topology: "
        + safe(health["policy"]["version"])
        + "/"
        + safe(health["policy"]["topology_version"])
        + "; checkout: "
        + safe(health["context"]["checkout"]),
    ]
    for py, runtime in health["runtimes"].items():
        lines.append(
            "- "
            + safe(py)
            + " patch/domain: "
            + safe(runtime["context"]["python_version"])
            + " / "
            + safe(runtime["domain"])
        )
        for shard in runtime["shards"]:
            for row in shard["timing"]["nodes"][:3]:
                seconds = sum(p["seconds"] for p in row["phases"].values())
                lines.append(
                    "  - "
                    + safe(shard["partition"])
                    + ": "
                    + safe(row["node"])
                    + " ("
                    + safe(round(seconds, 3))
                    + "s, "
                    + safe(row["worker"])
                    + ")"
                )
    lines += [
        "",
        "Phase sums include child/preparation/lock waiting; finish spread is not idle CPU or an optimality proof.",
        "",
        "History: "
        + safe(health["history"]["availability"])
        + "; comparable samples: "
        + safe(health["assessment"]["comparable_samples"]),
        "",
        "Current workflow cost: "
        + (
            "complete"
            if health["cost"]["complete"]
            else "partial/unavailable (this job or downstream work has not finished)"
        ),
        "",
        "R1 is a historical topology reference, not a current-schema history sample.",
        "",
        "Suggested review actions (no automatic configuration changes):",
    ]
    for action in health["assessment"]["recommendations"][:20]:
        lines.append(
            "- "
            + safe(action["action"])
            + ": "
            + safe(action["python"] + "/" + action["scope"] + "/" + action["reason"])
        )
    return "\n".join(lines) + "\n"


def fetch_current_summaries(context, token, directory: Path):
    """Mandatory exact current-run raw transport, distinct from optional history."""
    require(bool(token), "missing read-only current-run Actions token")
    require(
        re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", context["repository"]),
        "invalid repository",
    )
    deadline = time.monotonic() + 40
    prefix = "repos/" + context["repository"] + "/actions/"
    run = json_bytes(
        github_bytes(
            prefix + "runs/" + context["run_id"], token, 2 * MAX_HEALTH_BYTES, deadline
        ),
        2 * MAX_HEALTH_BYTES,
    )
    require(
        str(run["id"]) == context["run_id"]
        and type(run["run_attempt"]) is int
        and run["run_attempt"] == context["run_attempt"]
        and run["repository"]["full_name"] == context["repository"]
        and run["event"] == context["event"],
        "foreign current run metadata",
    )
    if context["event"] == "push":
        require(
            run["head_sha"] == context["checkout"]
            and run["head_branch"] == context["branch"],
            "current push head/branch mismatch",
        )
    metadata = json_bytes(
        github_bytes(
            prefix + f"runs/{context['run_id']}/artifacts?per_page=100",
            token,
            2 * MAX_HEALTH_BYTES,
            deadline,
        ),
        2 * MAX_HEALTH_BYTES,
    )
    names = {
        f"ci-health-{context['run_id']}-{context['run_attempt']}-{py}-summary.json"
        for py in ("3.12", "3.13")
    }
    directory.mkdir(parents=True, exist_ok=True)
    require(not list(directory.iterdir()), "current health download root must be fresh")
    facts = []
    for name in sorted(names):
        matches = [a for a in metadata["artifacts"] if a["name"] == name]
        require(
            len(matches) == 1 and not matches[0]["expired"],
            "missing/duplicate current runtime health artifact",
        )
        artifact = matches[0]
        integer(artifact["id"], 1, 2**63 - 1, "artifact ID")
        integer(artifact["size_in_bytes"], 1, MAX_HEALTH_BYTES, "artifact size")
        require(
            str(artifact["workflow_run"]["id"]) == context["run_id"]
            and artifact["workflow_run"]["head_sha"] == run["head_sha"],
            "foreign current artifact",
        )
        raw = github_bytes(
            prefix + f"artifacts/{artifact['id']}/zip",
            token,
            MAX_HEALTH_BYTES,
            deadline,
        )
        with (directory / (name + ".part")).open("xb") as stream:
            stream.write(raw)
        checksum = hashlib.sha256(raw).hexdigest()
        require(
            len(raw) == artifact["size_in_bytes"]
            and artifact["digest"] == "sha256:" + checksum,
            "current raw health identity mismatch",
        )
        report = json_bytes(raw)
        require(
            report["context"]["checkout"] == context["checkout"]
            and report["context"]["run_id"] == context["run_id"]
            and report["context"]["run_attempt"] == context["run_attempt"],
            "current health context mismatch",
        )
        (directory / (name + ".part")).rename(directory / name)
        facts.append(
            {
                "name": name,
                "artifact_id": artifact["id"],
                "bytes": len(raw),
                "sha256": checksum,
            }
        )
    return facts
