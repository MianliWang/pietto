from __future__ import annotations

from copy import deepcopy
import importlib.util
import re
import sys
from typing import Any, cast

import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
PYTHON_VERSION_PATH = REPO_ROOT / ".python-version"
PRIMARY = (("3.12", "twelve"), ("3.13", "thirteen"))
EXPECTED_JOBS = (
    "checks_twelve",
    "runtime_twelve",
    "python_twelve",
    "checks_thirteen",
    "runtime_thirteen",
    "python_thirteen",
    "target_conformance",
    "target_conformance_aggregate",
)
ACTIONS = {
    "actions/checkout": ("3d3c42e5aac5ba805825da76410c181273ba90b1", "v7.0.1"),
    "actions/setup-python": ("5fda3b95a4ea91299a34e894583c3862153e4b97", "v7.0.0"),
    "actions/setup-java": ("de7274f081f381c8f8158605e0321c36c376e2e6", "v6.0.1"),
    "astral-sh/setup-uv": ("c18668ad3cf93ea998bef934396af7bb5c839dc7", "v10.2.0"),
    "actions/upload-artifact": ("043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", "v7.0.1"),
    "actions/download-artifact": ("3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c", "v8.0.1"),
}
AUXILIARY = (
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
)


def _job(workflow: str, name: str) -> str:
    marker = f"  {name}:\n"
    assert workflow.count(marker) == 1
    return re.split(r"\n  [a-z_]+:\n", workflow.split(marker, 1)[1], maxsplit=1)[0]


def test_ci_triggers_permissions_runner_and_matrix_are_exact() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert re.search(
        r"(?m)^on:\n  pull_request:\n  push:\n    branches:\n      - main$", workflow
    )
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
    assert (
        tuple(re.findall(r"(?m)^  ([a-z_]+):$", workflow.split("jobs:\n", 1)[1]))
        == EXPECTED_JOBS
    )
    assert workflow.count("runs-on: ubuntu-latest") == len(EXPECTED_JOBS)
    assert PYTHON_VERSION_PATH.read_text(encoding="utf-8") == "3.12\n"
    for python, word in PRIMARY:
        for owner in ("checks", "runtime", "python"):
            assert f'python-version: "{python}"' in _job(workflow, f"{owner}_{word}")
        runtime = _job(workflow, f"runtime_{word}")
        assert re.findall(r"(?m)^          - (\w+)$", runtime) == [
            "matrix",
            "standalone",
            "remaining",
        ]
        assert "fail-fast: false" in runtime
        assert "needs:" not in runtime and "needs:" not in _job(
            workflow, f"checks_{word}"
        )
        assert "include:" not in runtime and "exclude:" not in runtime
    # Two three-way runtime matrices and the two-target matrix add five jobs.
    assert len(EXPECTED_JOBS) + 5 == 13


def test_ci_sets_java_21_and_pins_the_local_uv_version() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for python, word in PRIMARY:
        for owner in ("checks", "runtime"):
            job = _job(workflow, f"{owner}_{word}")
            for fragment in (
                "distribution: temurin",
                'java-version: "21"',
                "overwrite-settings: false",
                "verify-signature: true",
            ):
                assert fragment in job
        for owner in ("checks", "runtime", "python"):
            job = _job(workflow, f"{owner}_{word}")
            for fragment in (
                'version: "0.11.19"',
                "enable-cache: false",
                'echo "UV_PROJECT_ENVIRONMENT=$RUNNER_TEMP/pietto-venv" >> "$GITHUB_ENV"',
                'echo "UV_CACHE_DIR=$RUNNER_TEMP/uv-cache" >> "$GITHUB_ENV"',
                'echo "UV_PYTHON=$pythonLocation/bin/python" >> "$GITHUB_ENV"',
            ):
                assert fragment in job
            assert job.count("UV_PYTHON") == 1
            assert job.count("uv sync --locked") == 1
            assert job.index("uv sync --locked") < job.index(
                "uv run python scripts/ci_validation.py"
            )
    for forbidden in ("uv sync --python", "--upgrade", "--refresh"):
        assert forbidden not in workflow


