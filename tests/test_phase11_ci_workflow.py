from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from pathlib import Path

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_product_repair9_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYTHON_VERSION_PATH = REPO_ROOT / ".python-version"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"
EXPECTED_ACTIONS = (
    "actions/checkout",
    "actions/setup-python",
    "actions/setup-java",
    "astral-sh/setup-uv",
)
EXPECTED_COMMANDS = (
    "uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4",
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
)
BOUNDARY_HASH = "3d22a6e583e238b723d2dc20a7f809e3196a5ccae30fc54deaeb7d9a6b56dc1d"
GOLDEN_HASH = "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004"
SCRIPT_HASHES = {
    "scripts/validate.py": "e1607a47da34ff868ca09a128c8897a6a0dbad21",
    "scripts/check_generated.py": "51081d5337e0659e73f8666ba639c0d4c3fe3a4b",
    "scripts/check_goldens.py": "4f49ddc0a8a6836b68a83a98cc9c05389d4519a3",
}


def test_ci_triggers_permissions_runner_and_matrix_are_exact() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert re.search(
        r"(?m)^on:\n  pull_request:\n  push:\n    branches:\n      - main$", workflow
    )
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
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
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

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
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
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


def test_ci_has_no_write_credentials_publication_or_artifact_behavior() -> None:
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
        "upload-" + "artifact",
        "actions/upload-" + "artifact",
    ):
        assert forbidden not in lowered


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
        path: (REPO_ROOT / path).read_text(encoding="utf-8") for path in SCRIPT_HASHES
    }

    for path, expected_hash in SCRIPT_HASHES.items():
        assert _git_blob_hash(REPO_ROOT / path) == expected_hash

    assert "check_generated" not in script_sources["scripts/validate.py"]
    assert "check_goldens" not in script_sources["scripts/validate.py"]
    assert "package_smoke" not in script_sources["scripts/validate.py"]
    assert "check_goldens" not in script_sources["scripts/check_generated.py"]
    assert "package_smoke" not in script_sources["scripts/check_generated.py"]
    assert "check_generated" not in script_sources["scripts/check_goldens.py"]
    assert "package_smoke" not in script_sources["scripts/check_goldens.py"]
    assert "scripts/validate.py" not in script_sources["scripts/check_goldens.py"]
    assert "scripts/validate.py" not in script_sources["scripts/check_generated.py"]


def test_ci_and_package_smoke_preserve_metadata_and_compiler_boundaries() -> None:
    assert _sha256(PYTHON_VERSION_PATH) == (
        "7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d"
    )
    assert _sha256(PYPROJECT_PATH) == (
        "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01"
    )
    assert _sha256(UV_LOCK_PATH) == (
        "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea"
    )
    assert _sha256(REPO_ROOT / "Makefile") == (
        "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7"
    )
    assert (REPO_ROOT / "scripts" / "package_smoke.py").is_file()
    for path in ("package.json", "setup.py", "setup.cfg", "MANIFEST.in"):
        assert not (REPO_ROOT / path).exists()

    boundary_paths = [
        REPO_ROOT / "Makefile",
        REPO_ROOT / "grammar" / "Pietto.g4",
    ]
    boundary_paths.extend(
        path
        for path in (REPO_ROOT / "src" / "pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )

    assert _aggregate_hash(boundary_paths) == BOUNDARY_HASH
    assert _aggregate_hash((REPO_ROOT / "tests/fixtures/golden").iterdir()) == (
        GOLDEN_HASH
    )


def _aggregate_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        if not path.is_file():
            continue
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_blob_hash(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
