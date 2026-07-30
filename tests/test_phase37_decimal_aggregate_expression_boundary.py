from __future__ import annotations

import subprocess
from fnmatch import fnmatchcase
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    ALLOWED_SLICE3_CHANGED_PATHS,
    _non_slice3_repair_diff_paths,
    _non_slice3_repair_status_paths,
)
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = REPO_ROOT / "docs/spec/phase37-decimal-aggregate-expression-boundary-v1.md"
PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
DECIMAL_CARRIER_SPEC_PATH = (
    REPO_ROOT / "docs/spec/decimal-precision-scale-carrier-mvp-decision-v1.md"
)
EXPANDED_SCALAR_SPEC_PATH = (
    REPO_ROOT / "docs/spec/expanded-scalar-operator-matrix-v1.md"
)
COUNT_EXPRESSION_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-expression-mvp-decision-v1.md"
)
COUNT_DISTINCT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md"
)
MIN_MAX_SPEC_PATH = REPO_ROOT / "docs/spec/phase37-min-max-expression-boundary-v1.md"
PHASE24_CONTRACT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase24_decimal_aggregate_contract.py"
)
PHASE24_SEMANTICS_TEST_PATH = (
    REPO_ROOT / "tests/test_phase24_decimal_aggregate_semantics.py"
)
PHASE24_IR_TEST_PATH = REPO_ROOT / "tests/test_phase24_decimal_aggregate_ir.py"
PHASE24_SQL_TEST_PATH = REPO_ROOT / "tests/test_phase24_decimal_aggregate_sql.py"
PHASE26_DECIMAL_SCALAR_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_decimal_scalar_expression_semantics.py"
)
PHASE26_AGGREGATE_SEMANTICS_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_semantics.py"
)
PHASE26_AGGREGATE_IR_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_ir.py"
)
PHASE26_AGGREGATE_SQL_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_sql.py"
)
PHASE28_SEMANTICS_TEST_PATH = (
    REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_semantics.py"
)
PHASE31_NUMERIC_BOUNDARY_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_numeric_promotion_decimal_boundary.py"
)
PHASE31_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase31_aggregate_result_matrix_hardening.py"
)
PHASE36_DECIMAL_CARRIER_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py"
)
PHASE36_SCALAR_MATRIX_TEST_PATH = (
    REPO_ROOT / "tests/test_phase36_expanded_scalar_operator_matrix.py"
)
PHASE36_COMPLETION_TEST_PATH = REPO_ROOT / "tests/test_phase36_completion_audit.py"
AGGREGATES_SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
POSTGRES_SQL_SOURCE_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_SQL_SOURCE_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md",
    "src",
    "grammar",
    "src/pietto/generated",
    "fixtures",
    "tests/fixtures",
    "tests/_static_audit_helpers.py",
    "scripts",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
)

IN_PROGRESS_PHASE37_STATIC_AUDIT_PATTERNS = (
    "docs/spec/phase37-*.md",
    "tests/test_phase37_*.py",
)


def _spec() -> str:
    return _normalized(SPEC_PATH)


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


def _is_in_progress_phase37_static_audit_path(path: str) -> bool:
    return any(
        fnmatchcase(path, pattern)
        for pattern in IN_PROGRESS_PHASE37_STATIC_AUDIT_PATTERNS
    )


def test_phase37_slice8_spec_exists_and_has_required_sections() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 37 Decimal Aggregate Expression Boundary v1",
        "## Status",
        "## Current Accepted Decimal Direct-field Aggregate Surface",
        "## Current Accepted Bounded Decimal Sum/Avg Expression Surface",
        "## Deferred And Prohibited Decimal Aggregate-expression Surfaces",
        "## Phase 36 Decimal Precision-scale Carrier Deferral",
        "## Phase 37 Expression Boundary Interaction",
        "## SQL Portability And Fail-closed Diagnostics",
        "## Public Output And Release Stability",
        "Phase 37 Slice 8 is `Decimal Aggregate Expression Boundary`",
        "docs/spec/static-audit only",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_slice8_authorizes_no_behavior_source_or_public_surface_changes() -> None:
    spec = _spec()

    for required in (
        "Slice 8 is docs/spec/static-audit only with no behavior change",
        "does not change source/compiler behavior",
        "source syntax",
        "grammar",
        "generated ANTLR files",
        "parser behavior",
        "AST behavior",
        "semantic behavior",
        "IR behavior",
        "SQL lowering",
        "CLI behavior",
        "JSON v1",
        "Project JSON v2",
        "Semantic Metadata Artifact v1 schema or output",
        "diagnostics",
        "fixtures",
        "goldens",
        "scripts",
        "workflows",
        "package metadata",
        "lockfiles",
        "package version",
        "tags",
        "release",
        "publish/upload",
        "signing",
        "attestation",
    ):
        assert required in spec, required

    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)


