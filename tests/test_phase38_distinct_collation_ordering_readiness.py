from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = REPO_ROOT / "docs/spec/phase38-distinct-collation-ordering-readiness-v1.md"
PHASE38_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md"
)
TYPE_CAPABILITY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-type-capability-matrix-contract-v1.md"
)
BOUNDARY_TYPES_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-boundary-types-capability-contract-v1.md"
)
COUNT_FAMILY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-count-family-semantics-contract-v1.md"
)
COUNT_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md"
)
MIN_MAX_SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"
FILTER_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
SCALAR_MATRIX_SPEC_PATH = REPO_ROOT / "docs/spec/expanded-scalar-operator-matrix-v1.md"
DECIMAL_CARRIER_SPEC_PATH = (
    REPO_ROOT / "docs/spec/decimal-precision-scale-carrier-mvp-decision-v1.md"
)
ANY_BYTES_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/any-bytes-json-support-posture-v1.md"
ENUM_SPEC_PATH = REPO_ROOT / "docs/spec/enum-support-resolution-v1.md"
UUID_SPEC_PATH = REPO_ROOT / "docs/spec/uuid-support-completion-v1.md"

PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE36_ANY_BYTES_JSON_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_any_bytes_json_support_posture.py"
)
PHASE36_ENUM_TEST_PATH = REPO_ROOT / "tests/test_phase36_enum_support_resolution.py"
PHASE36_UUID_TEST_PATH = REPO_ROOT / "tests/test_phase36_uuid_support_completion.py"
PHASE36_DECIMAL_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py"
)
PHASE37_CURRENT_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_current_aggregate_matrix.py"
)
PHASE37_COUNT_DISTINCT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_count_distinct_expression_widening_boundary.py"
)
PHASE37_MIN_MAX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_min_max_expression_boundary.py"
)
PHASE37_FILTER_DISTINCT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py"
)

SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
POSTGRES_SQL_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_SQL_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE5_CHANGED_PATHS = {
    "docs/spec/phase38-distinct-collation-ordering-readiness-v1.md",
    "tests/test_phase38_distinct_collation_ordering_readiness.py",
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


def _combined_readiness_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            SPEC_PATH,
            PHASE38_PLAN_PATH,
            TYPE_CAPABILITY_SPEC_PATH,
            BOUNDARY_TYPES_SPEC_PATH,
            COUNT_FAMILY_SPEC_PATH,
            COUNT_DISTINCT_SPEC_PATH,
            MIN_MAX_SPEC_PATH,
            FILTER_DISTINCT_SPEC_PATH,
            FREEZE_SPEC_PATH,
            SCALAR_MATRIX_SPEC_PATH,
            DECIMAL_CARRIER_SPEC_PATH,
            ANY_BYTES_JSON_SPEC_PATH,
            ENUM_SPEC_PATH,
            UUID_SPEC_PATH,
            PHASE31_MATRIX_TEST_PATH,
            PHASE36_ANY_BYTES_JSON_TEST_PATH,
            PHASE36_ENUM_TEST_PATH,
            PHASE36_UUID_TEST_PATH,
            PHASE36_DECIMAL_TEST_PATH,
            PHASE37_CURRENT_MATRIX_TEST_PATH,
            PHASE37_COUNT_DISTINCT_TEST_PATH,
            PHASE37_MIN_MAX_TEST_PATH,
            PHASE37_FILTER_DISTINCT_TEST_PATH,
            SEMANTIC_AGGREGATES_PATH,
            POSTGRES_SQL_PATH,
            MYSQL_SQL_PATH,
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


def test_spec_exists_and_records_slice5_guardrail() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 38 Distinct Collation Ordering Readiness v1",
        "Phase 38 Slice 5 is Distinct / Collation / Ordering Readiness",
        "docs/spec/static-audit/tests-only",
        "authorizes no behavior change",
        "does not add or change source/compiler behavior",
        "grammar, generated ANTLR files",
        "semantic behavior, IR behavior, SQL lowering",
        "CLI behavior, JSON v1, Project JSON v2",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_current_count_distinct_matrix_is_documented() -> None:
    evidence = _combined_readiness_evidence()

    for required in (
        "`count_distinct(field)` | Accepted for direct fields whose resolved type is `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, or `UUID`",
        "`count_distinct(source.field)` | Accepted for supported single-input qualified direct fields",
        "result is `Int not null`",
        "def is_supported_count_distinct_argument",
        '"Bool"',
        '"Int"',
        '"Float"',
        '"Decimal"',
        '"Text"',
        '"Date"',
        '"Timestamp"',
        '"UUID"',
        "count_distinct` over `Any`, `Bytes`, `Json`, and Enum remains `PIE-S2314`",
        "SQL-style `count(distinct field)` | Not Pietto source syntax",
        "parser-rejected with `PIE-P1000`",
    ):
        assert required in evidence, required


def test_current_min_max_matrix_is_documented() -> None:
    evidence = _combined_readiness_evidence()

    for required in (
        "`min(field)` / `max(field)` | Accepted for direct fields whose resolved type is `Int`, `Float`, `Decimal`, `Date`, or `Timestamp`",
        "`min(source.field)` / `max(source.field)` | Accepted for supported single-input qualified direct fields",
        "result is nullable same type",
        "def is_supported_extrema_argument",
        'for name in ("Int", "Float", "Decimal", "Date", "Timestamp")',
        "`min/max(Text|Bool|UUID|Enum|Json|Bytes|Any|Unknown)`",
        "`min/max(expression)` | Future only",
        "Broad `min(expression)` / `max(expression)` remains deferred and fail-closed today",
        "Unsupported `min/max(expression)` shapes must fail closed",
        "`PIE-S2315`",
        "`PIE-S2314`",
    ):
        assert required in evidence, required


def test_readiness_vocabulary_is_documented() -> None:
    spec = _spec()

    for required in (
        "`distinct-compatible`",
        "`equality-comparable`",
        "`collation-dependent`",
        "`serialization-dependent`",
        "`orderable`",
        "`dialect-lowerable`",
        "`metadata-backed`",
        "`deterministic transform`",
        "`normalization policy`",
        "`stable ordering policy`",
        "`count_distinct` readiness requires equality/distinct semantics",
        "`min/max` readiness requires stable ordering semantics",
        "Generic comparison/order paths are not enough",
    ):
        assert required in spec, required


def test_count_distinct_readiness_matrix_and_caveats_are_locked() -> None:
    spec = _spec()

    for required in (
        "| `Bool` | Current direct `count_distinct(Bool)` accepted",
        "| `Int` | Current direct `count_distinct(Int)` accepted",
        "| `Float` | Current direct `count_distinct(Float)` accepted",
        "NaN and signed-zero policy",
        "| `Decimal` | Current direct `count_distinct(Decimal)` accepted",
        "Decimal precision-scale carrier",
        "| `Text` | Current direct `count_distinct(Text)` and lower/trim Text chains accepted",
        "Text collation, Unicode normalization, locale-sensitive folding",
        "| `Date` | Current direct `count_distinct(Date)` accepted",
        "| `Timestamp` | Current direct `count_distinct(Timestamp)` accepted",
        "| `UUID` | Current direct `count_distinct(UUID)` accepted under `limited_frozen`",
        "UUID metadata, storage, equality portability",
        "| Enum | Current `count_distinct(Enum)` rejected with `PIE-S2314`",
        "| `Json` | Current `count_distinct(Json)` rejected with `PIE-S2314`",
        "Json serialization/equality",
        "| `Bytes` | Current `count_distinct(Bytes)` rejected with `PIE-S2314`",
        "Bytes serialization, encoding",
        "| `Any` | Current `count_distinct(Any)` rejected with `PIE-S2314`",
        "not dynamic typing",
        "| `Unknown` | No stable distinct capability",
    ):
        assert required in spec, required


def test_min_max_readiness_matrix_and_caveats_are_locked() -> None:
    spec = _spec()

    for required in (
        "| `Int` | Current direct `min/max(Int)` accepted",
        "| `Float` | Current direct `min/max(Float)` accepted",
        "NaN and signed-zero ordering policy",
        "| `Decimal` | Current direct `min/max(Decimal)` accepted",
        "Decimal precision-scale carrier, precision propagation",
        "| `Date` | Current direct `min/max(Date)` accepted",
        "| `Timestamp` | Current direct `min/max(Timestamp)` accepted",
        "| `Text` | Current `min/max(Text)` rejected with `PIE-S2314`",
        "collation-dependent ordering",
        "| `Bool` | Current `min/max(Bool)` rejected with `PIE-S2314`",
        "| `UUID` | Current `min/max(UUID)` rejected/deferred",
        "UUID version/order metadata",
        "| Enum | Current `min/max(Enum)` rejected with `PIE-S2314`",
        "declaration/native/custom order metadata",
        "| `Json` | Current `min/max(Json)` rejected with `PIE-S2314`",
        "| `Bytes` | Current `min/max(Bytes)` rejected with `PIE-S2314`",
        "| `Any` | Current `min/max(Any)` rejected with `PIE-S2314`",
        "| `Unknown` | No stable ordering capability",
        "Semantic ordering must remain separate from storage ordering",
    ):
        assert required in spec, required


def test_lower_trim_text_chain_boundary_is_preserved() -> None:
    evidence = _combined_readiness_evidence()

    for required in (
        "`count_distinct(lower/trim Text chain)`",
        "chains made only of `lower(...)` and `trim(...)`",
        "exactly one `Text` field leaf",
        "count_distinct(lower(field))",
        "count_distinct(trim(field))",
        "count_distinct(lower(trim(field)))",
        "count_distinct(trim(lower(field)))",
        "repeated or nested `lower` / `trim` chains",
        "count_distinct(lower(source.field))",
        "does not authorize broad `count_distinct(expression)`",
        "count_distinct(len(status))",
        'count_distinct(matches(status, "x"))',
        "count_distinct(lower(status) + trim(status))",
        "count_distinct(lower(amount))",
        "nested aggregates",
        "aggregate projection composition",
        '_COUNT_DISTINCT_TRANSFORM_NAMES = frozenset({"lower", "trim"})',
        "def _is_count_distinct_text_transform_argument",
    ):
        assert required in evidence, required


def test_sql_syntax_modifier_and_window_deferrals_are_preserved() -> None:
    evidence = _combined_readiness_evidence()

    for required in (
        "SQL-style `count(distinct field)`",
        "generic `DISTINCT` syntax",
        "aggregate filters / SQL `FILTER (WHERE ...)`",
        "aggregate internal ordering",
        "`WITHIN GROUP`",
        "window functions / `OVER (...)`",
        "`count(*)` source syntax",
        "directly imported SQL modifier syntax",
        "generic aggregate modifiers",
        "modifier-like aggregate arguments",
        "Current row-level `where:` is not aggregate `FILTER`",
        "Current `satisfying:` is the only result-predicate user surface",
        "Current grouped `order by:` is result-level selected-output-name ordering",
        "value = count(distinct customer_id)",
        "value = sum(amount) FILTER (WHERE amount > 0)",
        "value = sum(amount) over (region)",
        "value = sum(amount) within group (order by amount)",
    ):
        assert required in evidence, required


def test_deferred_surfaces_future_prerequisites_and_public_lock_are_documented() -> (
    None
):
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    spec = _spec()

    for required in (
        "Slice 5 does not implement",
        "broad `count_distinct(expression)`",
        "`count(distinct field)`",
        "generic `DISTINCT` syntax",
        "`count_distinct(Json/Bytes/Any/Enum)`",
        "`min/max(Text)`",
        "`min/max(UUID)`",
        "`min/max(Enum)`",
        "`min/max(Json/Bytes/Any)`",
        "`min/max(expression)`",
        "new collation policy",
        "new normalization policy",
        "new serialization policy",
        "UUID ordering metadata implementation",
        "Enum ordering metadata implementation",
        "Decimal precision-scale carrier",
        "Float NaN/signed-zero policy implementation",
        "parser/AST/grammar/generated changes",
        "semantic/IR/SQL/CLI/JSON behavior changes",
        "fixtures/goldens changes",
        "scripts/workflows/package/release changes",
        "Any later behavior implementation requires a separate Gate 1 and Gate 2",
        "SQL portability proof",
        "public output compatibility",
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

    assert changed_paths <= ALLOWED_SLICE5_CHANGED_PATHS
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
