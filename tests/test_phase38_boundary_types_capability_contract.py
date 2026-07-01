from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = REPO_ROOT / "docs/spec/phase38-boundary-types-capability-contract-v1.md"
PHASE38_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md"
)
TYPE_CAPABILITY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-type-capability-matrix-contract-v1.md"
)
COUNT_FAMILY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-count-family-semantics-contract-v1.md"
)
ANY_BYTES_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/any-bytes-json-support-posture-v1.md"
ENUM_SPEC_PATH = REPO_ROOT / "docs/spec/enum-support-resolution-v1.md"
UUID_SPEC_PATH = REPO_ROOT / "docs/spec/uuid-support-completion-v1.md"
MIN_MAX_SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"

PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE36_ANY_BYTES_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_any_bytes_json_support_posture.py"
)
PHASE36_ENUM_TEST_PATH = REPO_ROOT / "tests/test_phase36_enum_support_resolution.py"
PHASE36_UUID_TEST_PATH = REPO_ROOT / "tests/test_phase36_uuid_support_completion.py"

SEMANTIC_CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE4_CHANGED_PATHS = {
    "docs/spec/phase38-boundary-types-capability-contract-v1.md",
    "tests/test_phase38_boundary_types_capability_contract.py",
}

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "src",
    "grammar",
    "src/pietto/generated",
    "fixtures",
    "tests/fixtures",
    "scripts",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
)


def _spec() -> str:
    return _normalized(SPEC_PATH)


def _combined_boundary_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            SPEC_PATH,
            PHASE38_PLAN_PATH,
            TYPE_CAPABILITY_SPEC_PATH,
            COUNT_FAMILY_SPEC_PATH,
            ANY_BYTES_JSON_SPEC_PATH,
            ENUM_SPEC_PATH,
            UUID_SPEC_PATH,
            MIN_MAX_SPEC_PATH,
            PHASE31_MATRIX_TEST_PATH,
            PHASE36_ANY_BYTES_JSON_TEST_PATH,
            PHASE36_ENUM_TEST_PATH,
            PHASE36_UUID_TEST_PATH,
            SEMANTIC_CATALOG_PATH,
            SEMANTIC_AGGREGATES_PATH,
            SEMANTIC_MODEL_PATH,
        )
    )


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
    return line[3:]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_spec_exists_and_records_slice4_guardrail() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 38 Boundary Types Capability Contract v1",
        "Phase 38 Slice 4 is Any / Json / Bytes / Enum / UUID Capability Boundary",
        "docs/spec/static-audit/tests-only",
        "authorizes no behavior change",
        "does not add or change source/compiler behavior",
        "grammar, generated ANTLR files",
        "semantic behavior, IR behavior, SQL lowering",
        "CLI behavior, JSON v1, Project JSON v2",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_current_boundary_type_posture_is_repo_derived() -> None:
    evidence = _combined_boundary_evidence()

    for required in (
        "`Any` | Builtin name in `BUILTIN_TYPE_NAMES`; top/deferred boundary",
        "`Json` | Builtin name; deferred builtin behavior surface",
        "`Bytes` | Builtin name; deferred builtin behavior surface",
        "Enum | Not builtin. Semantic `TypeKind.ENUM`, IR `EnumIR`, and metadata posture `metadata_only`",
        "`UUID` | Builtin name; `limited_frozen` support posture",
        "Evidence anchors include `docs/spec/any-bytes-json-support-posture-v1.md`",
        "`src/pietto/semantic/catalog.py`",
        "`src/pietto/semantic/aggregates.py`",
        "`tests/test_phase36_any_bytes_json_support_posture.py`",
        "`tests/test_phase36_enum_support_resolution.py`",
        "`tests/test_phase36_uuid_support_completion.py`",
        "BUILTIN_TYPE_NAMES = frozenset",
        '"Any"',
        '"Bytes"',
        '"Json"',
        '"UUID"',
        "def is_supported_count_argument",
        "TypeKind.ENUM",
        "TypeKind.UNKNOWN",
        'not _is_builtin(value_type, "Any")',
        "def is_supported_count_distinct_argument",
        '"UUID"',
        "class TypeKind",
        'ENUM = "enum"',
    ):
        assert required in evidence, required


def test_any_json_bytes_enum_uuid_sections_exist() -> None:
    spec = _spec()

    for required in (
        "## `Any` Boundary",
        "`Any` remains an opaque top/deferred boundary type, not dynamic typing",
        "`Any` is projectable and lowerable only through current generic field/projection paths",
        "`count(Any field)` remains rejected with `PIE-S2314`",
        "Future `Any` countability requires explicit lowerable-count policy, refinement, or metadata",
        "## `Json` Boundary",
        "`Json` remains a deferred builtin behavior surface",
        "direct `count(Json field)`",
        "does not imply structural typing, JSON literal syntax, JSON path extraction",
        "## `Bytes` Boundary",
        "`Bytes` remains a deferred builtin behavior surface",
        "direct `count(Bytes field)`",
        "does not imply binary literal syntax, encoding policy, byte operators",
        "## Enum Boundary",
        "Enum remains `metadata_only`, not a builtin scalar",
        "Future Enum count, order, min/max, distinct, group-key, or satisfying behavior",
        "Enum ordering must require explicit order metadata",
        "## `UUID` Boundary",
        "`UUID` remains `limited_frozen`",
        "direct `count(UUID field)`",
        "direct `count_distinct(UUID field)`",
        "UUID ordering or `min/max` requires explicit metadata",
    ):
        assert required in spec, required