def test_current_decimal_direct_field_aggregate_surface_is_locked() -> None:
    spec = _spec()
    evidence = " ".join(
        (
            spec,
            _normalized(FREEZE_SPEC_PATH),
            _read(PHASE24_CONTRACT_TEST_PATH),
            _read(PHASE24_SEMANTICS_TEST_PATH),
            _read(PHASE24_IR_TEST_PATH),
            _read(PHASE24_SQL_TEST_PATH),
            _read(AGGREGATES_SOURCE_PATH),
            _read(POSTGRES_SQL_SOURCE_PATH),
            _read(MYSQL_SQL_SOURCE_PATH),
        )
    )

    for required in (
        "`sum(Decimal field)` / `sum(source.Decimal field)`",
        "`avg(Decimal field)` / `avg(source.Decimal field)`",
        "`min(Decimal field)` / `min(source.Decimal field)`",
        "`max(Decimal field)` / `max(source.Decimal field)`",
        "result is nullable logical `Decimal`",
        "`sum(Decimal)`",
        "`avg(Decimal)`",
        "`min(Decimal)`",
        "`max(Decimal)`",
        "total_amount = sum(amount)",
        "average_amount = avg(amount)",
        "smallest_amount = min(amount)",
        "largest_amount = max(amount)",
        "DECIMAL_NULLABLE_VALUE_TYPE = ValueType(",
        "_SUPPORTED_NUMERIC_AGGREGATE_ARGUMENT_TYPES",
        "_SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES",
    ):
        assert required in evidence, required


def test_current_bounded_decimal_sum_avg_expression_surface_is_locked() -> None:
    spec = _spec()
    evidence = " ".join(
        (
            spec,
            _normalized(FREEZE_SPEC_PATH),
            _read(PHASE26_DECIMAL_SCALAR_TEST_PATH),
            _read(PHASE26_AGGREGATE_SEMANTICS_TEST_PATH),
            _read(PHASE26_AGGREGATE_IR_TEST_PATH),
            _read(PHASE26_AGGREGATE_SQL_TEST_PATH),
            _read(PHASE31_NUMERIC_BOUNDARY_TEST_PATH),
            _read(PHASE31_MATRIX_TEST_PATH),
        )
    )

    for required in (
        "Current bounded Decimal `sum/avg` expression participation remains unchanged",
        "Decimal `+` and `-` scalar expression support only",
        "contains at least one direct input field leaf",
        "`sum(...)` and `avg(...)` aggregate-expression argument behavior",
        "value = sum(price + price)",
        "value = sum(price + discount)",
        "value = avg(price - discount)",
        "decimal_total = sum(price + price)",
        "decimal_average = avg(price - price)",
        "decimal_total_expr = sum(price + discount)",
        "decimal_average_expr = avg(price - discount)",
        "Decimal `+` and `-` remain accepted only for Decimal/Decimal operands",
    ):
        assert required in evidence, required


def test_decimal_precision_scale_carrier_and_public_output_remain_deferred() -> None:
    spec = _spec()
    evidence = " ".join(
        (
            spec,
            _normalized(DECIMAL_CARRIER_SPEC_PATH),
            _read(PHASE36_DECIMAL_CARRIER_TEST_PATH),
            _read(PHASE36_COMPLETION_TEST_PATH),
        )
    )

    for required in (
        "Decimal precision-scale carrier",
        "No precision/scale carrier exists",
        "Slice 8 does not authorize a private carrier skeleton",
        "`Decimal(12, 2)` generic `TypeExpr.arguments` do not create accepted precision/scale semantics",
        "public outputs expose no Decimal precision or scale fields",
        "test_public_outputs_expose_no_precision_scale_fields",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "package version remains `0.1.0`",
    ):
        assert required in evidence, required


