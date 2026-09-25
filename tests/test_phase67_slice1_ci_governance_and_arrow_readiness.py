"""Behavioral governance, observation, health and optional readiness contracts."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import ci_validation as ci
from scripts import ci_workloads as w
import _pietto_differential_process_acquisition as process
import _pietto_phase67_arrow_compatibility_probe as probe

ROOT = Path(__file__).resolve().parents[1]


def universe():
    return sorted(
        [
            *(p + "::test_existing" for p in ci.MATRIX_FILES),
            *ci.STANDALONE_NODES,
            "tests/test_new.py::test_ordinary",
            "tests/test_new.py::test_marked",
        ]
    )


def test_new_ordinary_and_module_function_parameter_declarations_preserve_u():
    nodes = universe()
    declaration = (("process-portability",), {"family": "plan"})
    indices = w.resolve(ci.POLICY, nodes, {nodes[-1]: []})
    ordinary = "tests/test_new.py::test_ordinary"
    marked = "tests/test_new.py::test_marked"
    indices = w.resolve(ci.POLICY, nodes, {marked: [declaration] * 3})
    placed = w.place(ci.POLICY, nodes, indices)
    assert (
        ordinary in placed["general-runtime"] and marked in placed["plan-portability"]
    )
    assert (
        sum(map(len, placed.values()))
        == len(set().union(*map(set, placed.values())))
        == len(nodes)
    )
    assert set().union(*map(set, placed.values())) == set(nodes)
    assert ci.partition_nodes(nodes, indices) == placed


@pytest.mark.parametrize(
    "args,kwargs",
    [
        (("unknown",), {}),
        ((True,), {}),
        ((), {}),
        (("process-portability", "plan"), {}),
        (("process-portability",), {"family": "unknown"}),
        (("process-portability",), {"family": True}),
        (("process-portability",), {"family": "plan", "dependency_profile": "arrow"}),
        (("process-portability",), {"family": "plan", "acquisition_group": True}),
        (("process-portability",), {"family": "plan", "shard": "plan-portability"}),
    ],
)
def test_unknown_or_malformed_markers_do_not_become_general(args, kwargs):
    with pytest.raises(ValueError):
        w.resolve(
            ci.POLICY, universe(), {"tests/test_new.py::test_marked": [(args, kwargs)]}
        )


def test_conflicts_and_legacy_contradictions_have_no_winner():
    plan = (("process-portability",), {"family": "plan"})
    emission = (("process-portability",), {"family": "emission"})
    for node, marks in [
        ("tests/test_new.py::test_marked", [plan, emission]),
        (ci.STANDALONE_NODES[0], [emission]),
        (ci.MATRIX_FILES[0] + "::test_existing", [plan]),
    ]:
        with pytest.raises(ValueError, match="conflict|contradict"):
            w.resolve(ci.POLICY, universe(), {node: marks})


@pytest.mark.parametrize(
    "damage",
    [
        "version_bool",
        "threshold_bool",
        "group_split",
        "duplicate_rule",
        "unknown_group",
        "unknown_profile",
        "missing_mode",
        "extra_mode",
    ],
)
def test_registry_and_legacy_errors_fail_before_execution(damage):
    policy = deepcopy(ci.POLICY)
    nodes = universe()
    if damage == "version_bool":
        policy["version"] = True
    elif damage == "threshold_bool":
        policy["thresholds"]["startup"] = True
    elif damage == "group_split":
        req = deepcopy(
            next(r for r in policy["requirements"] if r["kind"] == "shared-acquisition")
        )
        req["family"] = "another"
        policy["requirements"].append(req)
        policy["placements"].append(
            {"kind": req["kind"], "family": "another", "shard": "general-runtime"}
        )
    elif damage == "duplicate_rule":
        policy["legacy_files"].append(deepcopy(policy["legacy_files"][0]))
    elif damage == "unknown_group":
        policy["requirements"][1]["acquisition_group"] = "unregistered"
    elif damage == "unknown_profile":
        policy["shards"][0]["dependency_profile"] = "install-something"
    elif damage == "missing_mode":
        nodes.remove(ci.STANDALONE_NODES[0])
    else:
        nodes.append(ci.STANDALONE[0] + "[new-mode]")
        nodes.sort()
    with pytest.raises(ValueError):
        w.resolve(w.validate_policy(policy), nodes, {})


def test_new_family_requires_only_registration_and_approved_placement():
    policy = deepcopy(ci.POLICY)
    policy["requirements"].append(
        {
            "kind": "process-portability",
            "family": "future-family",
            "acquisition_group": "",
            "dependency_profile": "core",
        }
    )
    node = "tests/test_new.py::test_marked"
    indices = w.resolve(
        w.validate_policy(policy),
        universe(),
        {node: [(("process-portability",), {"family": "future-family"})]},
    )
    with pytest.raises(ValueError, match="no approved placement"):
        w.place(policy, universe(), indices)
    policy["placements"].append(
        {
            "kind": "process-portability",
            "family": "future-family",
            "shard": "plan-portability",
        }
    )
    assert (
        node
        in w.place(w.validate_policy(policy), universe(), indices)["plan-portability"]
    )


def test_observer_only_attaches_to_the_exact_managed_root_and_preserves_exceptions(
    tmp_path, monkeypatch
):
    events = []
    monkeypatch.setattr(process, "_SESSION", None)
    monkeypatch.setattr(
        process, "_OBSERVER_ROOT", tmp_path / "pietto-differential-acquisition"
    )
    monkeypatch.setattr(process, "_OBSERVER_EVENTS", events)
    base = tmp_path / "popen-gw0" if os.environ.get("PYTEST_XDIST_WORKER") else tmp_path
    store = process.acquisition(SimpleNamespace(getbasetemp=lambda: base))
    value = object()
    assert (
        store._produce_observed("preparation", "source-relocated", lambda: value)
        is value
    )
    error = RuntimeError("preserve exception identity")

    def fail():
        raise error

    with pytest.raises(RuntimeError) as caught:
        store._produce_observed("preparation", "installed-wheel", fail)
    assert caught.value is error and [e["success"] for e in events] == [True, False]
    synthetic = process.DifferentialAcquisition(tmp_path / "synthetic")
    assert (
        synthetic._produce_observed("preparation", "source-relocated", lambda: value)
        is value
    )
    assert len(events) == 2
    monkeypatch.setattr(process, "_SESSION", None)
    another = process.acquisition(
        SimpleNamespace(getbasetemp=lambda: tmp_path / "other" / "worker")
    )
    assert another._observations is None


def observation(primary="3.13", duplicate=False):
    cell = [[3, 13], "7", "checkout"]
    event = {
        "kind": "cell",
        "key": cell,
        "start": 10.0,
        "seconds": 1.0,
        "success": True,
    }
    workers = {"gw0": {"enabled": True, "events": [event]}}
    if duplicate:
        workers["gw1"] = {"enabled": True, "events": [deepcopy(event)]}
    context = {"python": primary, "python_version": primary + ".13"}
    properties = [[0, "cell_manifest", json.dumps([cell + [["independent-request"]]])]]
    return context, workers, properties


def test_managed_repetition_is_namespaced_and_memo_reads_are_not_productions():
    identities = []
    for primary in ("3.12", "3.13"):
        context, workers, properties = observation(primary)
        observed = w.managed_observations(
            ci.POLICY,
            "shared-acquisition",
            context,
            [[3, 12], [3, 13]],
            "a" * 64,
            workers,
            properties,
        )
        assert len(observed["productions"]) == 1
        identities.append(observed["productions"][0]["identity"])
    assert identities[0] != identities[1]
    context, workers, properties = observation()
    for _ in range(3):  # Re-reading one observed production does not append an event.
        result = w.managed_observations(
            ci.POLICY,
            "shared-acquisition",
            context,
            [[3, 13]],
            "a" * 64,
            workers,
            properties,
        )
        assert len(result["productions"]) == 1


@pytest.mark.parametrize(
    "damage",
    ["duplicate", "foreign_shard", "missing_observation", "missing_cell", "failed"],
)
def test_illegal_or_unknown_managed_production_is_hard_failure(damage):
    context, workers, properties = observation(duplicate=damage == "duplicate")
    if damage == "missing_observation":
        workers["gw0"]["enabled"] = False
    if damage == "missing_cell":
        workers["gw0"]["events"] = []
    if damage == "failed":
        workers["gw0"]["events"][0]["success"] = False
    with pytest.raises(ValueError):
        w.managed_observations(
            ci.POLICY,
            "general-runtime" if damage == "foreign_shard" else "shared-acquisition",
            context,
            [[3, 13]],
            "a" * 64,
            workers,
            properties,
        )


def shard(
    part="general-runtime", elapsed=100.0, spread=0.0, startup=1.0, nodes=10, workers=4
):
    return {
        "partition": part,
        "elapsed_seconds": elapsed,
        "finish_spread_seconds": spread,
        "startup_seconds": startup,
        "selection": {"count": nodes},
        "worker_budget": workers,
        "timing": {"nodes": []},
        "groups": {part: {"count": nodes, "sha256": "a" * 64}},
        "runner": {
            "image": "ubuntu24",
            "image_version": "sample",
            "os": "Linux",
            "arch": "x86_64",
        },
    }


def history_sample(run, spread=0.0):
    return {
        "context": {"run_id": str(run)},
        "policy": ci.POLICY_ID,
        "runtimes": {
            py: {
                "context": {"python_version": py + ".13"},
                "domain": [[3, 13]],
                "collection": {"count": 10, "sha256": "a" * 64},
                "coverage": {"collected": 10},
                "shards": [shard(spread=spread)],
            }
            for py in ("3.12", "3.13")
        },
        "cost": w.unavailable_cost("synthetic fixture"),
    }


def test_health_empty_one_worker_zero_denominators_and_partial_cost_are_honest():
    t = ci.POLICY["thresholds"]
    assert w.screen([], t)[0]["code"] == "NO_RUNTIME_SAMPLE"
    assert w.screen([shard(elapsed=0, startup=0, nodes=1, workers=1)], t) == []
    assert w.screen([shard(nodes=1, workers=1)], t) == []
    current = history_sample(4, 40)
    result = w.analyze(current, [], t)
    assert (
        result["status"] == "INSUFFICIENT_EVIDENCE"
        and result["current_screen"] == "WATCH"
    )
    assert not result["repeat_confirmations"] and not result["cost_signals"]
    assert current["cost"]["sum_job_seconds"] is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0, True])
def test_health_rejects_nonfinite_and_boolean_durations(value):
    with pytest.raises(ValueError):
        w.screen([shard(elapsed=value)], ci.POLICY["thresholds"])


def test_two_of_three_comparable_history_and_topology_domain_patch_drift():
    current = history_sample(4, 40)
    history = [history_sample(3, 40), history_sample(2, 0), history_sample(1, 40)]
    assert (
        w.analyze(current, history, ci.POLICY["thresholds"])["status"]
        == "REVIEW_RECOMMENDED"
    )
    assert (
        w.analyze(current, history[:2], ci.POLICY["thresholds"])["status"]
        == "INSUFFICIENT_EVIDENCE"
    )
    for field in ("policy", "domain", "patch", "runner", "test-set"):
        changed = deepcopy(history)
        if field == "policy":
            changed[0]["policy"] = {**ci.POLICY_ID, "topology_version": 2}
        elif field == "domain":
            changed[0]["runtimes"]["3.13"]["domain"] = [[3, 12], [3, 13]]
        elif field == "patch":
            changed[0]["runtimes"]["3.13"]["context"]["python_version"] = "3.13.99"
        elif field == "runner":
            changed[0]["runtimes"]["3.13"]["shards"][0]["runner"]["image_version"] = (
                "different"
            )
        else:
            changed[0]["runtimes"]["3.13"]["collection"]["sha256"] = "b" * 64
            changed[0]["runtimes"]["3.13"]["shards"][0]["groups"]["general-runtime"][
                "sha256"
            ] = "b" * 64
        result = w.analyze(current, changed, ci.POLICY["thresholds"])
        assert (
            result["status"] == "INSUFFICIENT_EVIDENCE"
            and result["history_comparisons"][0]["differences"]
        )


def test_slow_correct_workload_only_suggests_review_and_preserves_selection():
    current = history_sample(4)
    s = current["runtimes"]["3.13"]["shards"][0]
    s["selection"]["count"] = 3
    s["timing"]["nodes"] = [
        {"node": "x|`\n::error::text", "phases": {"call": {"seconds": 80}}}
    ]
    before = deepcopy(current)
    result = w.analyze(current, [], ci.POLICY["thresholds"])
    assert current == before and result["recommendations"]
    assert {r["action"] for r in result["recommendations"]} <= {
        "inspect_long_node",
        "consider_merge",
    }
    current.update(assessment=result, history={"availability": "INSUFFICIENT_EVIDENCE"})
    current["context"]["checkout"] = "a" * 40
    s["timing"]["nodes"][0]["worker"] = "gw0"
    text = w.summary_markdown(current)
    assert "INSUFFICIENT_EVIDENCE" in text and "not idle CPU" in text


def test_pr_and_unavailable_history_do_not_fetch_or_invent_cost(monkeypatch):
    def forbidden(*args):
        raise AssertionError("PR must not fetch trusted main history")

    monkeypatch.setattr(w, "github_bytes", forbidden)
    context = {
        "event": "pull_request",
        "branch": "main",
        "repository": "MianliWang/pietto",
        "run_id": "7",
        "checkout": "a" * 40,
        "run_attempt": 1,
    }
    records, provenance, cost = w.fetch_history(context, "unused-token", ci.POLICY)
    assert (
        records == []
        and provenance["availability"] == "INSUFFICIENT_EVIDENCE"
        and cost["sum_job_seconds"] is None
    )

    def unavailable(*args):
        raise OSError("bounded unavailable")

    monkeypatch.setattr(w, "github_bytes", unavailable)
    records, provenance, cost = w.fetch_history(
        {**context, "event": "push"}, "unused-token", ci.POLICY
    )
    assert (
        not records
        and provenance["availability"] == "INSUFFICIENT_EVIDENCE"
        and cost["workflow_elapsed_seconds"] is None
    )


def test_coverage_v1_and_policy_descriptor_context_forgery_are_rejected():
    from test_phase11_ci_workflow import _reports, _verify

    for damage in ("v1", "policy", "bool_policy", "descriptor", "domain", "inputs"):
        collection, reports = _reports()
        if damage == "v1":
            reports[0]["format"] = "pietto.ci-coverage.v1"
        elif damage == "policy":
            reports[0]["policy"] = {**ci.POLICY_ID, "sha256": "f" * 64}
        elif damage == "bool_policy":
            reports[0]["policy"] = {**ci.POLICY_ID, "version": True}
        elif damage == "descriptor":
            reports[0]["requirements"]["indices"][0] = True
        elif damage == "domain":
            reports[0]["domain"] = [[3, 12]]
        else:
            reports[0]["inputs"] = "f" * 64
        with pytest.raises(ValueError):
            _verify(collection, reports)


def test_arrow_probe_import_is_inert_and_absence_is_not_a_skip_or_success(
    tmp_path, monkeypatch
):
    assert importlib.util.find_spec("pyarrow") is None
    assert len(probe.CASES) == 9 and set(probe.CASES) == set(w.CASES)

    def absent(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(probe.importlib, "import_module", absent)
    output = tmp_path / "readiness.json"
    with pytest.raises(ModuleNotFoundError):
        probe.main(["--report", str(output)])
    assert not output.exists()


def test_readiness_does_not_accept_exit_zero_without_every_real_witness():
    context = {
        "checkout": "a" * 40,
        "run_id": "synthetic",
        "run_attempt": 1,
        "python": "3.13",
        "python_version": "3.13.13",
    }
    value = {
        "format": w.READINESS_FORMAT,
        "context": context,
        "pyarrow": "25.0.1",
        "platform": {"system": "Linux", "machine": "x86_64"},
        "script_sha256": "a" * 64,
        "requirements_sha256": "b" * 64,
        "cases": {
            name: {"passed": True, "observations": {"pretend": True}}
            for name in w.CASES
        },
        "limits": probe.LIMITS,
        "exit_code": 0,
    }
    with pytest.raises(ValueError, match="required Arrow witness"):
        w.verify_readiness(value, context, "a" * 64, "b" * 64)
    del value["cases"]["ipc"]
    with pytest.raises(ValueError, match="incomplete"):
        w.verify_readiness(value, context, "a" * 64, "b" * 64)


def test_marker_registration_and_workflow_policy_are_connected():
    ini = (ROOT / "pytest.ini").read_text()
    assert "ci_workload(" in ini and "addopts" not in ini and "testpaths" not in ini
    from test_phase11_ci_workflow import _job

    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    for py, word in (("3.12", "twelve"), ("3.13", "thirteen")):
        runtime = _job(workflow, "runtime_" + word)
        assert [
            line.strip()[2:]
            for line in runtime.splitlines()
            if line.startswith("          - ")
        ] == list(ci.PARTITIONS)
        checks = _job(workflow, "checks_" + word)
        assert "name: Compiler / Package " + py in checks
        assert (
            "Run real isolated Arrow readiness experiment" in checks
            and "check-arrow --python " + py in checks
        )
        assert "--require-hashes --only-binary :all: --no-deps" in checks
        completion = _job(workflow, "python_" + word)
        assert (
            "--health-dir" in completion
            and "--readiness" in completion
            and "--summary" in completion
        )
    aggregate = _job(workflow, "target_conformance_aggregate")
    assert workflow.count("actions: read") == 1 and "actions: read" in aggregate
    assert (
        "Report workload health and bounded trusted history" in aggregate
        and "CI_HEALTH_TOKEN: ${{ github.token }}" in aggregate
    )
    assert "retention-days: 30" in aggregate


def readiness_fixture(context):
    # Explicit synthetic protocol fixture, based on the independently executed tiny probe.
    # This does not execute Arrow or certify native behavior inside the core suite.
    observations = {
        "adaptation": {
            "observations": {
                "narrowing_refused": True,
                "original_type": "int16",
                "product_adapter_implemented": False,
                "safe_widening": "int64",
            },
            "passed": True,
        },
        "alias": {
            "observations": {
                "backing_lifetime_retained": True,
                "borrowed_obligation": "retain owner and prohibit external mutation",
                "external_mutation_visible": True,
                "owned_copy_isolated": True,
                "whole_system_zero_copy": False,
            },
            "passed": True,
        },
        "capsules": {
            "observations": {
                "array_protocol": True,
                "binary16_preserved": True,
                "independent_c_implementation": False,
                "retained_after_exporter_and_reader_release": True,
                "schema_protocol": True,
                "stream_protocol": True,
                "uuid_extension_preserved": True,
            },
            "passed": True,
        },
        "carriers": {
            "observations": {
                "duplicate_labels_positional": True,
                "nullable_false_accepts_actual_null": True,
                "pietto_must_check_actual_nulls": True,
                "schema_equal_with_metadata": False,
                "schema_equal_without_metadata": True,
                "source_duplicate_labels": "PIE-S2305 remains unchanged",
                "typed_all_null": True,
                "zero_rows": True,
            },
            "passed": True,
        },
        "device": {
            "observations": {
                "c_array_api": True,
                "c_device_array_api": True,
                "device_class_available": True,
                "future_non_cpu": "explicit boundary; synthetic refusal is policy-only",
                "gpu_executed": False,
                "observed_cpu": True,
            },
            "passed": True,
        },
        "finite": {
            "observations": {
                "empty_batch_is_eof": False,
                "executor_success_proven": False,
                "normal_finite_finalization": True,
                "rechunk_order_and_multiplicity": True,
                "values": [1, 1, None, 2, 3],
            },
            "passed": True,
        },
        "ipc": {
            "observations": {
                "binary16_preserved": True,
                "boundary_rows": 2,
                "boundary_truncation_accepted": True,
                "complete_rows": 3,
                "explicit_result_completeness_required": True,
                "mid_message_refused": True,
                "roundtrip": True,
                "uuid_extension_preserved": True,
            },
            "passed": True,
        },
        "strings": {
            "observations": {
                "default": "string",
                "large_string": "explicit binding only",
                "large_string_type": "large_string",
                "metadata_retained_and_removed": True,
                "slice_offset": 1,
                "string_type": "string",
            },
            "passed": True,
        },
        "types": {
            "observations": {
                "bool_and_nulls": True,
                "decimal128": [9, 2],
                "decimal256": [65, 3],
                "finite_float64_signed_zero": True,
                "integer_types": ["int16", "int32", "int64"],
                "timestamp_timezone": None,
                "timestamp_unit": "us",
                "unicode_exact": True,
                "upstream_meaning_proven": False,
                "uuid_candidates": ["extension<arrow.uuid>", "fixed_size_binary[16]"],
                "uuid_choice": "canonical-extension",
            },
            "passed": True,
        },
    }
    return {
        "format": w.READINESS_FORMAT,
        "context": context,
        "pyarrow": "25.0.1",
        "platform": {"system": "Linux", "machine": "x86_64"},
        "script_sha256": "a" * 64,
        "requirements_sha256": "b" * 64,
        "cases": observations,
        "limits": probe.LIMITS,
        "exit_code": 0,
    }


def complete_history_fixture(run="37"):
    from test_phase11_ci_workflow import _reports

    runtimes = {}
    for py in ("3.12", "3.13"):
        collection, reports = _reports()
        context = {
            **collection["context"],
            "run_id": run,
            "python": py,
            "python_version": py + ".13",
        }
        domain = [[int(v) for v in py.split(".")]]
        shards = []
        for report in reports:
            report["context"] = context
            report["domain"] = domain
            observers = {f"gw{i}": {"enabled": True, "events": []} for i in range(4)}
            if report["partition"] == "shared-acquisition":
                cell = [domain[0], "7", "checkout"]
                report["properties"] = [
                    [0, "cell_manifest", json.dumps([cell + [["synthetic-request"]]])]
                ]
                observers["gw0"]["events"] = [
                    {
                        "kind": "cell",
                        "key": cell,
                        "start": 101.0,
                        "seconds": 1.0,
                        "success": True,
                    }
                ]
            phase_reports = [
                pytest.TestReport(
                    nodeid=node,
                    location=("test.py", 0, "test"),
                    keywords={},
                    outcome="passed",
                    longrepr=None,
                    when=phase,
                    duration=0.1,
                    start=101.0,
                    stop=101.1,
                    worker_id="gw0",
                )
                for node in report["nodes"]
                for phase in ("setup", "call", "teardown")
            ]
            scheduler = next(
                s["scheduler"]
                for s in ci.POLICY["shards"]
                if s["id"] == report["partition"]
            )
            timing = w.timing_summary(phase_reports, 100.0, scheduler)
            managed = w.managed_observations(
                ci.POLICY,
                report["partition"],
                context,
                domain,
                ci.INPUT_ID,
                observers,
                report["properties"],
            )
            health = w.shard_health(
                report,
                timing,
                managed,
                {
                    "image": "ubuntu24",
                    "image_version": "test",
                    "os": "Linux",
                    "arch": "x86_64",
                },
            )
            w.verify_shard_health(health, ci.POLICY, report)
            shards.append(health)
        coverage = {
            "collected": len(collection["nodes"]),
            "selected": len(collection["nodes"]),
            "executed_terminal": len(collection["nodes"]),
            "passed": len(collection["nodes"]),
            "skipped": 0,
            "python": py,
            "partitions": {r["partition"]: len(r["nodes"]) for r in reports},
        }
        runtimes[py] = {
            "format": w.HEALTH_FORMAT,
            "kind": "runtime",
            "context": context,
            "policy": ci.POLICY_ID,
            "domain": domain,
            "collection": collection["collection"],
            "coverage": coverage,
            "shards": shards,
            "readiness": readiness_fixture(context),
        }
    context = {
        "repository": "MianliWang/pietto",
        "checkout": "1" * 40,
        "run_id": run,
        "run_attempt": 1,
        "event": "push",
        "branch": "main",
    }
    value = {
        "format": w.HEALTH_FORMAT,
        "kind": "workflow",
        "context": context,
        "policy": ci.POLICY_ID,
        "runtimes": runtimes,
        "cost": w.unavailable_cost("synthetic"),
        "assessment": {},
        "history": {
            "availability": "INSUFFICIENT_EVIDENCE",
            "candidates": 0,
            "accepted": [],
            "rejected": [],
        },
        "reference": {
            "label": "synthetic fixture",
            "run_id": "0",
            "workflow_seconds": 100.0,
            "sum_job_seconds": 200.0,
            "realized_jobs": 15,
        },
    }
    value["assessment"] = w.analyze(value, [], ci.POLICY["thresholds"])
    return w.verify_workflow_health(value)


def test_readiness_positive_protocol_and_synthetic_non_cpu_refusal():
    context = {
        "checkout": "1" * 40,
        "run_id": "synthetic",
        "run_attempt": 1,
        "python": "3.13",
        "python_version": "3.13.13",
    }
    good = readiness_fixture(context)
    assert w.verify_readiness(good, context, "a" * 64, "b" * 64) is good
    for damage in ("cpu", "null", "uuid", "ipc", "phase", "pin"):
        value = deepcopy(good)
        if damage == "cpu":
            value["cases"]["device"]["observations"]["observed_cpu"] = False
        elif damage == "null":
            value["cases"]["carriers"]["observations"][
                "pietto_must_check_actual_nulls"
            ] = False
        elif damage == "uuid":
            value["cases"]["types"]["observations"]["uuid_choice"] = (
                "invisible-fallback"
            )
        elif damage == "ipc":
            value["cases"]["ipc"]["observations"][
                "explicit_result_completeness_required"
            ] = False
        elif damage == "phase":
            del value["cases"]["capsules"]
        else:
            value["pyarrow"] = "unreviewed-version"
        with pytest.raises(ValueError):
            w.verify_readiness(value, context, "a" * 64, "b" * 64)


def test_history_adapter_checks_raw_provenance_and_is_bounded(monkeypatch):
    from datetime import datetime, timezone
    import hashlib

    value = complete_history_fixture()
    raw = w.canonical(value)
    now = datetime.now(timezone.utc).isoformat()

    def run(number):
        return {
            "id": number,
            "head_sha": "1" * 40,
            "event": "push",
            "head_branch": "main",
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": "MianliWang/pietto"},
            "workflow_id": 7,
            "created_at": now,
            "updated_at": now,
        }

    artifact = {
        "id": 123,
        "name": "ci-health-37-1-summary.json",
        "expired": False,
        "size_in_bytes": len(raw),
        "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "workflow_run": {"id": 37, "head_sha": "1" * 40, "head_branch": "main"},
    }
    calls = []

    def get(path, token, limit, deadline):
        calls.append(path)
        assert token == "test-only-token"
        if path.endswith("/artifacts/123/zip"):
            return raw
        if "/artifacts?" in path:
            return w.canonical({"artifacts": [artifact]})
        if "/jobs?" in path:
            names = [
                *(f"Compiler / Package {py}" for py in ("3.12", "3.13")),
                *(
                    f"Runtime {py} / {part}"
                    for py in ("3.12", "3.13")
                    for part in ci.PARTITIONS
                ),
                "Python 3.12",
                "Python 3.13",
                "Target postgres",
                "Target mysql",
                "Target conformance aggregate",
            ]
            return w.canonical(
                {
                    "jobs": [
                        {
                            "name": name,
                            "status": "completed",
                            "conclusion": "success",
                            "started_at": now,
                            "completed_at": now,
                        }
                        for name in names
                    ]
                }
            )
        if "?branch=" in path:
            return w.canonical({"workflow_runs": [run(38), run(37)]})
        return w.canonical(run(38))

    monkeypatch.setattr(w, "github_bytes", get)
    context = {**value["context"], "run_id": "38"}
    records, provenance, cost = w.fetch_history(context, "test-only-token", ci.POLICY)
    assert (
        len(records) == 1
        and provenance["accepted"][0]["artifact_id"] == 123
        and len(calls) <= 7
    )
    assert (
        provenance["candidates"] == 2
        and cost["complete"]
        and cost["sum_job_seconds"] == 0
    )
    artifact["digest"] = "sha256:" + "0" * 64
    records, provenance, _ = w.fetch_history(context, "test-only-token", ci.POLICY)
    assert not records and provenance["availability"] == "INSUFFICIENT_EVIDENCE"
    assert (
        provenance["rejected"][-1]["reason"] == "HISTORY_READ_OR_VALIDATION_UNAVAILABLE"
    )


def test_mandatory_current_raw_transport_fails_on_digest_or_context_drift(
    tmp_path, monkeypatch
):
    import hashlib

    value = complete_history_fixture()
    rows = []
    payloads = {}
    for index, py in enumerate(("3.12", "3.13"), 1):
        data = w.canonical(value["runtimes"][py])
        payloads[index] = data
        rows.append(
            {
                "id": index,
                "name": f"ci-health-37-1-{py}-summary.json",
                "expired": False,
                "size_in_bytes": len(data),
                "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
                "workflow_run": {"id": 37, "head_sha": "1" * 40},
            }
        )

    def get(path, *args):
        if path.endswith("/runs/37"):
            return w.canonical(
                {
                    "id": 37,
                    "run_attempt": 1,
                    "repository": {"full_name": "MianliWang/pietto"},
                    "event": context["event"],
                    "head_branch": "main",
                    "head_sha": provider_head,
                }
            )
        return (
            w.canonical({"artifacts": rows})
            if "?per_page=" in path
            else payloads[int(path.split("/")[-2])]
        )

    context = value["context"]
    provider_head = context["checkout"]
    monkeypatch.setattr(w, "github_bytes", get)
    facts = w.fetch_current_summaries(context, "test-token", tmp_path / "valid")
    assert len(facts) == 2 and {p.name for p in (tmp_path / "valid").iterdir()} == {
        r["name"] for r in rows
    }
    context = {**context, "event": "pull_request", "branch": "12/merge"}
    provider_head = "2" * 40
    for row in rows:
        row["workflow_run"]["head_sha"] = provider_head
    assert (
        len(w.fetch_current_summaries(context, "test-token", tmp_path / "pr-merge"))
        == 2
    )
    rows[0]["digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="identity mismatch"):
        w.fetch_current_summaries(context, "test-token", tmp_path / "bad")
    assert list((tmp_path / "bad").glob("*.part"))


def test_historical_health_cannot_hide_missing_terminal_metadata_or_forge_advice():
    good = complete_history_fixture()
    for damage in ("partial", "nan", "spread", "owner", "extra", "advice", "readiness"):
        value = deepcopy(good)
        shard = value["runtimes"]["3.13"]["shards"][0]
        if damage == "partial":
            shard["evidence_complete"] = False
        elif damage == "nan":
            shard["timing"]["nodes"][0]["phases"]["call"]["seconds"] = float("nan")
        elif damage == "spread":
            shard["finish_spread_seconds"] = 99.0
        elif damage == "owner":
            shard["managed"]["productions"][0]["worker"] = "foreign"
        elif damage == "extra":
            shard["execute_yaml"] = "forbidden"
        elif damage == "advice":
            value["assessment"]["recommendations"] = [
                {
                    "action": "execute_yaml",
                    "python": "all",
                    "scope": "workflow",
                    "reason": "forged",
                    "provisional": False,
                }
            ]
        else:
            del value["runtimes"]["3.13"]["readiness"]["cases"]["ipc"]
        with pytest.raises(ValueError):
            w.verify_workflow_health(value)


def test_complete_cost_tradeoffs_remain_advisory_and_require_history():
    current = history_sample(4)
    history = [history_sample(i) for i in (3, 2, 1)]
    for value in history:
        value["cost"].update(
            complete=True,
            workflow_elapsed_seconds=100.0,
            sum_job_seconds=500.0,
            longest_dependency_path_job_seconds=90.0,
        )
    current["cost"].update(
        complete=True,
        workflow_elapsed_seconds=131.0,
        sum_job_seconds=650.0,
        longest_dependency_path_job_seconds=120.0,
    )
    result = w.analyze(current, history, ci.POLICY["thresholds"])
    assert result["status"] == "REVIEW_RECOMMENDED"
    assert set(result["repeated_cost_codes"]) == {
        "CRITICAL_PATH_REGRESSION",
        "RUNNER_COST_TRADEOFF",
    }
    assert {a["action"] for a in result["recommendations"]} == {
        "check_new_requirements",
        "consider_merge",
    }


def test_duplicate_history_cannot_manufacture_two_of_three_confirmation():
    current = history_sample(4, 40)
    repeated = history_sample(3, 40)
    with pytest.raises(ValueError, match="duplicate historical run"):
        w.analyze(
            current,
            [repeated, deepcopy(repeated), history_sample(1)],
            ci.POLICY["thresholds"],
        )
    foreign = history_sample(2, 40)
    foreign["context"]["repository"] = "foreign/repository"
    assert "repository" in w.context_compatible(current, foreign)


def test_cost_intervals_and_named_group_owners_fail_closed():
    with pytest.raises(ValueError, match="job timestamp interval"):
        w.run_cost(
            {"status": "in_progress"},
            [
                {
                    "name": "bad",
                    "status": "completed",
                    "started_at": "2026-09-25T00:00:02+00:00",
                    "completed_at": "2026-09-25T00:00:01+00:00",
                }
            ],
            ci.POLICY,
        )
    policy = deepcopy(ci.POLICY)
    policy["placements"] = [
        p for p in policy["placements"] if p["kind"] != "shared-acquisition"
    ]
    with pytest.raises(ValueError, match="no approved owner"):
        w.validate_policy(policy)
