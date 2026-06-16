from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-22-min-max-aggregate-mvp.md"


def _read() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized() -> str:
    return " ".join(_read().split())


def test_phase22_slice1_plan_exists_and_records_baseline() -> None:
    assert PLAN_PATH.is_file()

    plan = _normalized()
    for required in (
        "Phase 22 Slice 1 is complete as candidate decision and contract work only",
        "HEAD: `669a568a27db7d2479b400e5e26a447caf7b295d`",
        "Phase 21 GROUP BY Aggregate MVP is complete",
        "parser and AST support for `group by:` is complete",
        "`RelationIR.group_keys` and PostgreSQL/MySQL `GROUP BY` lowering are complete",
        "reviewed GROUP BY SQL goldens, CLI text, JSON v1, `--output` hardening, and completion audit coverage are complete",
    ):
        assert required in plan


def test_slice1_forbidden_surface_boundary_is_explicit() -> None:
    plan = _normalized()

    for required in (
        "Slice 1 changes no grammar, generated ANTLR, AST, semantic production code, Semantic IR production code, SQL renderer, CLI behavior, JSON schema, fixture, golden, `scripts/check_goldens.py` inventory, dependency, lockfile, package metadata, CI, runtime/database behavior, UI, LSP, policy/security DSL, or relationship query behavior",
        "This decision does not implement `min` or `max`",
        "It records the future implementation contract so later slices can remain narrow and auditable",
    ):
        assert required in plan


def test_required_candidate_directions_are_compared_and_min_max_is_selected() -> None:
    plan = _normalized()

    for required in (
        "`min(field)` / `max(field)` aggregate MVP",
        "`count(field)` aggregate MVP",
        "`count_distinct(field)` or distinct aggregate design",
        "Aggregate expression arguments",
        "Filtered aggregate design",
        "Result predicate / HAVING-like design",
        "Date/time bucketing or grouping helper design",
        "Relationship-driven safe composition / JOIN planning",
        "Project/multi-file language organization fallback",
        "Phase 22 selects **`min(field)` / `max(field)` Aggregate MVP** as the next core language direction",
        "Best fallback if `min/max` proves too risky",
    ):
        assert required in plan


def test_min_max_future_contract_is_decision_complete() -> None:
    plan = _normalized()

    for required in (
        "direct aliased aggregate projections only",
        "`alias = min(field)`",
        "`alias = max(field)`",
        "no-GROUP `select:` aggregate projections",
        "grouped `select:` aggregate projections",
        "existing single-input qualified field arguments",
        "exactly one argument",
        "one direct bare field or existing single-input qualified field reference only",
        "projection aliases are not accepted as aggregate arguments",
        "nested aggregate calls are not accepted as aggregate arguments",
        "expression arguments remain deferred",
        "`Int`",
        "`Float`",
        "`Date`",
        "`Timestamp`",
        "`min(Int) -> Int nullable`",
        "`max(Float) -> Float nullable`",
        "`min(Date) -> Date nullable`",
        "`max(Timestamp) -> Timestamp nullable`",
        "The result is nullable because SQL aggregate extrema over an empty input or empty group are nullable",
    ):
        assert required in plan


def test_diagnostics_ir_sql_and_golden_contracts_are_locked() -> None:
    plan = _normalized()

    for required in (
        "`PIE-S2308` for invalid aggregate context",
        "`PIE-S2309` for wrong arity",
        "`PIE-S2310` for aggregate composition",
        "`PIE-S2311` for nested aggregate",
        "`PIE-S2312` for mixed no-GROUP aggregate and non-aggregate projections",
        "`PIE-S2313` for unaliased aggregate projections",
        "`PIE-S2314` for unsupported direct field argument type",
        "`PIE-S2315` for expression arguments",
        "add no new diagnostic code unless a later implementation slice finds a concrete diagnostic gap",
        "valid `min/max` calls lower to existing `AggregateCallIR`",
        "no new public IR node is needed for v1",
        "PostgreSQL renders `MIN(\"field\")` and `MAX(\"field\")`",
        "old SQL goldens must remain byte-stable",
        "new reviewed min/max fixtures and goldens instead of rewriting unrelated goldens",
    ):
        assert required in plan


def test_min_max_remains_out_of_scalar_builtin_catalog() -> None:
    plan = _normalized()

    for required in (
        "`min` and `max` remain aggregate names only, not scalar builtins",
        "They must not be added to the scalar `BUILTIN_FUNCTIONS` catalog",
    ):
        assert required in plan


def test_deferred_boundaries_cover_required_non_goals() -> None:
    plan = _normalized()

    for required in (
        "production `min` or `max` aggregate behavior",
        "`count(field)`",
        "distinct aggregates or `count_distinct(field)`",
        "aggregate expression arguments such as `sum(amount + tax)`",
        "aggregate filters",
        "result predicates, `satisfying`, post-select `where`, `such that`, or SQL `HAVING` user syntax",
        "grouped `order by`",
        "date/time bucketing helpers",
        "relationship-driven query behavior",
        "JOIN or relation composition",
        "project configuration or multi-file implementation",
        "`Text`, `Decimal`, `Bool`, `Bytes`, `Json`, `UUID`, or `Any` `min/max` semantics",
        "runtime/database execution",
        "connector execution or schema introspection",
        "UI, Web playground, or LSP implementation",
        "policy/security DSL or runtime security implementation",
    ):
        assert required in plan


def test_proposed_phase22_slice_sequence_is_recorded() -> None:
    plan = _normalized()

    for required in (
        "Slice 1: Candidate Decision And Min/Max Contract**: complete as docs/static-audit only",
        "Slice 2: Min/Max Semantic Validation And Row Schema**: future implementation slice",
        "Slice 3: Min/Max IR Lowering**: future implementation slice",
        "Slice 4: PostgreSQL/MySQL SQL Lowering And Goldens**: future implementation slice",
        "Slice 5: CLI/JSON/Output And Malformed IR Hardening**: future tests/audit slice",
        "Slice 6: Completion Audit And Status Lock**: future audit-only slice",
    ):
        assert required in plan


def test_slice1_does_not_claim_min_max_is_implemented() -> None:
    plan = _normalized()

    for forbidden in (
        "min/max is implemented",
        "implements min/max",
        "min/max implementation is complete",
        "Phase 22 implements min/max",
    ):
        assert forbidden not in plan