def test_sql_null_versus_json_literal_null_is_explicit() -> None:
    spec = _spec()

    for required in (
        "## SQL `NULL` Versus JSON Literal `null`",
        "For `count(Json field)`, the relevant nullness is SQL nullness of the field",
        "`count(Json field)` counts SQL non-`NULL` field values",
        "A JSON literal `null` stored in a non-`NULL` JSON value is counted",
        "A SQL `NULL` field value is not counted",
        "Slice 4 introduces no JSON literal syntax, JSON path extraction",
        "Future Json behavior changes must define SQL `NULL` versus JSON literal `null` policy explicitly",
    ):
        assert required in spec, required


def test_metadata_vocabulary_is_documented_without_implementation() -> None:
    spec = _spec()

    for required in (
        "## Metadata Vocabulary Without Implementation",
        "does not implement metadata syntax",
        "metadata schema fields",
        "semantic carriers",
        "public JSON fields",
        "SQL behavior",
        "runtime behavior",
        "Pietto declaration order",
        "imported native DB enum order",
        "explicit lexical order",
        "custom order",
        "`uuid_version`",
        "`uuid_ordering`",
        "`native` ordering",
        "`lexical` ordering",
        "`binary` ordering",
        "`time` ordering",
        "`custom` ordering",
        "explicit refinement",
        "native metadata",
        "operator-constrained capability",
        "JSON native type metadata remains deferred",
        "Bytes encoding metadata remains deferred",
    ):
        assert required in spec, required


def test_capability_interaction_matrix_aligns_with_slice3_vocabulary() -> None:
    spec = _spec()

    for required in (
        "## Capability Interaction Matrix",
        "`lowerable` | Only current accepted field/projection/aggregate SQL paths are lowerable",
        "`projectable` | Generic field projection exists; it is not full scalar semantics",
        "`null-checkable` | Generic expression machinery exists",
        "`countable` | Current direct-count matrix: `Json`, `Bytes`, and `UUID` yes; `Any` and Enum no",
        "`orderable` | Not granted to these boundary types by generic comparisons or order-by paths",
        "`distinct-compatible` | Only `UUID` among these five has direct `count_distinct`",
        "`metadata-backed` | Enum and `UUID` have metadata/support postures",
        "`dialect-lowerable` | Accepted PostgreSQL/private MySQL emit paths only",
        "`serialization-dependent` | Future broad distinct or opaque comparisons must define serialization and equality first",
        "`collation-dependent` | Text and Enum ordering must not expand by analogy without explicit policy",
        "avoids user-visible `hashable`",
        "supports `distinct-compatible`, not hash behavior",
    ):
        assert required in spec, required


def test_current_aggregate_behavior_matrix_is_preserved() -> None:
    evidence = _combined_boundary_evidence()

    for required in (
        "## Aggregate Behavior Preservation Matrix",
        "| `Any` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` |",
        "| `Json` | accepted; PostgreSQL/MySQL SQL emits `COUNT(field)` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` |",
        "| `Bytes` | accepted; PostgreSQL/MySQL SQL emits `COUNT(field)` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` |",
        "| Enum | rejected with `PIE-S2314`; no longer reaches backend `PIE-B1000` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` |",
        "| `UUID` | accepted | accepted; result `Int not null` | rejected/deferred; no current support | rejected/deferred; no current support |",
        "This matrix is preservation only",
        "does not widen `count(expression)`",
        "`count_distinct(expression)`, `min/max(expression)`, aggregate filters",
        'COUNT("raw")',
        'COUNT("payload")',
        'COUNT("id")',
        "Direct `count(Enum field)` must fail closed",
    ):
        assert required in evidence, required


def test_deferred_and_prohibited_surfaces_remain_listed() -> None:
    spec = _spec()

    for required in (
        "Slice 4 does not implement",
        "`count(Any field)` behavior change",
        "`count(Enum field)` behavior change",
        "broad `count(expression)`",
        "`count_if(predicate)`",
        "broad `count_distinct(expression)`",
        "`count_distinct(Json/Bytes/Any/Enum)`",
        "`min/max(UUID)`",
        "`min/max(Enum)`",
        "`min/max(Json/Bytes/Any)`",
        "Enum ordering metadata implementation",
        "UUID ordering metadata implementation",
        "`Any` refinement",
        "Json path/type semantics",
        "Bytes operators/literals/encoding",
        "native DB metadata pull",
        "storage/DDL/runtime behavior",
        "parser/AST/grammar/generated changes",
        "semantic/IR/SQL/CLI/JSON behavior changes",
        "fixtures/goldens changes",
        "scripts/workflows/package/release changes",
    ):
        assert required in spec, required


def test_future_prerequisites_and_public_surface_lock_are_documented() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    spec = _spec()

    for required in (
        "Any later behavior implementation requires a separate Gate 1 and Gate 2",
        "SQL portability proof",
        "fixture/golden policy",
        "public output compatibility",
        "diagnostic policy",
        "release non-authorization",
        "SQL `NULL` versus JSON literal `null`",
        "ordering, collation, normalization, serialization, and metadata ownership",
        "Enum scalar behavior and order metadata",
        "UUID ordering metadata and fail-closed/warning policy",
        "`Any` refinement and capability ownership",
        "Json path/type behavior",
        "Bytes literal, encoding, and operator behavior",
        "source/compiler behavior unchanged",
        "grammar and generated parser inventory unchanged",
        "semantic behavior unchanged",
        "IR behavior unchanged",
        "SQL behavior unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in spec, required

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)


def test_forbidden_surfaces_and_phase38_plan_remain_unchanged() -> None:
    changed_paths = {_status_path(line) for line in _git_status()}

    assert changed_paths <= ALLOWED_SLICE4_CHANGED_PATHS
    assert (
        _git_status_for(
            (
                "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md",
            )
        )
        == ""
    )

    for changed_path in changed_paths:
        for forbidden in FORBIDDEN_DIFF_PATHS:
            assert not _path_matches(changed_path, forbidden), changed_path
