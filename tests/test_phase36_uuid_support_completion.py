from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/uuid-support-completion-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
SEMANTIC_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
SEMANTIC_GROUP_BY_PATH = REPO_ROOT / "src/pietto/semantic/group_by.py"
SEMANTIC_SATISFYING_PATH = REPO_ROOT / "src/pietto/semantic/satisfying.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
METADATA_MODEL_PATH = REPO_ROOT / "src/pietto/_metadata/model.py"
METADATA_BUILDER_PATH = REPO_ROOT / "src/pietto/_metadata/builder.py"
METADATA_SERIALIZER_PATH = REPO_ROOT / "src/pietto/_metadata/serializer.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"


def _phase36_slice4_docs() -> str:
    return f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"


def test_slice4_is_docs_spec_static_audit_only() -> None:
    combined = _phase36_slice4_docs()

    for required in (
        "Phase 36 Slice 4 selects Option A: docs/spec/static-audit only",
        "UUID Support Completion",
        "does not change behavior",
        "does not authorize UUID behavior implementation",
        "does not change source/compiler behavior",
        "does not change public outputs",
        "Any future UUID behavior changes require separately approved Gate 1 and Gate 2",
        "Slice 4 keeps the broader 12-slice Phase 36 plan intact",
    ):
        assert required in combined, required


def test_uuid_remains_limited_frozen_not_fully_stable_scalar() -> None:
    combined = _phase36_slice4_docs()
    metadata_builder = _read(METADATA_BUILDER_PATH)

    for required in (
        "`UUID` remains a limited/frozen scalar name, not a fully stable UUID scalar",
        "Slice 4 does not make `UUID` a fully stable UUID scalar",
        "`UUID` has limited/frozen support posture",
        '`support_posture="limited_frozen"`',
    ):
        assert required in combined, required

    assert '_LIMITED_FROZEN_BUILTINS = frozenset({"UUID"})' in metadata_builder


def test_current_supported_uuid_surfaces_are_documented() -> None:
    combined = _phase36_slice4_docs()

    for required in (
        "field declaration and shape facts",
        "source field facts",
        "projection",
        "aliases through the generic projection schema",
        "direct `count(UUID field)`",
        "direct `count_distinct(UUID field)`",
        'metadata/explain `support_posture="limited_frozen"`',
        "generic CLI, JSON, and SQL paths where already covered by existing tests",
    ):
        assert required in combined, required


def test_risky_generic_uuid_surfaces_are_documented() -> None:
    combined = _phase36_slice4_docs()

    for required in (
        "equality comparisons",
        "inequality comparisons",
        "ordering comparisons",
        "`order by UUID` field",
        "`group by UUID` field",
        "`satisfying` predicates involving UUID",
        "SQL portability",
        "UUID `min` and `max` boundary",
        "stable UUID ordering",
        "native UUID semantics",
        "dialect-specific UUID treatment",
    ):
        assert required in combined, required


def test_unsupported_uuid_surfaces_remain_closed() -> None:
    combined = _phase36_slice4_docs()

    for required in (
        "UUID literals",
        "UUID casts",
        "native DB metadata",
        "DDL/storage behavior",
        "schema introspection or db pull",
        "runtime/database execution",
        "UUID-specific JSON/API/schema fields",
        "UUID-specific Semantic Metadata Artifact v1 schema or output fields",
        "broad SQL behavior expansion",
        "UUID `min` or `max` support unless separately approved",
        "UUID `sum` or `avg`",
        "package, workflow, or release behavior",
    ):
        assert required in combined, required


def test_future_uuid_prerequisites_are_listed() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "precise comparison policy",
        "ordering policy",
        "group-key policy",
        "satisfying/result predicate policy",
        "aggregate matrix policy for `min`, `max`, `count`, and `count_distinct`",
        "dialect portability policy for PostgreSQL and private MySQL",
        "public output compatibility policy",
        "diagnostics/fail-closed policy",
        "validation proving no accidental literal, cast, native metadata, runtime, JSON, metadata, or SQL expansion",
    ):
        assert required in spec, required