def test_ci_invokes_only_the_accepted_release_readiness_commands() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert workflow.count(" --common") == 1
    for python, word in PRIMARY:
        checks = _job(workflow, f"checks_{word}")
        assert f"scripts/ci_validation.py gates --python {python}" in checks
        assert (" --common" in checks) == (python == "3.12")
        for command in AUXILIARY:
            assert checks.count(command) == 1
        assert f"scripts/ci_validation.py collect --python {python}" in checks
        assert "scripts/ci_validation.py run" not in checks
        runtime = _job(workflow, f"runtime_{word}")
        assert (
            f"scripts/ci_validation.py run --python {python} --partition ${{{{ matrix.partition }}}}"
            in runtime
        )
        assert all(command not in runtime for command in AUXILIARY)
    assert "scripts/validate.py" not in workflow
    for forbidden in (
        "emit_" + "postgres_sql",
        "emit_" + "mysql_sql",
        "build_" + "ir",
        "pa" + "rse_" + "file",
        "pietto emit-" + "sql",
    ):
        assert forbidden not in workflow


def test_every_action_is_pinned_to_a_reviewed_full_sha() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    uses = re.findall(
        r"(?m)^        uses: ([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)@([0-9a-f]{40}) # (v[0-9.]+)$",
        workflow,
    )
    assert len(uses) == workflow.count("uses:")
    assert {repository for repository, _, _ in uses} == set(ACTIONS)
    for repository, sha, version in uses:
        assert (sha, version) == ACTIONS[repository]
    assert not re.search(
        r"(?m)^\s*uses:\s+\S+@(v[0-9]+|main|master|HEAD|latest)\s*$", workflow
    )


def test_ci_has_no_write_credentials_and_only_scoped_evidence_artifacts() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    lowered = workflow.lower()
    for forbidden in (
        "contents: write",
        "write-all",
        "pull-requests:",
        "id-token:",
        "secrets.",
        "pass" + "word",
        "pyp" + "i",
        "tw" + "ine",
        "pub" + "lish",
        "dep" + "loy",
        "pull_request_target",
        "workflow_run:",
        "workflow_dispatch:",
        "continue-on-error",
        "cancel-in-progress",
        "|| true",
        "set +e",
    ):
        assert forbidden not in lowered
    assert workflow.count("persist-credentials: false") == len(EXPECTED_JOBS)
    for python, word in PRIMARY:
        for owner, part in (
            ("checks", "collection"),
            ("runtime", "${{ matrix.partition }}"),
        ):
            job = _job(workflow, f"{owner}_{word}")
            name = f"ci-coverage-${{{{ github.run_id }}}}-${{{{ github.run_attempt }}}}-{python}-{part}.json"
            assert f"name: {name}" in job
            assert f"path: ${{{{ runner.temp }}}}/coverage-reports/{name}" in job
            for fragment in (
                "archive: false",
                "if-no-files-found: error",
                "overwrite: false",
                "include-hidden-files: false",
                "retention-days: 1",
                "ARTIFACT_ID: ${{ steps.coverage.outputs.artifact-id }}",
                "ARTIFACT_DIGEST: ${{ steps.coverage.outputs.artifact-digest }}",
                '--artifact-id "$ARTIFACT_ID" --artifact-digest "$ARTIFACT_DIGEST"',
            ):
                assert fragment in job
        summary = _job(workflow, f"python_{word}")
        assert summary.count("digest-mismatch: error") == 4
        assert summary.count("skip-decompress: true") == 4
        for part in ("collection", "matrix", "standalone", "remaining"):
            assert (
                f"name: ci-coverage-${{{{ github.run_id }}}}-${{{{ github.run_attempt }}}}-{python}-{part}.json"
                in summary
            )
    for forbidden in ("github-token:", "run-id:", "repository:", "pattern:"):
        assert forbidden not in workflow
    target = _job(workflow, "target_conformance")
    aggregate = _job(workflow, "target_conformance_aggregate")
    for fragment in (
        "archive: false",
        "if-no-files-found: error",
        "overwrite: false",
        "include-hidden-files: false",
        "retention-days: 1",
    ):
        assert fragment in target
    assert aggregate.count("digest-mismatch: error") == 2
    assert aggregate.count("skip-decompress: true") == 2


def test_ci_does_not_rewrite_repository_outputs() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "ruff format .",
        "make generate-" + "par" + "ser",
        "-o src/pietto/generated",
        "git commit",
        "git push",
        "run: uv build",
    ):
        assert forbidden not in workflow


