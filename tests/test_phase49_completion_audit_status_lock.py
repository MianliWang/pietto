from __future__ import annotations

import json
from pathlib import Path
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
SPEC_PATH = REPO_ROOT / "docs/spec/phase49-completion-audit-status-lock-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

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
    "phase49-completion-audit-status-lock-v1.md",
)

EXPECTED_PHASE49_TESTS = (
    "tests/test_phase49_row_level_computed_let_schema_scope_lock.py",
    "tests/test_phase49_project_row_expression_schema_helper_contract.py",
    "tests/test_phase49_project_row_expression_type_nullability_adapter.py",
    "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
    "tests/test_phase49_computed_alias_origin_provenance_privacy.py",
    "tests/test_phase49_project_let_scope_value_facts.py",
    "tests/test_phase49_selected_let_derived_output_schema.py",
    "tests/test_phase49_let_visibility_order_shadowing_hardening.py",
    "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase49_computed_let_multi_hop_row_lineage.py",
    "tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py",
    "tests/test_phase49_compatibility_privacy_hash_lock_readiness.py",
    "tests/test_phase49_completion_audit_status_lock.py",
)

PRIVATE_CARRIER_NAMES = (
    "relation_row_schemas",
    "relation_row_schema_states",
    "relation_let_scope_facts",
    "relation_row_dependency_graphs",
    "relation_row_lineages",
)

PROJECT_JSON_V2_KEYS = (
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

PRIVATE_JSON_FORBIDDEN_TOKENS = (
    *PRIVATE_CARRIER_NAMES,
    "ProjectRowSchema",
    "ProjectRelationRowSchemaState",
    "ProjectRelationLetScopeFacts",
    "ProjectRelationRowDependencyGraph",
    "ProjectRelationRowLineage",
    "ProjectRowFieldProvenance",
    "ProjectRowDependencyNode",
    "ProjectRowDependencyEdge",
    "ProjectRowLineageSegment",
    "ProjectRowLineageFact",
    "provenance",
    "origin",
    "lineage",
    "dependency",
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

DEFERRED_BOUNDARIES = (
    "aggregate/grouped output schema",
    "aggregate/grouped lineage",
    "project explain/public metadata",
    "public lineage/export",
    "project IR/SQL/emit-sql",
    "JOIN/relationship/grain/fanout",
    "bridge/export/RAG/Arrow",
    "runtime/database behavior",
    "package release/version work",
)


def _phase49_docs() -> str:
    return " ".join(
        (
            PLAN_PATH.read_text(encoding="utf-8")
            + "\n"
            + SPEC_PATH.read_text(encoding="utf-8")
        ).split()
    )


def test_completion_spec_and_plan_readiness_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _phase49_docs()
    for required in (
        "Phase 49 Slice 14 is Completion audit/status lock",
        "`docs/spec/phase49-completion-audit-status-lock-v1.md`",
        "docs/spec/tests-only",
        "Phase 49 is complete only after Slice 14 Gate 3",
        "natural CI success",
        "Package version remains `0.1.0`",
        "tag, release, publish, upload, signing, or attestation",
        "No other file is approved in Slice 14 Gate 2",
    ):
        assert required in docs, required


def test_phase49_spec_inventory_is_locked() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    for spec_name in EXPECTED_PHASE49_SPECS:
        assert (REPO_ROOT / "docs/spec" / spec_name).is_file(), spec_name
        assert spec_name in plan, spec_name


def test_phase49_test_inventory_is_locked() -> None:
    for relative_path in EXPECTED_PHASE49_TESTS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_private_carriers_and_project_json_privacy_boundaries_are_locked() -> None:
    project_model = (REPO_ROOT / "src/pietto/_project/model.py").read_text(
        encoding="utf-8"
    )
    json_v2 = (REPO_ROOT / "src/pietto/_project/json_v2.py").read_text(encoding="utf-8")
    check = (REPO_ROOT / "src/pietto/_project/check.py").read_text(encoding="utf-8")

    for carrier_name in PRIVATE_CARRIER_NAMES:
        assert carrier_name in project_model, carrier_name
        assert carrier_name not in json_v2, carrier_name
        assert carrier_name not in check, carrier_name


def test_project_json_v2_public_envelope_remains_stable(tmp_path: Path) -> None:
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

        assert tuple(document) == PROJECT_JSON_V2_KEYS
        assert _json_paths_for_key(document, "status") == ("inputs[].status",)
        assert _json_paths_for_key(document, "reason") == ()
        for private_token in PRIVATE_JSON_FORBIDDEN_TOKENS:
            assert private_token not in serialized, private_token


def test_deferred_work_status_is_locked() -> None:
    docs = _phase49_docs()
    for deferred_boundary in DEFERRED_BOUNDARIES:
        assert deferred_boundary in docs, deferred_boundary


def test_package_version_remains_010() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.1.0"


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
