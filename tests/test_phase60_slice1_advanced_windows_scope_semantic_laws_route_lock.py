from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md"
)

OWNER = "Advanced Windows And Phase 51–60 Readiness Checkpoint"
HEADINGS = (
    "Answer And Static Scope",
    "Starting Authority",
    "Live Existing Window Authority Audit",
    "Existing Phase 60 And Later Classification",
    "Authored Resolved Validated Target-Lowerable Stages",
    "Authorship Provenance And Effective Defaults",
    "Typed Lazy Frame Model",
    "Resolution Pipeline And Unit Semantics",
    "Structural Legality And Empty-frame Evidence",
    "Function Frame And Modifier Admissibility",
    "Named-window Scope And Monotonic DAG",
    "Occurrence Identity And Semantic Equivalence",
    "Cross-domain Stage Boundaries",
    "Capability-gated Lowering And Lineage Attachment",
    "Phase 51–60 Checkpoint Boundary",
    "Exact 13-slice Route",
    "Route Expansion Rule",
    "Later-owner And Readiness Ledger",
    "Future Test Compatibility Contract",
    "Reader Closure And Changed-path Lock",
    "Public Compatibility Release And Non-goals",
    "Gate Workflow Lifecycle And Publication Subject",
)
LIVE_AUTHORITY_PATHS = frozenset(
    {
        "docs/language.md",
        "grammar/Pietto.g4",
        "src/pietto/_project/model.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/package_graph.py",
        "src/pietto/_project/package_graph_inspection.py",
        "src/pietto/_project/row_dependency_graph.py",
        "src/pietto/_project/row_lineage.py",
        "src/pietto/_project/window_persistence.py",
        "src/pietto/_project/window_semantics.py",
        "src/pietto/_window_identity.py",
        "src/pietto/ast_builder.py",
        "src/pietto/ast_nodes.py",
        "src/pietto/ir/builder.py",
        "src/pietto/ir/lowering.py",
        "src/pietto/ir/model.py",
        "src/pietto/semantic/capability_facts.py",
        "src/pietto/semantic/capability_providers.py",
        "src/pietto/semantic/capability_windows.py",
        "src/pietto/semantic/expressions.py",
        "src/pietto/semantic/window_analysis.py",
        "src/pietto/semantic/window_input_analysis.py",
        "src/pietto/semantic/window_navigation_analysis.py",
        "src/pietto/semantic/window_order_analysis.py",
        "src/pietto/semantic/window_partition_analysis.py",
        "src/pietto/semantic/window_semantics.py",
        "src/pietto/sql/expressions.py",
        "src/pietto/sql/mysql_expressions.py",
        "src/pietto/sql/mysql_relations.py",
        "src/pietto/sql/relations.py",
    }
)
PROVENANCE_STATES = (
    "Whole frame omitted",
    "Shorthand end omitted",
    "`EXCLUDE` omitted",
    "Explicit default-equivalent syntax",
    "Locally authored component",
    "Inherited component",
    "Resolved effective default",
    "Not-applicable frame",
)
ROUTE = (
    ("1", "Scope / Semantic Laws / Route Lock"),
    ("2", "Authored-To-Resolved Window And Frame Model"),
    (
        "3",
        "Structural Legality, Function-Frame Policy, Empty-Frame Classification, And Stage/Nesting Rules",
    ),
    ("4", "ROWS Semantics And Lowering"),
    (
        "5",
        "RANGE Semantics, Direction-Aware Bounds, Structural ORDER BY/Type Seam, And Lowering",
    ),
    ("6", "GROUPS And Peer-Group Semantics And Lowering"),
    ("7", "EXCLUDE Semantics Across All Units"),
    ("8", "Query-Local Named-Window Scope And DAG Inheritance"),
    ("9", "Value/Navigation Modifiers"),
    (
        "10",
        "Capability-Gated Lowering, Lineage, Determinism/Private Inspection, And Semantic-Equivalence Readiness",
    ),
    ("11", "Real Authored Advanced-Window E2E"),
    ("12", "Differential Compatibility"),
    (
        "13",
        "Phase 51–60 Completion/Readiness Audit And Phase 61 Handoff",
    ),
)
CHECKPOINT_INPUTS = (
    "Aggregate / Grouped Project Output-Schema Foundation",
    "Core Type-System Capability Foundation",
    "Window Function Syntax And Capability Contract",
    "Import / Module / Export Readiness",
    "Semantic Package Asset Schema",
    "Capability Profile Static Schema And Declared Checking",
    "PostgreSQL Extension Signature-Catalog Readiness",
    "Project Explain / Portability / Public Metadata Readiness",
    "Package Graph And Lineage / Provenance Integration",
    OWNER,
)