def test_existing_source_surfaces_do_not_add_uuid_specific_carriers() -> None:
    catalog = _read(CATALOG_PATH)
    semantic_model = _read(SEMANTIC_MODEL_PATH)
    ir_model = _read(IR_MODEL_PATH)
    metadata_model = _read(METADATA_MODEL_PATH)
    metadata_serializer = _read(METADATA_SERIALIZER_PATH)
    cli_json = _read(CLI_JSON_PATH)

    assert '"UUID"' in catalog
    assert 'BuiltinFunction("UUID"' not in catalog
    assert 'BuiltinFunction("uuid"' not in catalog

    for required in (
        "class ResolvedType:",
        "name: str",
        "kind: TypeKind",
        "class ValueType:",
        "resolved_type: ResolvedType",
        "nullability: EffectiveNullability",
    ):
        assert required in semantic_model, required

    for required in (
        "class TypeRefIR:",
        "declared_name: str",
        "canonical_name: str",
        "kind: TypeKindIR",
        "canonical_kind: TypeKindIR",
        "nullability: NullabilityIR",
    ):
        assert required in ir_model, required

    for required in (
        "class SemanticMetadataType:",
        "status: str",
        "name: str | None",
        "kind: str",
        "canonical_name: str | None",
        "canonical_kind: str",
        "nullability: str",
        "support_posture: str",
    ):
        assert required in metadata_model, required

    for output_source in (metadata_serializer, cli_json):
        for forbidden in (
            '"uuid"',
            '"uuid_literal"',
            '"uuid_cast"',
            '"uuid_storage"',
            '"native_uuid"',
            '"native_db"',
            '"database_metadata"',
            '"storage_metadata"',
            '"ddl_metadata"',
        ):
            assert forbidden not in output_source.lower(), forbidden


def test_current_shared_uuid_paths_remain_generic_in_source() -> None:
    expressions = _read(SEMANTIC_EXPRESSIONS_PATH)
    aggregates = _read(SEMANTIC_AGGREGATES_PATH)
    group_by = _read(SEMANTIC_GROUP_BY_PATH)
    satisfying = _read(SEMANTIC_SATISFYING_PATH)
    postgres = _read(POSTGRES_EXPRESSIONS_PATH)
    mysql = _read(MYSQL_EXPRESSIONS_PATH)

    assert 'return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)' in (
        expressions
    )
    assert "def _resolve_group_keys(" in group_by
    assert "def _infer_predicate(" in satisfying
    assert '"UUID"' in aggregates
    assert '"UUID"' in postgres
    assert '"UUID"' in mysql

    for renderer_source in (postgres, mysql):
        assert "_SUPPORTED_COUNT_DISTINCT_ARGUMENT_TYPES = frozenset(" in (
            renderer_source
        )
        assert '"Int", "Float", "Decimal", "Date", "Timestamp"' in renderer_source
        for forbidden in (
            "native uuid",
            "uuid literal",
            "uuid cast",
            "uuid storage",
            "CREATE TYPE",
            "UUID(",
        ):
            assert forbidden.lower() not in renderer_source.lower(), forbidden


def test_slice4_explicit_non_authorization_is_documented() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Slice 4 does not implement UUID behavior changes",
        "Slice 4 does not add fail-closed diagnostics",
        "does not approve UUID literals",
        "casts",
        "native metadata",
        "DDL",
        "runtime",
        "storage",
        "SQL golden updates",
        "JSON/schema updates",
        "Project JSON v2 schema updates",
        "Semantic Metadata Artifact v1 schema/output changes",
        "CLI output changes",
        "package metadata changes",
        "package version changes",
        "workflow changes",
        "release",
        "publish/upload",
        "signing",
        "attestation",
    ):
        assert required in spec, required
