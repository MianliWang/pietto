from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = REPO_ROOT / "docs/spec/phase38-count-family-semantics-contract-v1.md"
PHASE38_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
COUNT_EXPRESSION_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-expression-mvp-decision-v1.md"
)
FILTER_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md"
)
ANY_BYTES_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/any-bytes-json-support-posture-v1.md"
ENUM_SPEC_PATH = REPO_ROOT / "docs/spec/enum-support-resolution-v1.md"
UUID_SPEC_PATH = REPO_ROOT / "docs/spec/uuid-support-completion-v1.md"

PHASE23_COUNT_TEST_PATH = REPO_ROOT / "tests/test_phase23_count_field_semantics.py"
PHASE24_READINESS_TEST_PATH = (
    REPO_ROOT / "tests/test_phase24_aggregate_expression_arguments_readiness.py"
)
PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE36_ANY_BYTES_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_any_bytes_json_support_posture.py"
)
PHASE36_ENUM_TEST_PATH = REPO_ROOT / "tests/test_phase36_enum_support_resolution.py"
PHASE37_CURRENT_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_current_aggregate_matrix.py"
)
PHASE37_FILTER_DISTINCT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py"
)
PHASE37_GROUPED_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_grouped_aggregate_interaction_hardening.py"
)

SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
SEMANTIC_CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
POSTGRES_SQL_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_SQL_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def _spec() -> str:
    return _normalized(SPEC_PATH)


def _combined_current_count_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            SPEC_PATH,
            PHASE38_PLAN_PATH,
            FREEZE_SPEC_PATH,
            COUNT_EXPRESSION_SPEC_PATH,
            FILTER_DISTINCT_SPEC_PATH,
            ANY_BYTES_JSON_SPEC_PATH,
            ENUM_SPEC_PATH,
            UUID_SPEC_PATH,
            PHASE23_COUNT_TEST_PATH,
            PHASE24_READINESS_TEST_PATH,
            PHASE31_MATRIX_TEST_PATH,
            PHASE36_ANY_BYTES_JSON_TEST_PATH,
            PHASE36_ENUM_TEST_PATH,
            PHASE37_CURRENT_MATRIX_TEST_PATH,
            PHASE37_FILTER_DISTINCT_TEST_PATH,
            PHASE37_GROUPED_TEST_PATH,
            SEMANTIC_AGGREGATES_PATH,
            SEMANTIC_CATALOG_PATH,
            POSTGRES_SQL_PATH,
            MYSQL_SQL_PATH,
        )
    )


def test_spec_exists_and_records_slice2_guardrail() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 38 Count Family Semantics Contract v1",
        "Phase 38 Slice 2 is Count Family Semantics Contract",
        "docs/spec/static-audit/tests-only",
        "authorizes no behavior change",
        "does not implement `count(expression)`",
        "does not implement `count(constant)` or `count(1)`",
        "does not implement `count_if`",
        "does not add aliases such as `row_count()` or `count_row()`",
        "does not broaden `count_distinct`",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_current_count_family_inventory_is_evidence_backed() -> None:
    evidence = _combined_current_count_evidence()

    for required in (
        "`count()` | Accepted as SQL `COUNT(*)`; result is `Int not null`",
        "`count(field)` | Accepted for a direct field argument whose resolved type passes current count rules",
        "`count(source.field)` | Accepted for supported single-input qualified direct fields",
        "`count(Any field)` | Rejected with `PIE-S2314`",
        "`count(Json field)` | Accepted and SQL-emitting",
        "`count(Bytes field)` | Accepted and SQL-emitting",
        "`count(Enum field)` | Rejected with `PIE-S2314`",
        "no longer reaches backend `PIE-B1000`",
        "`count(UUID field)` | Accepted under the current `limited_frozen` UUID surface",
        "`count(expression)` | Deferred and fail-closed today",
        "`count(constant)` / `count(1)` | Not current behavior",
        "`count_if(predicate)` | No current aggregate or builtin function surface",
        "`row_count()` / `count_row()` | No current function surface",
        "`count_distinct(field)` | Accepted for current direct-field subset",
        "`count_distinct(expression)` | Accepted only for bounded lower/trim Text chains",
        "`count(distinct field)` | Not Pietto source syntax",
        "parser-rejected with `PIE-P1000`",
    ):
        assert required in evidence, required

    for source_evidence in (
        "def is_supported_count_argument",
        "value_type.resolved_type.kind not in",
        "TypeKind.ENUM",
        'not _is_builtin(value_type, "Any")',
        "def deferred_argument_expression_diagnostic",
        'COUNT_AGGREGATE_NAME = "count"',
        'COUNT_DISTINCT_AGGREGATE_NAME = "count_distinct"',
        'BuiltinFunction("lower", ("Text",), "Text")',
        'BuiltinFunction("trim", ("Text",), "Text")',
        'BuiltinFunction("len", ("Text",), "Int")',
        'BuiltinFunction("matches", ("Text", "Text"), "Bool")',
    ):
        assert source_evidence in evidence, source_evidence


def test_count_star_and_count_field_semantics_are_documented() -> None:
    spec = _spec()

    for required in (
        "`count()` is the preferred Pietto spelling for all-row count",
        "counts input rows, not values of a field",
        "lowers to SQL `COUNT(*)`",
        "returns `Int not null`",
        "returns `0` for an empty input",
        "does not inspect any field",
        "remains distinct from `count(field)`",
        "`count(field)` and `count(source.field)` count SQL non-null field values",
        "differs from `count()` because it excludes rows where the field value is SQL `NULL`",
        "current diagnostics for unsupported types, unknown fields, expression arguments",
    ):
        assert required in spec, required


