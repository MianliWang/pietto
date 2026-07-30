from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    ALLOWED_SLICE3_CHANGED_PATHS as PHASE39_REPAIR_CHANGED_PATHS,
)
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = REPO_ROOT / "docs/spec/phase38-type-capability-matrix-contract-v1.md"
PHASE38_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md"
)
COUNT_FAMILY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-count-family-semantics-contract-v1.md"
)
SCALAR_MATRIX_SPEC_PATH = REPO_ROOT / "docs/spec/expanded-scalar-operator-matrix-v1.md"
ANY_BYTES_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/any-bytes-json-support-posture-v1.md"
ENUM_SPEC_PATH = REPO_ROOT / "docs/spec/enum-support-resolution-v1.md"
UUID_SPEC_PATH = REPO_ROOT / "docs/spec/uuid-support-completion-v1.md"
DECIMAL_CARRIER_SPEC_PATH = (
    REPO_ROOT / "docs/spec/decimal-precision-scale-carrier-mvp-decision-v1.md"
)
COUNT_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md"
)
MIN_MAX_SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"

PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE36_SCALAR_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_expanded_scalar_operator_matrix.py"
)
PHASE36_ANY_BYTES_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_any_bytes_json_support_posture.py"
)
PHASE36_ENUM_TEST_PATH = REPO_ROOT / "tests/test_phase36_enum_support_resolution.py"
PHASE36_UUID_TEST_PATH = REPO_ROOT / "tests/test_phase36_uuid_support_completion.py"
PHASE36_DATETIME_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_datetime_time_interval_boundary.py"
)
PHASE36_DECIMAL_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py"
)
PHASE37_COUNT_DISTINCT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_count_distinct_expression_widening_boundary.py"
)
PHASE37_MIN_MAX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_min_max_expression_boundary.py"
)