def test_existing_release_readiness_scripts_remain_independent() -> None:
    scripts = {
        name: (REPO_ROOT / "scripts" / name).read_text(encoding="utf-8")
        for name in ("validate.py", "check_generated.py", "check_goldens.py")
    }
    for name in ("check_generated", "check_goldens", "package_smoke"):
        assert name not in scripts["validate.py"]
    assert "check_goldens" not in scripts["check_generated.py"]
    assert "package_smoke" not in scripts["check_generated.py"]
    assert "check_generated" not in scripts["check_goldens.py"]
    assert "package_smoke" not in scripts["check_goldens.py"]
    assert "scripts/validate.py" not in scripts["check_generated.py"]
    assert "scripts/validate.py" not in scripts["check_goldens.py"]


def test_two_target_cells_and_strict_always_aggregate_are_explicit() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for python, word in PRIMARY:
        summary = _job(workflow, f"python_{word}")
        assert f"name: Python {python}" in summary
        assert f"needs: [checks_{word}, runtime_{word}]" in summary
        assert "if: always()" in summary
        assert f"CHECKS_STATUS: ${{{{ needs.checks_{word}.result }}}}" in summary
        assert f"RUNTIME_STATUS: ${{{{ needs.runtime_{word}.result }}}}" in summary
        assert (
            '--checks-status "$CHECKS_STATUS" --runtime-status "$RUNTIME_STATUS"'
            in summary
        )
        assert f"scripts/ci_validation.py verify --python {python}" in summary
    target = _job(workflow, "target_conformance")
    aggregate = _job(workflow, "target_conformance_aggregate")
    assert (
        "      matrix:\n        target:\n          - postgres\n          - mysql\n"
        in target
    )
    assert "fail-fast: false" in target and 'python-version: "3.13"' in target
    assert "exclude:" not in target and "include:" not in target
    assert "needs: [python_twelve, python_thirteen, target_conformance]" in aggregate
    assert "if: always()" in aggregate
    assert (
        "COMPILER_STATUS: ${{ needs.python_twelve.result == 'success' && needs.python_thirteen.result == 'success' && 'success' || 'failure' }}"
        in aggregate
    )
    assert "TARGET_STATUS: ${{ needs.target_conformance.result }}" in aggregate
    assert (
        '--compiler-status "$COMPILER_STATUS" --target-status "$TARGET_STATUS"'
        in aggregate
    )
    assert "_pietto_target_conformance.py run" in target
    for section in (target, aggregate):
        assert "_pietto_target_conformance.py verify-receipts" in section
        assert '--expected-commit "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID"' in section
        assert '--run-attempt "$GITHUB_RUN_ATTEMPT"' in section
        assert "--pins tests/phase66_target_pins.json" in section
    assert "ARTIFACT_DIGEST: ${{ steps.receipt.outputs.artifact-digest }}" in target
    assert "ARTIFACT_ID: ${{ steps.receipt.outputs.artifact-id }}" in target
    assert '--artifact-digest "$ARTIFACT_DIGEST" --artifact-id "$ARTIFACT_ID"' in target


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pietto_ci_validation", ROOT / "scripts/ci_validation.py"
)
assert SPEC is not None and SPEC.loader is not None
ci = cast(Any, importlib.util.module_from_spec(SPEC))
SPEC.loader.exec_module(ci)
CONTEXT = {
    "checkout": "1" * 40,
    "run_id": "37",
    "run_attempt": 1,
    "python": "3.13",
    "python_version": "3.13.13",
}
FUTURE = "tests/test_new_ordinary.py::test_future"


def _universe():
    # This is the full collected input, constructed before asking the classifier.
    return sorted(
        [
            *(path + "::test_existing" for path in ci.MATRIX_FILES),
            *ci.STANDALONE_NODES,
            FUTURE,
            FUTURE + "_other",
        ]
    )


