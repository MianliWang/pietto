from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-21-group-by-contract-planning.md"


def _read() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized() -> str:
    return " ".join(_read().split())


def test_phase21_slice1_plan_exists() -> None:
    assert PLAN_PATH.is_file()


def test_trusted_phase20_baseline_is_recorded() -> None:
    plan = _normalized()

    for required in (
        "HEAD: `e67bf35cc130332aeb786a913fa5d76dac00fca9`",
        "no-GROUP `count()`, `sum(field)`, and `avg(field)` aggregate MVP is complete",
        "semantic validation, Semantic IR lowering, PostgreSQL SQL lowering, and MySQL SQL lowering are complete",
        "reviewed SQL goldens and the Phase 20 completion audit are complete",
    ):
        assert required in plan


def test_core_language_strategic_priority_is_recorded() -> None:
    plan = _normalized()

    for required in (
        "Pietto prioritizes core language capability",
        "powerful, concise, easy-to-use, safe, typed, SQL-native DSL",
        "Syntax design quality is central",
        "diagnostic-first",
        "fail-closed",
    ):
        assert required in plan


def test_required_candidate_directions_are_compared() -> None:
    plan = _normalized()

    for required in (
        "GROUP BY aggregate syntax and semantic contract",
        "GROUP BY implementation MVP",
        "Result predicate / HAVING-like design",
        "Aggregate expression arguments",
        "Relationship-driven safe composition / JOIN planning",
        "Nested table / structured result planning",
        "Project / multi-file language organization",
        "CLI/docs/examples usability fallback",
    ):
        assert required in plan


def test_group_by_contract_planning_is_selected_and_implementation_deferred() -> None:
    plan = _normalized()

    for required in (
        "Phase 21 selects **GROUP BY aggregate syntax and semantic contract** as the next core language direction",
        "This decision does not implement GROUP BY",
        "Implementation is explicitly deferred",
        "Contract planning only",
        "separately authorized",
    ):
        assert required in plan


def test_future_slice_sequence_is_recorded() -> None:
    plan = _normalized()

    for required in (
        "Slice 1: Candidate Decision**: complete",
        "Slice 2: Syntax And Clause-Scope Contract**: complete as docs/audit only",
        "Slice 3: Semantic / IR / SQL / Diagnostics Contract**: current docs/audit-only slice",
        "Slice 4: Parser + AST parse-only implementation",
        "Slice 5: Semantic grouped relation validation and grouped output schema",
        "Slice 6: IR group key lowering",
        "Slice 7: PostgreSQL/MySQL SQL lowering and goldens",
        "Slice 8: CLI / invalid-shape hardening / no-regression checks",
        "Slice 9: GROUP BY completion audit",
    ):
        assert required in plan

    assert "Slice 4: Completion Audit And Status Lock" not in plan


def test_source_syntax_constraints_are_preserved() -> None:
    plan = _normalized()

    for required in (
        "`source name: Shape is connector`",
        "`alias = expression` for select aliases",
        "no Pietto source-level `AS`",
        "no `source name: Shape = connector` syntax",
    ):
        assert required in plan


def test_relationship_metadata_remains_read_only() -> None:
    plan = _normalized()

    for required in (
        "Relationship metadata remains read-only metadata and not query behavior",
        "relationship-driven query behavior",
        "JOIN or relation composition",
    ):
        assert required in plan


def test_forbidden_surfaces_are_deferred_or_unchanged() -> None:
    plan = _normalized()

    for required in (
        "adds no grammar/generated, AST, semantic, IR, SQL, CLI, JSON, fixture, golden, dependency, CI, runtime, UI, LSP, policy DSL, or database behavior change",
        "grammar or source syntax changes",
        "generated ANTLR changes",
        "parser or AST changes",
        "semantic model changes",
        "Semantic IR model, export, builder, or lowering changes",
        "PostgreSQL or MySQL SQL renderer changes",
        "CLI, JSON, or public API changes",
        "fixture, SQL golden, or `scripts/check_goldens.py` changes",
        "dependency, package, lockfile, or CI changes",
        "runtime or database execution",
        "UI, playground, or LSP implementation",
        "policy DSL or runtime security implementation",
    ):
        assert required in plan


def test_deferred_non_core_and_aggregate_features_are_recorded() -> None:
    plan = _normalized()

    for required in (
        "SQL HAVING user syntax",
        "`satisfying`, `filter`, post-select `where`, or `such that` implementation",
        "aggregate expression argument implementation",
        "Decimal aggregate semantics",
        "casts",
        "project configuration or multi-file implementation",
    ):
        assert required in plan


def test_plan_does_not_claim_group_by_is_implemented() -> None:
    plan = _normalized()

    forbidden_claims = (
        "GROUP BY is implemented",
        "implements GROUP BY",
        "GROUP BY implementation is complete",
        "Phase 21 implements GROUP BY",
    )
    for forbidden in forbidden_claims:
        assert forbidden not in plan
