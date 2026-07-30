from __future__ import annotations

import ast
import subprocess
import tomllib
from pathlib import Path
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase50-explain-public-metadata-package-integration-boundary-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
TEST_PATH = Path(__file__).resolve()

SLICE10_TITLE = (
    "# Phase 50 Slice 10 Explain / Public Metadata / Package Integration Boundary v1"
)
SLICE9_SHA = "f886589ac2f64eeb3770c914e7c049e2da105daa"
SLICE9_CI_RUN_ID = "29170827348"

SPEC_SECTION_HEADINGS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Current Public Artifact Inventory",
    "Current Private Fact Inventory",
    "Conceptual Vocabulary",
    "Exposure-route Comparison",
    "Recommended Public Projection Boundary",
    "Artifact Separation And Ownership",
    "Single-file Explain Boundary",
    "Project JSON v2 Boundary",
    "Semantic Metadata Artifact v1 Boundary",
    "Future Project Explain Readiness",
    "Package Identity And Asset Exposure",
    "Package Requirement And Availability Exposure",
    "Capability Profile And Extension Exposure",
    "Portability Report Readiness",
    "Lineage Origin And Provenance Exposure",
    "Package Graph And Dependency Exposure",
    "Public Identity And Reference Rules",
    "Deterministic Ordering",
    "Schema Versioning And Compatibility",
    "Unknown Absent Null And Redaction Posture",
    "Privacy And Trust Boundary",
    "Diagnostic And Fail-closed Matrix",
    "CLI JSON And Artifact Separation",
    "Cross-phase Dependencies",
    "Bounded Phase 58 Handoff",
    "Explicit Deferrals And Non-goals",
    "Package Version And Release Boundary",
    "Separate Authorization And Stop Conditions",
)

ALLOWED_PHASE50_SLICE10_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-explain-public-metadata-package-integration-boundary-v1.md",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
}

ALLOWED_PHASE50_SLICE11_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-completion-audit-and-status-lock-v1.md",
    "tests/test_phase50_completion_audit_and_status_lock.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
}

COMPATIBILITY_TEST_PATHS = (
    REPO_ROOT
    / "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    REPO_ROOT / "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    REPO_ROOT
    / "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    REPO_ROOT / "tests/test_phase50_type_system_gap_capability_readiness.py",
    REPO_ROOT / "tests/test_phase50_window_function_readiness.py",
    REPO_ROOT / "tests/test_phase50_import_module_export_readiness.py",
    REPO_ROOT / "tests/test_phase50_semantic_package_model_readiness.py",
    REPO_ROOT / "tests/test_phase50_postgresql_extension_capability_readiness.py",
    REPO_ROOT / "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
)

PHASE50_SLICE10_TEST_PATHS = (
    TEST_PATH,
    *COMPATIBILITY_TEST_PATHS,
)

PROTECTED_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
    "docs/spec/phase50-semantic-package-extension-capability-scope-lock-v1.md",
    "docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md",
    "docs/spec/phase50-aggregate-grouped-project-output-schema-readiness-v1.md",
    "docs/spec/phase50-type-system-gap-capability-readiness-v1.md",
    "docs/spec/phase50-window-function-readiness-v1.md",
    "docs/spec/phase50-import-module-export-readiness-v1.md",
    "docs/spec/phase50-semantic-package-model-readiness-v1.md",
    "docs/spec/phase50-postgresql-extension-capability-readiness-v1.md",
    "docs/spec/phase50-multi-dialect-capability-ecosystem-readiness-v1.md",
    "src",
    "grammar",
    "scripts",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "tests/fixtures",
    "tests/goldens",
    "examples",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized_section(path: Path, heading: str) -> str:
    text = _read(path)
    marker = f"## {heading}"
    start = text.index(marker)
    end = text.find("\n## ", start + len(marker))
    if end == -1:
        end = len(text)
    return " ".join(text[start:end].split())


