from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import tomllib
from pathlib import Path
from typing import Any, cast

from pietto import cli_json

REPO_ROOT = Path(__file__).resolve().parents[1]

CONTRACT_PATH = REPO_ROOT / "docs/spec/semantic-metadata-artifact-v1.md"
CANDIDATE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/semantic-metadata-artifact-candidate-decision-v1.md"
)
PLAN_PATH = REPO_ROOT / "docs/plan/phase-32-semantic-explain-and-metadata-output.md"
CLI_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/cli-json-v1.md"
CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"

STATUS_DOCS = (AGENTS_PATH, PIETTO_SPEC_PATH)


def test_artifact_v1_identity_and_version_domain_are_locked() -> None:
    contract = _normalized(CONTRACT_PATH)
    candidate = _normalized(CANDIDATE_SPEC_PATH)
    cli_json_v1 = _normalized(CLI_JSON_SPEC_PATH)

    for required in (
        "Semantic Metadata Artifact v1",
        "`schema_version: 1` is the Semantic Metadata Artifact v1 version domain",
        "separate from existing single-file CLI JSON v1",
        "separate from future project-level JSON v2",
        "Semantic Metadata Artifact v1 is not a mutation of CLI JSON v1",
        "pietto explain <file> [--format text|json]",
        "Slice 2 is complete as docs/spec/static-audit/contract-only work",
    ):
        assert required in contract, required

    assert "Semantic Metadata Artifact v1" in candidate
    assert "JSON schema version 1 remains exclusively single-file" in cli_json_v1


def test_success_and_failure_envelopes_are_contractual() -> None:
    contract = _normalized(CONTRACT_PATH)

    for required in (
        "artifact, schema_version, command, ok, path, diagnostics, metadata",
        "artifact, schema_version, command, ok, path, diagnostics, error",
        '| `$.artifact` | string | yes | non-null | Constant `"Semantic Metadata Artifact v1"`',
        "| `$.schema_version` | integer | yes | non-null | Constant `1`",
        '| `$.command` | string | yes | non-null | Constant `"explain"`',
        "| `$.metadata` | object | yes | non-null | Normalized metadata payload",
        "| `$.error` | absent | yes | n/a | Must not appear on success",
        "| `$.error.stage` | string | yes | non-null | One of",
        "| `$.metadata` | absent | yes | n/a | Must be absent, not `null`, on failure",
        "CLI process exit-code behavior is deferred to the later CLI integration slice",
    ):
        assert required in contract, required


def test_failure_policy_has_no_partial_metadata() -> None:
    contract = _normalized(CONTRACT_PATH)
    candidate = _normalized(CANDIDATE_SPEC_PATH)

    for required in (
        "Artifact v1 is emitted only after this future pipeline succeeds",
        "parse -> semantic analysis -> existing IR construction -> normalized metadata artifact",
        "must not invoke SQL lowering, connector execution, database connections, SQL execution, or runtime behavior",
        "diagnostics/error information only",
        "must not expose partial definitions, partial relations, partial schemas, partial projections, partial aggregates, or partial lineage",
    ):
        assert required in contract, required

    assert (
        "Metadata is emitted only after parse, semantic analysis, and IR construction all succeed"
        in candidate
    )


def test_diagnostics_reuse_json_v1_shape_without_mutating_json_v1() -> None:
    contract = _normalized(CONTRACT_PATH)
    cli_json_v1 = _normalized(CLI_JSON_SPEC_PATH)

    for required in (
        "reuses the existing CLI JSON v1 diagnostic object shape by reference",
        "docs/spec/cli-json-v1.md",
        "src/pietto/cli_json.py::diagnostic_to_json_dict",
        "`code`",
        "`severity`",
        "`message`",
        "`location`",
        "`suggestion`",
        "must not mutate CLI JSON v1",
        "change JSON v1 schema version",
    ):
        assert required in contract, required

    assert "Every compiler diagnostic uses" in cli_json_v1
    check_result = cli_json.check_result_to_json_dict(path="input.pietto")
    emit_result = cli_json.emit_sql_result_to_json_dict(
        path="input.pietto",
        dialect="postgres",
    )
    assert tuple(check_result) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "cli_errors",
    )
    assert tuple(emit_result) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    )


def test_metadata_payload_categories_are_locked() -> None:
    contract = _normalized(CONTRACT_PATH)

    for required in (
        "`$.metadata.source`",
        "`$.metadata.definitions`",
        "`$.metadata.sources`",
        "`$.metadata.relations`",
        "`$.metadata.types`",
        "Definition Object",
        "Source Object",
        "Relation Object",
        "Schema And Field Objects",
        "Type Object",
        "Query Object",
        "Projection Object",
        "Aggregate Object",
        "Basic Lineage Object",
    ):
        assert required in contract, required