def test_deferred_decimal_expression_surfaces_remain_prohibited() -> None:
    spec = _spec()
    evidence = " ".join(
        (
            spec,
            _normalized(EXPANDED_SCALAR_SPEC_PATH),
            _normalized(DEFERRED_REGISTER_PATH),
            _read(PHASE26_DECIMAL_SCALAR_TEST_PATH),
            _read(PHASE26_AGGREGATE_SEMANTICS_TEST_PATH),
            _read(PHASE28_SEMANTICS_TEST_PATH),
            _read(PHASE31_NUMERIC_BOUNDARY_TEST_PATH),
            _read(PHASE36_SCALAR_MATRIX_TEST_PATH),
        )
    )

    for required in (
        "Decimal literals",
        "literal-only aggregate args such as `sum(1)` / `avg(1)`",
        "Decimal multiplication",
        "Decimal division",
        "mixed Decimal promotion widening",
        "Decimal precision/scale propagation or output metadata",
        "backend/native DB Decimal metadata",
        "value = sum(1)",
        "value = avg(1)",
        "value = sum(price * discount)",
        "value = avg(price * price)",
        "value = sum(price + amount)",
        "value = sum(price + score)",
        "PIE-S2105",
        "PIE-S2315",
    ):
        assert required in evidence, required


def test_phase37_decimal_expression_widening_remains_deferred_only() -> None:
    spec = _spec()
    evidence = " ".join(
        (
            spec,
            _normalized(PHASE37_PLAN_PATH),
            _normalized(COUNT_EXPRESSION_SPEC_PATH),
            _normalized(COUNT_DISTINCT_SPEC_PATH),
            _normalized(MIN_MAX_SPEC_PATH),
        )
    )

    for required in (
        "Decimal expression support for `count(expression)`",
        "broad Decimal `count_distinct(expression)`",
        "Decimal `min/max(expression)` widening",
        "`count(expression)` remains a future candidate only and is not implemented",
        "broad `count_distinct(expression)` remains deferred",
        "`min(expression)` and `max(expression)` remain future candidates only",
        "Decimal precision-scale widening",
        "Decimal literal support",
        "Decimal multiplication support",
        "Decimal division support",
        "mixed Decimal promotion widening",
        "Decimal expressions",
        "Decimal literals",
        "Decimal multiplication/division",
    ):
        assert required in evidence, required


def test_sql_portability_and_fail_closed_diagnostic_posture_are_locked() -> None:
    spec = _spec()
    evidence = " ".join(
        (
            spec,
            _read(PHASE24_SQL_TEST_PATH),
            _read(PHASE26_AGGREGATE_SQL_TEST_PATH),
            _read(POSTGRES_SQL_SOURCE_PATH),
            _read(MYSQL_SQL_SOURCE_PATH),
        )
    )

    for required in (
        "Current PostgreSQL and private MySQL SQL lowering remains byte-compatible",
        "no casts",
        "no dialect precision promises",
        "no native Decimal metadata",
        "no fixture or golden updates",
        "Unsupported Decimal aggregate-expression shapes must remain diagnostic-first",
        "`PIE-S2105`",
        "`PIE-S2314`",
        "`PIE-S2315`",
        "Slice 8 adds no diagnostic code",
        "test_decimal_aggregate_goldens_lock_no_cast_function_shape",
        'SUM("amount")',
        "SUM(`amount`)",
        "value = sum(amount / tax)",
        "value = avg(price * price)",
    ):
        assert required in evidence, required


def test_forbidden_surfaces_are_not_modified_or_untracked() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)
    status_output = _git_status_for(FORBIDDEN_DIFF_PATHS)

    assert (_non_slice3_repair_diff_paths(diff_output) == set()) or _slice5_gate2()
    assert (_non_slice3_repair_status_paths(status_output) == set()) or _slice5_gate2()


def test_only_phase37_static_audit_files_are_changed_or_untracked() -> None:
    status_lines = _git_status()
    changed_paths = {line[3:] for line in status_lines}
    forbidden_paths = sorted(
        path
        for path in changed_paths
        if not _is_in_progress_phase37_static_audit_path(path)
    )

    assert (set(forbidden_paths) <= ALLOWED_SLICE3_CHANGED_PATHS) or _slice5_gate2()
