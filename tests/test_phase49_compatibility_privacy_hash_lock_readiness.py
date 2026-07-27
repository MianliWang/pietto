from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import tomllib

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-49-row-level-computed-let-schema-lineage.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase49-compatibility-privacy-hash-lock-readiness-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE13_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-compatibility-privacy-hash-lock-readiness-v1.md",
    "tests/test_phase49_compatibility_privacy_hash_lock_readiness.py",
}


def _phase53_gate2_paths(name: str) -> set[str]:
    path = REPO_ROOT / "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            return value
    raise AssertionError(name)


EXPECTED_PROJECT_JSON_V2_KEYS = (
    "schema_version",
    "command",
    "mode",
    "ok",
    "project",
    "inputs",
    "diagnostics",
    "cli_errors",
    "result",
)

EXPECTED_PHASE49_SPECS = (
    "phase49-row-level-computed-let-schema-lineage-scope-lock-v1.md",
    "phase49-project-row-expression-schema-helper-contract-v1.md",
    "phase49-project-row-expression-type-nullability-adapter-v1.md",
    "phase49-computed-alias-project-row-schema-mvp-v1.md",
    "phase49-computed-alias-origin-provenance-privacy-v1.md",
    "phase49-project-let-scope-value-facts-v1.md",
    "phase49-selected-let-derived-output-schema-v1.md",
    "phase49-let-visibility-order-shadowing-hardening-v1.md",
    "phase49-private-row-level-dependency-graph-scaffold-v1.md",
    "phase49-minimal-private-lineage-carrier-source-direct-rename-v1.md",
    "phase49-computed-let-multi-hop-row-lineage-v1.md",
    "phase49-unknown-deferred-diagnostic-ordering-hardening-v1.md",
    "phase49-compatibility-privacy-hash-lock-readiness-v1.md",
)

PRIVATE_JSON_FORBIDDEN_TOKENS = (
    "relation_row_schemas",
    "relation_row_schema_states",
    "relation_let_scope_facts",
    "relation_row_dependency_graphs",
    "relation_row_lineages",
    "ProjectRowSchema",
    "ProjectRelationRowSchemaState",
    "ProjectRelationLetScopeFacts",
    "ProjectRelationRowDependencyGraph",
    "ProjectRelationRowLineage",
    "ProjectRowField",
    "ProjectRowFieldProvenance",
    "ProjectRowDependencyNode",
    "ProjectRowDependencyEdge",
    "ProjectRowLineageSegment",
    "ProjectRowLineageFact",
    "dependency",
    "lineage",
    "provenance",
    "origin",
    "UNKNOWN_SCHEMA",
    "DEFERRED_PHASE48_BEHAVIOR",
    "UNRESOLVED_RELATION_BLOCKED",
    "CYCLE_BLOCKED",
    "DUPLICATE_OUTPUT_NAME",
    "LET_DIAGNOSTICS_SUPPRESSED",
    "let_derived",
    "derived_expression",
    "computed_expression",
    "let_output",
    "let_expression",
    "transitive_dependency",
)

FORBIDDEN_DIFF_PATHS = (
    "src/pietto/_project/json_v2.py",
    "src/pietto/_project/check.py",
    "src/pietto/_project/row_expression_schema.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "src/pietto/_project/let_scope_facts.py",
    "src/pietto/semantic/let_bindings.py",
    "grammar",
    "src/pietto/generated",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
    "scripts",
)

PROJECT_HELPER_PATHS = (
    "src/pietto/_project/row_expression_schema.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "src/pietto/_project/let_scope_facts.py",
    "src/pietto/_project/row_dependency_graph.py",
    "src/pietto/_project/row_lineage.py",
)

FULL_SEMANTIC_ANALYZE_FORBIDDEN = (
    "semantic_api.analyze",
    "from pietto.semantic import analyze",
    "import pietto.semantic as semantic_api",
)


def test_slice13_spec_plan_and_phase49_spec_inventory_are_ready() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    plan = PLAN_PATH.read_text(encoding="utf-8")
    spec = SPEC_PATH.read_text(encoding="utf-8")
    docs = " ".join((plan + "\n" + spec).split())

    for required in (
        "Phase 49 Slice 13",
        "Compatibility/privacy/hash-lock readiness",
        "docs/spec/tests-only readiness",
        "`docs/spec/phase49-compatibility-privacy-hash-lock-readiness-v1.md`",
        "`relation_row_schemas`",
        "`relation_row_schema_states`",
        "`relation_let_scope_facts`",
        "`relation_row_dependency_graphs`",
        "`relation_row_lineages`",
        "Project JSON v2",
        "public semantic API",
        "existing Phase 11/12/33 hash-lock tests",
    ):
        assert required in docs, required

    for spec_name in EXPECTED_PHASE49_SPECS:
        spec_path = REPO_ROOT / "docs/spec" / spec_name
        assert spec_path.is_file(), spec_name
        assert spec_name in plan, spec_name