def _reports():
    universe = _universe()
    base = {
        "format": ci.FORMAT,
        "context": dict(CONTEXT),
        "exit_code": 0,
        "collection": ci.collection_identity(universe),
        "elapsed_seconds": 1.0,
    }
    collection = {**base, "kind": "collection", "nodes": universe}
    partitions = []
    for part, nodes in ci.partition_nodes(universe).items():
        partitions.append(
            {
                **deepcopy(base),
                "kind": "partition",
                "partition": part,
                "nodes": nodes,
                "outcomes": [
                    [i, "passed", "passed", "passed"] for i in range(len(nodes))
                ],
                "workers": 4,
                "properties": [],
                "skips": [],
            }
        )
    return collection, partitions


def _verify(collection, partitions, checks="success", runtime="success"):
    return ci.reconcile(collection, partitions, CONTEXT, checks, runtime)


def test_unknown_ordinary_nodes_and_six_standalone_modes_keep_complete_coverage():
    collection, reports = _reports()
    result = _verify(collection, reports)
    matrix, standalone, remaining = reports
    assert remaining["nodes"] == [FUTURE, FUTURE + "_other"]
    assert standalone["nodes"] == sorted(ci.STANDALONE_NODES)
    assert matrix["nodes"] == sorted(p + "::test_existing" for p in ci.MATRIX_FILES)
    selections = [set(report["nodes"]) for report in reports]
    assert sum(map(len, selections)) == len(set.union(*selections))
    assert set.union(*selections) == set(collection["nodes"])
    assert (
        result["collected"]
        == result["selected"]
        == result["executed_terminal"]
        == len(collection["nodes"])
    )
    assert result["passed"] == len(collection["nodes"]) and result["skipped"] == 0


@pytest.mark.parametrize(
    "damage", ("missing", "duplicate", "foreign", "empty", "stale_mode", "missing_file")
)
def test_selector_drift_never_becomes_an_empty_or_partial_success(damage):
    collection, reports = _reports()
    if damage == "missing":
        reports[1]["nodes"].pop()
        reports[1]["outcomes"].pop()
    elif damage == "duplicate":
        reports[1]["nodes"].append(reports[0]["nodes"][0])
    elif damage == "foreign":
        reports[1]["nodes"][0] = "foreign::test_foreign"
    elif damage == "empty":
        reports[1]["nodes"] = []
        reports[1]["outcomes"] = []
    else:
        nodes = collection["nodes"]
        if damage == "stale_mode":
            nodes.remove(ci.STANDALONE_NODES[0])
        else:
            nodes.remove(ci.MATRIX_FILES[0] + "::test_existing")
        collection["collection"] = ci.collection_identity(nodes)
    with pytest.raises(ValueError):
        _verify(collection, reports)


def test_independent_universe_catches_a_classifier_that_omits_a_node(monkeypatch):
    original = ci.partition_nodes

    def incomplete(nodes):
        partitions = original(nodes)
        partitions["remaining"].remove(FUTURE)
        return partitions

    monkeypatch.setattr(ci, "partition_nodes", incomplete)
    collection, reports = _reports()
    with pytest.raises(ValueError, match="union"):
        _verify(collection, reports)


@pytest.mark.parametrize(
    "field,value",
    (
        ("python", "3.12"),
        ("python_version", "3.13.12"),
        ("checkout", "2" * 40),
        ("run_id", "38"),
        ("run_attempt", 2),
        ("run_attempt", True),
    ),
)
def test_foreign_runtime_checkout_run_and_attempt_are_rejected(field, value):
    collection, reports = _reports()
    reports[0]["context"][field] = value
    with pytest.raises(ValueError):
        _verify(collection, reports)


@pytest.mark.parametrize(
    "damage",
    (
        "missing_shard",
        "duplicate_shard",
        "wrong_collection",
        "wrong_digest",
        "wrong_owner",
        "foreign_owner",
        "foreign_field",
        "pytest_failed",
    ),
)
def test_reports_cannot_substitute_other_parts_or_hide_pytest_failure(damage):
    collection, reports = _reports()
    if damage == "missing_shard":
        reports.pop()
    elif damage == "duplicate_shard":
        reports[1] = deepcopy(reports[0])
    elif damage == "wrong_collection":
        reports[0]["collection"]["count"] += 1
    elif damage == "wrong_digest":
        reports[0]["collection"]["sha256"] = "0" * 64
    elif damage == "wrong_owner":
        reports[0]["partition"] = "remaining"
    elif damage == "foreign_owner":
        reports[1]["partition"] = "foreign"
    elif damage == "foreign_field":
        reports[0]["claimed_pass"] = True
    else:
        reports[0]["exit_code"] = 1
    with pytest.raises(ValueError):
        _verify(collection, reports)