def test_type_encoding_boundary_is_locked() -> None:
    contract = _normalized(CONTRACT_PATH)
    catalog = _read(CATALOG_PATH)

    for builtin in ("Any", "Bytes", "Date", "Decimal", "Json", "Timestamp", "UUID"):
        assert f'"{builtin}"' in catalog

    for required in (
        "`status` | string | yes | `known` or `unknown`",
        "`kind` | string | yes | `builtin`, `type_alias`, `enum`, `shape`, or `unknown`",
        "`support_posture` | string | yes | `current`, `limited_frozen`, `deferred_builtin`, `metadata_only`, or `unknown`",
        "ValueTypeKind.UNKNOWN",
        "does not collapse `EffectiveNullability.UNKNOWN`",
        '`Bytes` and `Json` are known builtins with `support_posture: "deferred_builtin"`',
        '`UUID` is a known builtin with `support_posture: "limited_frozen"`',
        'Enum fields use `kind: "enum"` with `support_posture: "metadata_only"`',
        "Decimal has no precision or scale fields",
        "Date and Timestamp have no timezone, literal, temporal arithmetic, precision, native database metadata, or schema-introspection fields",
    ):
        assert required in contract, required


def test_aggregate_and_lineage_boundaries_are_locked() -> None:
    contract = _normalized(CONTRACT_PATH)
    aggregates = _read(AGGREGATES_PATH)

    for aggregate_name in ("count", "count_distinct", "sum", "avg", "min", "max"):
        assert aggregate_name in contract
    for source_constant in (
        "COUNT_AGGREGATE_NAME",
        "COUNT_DISTINCT_AGGREGATE_NAME",
        "SUM_AGGREGATE_NAME",
        "AVG_AGGREGATE_NAME",
        "MIN_AGGREGATE_NAME",
        "MAX_AGGREGATE_NAME",
    ):
        assert source_constant in aggregates

    for required in (
        "bounded numeric aggregate expressions",
        "group keys",
        "satisfying result predicates",
        "grouped result ordering",
        "adds no aggregate functions",
        "direct source relation and field provenance for direct field projections",
        "normalized direct field leaves used by currently supported bounded expressions",
        "normalized direct field leaves used by currently supported aggregate arguments",
        "excludes raw `SymbolId`, raw `FieldId`, AST identity, raw IR nodes",
        "relationship traversal, JOIN lineage, multi-file lineage, graph lineage",
    ):
        assert required in contract, required


def test_path_ordering_and_source_location_policy_are_locked() -> None:
    contract = _normalized(CONTRACT_PATH)

    for required in (
        "Artifact v1 is single-file only",
        "Existing compiler diagnostic order",
        "Single-file source/IR definition order",
        "Existing row-field order",
        "Projection order",
        "Deterministic first-encounter order",
        "existing user-supplied string / `str(path)` posture",
        "does not canonicalize paths by default",
        "promise absolute paths",
        "promise project-relative paths",
        "introduce project-root semantics",
        "must not fabricate `0:0` coordinates",
    ):
        assert required in contract, required


def test_forbidden_fields_non_goals_and_slice3_handoff_are_locked() -> None:
    contract = _normalized(CONTRACT_PATH)
    project = cast(dict[str, Any], _pyproject()["project"])

    assert project["version"] == "0.1.0"

    for required in (
        "relationship metadata",
        "SQL dialect or backend fields",
        "a global per-program `deferred` field",
        "connector secrets, connector arguments, connector configuration values",
        "runtime, database, physical database, and schema-introspection metadata",
        "project, workspace, or multi-file facts",
        "JSON v2 fields",
        "public MySQL API expansion",
        "package version, release, tag, publish, upload, signing, or attestation data",
        "Phase 32 MVP does not add a public Python API",
        "Slice 2 adopts no tooling",
        "Slice 3 may plan a private metadata model and builder",
    ):
        assert required in contract, required


def test_slice2_status_docs_record_contract_only_completion() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in (
            "Phase 32 Slice 2 Semantic Metadata Artifact v1 Contract is complete",
            "Slice 2 is docs/spec/static-audit/contract-only",
            "Phase 32 as a whole is not complete",
            "No `pietto explain` CLI behavior was implemented in Slice 2",
            "no source, CLI, JSON v1, semantic, IR, SQL, diagnostic, fixture, golden, example, package, dependency, workflow, version, release, tooling, tag, publish, upload, signing, or attestation behavior changed",
        ):
            assert required in status, f"{path}: missing {required!r}"


def test_phase32_plan_records_slice2_without_release_or_tooling_changes() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 32 Slice 2 is complete as Semantic Metadata Artifact v1 Contract work only",
        "docs/spec/semantic-metadata-artifact-v1.md",
        "tests/test_phase32_semantic_metadata_artifact_contract.py",
        "Slice 2 does not implement `pietto explain`",
        "package version changes, release operations, or tooling adoption",
        "uv run pytest tests/test_phase32_semantic_metadata_artifact_contract.py",
    ):
        assert required in plan, required


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _pyproject() -> dict[str, object]:
    return tomllib.loads(_read(PYPROJECT_PATH))