SEMANTIC_CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
SEMANTIC_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE3_CHANGED_PATHS = {
    "docs/spec/phase38-type-capability-matrix-contract-v1.md",
    "tests/test_phase38_type_capability_matrix_contract.py",
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


def _combined_capability_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            SPEC_PATH,
            PHASE38_PLAN_PATH,
            COUNT_FAMILY_SPEC_PATH,
            SCALAR_MATRIX_SPEC_PATH,
            ANY_BYTES_JSON_SPEC_PATH,
            ENUM_SPEC_PATH,
            UUID_SPEC_PATH,
            DECIMAL_CARRIER_SPEC_PATH,
            COUNT_DISTINCT_SPEC_PATH,
            MIN_MAX_SPEC_PATH,
            PHASE31_MATRIX_TEST_PATH,
            PHASE36_SCALAR_MATRIX_TEST_PATH,
            PHASE36_ANY_BYTES_JSON_TEST_PATH,
            PHASE36_ENUM_TEST_PATH,
            PHASE36_UUID_TEST_PATH,
            PHASE36_DATETIME_TEST_PATH,
            PHASE36_DECIMAL_TEST_PATH,
            PHASE37_COUNT_DISTINCT_TEST_PATH,
            PHASE37_MIN_MAX_TEST_PATH,
            SEMANTIC_CATALOG_PATH,
            SEMANTIC_MODEL_PATH,
            SEMANTIC_AGGREGATES_PATH,
            SEMANTIC_EXPRESSIONS_PATH,
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


def test_spec_exists_and_records_slice3_guardrail() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 38 Type Capability Matrix Contract v1",
        "Phase 38 Slice 3 is Type Capability Matrix Contract",
        "docs/spec/static-audit/tests-only",
        "authorizes no behavior change",
        "does not add or change source/compiler behavior",
        "grammar, generated ANTLR files",
        "semantic behavior, IR behavior, SQL lowering",
        "CLI behavior, JSON v1, Project JSON v2",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_current_repo_derived_capability_inventory_is_grounded() -> None:
    evidence = _combined_capability_evidence()

    for required in (
        "`src/pietto/semantic/catalog.py` defines `Any`, `Bool`, `Bytes`, `Date`, `Decimal`, `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`",
        "`src/pietto/semantic/catalog.py` defines `lower(Text)`, `trim(Text)`, `len(Text)`, and `matches(Text, Text)`",
        "`src/pietto/semantic/model.py` defines `TypeKind`, `EffectiveNullability`, `ValueTypeKind`, `ResolvedType`, and `ValueType`",
        "`src/pietto/semantic/aggregates.py` defines direct field support",
        "`src/pietto/semantic/expressions.py` defines current unary, binary, comparison, between, literal, call, and aggregate projection expression typing",
        'BuiltinFunction("lower", ("Text",), "Text")',
        'BuiltinFunction("trim", ("Text",), "Text")',
        'BuiltinFunction("len", ("Text",), "Int")',
        'BuiltinFunction("matches", ("Text", "Text"), "Bool")',
        "class TypeKind",
        "class EffectiveNullability",
        "class ValueTypeKind",
        "def is_supported_count_argument",
        "def is_supported_count_distinct_argument",
        "def is_supported_numeric_argument",
        "def is_supported_extrema_argument",
        "def _is_supported_sum_avg_numeric_expression_shape",
        "def _binary_arithmetic_result_type",
    ):
        assert required in evidence, required


def test_capability_vocabulary_is_contractual_not_behavioral() -> None:
    spec = _spec()

    for required in (
        "`lowerable`",
        "`projectable`",
        "`null-checkable`",
        "`countable`",
        "`numeric`",
        "`arithmetic-capable`",
        "`orderable`",
        "`equality-comparable`",
        "`distinct-compatible`",
        "`text-transform-capable`",
        "`collation-dependent`",
        "`serialization-dependent`",
        "`metadata-backed`",
        "`dialect-lowerable`",
        "`aggregate-compatible`",
        "does not define hash behavior",
        "supports `distinct-compatible`",
    ):
        assert required in spec, required


def test_current_scalar_type_capability_matrix_is_complete() -> None:
    spec = _spec()

    for required in (
        "| `Bool` | current builtin projection | generic yes | yes | yes | no | no | Bool `and` / `or` only",
        "| `Int` | current builtin projection | generic yes | yes | yes | yes; `avg(Int)` returns `Float` | yes | `+`, `-`, `*`, `%` with `Int`",
        "| `Float` | current builtin projection | generic yes | yes | yes | yes | yes | `+`, `-`, `*` with numeric promotion",
        "| `Decimal` | current builtin projection | generic yes | yes | yes | yes | yes | current `Decimal + Decimal` and `Decimal - Decimal` only",
        "| `Text` | current builtin projection | generic yes | yes | yes | no | no | no Text arithmetic",
        "| `Date` | current builtin temporal projection | generic yes | yes | yes | no | yes | no temporal arithmetic",
        "| `Timestamp` | current builtin temporal projection | generic yes | yes | yes | no | yes | no temporal arithmetic",
        "| `DateTime` | no builtin | no resolved field | no | no | no | no | no | no | no | unsupported/deferred, `PIE-S2002` |",
        "| `Time` | no builtin | no resolved field | no | no | no | no | no | no | no | unsupported/deferred, `PIE-S2002` |",
        "| `Interval` | no builtin | no resolved field | no | no | no | no | no | no | no | unsupported/deferred, `PIE-S2002` |",
        "| `UUID` | current `limited_frozen` projection | generic yes | yes | yes | no | no | no",
        "| Enum | metadata/projection readiness only | generic expression machinery, no Enum-specific contract | no, `PIE-S2314` | no, `PIE-S2314` | no | no | no",
        "| `Json` | current deferred builtin projection | generic yes | yes | no | no | no | no",
        "| `Bytes` | current deferred builtin projection | generic yes | yes | no | no | no | no",
        "| `Any` | current top/deferred projection | generic yes | no, `PIE-S2314` | no | no | no | no",
        "| `Unknown` | not accepted as known capability | no stable capability | no | no | no | no | no | no | no",
    ):
        assert required in spec, required


def test_aggregate_requirement_matrix_is_locked() -> None:
    spec = _spec()

    for required in (
        "`count()` | Current row-count aggregate",
        "SQL `COUNT(*)`, result `Int not null`, empty input returns `0`",
        "`count(field)` / `count(source.field)`",
        "resolved type must not be `Enum`, `Unknown`, or builtin `Any`",
        "future `count(expression)`",
        "dialect-lowerable expression and explicit SQL nullness semantics",
        "future `count_if(predicate)`",
        "`FALSE`, SQL `NULL`, and SQL `UNKNOWN` do not count",
        "`sum/avg(field)`",
        "Current direct numeric aggregate fields: `Int`, `Float`, `Decimal`",
        "bounded `sum/avg(expression)`",
        "Int/Float numeric literal leaves allowed only in approved non-literal-only forms",
        "`min/max(field)`",
        "Current direct extrema subset: `Int`, `Float`, `Decimal`, `Date`, `Timestamp`",
        "`count_distinct(field)`",
        "Current distinct-compatible subset: `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, `UUID`",
        "`count_distinct(lower/trim Text chain)`",
        "future broad `count_distinct(expression)`",
        "collation/normalization, serialization",
    ):
        assert required in spec, required


def test_countability_is_separate_from_numeric_orderable_and_distinct() -> None:
    spec = _spec()

    for required in (
        "Countability is weaker than numeric, orderable, and distinct compatibility",
        "Current direct `count(field)` counts SQL non-null values",
        "arithmetic support for `sum` / `avg`",
        "orderability or `min` / `max`",
        "equality and distinct compatibility for `count_distinct`",
        "stable group-key or `satisfying` semantics",
        "native database metadata, runtime behavior",
        "This distinction matters most for `Json`, `Bytes`, and `UUID`",
    ):
        assert required in spec, required


def test_any_json_bytes_enum_uuid_boundaries_are_documented() -> None:
    spec = _spec()

    for required in (
        "`Any`: keep non-countable, non-arithmetic, non-orderable, and",
        "Future countability must be explicit lowerable-count policy",
        "`Json`: keep direct `count(Json field)` accepted",
        "SQL field nullness separately from JSON literal `null`",
        "`Bytes`: keep direct `count(Bytes field)` accepted",
        "Do not add binary literal, encoding, comparison, distinct, ordering",
        "Enum: keep `metadata_only`; `count(Enum field)` remains semantic",
        "`UUID`: keep `limited_frozen`; projection, direct `count(UUID field)`, and",
        "direct `count_distinct(UUID field)` remain current",
        "Do not add UUID ordering, `min/max`, native behavior",
    ):
        assert required in spec, required


def test_decimal_float_text_readiness_caveats_are_documented() -> None:
    evidence = _combined_capability_evidence()

    for required in (
        "internal precision-scale carrier implemented by Phase 41",
        "Phase 41 implements Decimal precision-scale semantic validation and a private",
        "`Decimal(12, 2)` now validates as a logical Decimal type form",
        "internal `DecimalPrecisionScale` facts",
        "`Decimal()` remains compatible",
        "Non-Decimal type arguments remain the current compatibility surface",
        "metadata/explain precision-scale display",
        "Decimal literals, multiplication, division, mixed Decimal promotion",
        "Float currently participates in direct `count_distinct(Float)` and direct",
        "`min/max(Float)`",
        "no Float-specific distinct/order caveat beyond",
        "Text currently participates in direct `count_distinct(Text)`",
        "lower/trim Text-chain subset",
        "Text collation, Unicode normalization, locale-sensitive folding",
        "backend-specific equality rules remain deferred",
    ):
        assert required in evidence, required


def test_generic_comparison_ordering_and_dialect_boundaries_are_preserved() -> None:
    evidence = _combined_capability_evidence()

    for required in (
        "Generic known-child comparison behavior currently produces `Bool UNKNOWN`",
        "risky shared paths for `UUID`, Enum, `Any`, `Bytes`, `Json`",
        "not stable type-specific compatibility guarantees",
        "does not promote those generic paths into stable UUID comparison",
        "Enum SQL scalar comparison",
        "Dialect-lowerability means an already accepted Pietto expression",
        "deterministic SQL lowering in the current PostgreSQL and private MySQL emitters",
        "backend execution",
        "runtime checks",
        "schema introspection",
        "native DB metadata",
        "Metadata-backed types remain distinct from native database behavior",
    ):
        assert required in evidence, required


def test_deferred_and_prohibited_surfaces_remain_closed() -> None:
    spec = _spec()

    for required in (
        "Slice 3 does not implement",
        "new type capabilities or changed aggregate acceptance",
        "`count(expression)`, `count(constant)`, `count(1)`, or",
        "`count_if(predicate)`",
        "`row_count()` / `count_row()`",
        "`count(distinct field)` or generic aggregate modifiers",
        "broad `count_distinct(expression)`",
        "broad `sum/avg(expression)` beyond current bounded behavior",
        "`min/max(expression)`",
        "generic aggregate filters",
        "window functions",
        "nested aggregates",
        "aggregate projection composition",
        "new collation, normalization, serialization, native DB metadata",
        "parser/AST/grammar/generated behavior changes",
        "semantic, IR, SQL, CLI/JSON, fixture/golden",
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


def test_forbidden_surfaces_and_phase38_plan_remain_unchanged() -> None:
    changed_paths = {_status_path(line) for line in _git_status()}

    assert (changed_paths <= PHASE39_REPAIR_CHANGED_PATHS) or _slice5_gate2()
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
            if changed_path not in PHASE39_REPAIR_CHANGED_PATHS:
                assert (
                    not _path_matches(changed_path, forbidden)
                ) or _slice5_gate2(), changed_path