@pytest.mark.parametrize(
    "row",
    (
        [0, "failed", None, "passed"],
        [0, "passed", "failed", "passed"],
        [0, "passed", "passed", "failed"],
        [0, "passed", None, "passed"],
        [0, "passed", "passed", None],
        [True, "passed", "passed", "passed"],
        [99, "passed", "passed", "passed"],
    ),
)
def test_setup_call_teardown_and_terminal_identity_must_all_be_complete(row):
    collection, reports = _reports()
    reports[0]["outcomes"][0] = row
    with pytest.raises(ValueError):
        _verify(collection, reports)


def test_missing_and_duplicate_terminal_ids_are_rejected():
    for duplicate in (False, True):
        collection, reports = _reports()
        if duplicate:
            reports[0]["outcomes"][1] = list(reports[0]["outcomes"][0])
        else:
            reports[0]["outcomes"].pop()
        with pytest.raises(ValueError):
            _verify(collection, reports)


def test_existing_test_skips_remain_observed_terminal_results():
    collection, reports = _reports()
    reports[0]["outcomes"][0] = [0, "skipped", None, "passed"]
    reports[0]["outcomes"][1] = [1, "passed", "skipped", "passed"]
    reports[0]["skips"] = [
        [0, "existing historical object absent"],
        [1, "existing historical object absent"],
    ]
    result = _verify(collection, reports)
    assert result["skipped"] == 2 and result["passed"] == len(collection["nodes"]) - 2


@pytest.mark.parametrize(
    "status", ("failure", "skipped", "cancelled", "timed_out", "", "unknown")
)
@pytest.mark.parametrize("owner", ("checks", "runtime"))
def test_green_reports_cannot_mask_non_successful_dependency_jobs(status, owner):
    collection, reports = _reports()
    with pytest.raises(ValueError, match="jobs"):
        _verify(collection, reports, **{owner: status})


def test_raw_reports_are_bounded_data_and_duplicate_keys_are_rejected(tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"format":1,"format":2}')
    with pytest.raises(ValueError, match="duplicate"):
        ci.read_report(path)
    path.write_bytes(b" " * (ci.MAX_REPORT_BYTES + 1))
    with pytest.raises(ValueError, match="8 MiB"):
        ci.read_report(path)
    path.unlink()
    collection, _ = _reports()
    ci.write_report(path, collection)
    assert ci.read_report(path) == collection
    with pytest.raises(FileExistsError):
        ci.write_report(path, collection)
    link = tmp_path / "link.json"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="regular"):
        ci.read_report(link)


def test_default_local_gates_and_existing_worker_policy_remain_complete(monkeypatch):
    v = ci.validate
    assert tuple(name for name, _ in v.GATES) == (
        "lockfile",
        "format",
        "lint",
        "production typing",
        "test typing",
        "tests",
    )
    assert v.PYTEST_MAX_RESOURCE_WORKERS == 4
    parser = v._build_parser()
    monkeypatch.setattr(
        v, "_resource_worker_count", lambda maximum=None: min(maximum or 4, 4)
    )
    assert ci.runtime_command() == (
        sys.executable,
        "-m",
        "pytest",
        "-n",
        "4",
        "--dist=loadfile",
    )
    assert ci.runtime_command(2) == (
        sys.executable,
        "-m",
        "pytest",
        "-n",
        "2",
        "--dist=loadfile",
    )
    assert ci.runtime_command(4, "standalone")[-1] == "--dist=load"
    assert ci.runtime_command(4, "remaining")[-1] == "--dist=loadfile"
    assert tuple(
        name for name, _ in v._resolved_gates(parser.parse_args(()), parser)
    ) == tuple(name for name, _ in v.GATES)
    monkeypatch.setattr(v, "_resource_worker_count", lambda maximum=None: 1)
    for part in ci.PARTITIONS:
        assert ci.runtime_command(partition=part) == (sys.executable, "-m", "pytest")
    assert v.REPO_ROOT == ROOT