def test_sql_null_and_json_null_distinction_is_documented() -> None:
    spec = _spec()

    for required in (
        "## SQL `NULL` Versus JSON Literal `null`",
        "For `count(Json field)`, the relevant nullness is SQL nullness of the field",
        "SQL `NULL` field values are not counted by `count(Json field)`",
        "JSON literal `null` is not automatically the same thing as a SQL `NULL` field value",
        "Pietto currently has no JSON literal syntax",
        "future Json countability changes must define SQL-null versus JSON-null policy explicitly",
    ):
        assert required in spec, required


def test_future_count_expression_semantics_are_candidate_only() -> None:
    spec = _spec()

    for required in (
        "`count(expression)` remains a future candidate only",
        "Slice 2 does not implement it",
        "SQL-style non-null expression result counting",
        "Rows whose expression result is SQL `NULL` are not counted",
        "Rows whose expression result is non-`NULL` are counted",
        "a Bool expression counts both `TRUE` and `FALSE` when non-`NULL`",
        "`count(expression)` is not the same as `count_if(predicate)`",
        "unsupported shapes must fail closed before SQL lowering",
        "PostgreSQL/private MySQL portability",
        "public output compatibility review",
    ):
        assert required in spec, required


def test_constant_count_and_null_literal_posture_are_documented() -> None:
    spec = _spec()

    for required in (
        "`count(constant)` and `count(1)` are not current behavior",
        "future SQL migration compatibility candidates only",
        "idiomatic new Pietto code should use `count()`",
        "non-idiomatic but SQL-valid forms should not become accepted accidentally",
        "must not silently rewrite `count(1)` to `count()`",
        "future warning, lint, or strict-mode treatment must be separate",
        "Slice 2 does not introduce a `NULL` literal just to support `count(NULL)`",
        "If a future Pietto NULL literal is approved",
        "whether it preserves SQL `COUNT(NULL)` behavior",
    ):
        assert required in spec, required


def test_count_if_and_alias_non_adoption_are_documented() -> None:
    spec = _spec()

    for required in (
        "`count_if(predicate)` remains a future candidate only",
        "predicate argument must be `Bool` or nullable `Bool`",
        "`TRUE` counts",
        "`FALSE`, SQL `NULL`, and SQL three-valued `UNKNOWN` do not count",
        "result is `Int not null`",
        "no matching rows returns `0`",
        "`count_if(predicate)` is different from `count(predicate)`",
        "Slice 2 does not adopt `row_count()` or `count_row()`",
        "Aliases should not be introduced if they only duplicate `count()`",
        "`row_count = count()`",
    ):
        assert required in spec, required


def test_count_distinct_is_not_broadened_by_slice2() -> None:
    spec = _spec()

    for required in (
        "`count_distinct(...)` remains a separate aggregate spelling",
        "`count_distinct(field)`",
        "`count_distinct(source.field)`",
        "`count_distinct(lower/trim Text chain)` over exactly one `Text` field leaf",
        "Slice 2 does not broaden `count_distinct(expression)`",
        "does not introduce generic SQL-style `count(distinct field)` syntax",
        "`count` depends on SQL lowerability and SQL nullness",
        "`count_distinct` additionally depends on equality, distinct compatibility",
        "collation, normalization, serialization, deterministic transform, and dialect portability",
    ):
        assert required in spec, required


def test_count_family_capability_boundary_is_documented() -> None:
    spec = _spec()

    for required in (
        "Broad countability is not numeric capability",
        "arithmetic capability",
        "orderable capability",
        "distinct compatibility",
        "`count(expression)` should depend mainly on SQL lowerability and nullness",
        "`sum` / `avg` require numeric and arithmetic capability",
        "`min` / `max` require orderable capability",
        "`count_distinct` requires equality/distinct compatibility plus collation",
        "Any, Json, Bytes, Enum, and UUID",
        "does not imply arithmetic, ordering, or distinct support",
    ):
        assert required in spec, required


def test_boundary_type_count_posture_is_documented() -> None:
    spec = _spec()

    for required in (
        "`Any`: current `count(Any field)` rejection remains `PIE-S2314`",
        "not as dynamic typing or permissive SQL fallback",
        "`Json`: current direct `count(Json field)` remains accepted",
        "SQL `NULL` versus JSON literal `null` explicit",
        "`Bytes`: current direct `count(Bytes field)` remains accepted",
        "no binary semantics, encoding policy, comparison, distinct, ordering",
        "Enum: current `count(Enum field)` remains semantic `PIE-S2314`",
        "after Enum scalar and SQL portability policy",
        "`UUID`: current direct `count(UUID field)` remains accepted under `limited_frozen`",
        "no UUID ordering, `min/max`, native behavior, literal, cast, storage",
    ):
        assert required in spec, required


def test_diagnostics_and_deferred_surfaces_remain_preserved() -> None:
    spec = _spec()

    for required in (
        "Slice 2 changes no diagnostics and adds no diagnostic code",
        "`PIE-S2308`",
        "`PIE-S2309`",
        "`PIE-S2310`",
        "`PIE-S2311`",
        "`PIE-S2313`",
        "`PIE-S2314`",
        "`PIE-S2315`",
        "`PIE-P1000`",
        "Future count-family implementation work must prove no accidental expansion",
        "source syntax",
        "grammar or generated parser files",
        "semantic, IR, or SQL behavior beyond the approved row",
        "fixtures or golden SQL bytes",
    ):
        assert required in spec, required


def test_public_surface_and_release_non_authorization_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    spec = _spec()

    for required in (
        "CLI text output unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "generated parser inventory unchanged",
        "package version remains `0.1.0`",
        "no package/workflow/release metadata change",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in spec, required

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