def _read() -> str:
    return SPEC.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _tables(section: str) -> tuple[tuple[tuple[str, ...], ...], ...]:
    tables: list[tuple[tuple[str, ...], ...]] = []
    rows: list[tuple[str, ...]] = []
    for line in (*section.splitlines(), ""):
        if line.startswith("| "):
            if not line.startswith("| ---"):
                rows.append(tuple(cell.strip() for cell in line.strip("|").split("|")))
        elif rows:
            tables.append(tuple(rows))
            rows = []
    return tuple(tables)


def _normalized(section: str) -> str:
    return " ".join(section.split())


def test_owner_heading_inventory_static_scope_and_starting_authority_are_exact() -> (
    None
):
    document = _read()
    assert (
        tuple(
            line.removeprefix("## ")
            for line in document.splitlines()
            if line.startswith("## ")
        )
        == HEADINGS
    )
    answer = _section(document, "Answer And Static Scope")
    assert answer.count(OWNER) == 1
    assert _tables(answer)[0][1:] == (
        ("Production changes", "`0`"),
        ("Public behavior changes", "`0`"),
        ("Public schema changes", "`0`"),
        ("Grammar/generated changes", "`0`"),
        ("Golden changes", "`0`"),
        ("Package/build metadata changes", "`0`"),
        ("Workflow/validator changes", "`0`"),
        ("Slice 2 implementation", "`FORBIDDEN`"),
        ("Current version", "`0.1.0`"),
    )
    starting = _normalized(_section(document, "Starting Authority"))
    for evidence in (
        "852568c33ed4a6ad7d311d776f68f5971ab90dd5",
        "7f479de3b76e49cb028fb4463f0de86b66f1329c",
        "33158588908",
        "e6da1fbe6b18ad88ae3c09568ba1f7d0e76817d1",
        "33155753995",
        "Phase 59 = COMPLETED",
        "Validation/Test Performance Optimization Interlude = COMPLETED",
        "Phase 60 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in starting


def test_live_window_authority_is_exhaustively_classified_without_recreation() -> None:
    section = _section(_read(), "Live Existing Window Authority Audit")
    paths = frozenset(
        re.findall(r"`((?:docs|grammar|src)/[^`]+\.(?:g4|md|py))`", section)
    )
    assert paths == LIVE_AUTHORITY_PATHS
    assert all((REPO_ROOT / path).is_file() for path in paths)
    normalized = _normalized(section)
    for evidence in (
        "frame-free inline window implementation",
        "frames and named windows are absent",
        "rejects nested or same-stage window dependencies",
        "they authorize no advanced feature",
        "explicitly frame free",
        "no frame role exists",
        "must not migrate",
        "Slice 1 does not change it",
    ):
        assert evidence in normalized

    classified = _tables(
        _section(_read(), "Existing Phase 60 And Later Classification")
    )[0][1:]
    assert tuple(row[0] for row in classified) == (
        "Existing and retained",
        "Phase 60",
        "Later owner",
    )
    assert all(row[1] for row in classified)


def test_stages_provenance_defaults_and_lazy_typed_model_are_exact() -> None:
    stages = _tables(
        _section(_read(), "Authored Resolved Validated Target-Lowerable Stages")
    )[0][1:]
    assert tuple(row[0] for row in stages) == (
        "Authored",
        "Resolved",
        "Validated",
        "Target-lowerable",
    )
    assert all(row[1] for row in stages)

    provenance = _section(_read(), "Authorship Provenance And Effective Defaults")
    rows = _tables(provenance)[0][1:]
    assert tuple(row[0] for row in rows) == PROVENANCE_STATES
    normalized = _normalized(provenance)
    for evidence in (
        "must not be encoded by one overloaded `None`",
        "RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW",
        "EXCLUDE NO OTHERS",
        "RESPECT NULLS",
        "FROM FIRST",
        "composed before defaults are resolved",
    ):
        assert evidence in normalized

    model = _normalized(_section(_read(), "Typed Lazy Frame Model"))
    for token in (
        "`ROWS`",
        "`RANGE`",
        "`GROUPS`",
        "UNBOUNDED PRECEDING",
        "offset PRECEDING",
        "CURRENT ROW",
        "offset FOLLOWING",
        "UNBOUNDED FOLLOWING",
        "`NO OTHERS`",
        "`CURRENT ROW`",
        "`GROUP`",
        "`TIES`",
        "lazy view",
        "Python equality operation never becomes semantic authority",
    ):
        assert token in model


def test_resolution_unit_exclusion_legality_and_empty_evidence_are_exact() -> None:
    resolution = _normalized(
        _section(_read(), "Resolution Pipeline And Unit Semantics")
    )
    ordered = (
        "partition -> ordering -> peer groups -> bounds -> partition clipping -> "
        "EXCLUDE -> function evaluation"
    )
    assert ordered in resolution
    for evidence in (
        "`ROWS` bounds count exact ordered row occurrences",
        "`GROUPS` bounds count peer groups",
        "reverse their arithmetic direction under `DESC`",
        "under `ROWS`, it is the exact current row occurrence",
        "under `RANGE` and `GROUPS`",
        "It is not Python `==`",
        "`EXCLUDE TIES` removes its other peers but retains the current occurrence",
    ):
        assert evidence in resolution

    legality = _section(_read(), "Structural Legality And Empty-frame Evidence")
    rows = _tables(legality)[0][1:]
    assert tuple(row[0] for row in rows) == (
        "Structurally invalid",
        "Guaranteed nonempty",
        "Possibly empty",
        "Always empty",
    )
    normalized = _normalized(legality)
    for evidence in (
        "A start cannot be `UNBOUNDED FOLLOWING`",
        "an end cannot be `UNBOUNDED PRECEDING`",
        "UNBOUNDED PRECEDING < offset PRECEDING < CURRENT ROW",
        "Two bounds in the same offset category are not rejected by category alone",
        "existing exact nonnegative `Int`-literal authority",
        "remain Phase 64",
        "an exact zero `Int` offset is semantically equivalent to `CURRENT ROW`",
        "offset-free RANGE forms",
        "stops before `Validated` with typed missing-evidence rejection",
        "Every analyzed frame result carries exactly one classification",
        "Both bounds and exclusion participate",
        "Empty-frame result nullability/type refinement remains Phase 64",
    ):
        assert evidence in normalized


def test_function_frame_null_treatment_and_from_policies_are_exact() -> None:
    section = _section(_read(), "Function Frame And Modifier Admissibility")
    rows = _tables(section)[0][1:]
    assert tuple(row[0] for row in rows) == (
        "Ranking/distribution",
        "Offset navigation",
        "Frame value",
        "Nth frame value",
        "Aggregate-as-window",
    )
    assert rows[0][1] == (
        "`row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile`"
    )
    assert rows[1][1] == "`lag`, `lead`"
    assert rows[2][1] == "`first_value`, `last_value`"
    assert rows[3][1] == "`nth_value`"
    assert rows[1][3] == "`RESPECT NULLS` or `IGNORE NULLS`"
    assert rows[2][3] == "`RESPECT NULLS` or `IGNORE NULLS`"
    assert rows[3][4] == "`FROM FIRST` or `FROM LAST`"
    normalized = _normalized(section)
    assert "rejected rather than silently ignored" in normalized
    assert "Slice 9 owns the private `first_value`, `last_value`, and `nth_value`" in (
        normalized
    )
    assert "exact positive `Int`-literal position" in normalized
    assert "NULL treatment never changes frame membership" in normalized
    assert "`RESPECT NULLS` retains every candidate row" in normalized
    assert "`IGNORE NULLS` removes only candidate rows" in normalized
    assert "the offset counts that partition candidate sequence" in normalized
    assert "candidates come from the post-exclusion frame" in normalized
    assert "An absent candidate or absent requested position yields NULL" in normalized
    assert "changes only the direction in which `nth_value` counts" in normalized


def test_named_window_identity_monotonic_dag_and_equivalence_are_separate() -> None:
    named = _normalized(_section(_read(), "Named-window Scope And Monotonic DAG"))
    for evidence in (
        "query-block-scoped occurrence identity",
        "A bare name string is lookup syntax, not identity",
        "Forward and backward references are both legal",
        "rejects duplicate declarations, dangling references, and cycles",
        "zero or one base",
        "`PARTITION`, `ORDER`, and `FRAME`",
        "Repeating an inherited component is an error",
        "no override precedence",
        "resolved declarations and uses retain query source order",
        "never sorts or deduplicates authored occurrences",
        "Direct reference and composition authorship remain different",
    ):
        assert evidence in named

    equality = _normalized(
        _section(_read(), "Occurrence Identity And Semantic Equivalence")
    )
    for evidence in (
        "Current `WindowOccurrenceIdentity` remains the identity root",
        "Semantic equivalence is a separate future-stable relation",
        "never rewrites equality or hashing of authored occurrences",
        "Phase 61 may use this equivalence seam",
        "remain distinct provenance and lineage facts",
    ):
        assert evidence in equality


def test_cross_domain_capability_and_phase59_lineage_boundaries_are_exact() -> None:
    cross = _normalized(_section(_read(), "Cross-domain Stage Boundaries"))
    for evidence in (
        "aggregate argument ORDER BY != window ORDER BY",
        "frame membership != NULL treatment",
        "frame membership precedes aggregate FILTER application",
        "package dependency != semantic visibility",
        "current-window/frame evidence != Phase 59 identity migration",
        "cannot contain a nested window call",
        "cannot resolve to another output in the same window stage",
        "Aggregate internal ordering, `FILTER`",
        "remain Phase 65",
        "`QUALIFY` and post-window filtering remain Phase 63",
    ):
        assert evidence in cross

    lowering = _normalized(
        _section(_read(), "Capability-gated Lowering And Lineage Attachment")
    )
    for evidence in (
        "every used atom",
        "Dialect name alone",
        "does not re-resolve names",
        "delegate defaults to the database",
        "Slice 1 authorizes none",
        "Repeated input occurrences remain repeated",
        "No new frame fact changes package, module, declaration, field, let",
        "private inspection preserves query/declaration/use/component source order",
        "no runtime address or owner token",
        "performs no semantic-equivalence deduplication",
        "no public or canonical cross-version compatibility commitment",
    ):
        assert evidence in lowering


def test_checkpoint_exact_route_and_expansion_rule_are_locked() -> None:
    checkpoint = _tables(_section(_read(), "Phase 51–60 Checkpoint Boundary"))[0][1:]
    assert tuple(row[0] for row in checkpoint) == tuple(str(i) for i in range(51, 61))
    assert tuple(row[1] for row in checkpoint) == CHECKPOINT_INPUTS

    route = _tables(_section(_read(), "Exact 13-slice Route"))[0][1:]
    assert tuple((row[0], row[1]) for row in route) == ROUTE
    assert all(row[2] for row in route)
    expansion = _normalized(_section(_read(), "Route Expansion Rule"))
    for evidence in (
        "exactly 13 slices",
        "genuinely independent Phase 60-owned",
        "cannot fit any existing Slice",
        "Reader omissions",
        "backend limitations",
        "ARCHITECTURE_DECISION_REQUIRED",
        "never changed silently",
    ):
        assert evidence in expansion


def test_later_owners_future_test_contract_and_reader_closure_are_exact() -> None:
    later = _tables(_section(_read(), "Later-owner And Readiness Ledger"))[0][1:]
    assert tuple(row[0] for row in later) == tuple(str(i) for i in range(61, 71))
    assert all(row[1] and row[2] for row in later)
    assert "physical sharing may use semantic equivalence" in later[0][2]
    assert "`QUALIFY`" in later[2][1]
    assert "numeric/Decimal/temporal/date/timestamp/interval/timezone" in later[3][2]
    assert "reusable window assets" in later[5][2]
    assert "first Rust-kernel decision" in later[7][1]
    assert "Backend/catalog capability expansion" in later[8][1]
    assert "public window/frame/lineage projection" in later[9][2]

    future = _normalized(_section(_read(), "Future Test Compatibility Contract"))
    for evidence in (
        "xdist-compatible by default",
        "serial fallback compatible",
        "isolated in temp/env/Git/build surfaces",
        "independent of execution order",
        "shared repository fact acquisition where eligible, owner-local policy interpretation",
        "paired CLI probe infrastructure where applicable",
        "must not add a suite-wide serial switch",
        "Python 3.12/3.13",
        "backend-capability negative cases",
    ):
        assert evidence in future

    readers = _normalized(_section(_read(), "Reader Closure And Changed-path Lock"))
    for evidence in (
        "Fixed-point reader closure found two compatibility readers",
        "A2/M5/D0",
        "sole direct reader",
        "required eighth path",
        "READER_CLOSURE_DRIFT",
    ):
        assert evidence in readers


def test_public_zero_delta_gate_lifecycle_and_subject_are_exact() -> None:
    public = _normalized(
        _section(_read(), "Public Compatibility Release And Non-goals")
    )
    for evidence in (
        "changes no public PostgreSQL emitter",
        "Current advanced-window source remains rejected",
        "no database execution",
        "public graph/window schema",
        "Version remains `0.1.0`",
    ):
        assert evidence in public

    gate = _normalized(
        _section(_read(), "Gate Workflow Lifecycle And Publication Subject")
    )
    for evidence in (
        "one foreground Ponytail FULL review",
        "at most one causal repair generation",
        "UV_PYTHON=3.13 uv run python scripts/validate.py --timings",
        "A validator failure is terminal",
        "staged exactly once, committed once, pushed once",
        "No rerun, dispatch, amend, rebase, squash, force push",
        "Slice 2 is not implemented or authorized",
        "Add Phase 60 advanced window route lock",
    ):
        assert evidence in gate