def test_raw_artifact_names_bind_current_run_attempt_runtime_and_partition():
    assert ci.report_name(CONTEXT, "matrix") == "ci-coverage-37-1-3.13-matrix.json"
    assert (
        len({ci.report_name(CONTEXT, part) for part in ("collection", *ci.PARTITIONS)})
        == 4
    )
    with pytest.raises(ValueError):
        ci.report_name(CONTEXT, "missing")


def test_ci_plugin_exports_only_known_or_optional_pytest_hooks():
    manager = pytest.PytestPluginManager()
    manager.register(ci)
    manager.check_pending()


def test_runtime_launch_prepares_fresh_invocation_parent(tmp_path, monkeypatch):
    commands = []

    def gate(name, command, guard):
        commands.append(command)
        base = Path(command[command.index("--basetemp") + 1])
        assert base.parent.is_dir() and not base.exists()
        assert "--durations=30" in command and "--durations-min=1" in command
        return 0

    monkeypatch.setattr(ci, "run_gate", gate)
    report = tmp_path / "reports" / "partition.json"
    arguments = [
        "run",
        "--python",
        f"{sys.version_info.major}.{sys.version_info.minor}",
        "--run-id",
        "unit",
        "--run-attempt",
        "1",
        "--partition",
        "matrix",
        "--report",
        str(report),
    ]
    assert ci.main(arguments) == 0 and len(commands) == 1
    report.write_text("preserve existing evidence")
    assert ci.main(arguments) == 1 and len(commands) == 1
    assert report.read_text() == "preserve existing evidence"


@pytest.mark.parametrize("name", ("MATRIX_FILES", "STANDALONE", "STANDALONE_NODES"))
def test_duplicate_special_selector_definitions_fail_before_routing(monkeypatch, name):
    nodes = _universe()
    selectors = getattr(ci, name)
    monkeypatch.setattr(ci, name, (*selectors, selectors[0]))
    with pytest.raises(ValueError, match="overlapping special selectors"):
        ci.partition_nodes(nodes)


def test_independent_universe_rejects_classifier_created_overlap(monkeypatch):
    original = ci.partition_nodes

    def overlapping(nodes):
        partitions = original(nodes)
        partitions["remaining"] = sorted(
            [*partitions["remaining"], partitions["matrix"][0]]
        )
        return partitions

    monkeypatch.setattr(ci, "partition_nodes", overlapping)
    collection, reports = _reports()
    with pytest.raises(ValueError, match="overlapping"):
        _verify(collection, reports)


def test_timing_summary_is_bounded_escaped_and_separate_from_coverage(tmp_path):
    import json
    from types import SimpleNamespace

    options = {
        "--ci-report": str(tmp_path / "report.json"),
        "--ci-context": json.dumps(CONTEXT),
        "--ci-partition": "standalone",
        "dist": "load",
    }
    plugin = ci.Coverage(
        SimpleNamespace(getoption=lambda name, default=None: options.get(name, default))
    )
    unusual = 'tests/test_new.py::test_value["line\n雪]'
    ids = [unusual, *(f"test_{n}" for n in range(40)), *ci.STANDALONE_NODES]
    reports = [
        pytest.TestReport(
            nodeid=node,
            location=("test.py", 0, "test"),
            keywords={},
            outcome="passed",
            longrepr=None,
            when=phase,
            duration=1.0 if node in ci.STANDALONE_NODES else 2.0,
            start=100.0,
            stop=102.0,
            worker_id=f"gw{index % 4}",
        )
        for index, node in enumerate(ids)
        for phase in ("setup", "call", "teardown")
    ]
    output = []
    plugin.pytest_terminal_summary(
        SimpleNamespace(
            stats={"passed": reports, "warnings": [object()]}, write_line=output.append
        )
    )
    assert len(output) == 1 and len(output[0].splitlines()) == 1
    timing = json.loads(output[0].removeprefix("[ci-timing] "))
    assert len(timing["nodes"]) == 36
    assert {unusual, *ci.STANDALONE_NODES} <= {row["node"] for row in timing["nodes"]}
    assert sum(w["calls"] for w in timing["workers"].values()) == len(ids)
    assert all(
        set(row["phases"]) == {"setup", "call", "teardown"} for row in timing["nodes"]
    )
    assert timing["scheduler"] == "load"
    assert not (tmp_path / "report.json").exists()
