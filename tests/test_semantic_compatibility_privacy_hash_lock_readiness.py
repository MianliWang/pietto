from __future__ import annotations

import json
from pathlib import Path

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

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


def test_project_helpers_do_not_call_full_semantic_analyze() -> None:
    for relative_path in PROJECT_HELPER_PATHS:
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for forbidden in FULL_SEMANTIC_ANALYZE_FORBIDDEN:
            assert forbidden not in source, relative_path

    let_scope_source = (REPO_ROOT / "src/pietto/_project/let_scope_facts.py").read_text(
        encoding="utf-8"
    )
    assert "analyze_relation_let_bindings" in let_scope_source


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
