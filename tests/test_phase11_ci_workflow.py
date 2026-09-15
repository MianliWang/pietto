from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYTHON_VERSION_PATH = REPO_ROOT / ".python-version"
VALIDATION_ACTIONS = (
    "actions/checkout",
    "actions/setup-python",
    "actions/setup-java",
    "astral-sh/setup-uv",
)
EXPECTED_COMMANDS = (
    "uv run python scripts/validate.py --timings",
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
)


def _job(workflow: str, name: str) -> str:
    marker = f"  {name}:\n"
    assert workflow.count(marker) == 1
    return re.split(r"\n  [a-z_]+:\n", workflow.split(marker, 1)[1], maxsplit=1)[0]


EXPECTED_ACTIONS = (
    *VALIDATION_ACTIONS,
    "actions/checkout",
    "actions/setup-python",
    "astral-sh/setup-uv",
    "actions/upload-artifact",
    "actions/checkout",
    "actions/setup-python",
    "astral-sh/setup-uv",
    "actions/download-artifact",
    "actions/download-artifact",
)


def test_ci_triggers_permissions_runner_and_matrix_are_exact() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert re.search(
        r"(?m)^on:\n  pull_request:\n  push:\n    branches:\n      - main$", workflow
    )
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
    workflow = _job(workflow, "validation")
    assert "runs-on: ubuntu-latest" in workflow
    assert re.findall(r'(?m)^          - "(3\.\d+)"$', workflow) == [
        "3.12",
        "3.13",
    ]
    assert (
        "      matrix:\n"
        "        python-version:\n"
        '          - "3.12"\n'
        '          - "3.13"\n'
        "    steps:\n"
    ) in workflow
    assert re.search(
        r"(?m)^      - name: Set up Python\n"
        r"        uses: actions/setup-python@[0-9a-f]{40} # v[0-9.]+\n"
        r"        with:\n"
        r"          python-version: \$\{\{ matrix\.python-version \}\}$",
        workflow,
    )
    assert PYTHON_VERSION_PATH.read_text(encoding="utf-8") == "3.12\n"
    assert "fail-fast: false" in workflow


def test_ci_sets_java_21_and_pins_the_local_uv_version() -> None:
    workflow = _job(WORKFLOW_PATH.read_text(encoding="utf-8"), "validation")

    assert "distribution: temurin" in workflow
    assert 'java-version: "21"' in workflow
    assert "overwrite-settings: false" in workflow
    assert 'version: "0.11.19"' in workflow
    assert "enable-cache: false" in workflow
    assert "${{ runner.temp }}" not in workflow
    assert (
        'echo "UV_PROJECT_ENVIRONMENT=$RUNNER_TEMP/pietto-venv" >> "$GITHUB_ENV"'
        in workflow
    )
    assert 'echo "UV_CACHE_DIR=$RUNNER_TEMP/uv-cache" >> "$GITHUB_ENV"' in workflow
    assert 'echo "UV_PYTHON=$pythonLocation/bin/python" >> "$GITHUB_ENV"' in workflow
    assert workflow.count("UV_PYTHON") == 1
    assert workflow.count('>> "$GITHUB_ENV"') == 3
    assert workflow.count("run: uv sync --locked") == 1
    assert workflow.count("uv sync --locked") == 1
    assert "uv sync --python" not in workflow
    assert "--upgrade" not in workflow
    assert "--refresh" not in workflow

    proof_marker = "      - name: Verify matrix interpreter\n"
    assert workflow.count(proof_marker) == 1
    proof_start = workflow.index(proof_marker)
    proof_end = workflow.find("\n      - name:", proof_start + len(proof_marker))
    assert proof_end != -1
    proof_step = workflow[proof_start:proof_end]

    assert workflow.index("        run: uv sync --locked") < proof_start
    assert proof_end < workflow.index("      - name: Smoke test installed package\n")
    assert proof_step.startswith(
        "      - name: Verify matrix interpreter\n"
        "        env:\n"
        "          EXPECTED_PYTHON: ${{ matrix.python-version }}\n"
        "        run: |\n"
    )
    for fragment in (
        "\"$pythonLocation/bin/python\" - <<'PY'",
        'print(f"setup-python interpreter: {sys.executable}")',
        "setup-python version: ",
        "platform.python_implementation()",
        "platform.python_version()",
        "uv run python - <<'PY'",
        'print(f"uv interpreter: {sys.executable}")',
        "uv Python: ",
        'expected = tuple(map(int, os.environ["EXPECTED_PYTHON"].split(".")))',
        "actual = sys.version_info[:2]",
        "uv/package-smoke interpreter: ",
    ):
        assert fragment in proof_step
    assert re.search(
        r"(?m)^          if actual != expected:\n"
        r"              raise SystemExit\(",
        proof_step,
    )
    assert "continue-on-error" not in workflow
    assert "|| true" not in proof_step
    assert "set +e" not in proof_step


def test_ci_invokes_only_the_accepted_release_readiness_commands() -> None:
    workflow = _job(WORKFLOW_PATH.read_text(encoding="utf-8"), "validation")
    run_commands = tuple(
        match.group(1)
        for match in re.finditer(
            r"(?m)^        run: (uv run python scripts/.+)$", workflow
        )
    )

    assert run_commands == EXPECTED_COMMANDS
    for command in EXPECTED_COMMANDS:
        assert workflow.count(command) == 1

    for forbidden in (
        "emit_" + "postgres_sql",
        "emit_" + "mysql_sql",
        "build_" + "ir",
        "pa" + "rse_" + "file",
        "ana" + "lyze",
        "pietto emit-" + "sql",
    ):
        assert forbidden not in workflow