def _string_set_assignment(path: Path, assignment_name: str) -> set[str]:
    tree = ast.parse(_read(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == assignment_name
            for target in node.targets
        ):
            continue
        assert isinstance(node.value, ast.Set)
        values: set[str] = set()
        for element in node.value.elts:
            assert isinstance(element, ast.Constant)
            assert isinstance(element.value, str)
            values.add(element.value)
        return values
    raise AssertionError(f"assignment not found: {assignment_name}")


def _is_allowed_read_only_git_args(args: list[str]) -> bool:
    if args == ["status", "--porcelain", "--untracked-files=all"]:
        return True
    if args == ["diff", "--cached", "--name-status"]:
        return True
    if args == ["tag", "--points-at", "HEAD"]:
        return True
    return len(args) == 3 and args[:2] == ["diff", "--"] and args[2] in PROTECTED_PATHS


def _git_output(args: list[str]) -> str:
    assert _is_allowed_read_only_git_args(args)
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.rstrip()


def _dirty_paths() -> set[str]:
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def _literal_string(node: ast.expr) -> str:
    assert isinstance(node, ast.Constant)
    assert isinstance(node.value, str)
    return node.value


def test_slice10_artifacts_status_and_exact_heading_order_are_locked() -> None:
    assert SPEC_PATH.exists()
    spec = _read(SPEC_PATH)
    plan = _read(PLAN_PATH)

    assert spec.startswith(f"{SLICE10_TITLE}\n")
    assert (
        tuple(
            line.removeprefix("## ")
            for line in spec.splitlines()
            if line.startswith("## ")
        )
        == SPEC_SECTION_HEADINGS
    )

    status = _normalized_section(PLAN_PATH, "Status")
    for required in (
        f"Phase 50 Slice 9 **Multi-dialect Capability Ecosystem Readiness** completed at `{SLICE9_SHA}`",
        f"documented natural CI run `{SLICE9_CI_RUN_ID}`",
        "Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary** completed",
        "9bc6ed82f3741e3c242981bb88edfb50c73fc586",
        "29179160024",
        "Phase 50 Slice 11 **Completion Audit And Status Lock** is the current",
        "Slice 11 is not complete in Gate 2",
        "Phase 50 remains in progress through Gate 2",
        "Phases 51 through 60 remain unstarted and separately authorized",
        "Phase 58 remains readiness-only and unstarted",
    ):
        assert required in status, required
    assert "Phase 50 is complete after Slice 11 Gate 2" not in status
    assert "Slice 10 completed" in status
    assert "Slice 11 is complete" not in plan


def test_route_b_artifact_separation_and_no_behavior_boundary_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Slice 10 implements no compiler or runtime behavior.",
        "Route B is explicit independently versioned public projections from private facts.",
        "CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2 check, future",
        "future package-inspection report remain separate artifact families.",
        "No universal metadata document is selected.",
        "No private fact becomes public by being named as a future input.",
        "Future artifact schemas remain independently versioned.",
        "Phase 58 remains readiness-only, unstarted, and separately authorized.",
    ):
        assert required in spec, required

    for forbidden in (
        "adds a serializer",
        "adds a CLI command",
        "implements project explain",
        "implements a portability report",
        "implements package inspection",
    ):
        assert forbidden not in spec, forbidden


def test_existing_public_artifacts_and_private_carriers_are_separate() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "CLI JSON v1 | IMPLEMENTED_STABLE",
        "Semantic Metadata Artifact v1 | IMPLEMENTED_STABLE",
        "Project JSON v2 check envelope | IMPLEMENTED_LIMITED",
        "Project row schemas, fields, availability states/reasons",
        "origin/provenance, relation dependency graphs, row",
        "Project JSON v2 fields, Semantic Metadata Artifact v1 fields, CLI",
        "Artifact v1 direct single-file field-leaf lineage remains a bounded public artifact fact",
        "Its failure envelope omits metadata rather than serializing a null metadata value.",
        "Project JSON v2 does not gain project explain, package inspection, portability,",
    ):
        assert required in spec, required


def test_package_profile_extension_and_portability_boundaries_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Package/profile/extension/dialect facts are declared readiness facts, not current public or runtime facts.",
        "declared readiness facts. They are not the Python",
        "Declared facts must never be presented as resolved, installed, or runtime-proven facts.",
        "Capability profile, dialect profile, overlay, extension catalog, and extension",
        "SQLite has rejection evidence only. DuckDB, BigQuery, Snowflake,",
        "SUPPORTED_IDENTICALLY",
        "SUPPORTED_WITH_DIALECT_SPECIFIC_LOWERING",
        "SUPPORTED_WITH_SEMANTIC_DIFFERENCES",
        "UNKNOWN_OR_NOT_DECLARED",
        "BLOCKED_BY_MISSING_CAPABILITY",
        "Portability reporting must not imply runtime validation, fallback, degradation, or automatic translation.",
    ):
        assert required in spec, required


def test_public_private_versioning_and_fail_closed_postures_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Package semantic release is an exact SemVer readiness fact.",
        "Extension/profile/",
        "overlay release facts are exact opaque readiness identifiers.",
        "Unknown, absent, null, redacted, private-only, conflicting, unresolved, and",
        "Private-only facts remain omitted.",
        "Conflicting, unresolved, unsupported, and unavailable facts must not become fabricated values, fake nulls, or assumed unknowns.",
        "An unresolved dependency, duplicate/conflicting declaration, missing exact identity, missing capability, missing lowering, ambiguity, or cycle receives no winner.",
        "It must fail closed rather than be inferred, deduplicated, or silently resolved.",
        "Supplied digests, locators, revisions, author text, and curator descriptions",
        "They provide no verification,",
        "Slice 10 assigns no diagnostic code, message, severity, ordering change, CLI",
    ):
        assert required in spec, required


def test_phase_ownership_and_bounded_handoff_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Phase 55 owns semantic-package asset schema.",
        "Phase 56 owns capability/dialect/",
        "extension profile schema and declared checking.",
        "Phase 57 owns PostgreSQL",
        "extension signature-catalog readiness.",
        "Phase 58 owns explain, portability, and",
        "public metadata readiness.",
        "Phase 59 owns package graph and lineage/provenance",
        "integration.",
        "Phase 60 is the ecosystem completion checkpoint.",
        "Slice 10 does not begin Slice 11 or Phases 52-60.",
    ):
        assert required in spec, required


