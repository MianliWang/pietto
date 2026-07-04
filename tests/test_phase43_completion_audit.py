from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-43-let-binding-aggregate-and-grouped-query-integration-mvp.md"
)
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase43-let-binding-aggregate-grouped-integration-scope-lock-v1.md"
)
REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE43_DOC_PATHS = (
    "docs/plan/phase-43-let-binding-aggregate-and-grouped-query-integration-mvp.md",
    "docs/spec/phase43-let-binding-aggregate-grouped-integration-scope-lock-v1.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
)

PHASE43_TEST_PATHS = (
    "tests/test_phase43_let_binding_aggregate_grouped_scope_lock.py",
    "tests/test_phase43_let_binding_sum_avg_aggregate_args.py",
    "tests/test_phase43_let_binding_count_aggregate_args.py",
    "tests/test_phase43_let_binding_group_by_keys.py",
    "tests/test_phase43_let_binding_grouped_order_by.py",
    "tests/test_phase43_let_binding_satisfying_aggregate_wrapped.py",
    "tests/test_phase43_cli_json_metadata_sql_compatibility.py",
    "tests/test_phase43_completion_audit.py",
)

ALLOWED_SLICE8_CHANGED_PATHS = {
    *PHASE43_DOC_PATHS,
    "tests/test_phase43_completion_audit.py",
    "tests/test_phase43_let_binding_aggregate_grouped_scope_lock.py",
    "tests/test_phase29_v02_deferred_feature_register.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase40_completion_audit.py",
    "tests/test_phase41_decimal_precision_scale_completion_audit.py",
}

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "src",
    "grammar",
    "src/pietto/generated",
    "tests/fixtures",
    "fixtures",
    "goldens",
    "examples",
    "scripts",
    ".github/workflows",
    ".github/dependabot.yml",
    "pyproject.toml",
    "uv.lock",
)

PUBLIC_OUTPUT_SURFACE_PATHS = (
    "src/pietto/_metadata",
    "src/pietto/_project/json_v2.py",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
)

IR_PATHS = (
    "src/pietto/ir/model.py",
    "src/pietto/ir/builder.py",
    "src/pietto/ir/lowering.py",
)

POSITIVE_RELEASE_CLAIMS = (
    "tag created",
    "release created",
    "package release occurred",
    "published package",
    "uploaded package",
    "signing completed",
    "attestation completed",
    "release operation occurred",
)


def _phase43_docs() -> str:
    return " ".join(_normalized(REPO_ROOT / path) for path in PHASE43_DOC_PATHS)


def _phase43_evidence() -> str:
    return " ".join(
        _normalized(REPO_ROOT / path)
        for path in (*PHASE43_DOC_PATHS, *PHASE43_TEST_PATHS)
    )


def _public_output_surface_text() -> str:
    chunks: list[str] = []
    for relative_path in PUBLIC_OUTPUT_SURFACE_PATHS:
        path = REPO_ROOT / relative_path
        if path.is_file():
            chunks.append(_normalized(path))
            continue
        chunks.extend(_normalized(child) for child in sorted(path.glob("**/*.py")))
    return " ".join(chunks)


def _git_status() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return [line for line in result.stdout.splitlines() if line]