def test_every_action_is_pinned_to_a_reviewed_full_sha() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    uses = re.findall(
        r"(?m)^        uses: ([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)@"
        r"([0-9a-f]{40}) # (v[0-9.]+)$",
        workflow,
    )

    assert len(uses) == len(EXPECTED_ACTIONS)
    assert tuple(repository for repository, _sha, _version in uses) == EXPECTED_ACTIONS
    assert not re.search(
        r"(?m)^\s*uses:\s+\S+@(v[0-9]+|main|master|HEAD|latest)\s*$",
        workflow,
    )


def test_ci_has_no_write_credentials_and_only_scoped_evidence_artifacts() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    lowered = workflow.lower()

    assert "persist-credentials: false" in workflow
    assert "contents: write" not in lowered
    assert "write-all" not in lowered
    assert "pull-requests:" not in lowered
    assert "id-token:" not in lowered
    assert "secrets." not in lowered
    for forbidden in (
        "pass" + "word",
        "pyp" + "i",
        "tw" + "ine",
        "pub" + "lish",
        "dep" + "loy",
    ):
        assert forbidden not in lowered
    assert "pull_request_target" not in lowered
    assert "workflow_run:" not in lowered
    assert "workflow_dispatch:" not in lowered
    assert "continue-on-error" not in lowered
    assert workflow.count("persist-credentials: false") == 3
    assert workflow.count("actions/upload-artifact@") == 1
    assert workflow.count("actions/download-artifact@") == 2
    target = _job(workflow, "target_conformance")
    aggregate = _job(workflow, "target_conformance_aggregate")
    assert "archive: false" in target and "if-no-files-found: error" in target
    assert "overwrite: false" in target and "include-hidden-files: false" in target
    assert "retention-days: 1" in target
    assert (
        "path: ${{ runner.temp }}/phase66-target/${{ matrix.target }}/phase66-${{ matrix.target }}-${{ github.run_id }}-${{ github.run_attempt }}.json"
        in target
    )
    assert aggregate.count("digest-mismatch: error") == 2
    assert aggregate.count("skip-decompress: true") == 2
    assert "github-token:" not in aggregate and "run-id:" not in aggregate
    assert "repository:" not in aggregate and "pattern:" not in aggregate


def test_ci_does_not_rewrite_repository_outputs() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "ruff format ." not in workflow
    assert "make generate-" + "par" + "ser" not in workflow
    assert "-o src/pietto/generated" not in workflow
    assert "git commit" not in workflow
    assert "git push" not in workflow
    assert "run: uv build" not in workflow


def test_existing_release_readiness_scripts_remain_independent() -> None:
    script_sources = {
        path: (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "scripts/validate.py",
            "scripts/check_generated.py",
            "scripts/check_goldens.py",
        )
    }

    assert "check_generated" not in script_sources["scripts/validate.py"]
    assert "check_goldens" not in script_sources["scripts/validate.py"]
    assert "package_smoke" not in script_sources["scripts/validate.py"]
    assert "check_goldens" not in script_sources["scripts/check_generated.py"]
    assert "package_smoke" not in script_sources["scripts/check_generated.py"]
    assert "check_generated" not in script_sources["scripts/check_goldens.py"]
    assert "package_smoke" not in script_sources["scripts/check_goldens.py"]
    assert "scripts/validate.py" not in script_sources["scripts/check_goldens.py"]
    assert "scripts/validate.py" not in script_sources["scripts/check_generated.py"]


def test_two_target_cells_and_strict_always_aggregate_are_explicit() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert tuple(
        re.findall(r"(?m)^  ([a-z_]+):$", workflow.split("jobs:\n", 1)[1])
    ) == ("validation", "target_conformance", "target_conformance_aggregate")
    target = _job(workflow, "target_conformance")
    aggregate = _job(workflow, "target_conformance_aggregate")
    assert (
        "      matrix:\n        target:\n          - postgres\n          - mysql\n"
        in target
    )
    assert "fail-fast: false" in target and 'python-version: "3.13"' in target
    assert "exclude:" not in target and "include:" not in target
    assert "needs: [validation, target_conformance]" in aggregate
    assert "if: always()" in aggregate
    for value in (
        "COMPILER_STATUS: ${{ needs.validation.result }}",
        "TARGET_STATUS: ${{ needs.target_conformance.result }}",
        '--compiler-status "$COMPILER_STATUS" --target-status "$TARGET_STATUS"',
    ):
        assert value in aggregate
    assert "_pietto_target_conformance.py run" in target
    assert "_pietto_target_conformance.py verify-receipts" in target
    assert "_pietto_target_conformance.py verify-receipts" in aggregate
    for section in (target, aggregate):
        assert '--expected-commit "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID"' in section
        assert '--run-attempt "$GITHUB_RUN_ATTEMPT"' in section
        assert "--pins tests/phase66_target_pins.json" in section
    assert "ARTIFACT_DIGEST: ${{ steps.receipt.outputs.artifact-digest }}" in target
    assert "ARTIFACT_ID: ${{ steps.receipt.outputs.artifact-id }}" in target
    assert '--artifact-digest "$ARTIFACT_DIGEST" --artifact-id "$ARTIFACT_ID"' in target