def test_plan_slice10_allowlist_and_gate_discipline_are_locked() -> None:
    plan_allowlist = _normalized_section(PLAN_PATH, "Slice 10 Gate 2 Allowlist")
    plan_validation = _normalized_section(PLAN_PATH, "Slice 10 Focused Validation")
    plan_stops = _normalized_section(PLAN_PATH, "Slice 10 Stop Conditions")

    for relative_path in ALLOWED_PHASE50_SLICE10_GATE2_PATHS:
        assert relative_path in plan_allowlist, relative_path
    assert "No thirteenth repository path is approved." in plan_allowlist
    for required in (
        "the focused Slice 10 static test and complete ten-file Phase 50 static-audit bundle",
        "the corrected no-history/no-network/no-database/no-import-execution scan",
        'subprocess.run(["git", *args], ...)',
        "Do not run full pytest",
    ):
        assert required in plan_validation, required
    for required in (
        "the completed Slice 9 baseline or exact twelve-file dirty set differs",
        "any thirteenth repository path changes",
        "Phase 58/59 implementation",
        "focused Slice 10 pytest",
    ):
        assert required in plan_stops, required


def test_all_nine_compatibility_allowlists_are_exact() -> None:
    assert len(ALLOWED_PHASE50_SLICE10_GATE2_PATHS) == 12
    assert len(PHASE50_SLICE10_TEST_PATHS) == 10
    for path in COMPATIBILITY_TEST_PATHS:
        assert (
            _string_set_assignment(path, "ALLOWED_PHASE50_SLICE10_GATE2_PATHS")
            == ALLOWED_PHASE50_SLICE10_GATE2_PATHS
        )


def test_static_git_helper_is_literal_and_read_only() -> None:
    source = _read(TEST_PATH)
    tree = ast.parse(source)
    subprocess_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]
    assert len(subprocess_calls) == 1
    call = subprocess_calls[0]
    assert len(call.args) == 1
    assert isinstance(call.args[0], ast.List)
    assert _literal_string(call.args[0].elts[0]) == "git"
    assert isinstance(call.args[0].elts[1], ast.Starred)
    assert isinstance(call.args[0].elts[1].value, ast.Name)
    assert call.args[0].elts[1].value.id == "args"

    keywords = {keyword.arg: keyword.value for keyword in call.keywords}
    assert set(keywords) == {"cwd", "check", "text", "stdout", "stderr"}
    assert isinstance(keywords["cwd"], ast.Name)
    assert keywords["cwd"].id == "REPO_ROOT"
    assert isinstance(keywords["check"], ast.Constant)
    assert keywords["check"].value is True
    assert isinstance(keywords["text"], ast.Constant)
    assert keywords["text"].value is True
    for name in ("stdout", "stderr"):
        keyword_value = keywords[name]
        assert isinstance(keyword_value, ast.Attribute)
        attribute_owner = keyword_value.value
        assert isinstance(attribute_owner, ast.Name)
        assert attribute_owner.id == "subprocess"
        assert keyword_value.attr == "PIPE"

    mutating_subcommands = (
        "add",
        "commit",
        "push",
        "fetch",
        "pull",
        "merge",
        "rebase",
        "reset",
        "restore",
        "checkout",
        "switch",
        "clean",
        "revert",
        "cherry-pick",
        "branch",
    )
    assert all(f'["{subcommand}"' not in source for subcommand in mutating_subcommands)


def test_all_static_git_calls_use_only_read_only_arguments() -> None:
    tree = ast.parse(_read(TEST_PATH))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_git_output"
    ]
    assert calls
    for call in calls:
        assert len(call.args) == 1
        assert isinstance(call.args[0], ast.List)
        values = call.args[0].elts
        assert values
        subcommand = _literal_string(values[0])
        if subcommand == "status":
            assert [_literal_string(value) for value in values] == [
                "status",
                "--porcelain",
                "--untracked-files=all",
            ]
        elif subcommand == "diff":
            assert len(values) == 3
            assert _literal_string(values[1]) in {"--", "--cached"}
            if _literal_string(values[1]) == "--cached":
                assert _literal_string(values[2]) == "--name-status"
        elif subcommand == "tag":
            assert [_literal_string(value) for value in values] == [
                "tag",
                "--points-at",
                "HEAD",
            ]
        else:
            raise AssertionError(subcommand)


def test_package_version_tag_protected_paths_and_dirty_set_are_locked() -> None:
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = pyproject["project"]
    assert isinstance(project, dict)
    assert project["version"] == "0.1.0"
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    assert not (REPO_ROOT / "tests/goldens").exists()

    for relative_path in PROTECTED_PATHS:
        assert (_git_output(["diff", "--", relative_path]) == "") or _slice5_gate2(), (
            relative_path
        )

    assert (
        _dirty_paths()
        in (
            set(),
            ALLOWED_PHASE50_SLICE10_GATE2_PATHS,
            ALLOWED_PHASE50_SLICE11_GATE2_PATHS,
        )
    ) or _slice5_gate2()