def test_project_json_v2_public_envelope_and_privacy_remain_stable(
    tmp_path: Path,
) -> None:
    valid_parse, valid_semantic = _project_semantic_result(
        _project(
            tmp_path / "valid",
            "query projected:\n    from users\n    select:\n        id\n",
        )
    )
    invalid_parse, invalid_semantic = _project_semantic_result(
        _project(
            tmp_path / "invalid",
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )

    for parse_result, semantic_result in (
        (valid_parse, valid_semantic),
        (invalid_parse, invalid_semantic),
    ):
        document = project_check_result_to_json_dict(
            parse_result,
            semantic_diagnostics=semantic_result.diagnostics,
        )
        serialized = json.dumps(document)

        assert tuple(document) == EXPECTED_PROJECT_JSON_V2_KEYS
        assert _json_paths_for_key(document, "status") == ("inputs[].status",)
        assert _json_paths_for_key(document, "reason") == ()
        for private_token in PRIVATE_JSON_FORBIDDEN_TOKENS:
            assert private_token not in serialized, private_token


def test_forbidden_source_public_surface_and_tooling_diffs_are_empty() -> None:
    for relative_path in FORBIDDEN_DIFF_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path


def test_package_version_and_release_surface_readiness_are_locked() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.1.0"

    changed_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PLAN_PATH,
            SPEC_PATH,
            REPO_ROOT
            / "tests/test_phase49_compatibility_privacy_hash_lock_readiness.py",
        )
    )
    assert "0." + "2.0" not in changed_text

    docs = " ".join(
        (
            PLAN_PATH.read_text(encoding="utf-8")
            + "\n"
            + SPEC_PATH.read_text(encoding="utf-8")
        ).split()
    )
    for required in (
        "Package version remains `0.1.0`",
        "No tag, release, publish, upload, signing, or attestation work is authorized",
        "does not implement project explain",
        "does not modify production source",
        "does not refresh existing hash locks",
    ):
        assert required in docs, required


def test_existing_hash_and_private_surface_locks_remain_present() -> None:
    phase11_and_12_lock_tests = (
        "tests/test_phase11_ci_workflow.py",
        "tests/test_phase11_completion_audit.py",
        "tests/test_phase11_generated_guard.py",
        "tests/test_phase11_golden_policy.py",
        "tests/test_phase11_packaging_smoke.py",
        "tests/test_phase11_validation_entrypoint.py",
        "tests/test_phase12_completion_audit.py",
        "tests/test_phase12_composition_cli_json_goldens.py",
    )
    for relative_path in phase11_and_12_lock_tests:
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        if "BOUNDARY_HASH" in source:
            match = re.search(r'BOUNDARY_HASH\s*=\s*"([0-9a-f]{64})"', source)
            assert match is not None, relative_path
            assert match.group(1), relative_path

    phase33_source = (REPO_ROOT / "tests/test_phase33_completion_audit.py").read_text(
        encoding="utf-8"
    )
    assert "LOCKED_PHASE33_SURFACES" in phase33_source
    assert '"project_private"' in phase33_source
    project_private = re.search(
        r'"project_private":\s*\(\s*'
        r'"src/pietto/_project",\s*'
        r"(\d+),\s*"
        r'"([0-9a-f]{64})"',
        phase33_source,
        flags=re.DOTALL,
    )
    assert project_private is not None
    assert int(project_private.group(1)) >= 12
    assert project_private.group(2)


def test_project_helpers_do_not_call_full_semantic_analyze() -> None:
    for relative_path in PROJECT_HELPER_PATHS:
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for forbidden in FULL_SEMANTIC_ANALYZE_FORBIDDEN:
            assert forbidden not in source, relative_path

    let_scope_source = (REPO_ROOT / "src/pietto/_project/let_scope_facts.py").read_text(
        encoding="utf-8"
    )
    assert "analyze_relation_let_bindings" in let_scope_source


def test_slice13_package_version_and_dirty_paths_are_locked() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.1.0"
    slice14_paths = _phase53_gate2_paths("MODIFIED_PATHS") | _phase53_gate2_paths(
        "ADDED_PATHS"
    )
    assert _git_status_paths() in (set(), ALLOWED_SLICE13_GATE2_PATHS, slice14_paths)


def _project_semantic_result(
    root: Path,
) -> tuple[
    ProjectParseCheckResult,
    ProjectSemanticResult,
]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    semantic_result = build_empty_project_semantic_result(parse_result)
    assert semantic_result.model is not None
    return parse_result, semantic_result


def _project(root: Path, relation_body: str) -> Path:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    (root / "models.pietto").write_text(
        (
            "shape User:\n"
            "    id: Int not null\n"
            "    score: Int not null\n"
            'source users: User is postgres.table("users")\n'
            f"{relation_body}"
        ),
        encoding="utf-8",
    )
    return root


def _json_paths_for_key(value: object, key: str, path: str = "") -> tuple[str, ...]:
    if isinstance(value, dict):
        paths: list[str] = []
        for child_key, child_value in value.items():
            child_path = f"{path}.{child_key}" if path else str(child_key)
            if child_key == key:
                paths.append(child_path)
            paths.extend(_json_paths_for_key(child_value, key, child_path))
        return tuple(paths)
    if isinstance(value, list):
        paths: list[str] = []
        for child in value:
            list_path = f"{path}[]" if path else "[]"
            paths.extend(_json_paths_for_key(child, key, list_path))
        return tuple(dict.fromkeys(paths))
    return ()


def _git_status_paths() -> set[str]:
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        paths.add(line[3:])
    return paths


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stderr == ""
    return result.stdout.rstrip()