def _git_status_for(paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def _status_path(line: str) -> str:
    if len(line) > 2 and line[2] == " ":
        return line[3:]
    return line.split(maxsplit=1)[1]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_phase43_artifact_inventory_is_complete_through_slice8() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert REGISTER_PATH.is_file()
    for relative_path in PHASE43_TEST_PATHS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    docs = _phase43_docs()
    for required in (
        "| 1 | Identity, Scope Lock, And Static Audit |",
        "| 2 | `sum(row_let)` / `avg(row_let)` Inline Aggregate Arguments |",
        "| 3 | `count(row_let)` / `count_distinct(row_let)` Inline Aggregate Arguments |",
        "| 4 | `group by row_let` Inline Group Key MVP |",
        "| 5 | Grouped `order by row_let` Safe Subset |",
        "| 6 | `satisfying` Boundary For Aggregate-Wrapped Let |",
        "| 7 | CLI / JSON / Metadata / SQL Compatibility Hardening |",
        "| 8 | Completion Audit And Status Lock |",
        "complete completion audit/status lock; no behavior change",
        "No remaining Phase 43 slice is pending after Slice 8",
    ):
        assert required in docs, required


def test_phase43_slice8_status_lock_is_no_behavior_work() -> None:
    docs = _phase43_docs()

    for required in (
        "Phase 43 Slice 8 is Completion Audit And Status Lock",
        "docs/spec/static-audit/status-lock work only",
        "implements no compiler behavior change",
        "Slice 8 does not claim Gate 3 natural CI success before Gate 3",
        "Phase 43 is complete as an eight-slice let-binding aggregate/grouped-query integration phase once Gate 3 records",
        "final commit, push, and natural CI `headSha` verification",
        "Slice 8 adds only completion audit and status-lock coverage",
        "does not start Phase 44 or any maintenance/Dependabot work",
        "Package version remains `0.1.0`",
        "No tag/release/publish/upload/signing or attestation is authorized by Slice 8",
    ):
        assert required in docs, required

    for forbidden in (
        "Gate 3 natural CI succeeded",
        "Gate 3 natural CI has succeeded",
        "natural CI success is complete",
        "Phase 44 has started",
        "Dependabot work has started",
    ):
        assert forbidden not in docs, forbidden


def test_slice1_through_slice7_outcomes_remain_locked() -> None:
    evidence = _phase43_evidence()

    for required in (
        "Slice 1 identity/scope lock/static audit",
        "Slice 2 direct `sum(row_let)` / `avg(row_let)` inline aggregate arguments",
        "Slice 3 direct `count(row_let)` / `count_distinct(row_let)` inline aggregate arguments",
        "Slice 4 direct field-backed `group by row_let`",
        "Slice 5 selected field-backed grouped `order by row_let`",
        "Slice 6 selected aggregate-wrapped `satisfying` let calls",
        "Slice 7 CLI / JSON / metadata / SQL compatibility hardening",
        "Slice 8 completion audit/status lock with no behavior change",
        "sum(row_let)",
        "avg(row_let)",
        "count(row_let)",
        "count_distinct(row_let)",
        "group by row_let",
        "order by row_let",
        "satisfying: sum(row_let)",
        "Semantic Metadata Artifact v1",
    ):
        assert required in evidence, required


def test_final_deferred_fail_closed_boundary_is_locked() -> None:
    docs = _phase43_docs()

    for required in (
        "raw `satisfying: row_let > 0`",
        "`limit row_let`",
        "qualified let references such as `orders.gross`",
        "projection aliases as same-select expression leaves",
        "`min(row_let)` and `max(row_let)`",
        "literal-only aggregate behavior",
        "expression or literal group keys",
        "arbitrary grouped order expressions",
        "broad direct aggregate calls inside `satisfying:`",
        "unselected aggregate-let calls inside `satisfying:`",
        "broad `count_distinct(expression)` hidden behind row-level lets",
        "Decimal precision fusion",
        "aggregate typeclass registry implementation",
        "public JSON, Project JSON v2, explain, or Semantic Metadata Artifact v1 schema expansion",
        "runtime/database, project/multi-file, LSP/editor, Arrow/PyArrow",
        "relationship/JOIN, Dependabot, maintenance, package, tag, release, publish",
    ):
        assert required in docs, required

    for forbidden in (
        "raw satisfying row-let behavior is implemented",
        "limit row-let behavior is implemented",
        "min(row_let) is implemented",
        "max(row_let) is implemented",
        "literal-only aggregate behavior is implemented",
        "arbitrary grouped order expressions are implemented",
    ):
        assert forbidden not in docs, forbidden


def test_ir_public_output_and_hidden_layer_boundaries_remain_locked() -> None:
    docs = _phase43_docs()
    ir_text = " ".join(_read(REPO_ROOT / path) for path in IR_PATHS)
    public_output_surface = _public_output_surface_text()

    for required in (
        "no `LetBindingIR`",
        "no `RelationLayerIR`",
        "no hidden CTE insertion",
        "no hidden subquery insertion",
        "no public `let_scopes` metadata key",
        "no Project JSON v2 key",
        "no explain/metadata schema key",
        "no global status-doc change",
    ):
        assert required in docs, required

    assert "LetBindingIR" not in ir_text
    assert "RelationLayerIR" not in ir_text
    assert "let_scopes" not in public_output_surface
    for forbidden in ("precision_scale", '"precision"', '"scale"'):
        assert forbidden not in public_output_surface, forbidden


def test_deferred_register_records_phase43_completion_without_unfreezing() -> None:
    register = _normalized(REGISTER_PATH)

    for required in (
        "Phase 43 Slice 8 completes the let-binding aggregate/grouped integration completion audit and status lock without behavior expansion",
        "bug fixes only",
        "Aggregate typeclass, literal-only aggregate behavior, expression/literal group keys",
        "grouped let ordering outside the approved Phase 43 Slice 5 direct selected-field subset",
        "raw `satisfying` let-name behavior outside the approved Phase 43 Slice 6 selected aggregate-wrapped let subset",
        "`limit let_name` behavior unfreeze only when a later implementation slice is explicitly approved",
        "No new aggregate functions",
        "No new aggregate functions, modifiers, filters, window functions",
        "hidden relation layer, CTE, subquery, JOIN, relationship traversal",
    ):
        assert required in register, required

    for forbidden in (
        "Slice 8 implements aggregate behavior",
        "Slice 8 authorizes aggregate expansion",
        "register authorizes Phase 43 behavior expansion",
        "implementation authorized",
    ):
        assert forbidden not in register, forbidden


def test_package_version_release_and_global_status_boundaries_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    docs = _phase43_docs()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    lowered = docs.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden

    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        assert relative_path in FORBIDDEN_DIFF_PATHS
        assert "Phase 43 is complete as an eight-slice" not in _normalized(
            REPO_ROOT / relative_path
        )


def test_forbidden_surfaces_are_unchanged_or_untracked() -> None:
    diff_paths = set(
        filter(
            None,
            _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS).splitlines(),
        )
    )
    status_paths = {
        _status_path(line)
        for line in _git_status_for(FORBIDDEN_DIFF_PATHS).splitlines()
        if line
    }

    assert diff_paths <= ALLOWED_SLICE8_CHANGED_PATHS
    assert status_paths <= ALLOWED_SLICE8_CHANGED_PATHS


def test_changed_set_is_slice8_allowlist_or_clean_ci_checkout() -> None:
    status_paths = {_status_path(line) for line in _git_status()}

    assert status_paths <= ALLOWED_SLICE8_CHANGED_PATHS

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert not any(
            _path_matches(path, forbidden) and path not in ALLOWED_SLICE8_CHANGED_PATHS
            for path in status_paths
        )
