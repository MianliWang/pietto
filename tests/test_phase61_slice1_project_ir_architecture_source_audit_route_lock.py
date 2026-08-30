from __future__ import annotations

import ast
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-project-ir-architecture-source-audit-route-lock-v1.md"
)
IR_MODEL = REPO_ROOT / "src/pietto/ir/model.py"
IR_BUILDER = REPO_ROOT / "src/pietto/ir/builder.py"
PROJECT_MODEL = REPO_ROOT / "src/pietto/_project/model.py"
RELATION_RESOLUTION = REPO_ROOT / "src/pietto/_project/module_relation_resolution.py"
SEMANTIC_FACTS = REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
WINDOW_FACTS = REPO_ROOT / "src/pietto/_project/window_semantics.py"
PACKAGE_GRAPH = REPO_ROOT / "src/pietto/_project/package_graph.py"
LET_BINDINGS = REPO_ROOT / "src/pietto/semantic/let_bindings.py"
SQL_RELATIONS = REPO_ROOT / "src/pietto/sql/relations.py"

OWNER = (
    "Private target-independent Project Logical IR, exact semantic composition, "
    "and verifiable analysis boundary."
)
HEADINGS = (
    "Answer And Static Scope",
    "Starting Authority",
    "Audit Method And Current Source Snapshot",
    "Live Pietto Architecture Audit",
    "Mature Source Audit Dispositions",
    "Frozen Owner And Layer Laws",
    "Identity Value Use And Edge Laws",
    "Relation Multiplicity Definition Sharing And Execution",
    "Current Operator Algebra And Evaluation Order",
    "Output Value Boundary",
    "Exact Provided Required Estimate And Effect Domains",
    "Construction States And Complete Project Result",
    "Graph Topology Analysis And Verifier Boundary",
    "Provenance Snapshot And Persistent Identity",
    "Recursion Readiness",
    "Correlation Nested And Grain Readiness",
    "Canonical IR Optimizer And Target Separation",
    "Exact 12-slice Route",
    "Route Expansion Rule",
    "Later Owner Ledger",
    "Reader Closure And Changed-path Lock",
    "Compatibility Non-goals And Production Zero-delta",
    "Gate Lifecycle Publication And Next Owner",
)
UPSTREAM_HEADS = {
    "LLVM": "e046dce4a4c80610b49d67bc02c85f86b1a6353d",
    "Rust compiler": "3cabe36ceb022e2f56d4d330b1e2886f31117f18",
    "Go compiler": "603439a1c6f2d37c7f02e246342847056ed04c21",
    "GHC": "578bd18509f0d2aeb004231a197f7f3898f86a2a",
    "Malloy": "c8c6932f9f1f0f5ff6034b2889dee137c76ab00f",
    "Cube": "4567c074fe4a2d13d278c3dd4c6c71217094bc4a",
    "Apache Calcite": "4f899823ede7ffd2dabcc5834cff2acb0a68af54",
    "Substrait": "f3667cc01f8d37236fad4b0e28981bcaf4f21a48",
    "PostgreSQL": "2fb8da5a245661287833b05a1b2e275ddf83bbd7",
    "DuckDB": "8616efa9da9921b9111fe46373af7936a5d96d16",
    "Soufflé": "a1303be3c0166400dee3d1f36f0d96abe03e6901",
    "Differential dataflow": "aa8745f93ea8abe131104fc7885ba4fd47e63902",
}
PIETTO_AUDIT_PATHS = frozenset(
    {
        "grammar/Pietto.g4",
        "src/pietto/_project/aggregate_grouped_clause_facts.py",
        "src/pietto/_project/aggregate_grouped_dependency_lineage.py",
        "src/pietto/_project/aggregate_grouped_schema.py",
        "src/pietto/_project/module_relation_resolution.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/module_attribution.py",
        "src/pietto/_project/module_catalog.py",
        "src/pietto/_project/package_graph.py",
        "src/pietto/_project/row_lineage.py",
        "src/pietto/_project/window_persistence.py",
        "src/pietto/_project/window_semantics.py",
        "src/pietto/ir/builder.py",
        "src/pietto/ir/model.py",
        "src/pietto/semantic/analyzer.py",
        "src/pietto/semantic/expressions.py",
        "src/pietto/semantic/group_by.py",
        "src/pietto/semantic/let_bindings.py",
        "src/pietto/semantic/predicate_checks.py",
        "src/pietto/semantic/relation_limits.py",
        "src/pietto/semantic/relations.py",
        "src/pietto/semantic/satisfying.py",
        "src/pietto/semantic/window_semantics.py",
        "src/pietto/sql/relations.py",
    }
)
ROUTE = (
    ("1", "Architecture, Mature-Source Audit, Semantic Laws, And Route Lock"),
    (
        "2",
        "Scope, Stages, Plan/Value/Use Occurrences, Anchors, And Construction States",
    ),
    (
        "3",
        "Row/Output Model, Provided/Required Properties, Effects, And Estimate Boundary",
    ),
    ("4", "Current Logical Operator Algebra And Exact Property Transfer"),
    (
        "5",
        "Canonical Single-Relation Construction From Existing Project Semantic Facts",
    ),
    ("6", "Cross-Module Relation Composition And Acyclic Project Plan DAG"),
    (
        "7",
        "Aggregate/Window Evaluation Context, Policy/Effect Preservation, And No-Ambient Authority",
    ),
    (
        "8",
        "Integrity, Verifier, Analysis Invalidation, Semantic Equivalence, And Optimizer/Recursion Readiness",
    ),
    ("9", "Private Inspection, Query, Canonical Serialization, And Pure Boundary"),
    ("10", "Real Authored Multi-Module Project IR E2E"),
    ("11", "Differential Compatibility"),
    ("12", "Completion Audit And Phase 62 Handoff"),
)


def _read(path: Path = SPEC) -> str:
    return path.read_text(encoding="utf-8")


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


def _class_fields(path: Path, class_name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(path), filename=str(path))
    classes = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    assert len(classes) == 1
    return tuple(
        node.target.id
        for node in classes[0].body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    )


def _enum_members(path: Path, class_name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(path), filename=str(path))
    classes = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    assert len(classes) == 1
    return tuple(
        target.id
        for node in classes[0].body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    )


def test_owner_heading_zero_delta_and_starting_authority_are_exact() -> None:
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
    assert _normalized(answer).count(OWNER) == 1
    assert _tables(answer)[0][1:] == (
        ("Production changes", "`0`"),
        ("Public behavior changes", "`0`"),
        ("Public schema changes", "`0`"),
        ("Grammar/generated changes", "`0`"),
        ("SQL/backend changes", "`0`"),
        ("Golden changes", "`0`"),
        ("Package/build metadata changes", "`0`"),
        ("Workflow/validator changes", "`0`"),
        ("Slice 2 implementation", "`FORBIDDEN`"),
        ("Current version", "`0.1.0`"),
    )
    starting = _normalized(_section(document, "Starting Authority"))
    for evidence in (
        "bf4eeb06507f84374b9d97070423face3e54d929",
        "1ca3542b1f373cdce6b7035b33000eda474ae39d",
        "33295132391",
        "Complete Phase 60 advanced windows",
        "Phase 60 = COMPLETED",
        "Phase 61 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in starting


def test_current_upstream_snapshots_and_dispositions_are_complete() -> None:
    document = _read()
    snapshot = _tables(_section(document, "Audit Method And Current Source Snapshot"))[
        0
    ][1:]
    assert {row[0]: row[2].strip("`") for row in snapshot} == UPSTREAM_HEADS
    assert all("https://" in row[3] for row in snapshot)

    dispositions = _tables(_section(document, "Mature Source Audit Dispositions"))[0][
        1:
    ]
    assert {row[0] for row in dispositions} == {"Pietto", *UPSTREAM_HEADS}
    assert {row[3] for row in dispositions} == {
        "`ADOPT`",
        "`ADAPT`",
        "`REJECT`",
        "`LATER OWNER`",
    }
    assert all(all(cell for cell in row) for row in dispositions)
    assert "independent missing Phase-61 owner" in _normalized(
        _section(document, "Mature Source Audit Dispositions")
    )


def test_live_pietto_authority_is_classified_and_relation_ir_is_unchanged() -> None:
    section = _section(_read(), "Live Pietto Architecture Audit")
    paths = frozenset(
        re.findall(r"`((?:grammar|src)/[^`]+\.(?:g4|py))(?:[^`]*)?`", section)
    )
    assert paths == PIETTO_AUDIT_PATHS
    assert all((REPO_ROOT / path).is_file() for path in paths)

    assert _class_fields(IR_MODEL, "RelationIR") == (
        "symbol",
        "name",
        "kind",
        "source",
        "filter",
        "projections",
        "row_schema",
        "span",
        "order_by",
        "limit",
        "group_keys",
        "result_predicate",
        "named_windows",
    )
    assert _class_fields(SEMANTIC_FACTS, "ProjectModuleRelationSemanticFacts") == (
        "owner",
        "base_row_fact",
        "resolution",
        "state",
        "let_scope_facts",
        "let_bindings",
        "select_facts",
        "group_key_occurrences",
        "aggregate_grouped_clause_readiness",
        "clause_dependencies",
        "aggregate_result_facts",
        "window_outputs",
        "named_window_namespace",
        "helper_diagnostics",
    )
    assert "Validate relation-local let clauses and return private value scopes." in (
        _read(LET_BINDINGS)
    )
    assert "deduplicate_window_dependency_edges" in _read(WINDOW_FACTS)


def test_layer_identity_use_multiplicity_and_execution_laws_are_exact() -> None:
    layers = _normalized(_section(_read(), "Frozen Owner And Layer Laws"))
    assert (
        "AST / authored syntax != semantic model != existing script-level Semantic IR "
        "!= Project semantic facts != canonical Project Logical IR != optimizer memo "
        "/ rewrite alternatives != target-lowerable plan != physical SQL strategy"
        in layers
    )
    assert "It is not migrated, wrapped into a god object" in layers
    assert "never becomes a second semantic analyzer" in layers

    identity = _normalized(_section(_read(), "Identity Value Use And Edge Laws"))
    for evidence in (
        "source declaration occurrence",
        "Project semantic-fact occurrence",
        "Project plan-node occurrence",
        "Project output-value occurrence",
        "relation-use occurrence",
        "consumer input-slot occurrence",
        "Project-IR-local reference",
        "runtime row key",
        "presentation ordinal",
        "future persistent/cache identity",
        "producer output port -> exact use occurrence -> exact consumer input slot",
        "Two identical uses remain two use occurrences",
        "A direct node-to-node edge is insufficient authority",
        "A plan-node occurrence is not its output-value occurrence",
        "a use occurrence is not the consumer input slot",
    ):
        assert evidence in identity

    multiplicity = _normalized(
        _section(_read(), "Relation Multiplicity Definition Sharing And Execution")
    )
    for evidence in (
        "relation value = BAG BAG != SET",
        "preserve row multiplicity",
        "relation definition != relation use occurrence != logical DAG sharing != "
        "materialization != physical execution count",
        "Canonical Project IR is not an execution schedule",
    ):
        assert evidence in multiplicity


def test_current_operator_order_and_let_boundary_match_live_source() -> None:
    section = _section(_read(), "Current Operator Algebra And Evaluation Order")
    rows = _tables(section)[0][1:]
    assert tuple(row[0] for row in rows) == (
        "Relation input",
        "Row filter",
        "Group/aggregate",
        "Result filter",
        "Window evaluation",
        "Final projection",
        "Relation ordering",
        "Limit",
    )
    normalized = _normalized(section)
    assert (
        "relation input -> row filtering -> grouping / admitted aggregate results -> "
        "post-aggregate satisfying -> window evaluation -> final output projection -> "
        "relation ordering -> limit" in normalized
    )
    assert "`let:` is a lexical expression environment" in normalized
    assert "It is not a row-transforming operator" in normalized

    sql = _read(SQL_RELATIONS)
    render = sql[
        sql.index("def render_relation_sql(") : sql.index("def _render_input(")
    ]
    clause_markers = (
        'f"FROM ',
        'f"WHERE ',
        '"GROUP BY"',
        '"HAVING"',
        '"WINDOW"',
        '"ORDER BY"',
        'f"LIMIT ',
    )
    assert tuple(render.index(marker) for marker in clause_markers) == tuple(
        sorted(render.index(marker) for marker in clause_markers)
    )
    assert "let_expansions = _let_expansions" in _read(IR_BUILDER)


def test_output_property_estimate_effect_and_construction_boundaries_are_exact() -> (
    None
):
    output = _normalized(_section(_read(), "Output Value Boundary"))
    for evidence in (
        "Project output value == ExpressionIR forever",
        "typed output-value occurrence",
        "Current relation-stage outputs are typed `BAG` relation values",
        "current authored selected-output form remains",
        "later record and nested relation selected outputs",
        "creates no speculative `NestedOutputField`, `OpenRelationPlan`, or `FixpointPlan`",
    ):
        assert evidence in output

    production = "\n".join(
        _read(path)
        for root in (REPO_ROOT / "src/pietto/ir", REPO_ROOT / "src/pietto/_project")
        for path in sorted(root.glob("*.py"))
    )
    for forbidden in (
        "CanonicalProjectIR",
        "NestedOutputField",
        "OpenRelationPlan",
        "FixpointPlan",
    ):
        assert forbidden not in production

    properties = _normalized(
        _section(_read(), "Exact Provided Required Estimate And Effect Domains")
    )
    for evidence in (
        "ProvidedProperties != RequiredInputProperties",
        "ExactSemanticProperties != EstimatedStatistics",
        "estimated row count selectivity cost NDV memory estimate",
        "determinism / volatility may-error behavior side effects evaluation "
        "multiplicity sensitivity",
        "Changing evaluation count or error/effect behavior",
        "invents no current function classification",
    ):
        assert evidence in properties

    construction = _normalized(
        _section(_read(), "Construction States And Complete Project Result")
    )
    for state in ("CONCRETE", "UNKNOWN", "DEFERRED", "BLOCKED", "AMBIGUOUS"):
        assert state in construction
    assert "one bad relation does not erase unrelated concrete plans" in construction
    assert "No partially meaningful `UnknownPlanNode`" in construction

    assert _enum_members(PROJECT_MODEL, "ProjectRelationRowSchemaStatus") == (
        "CONCRETE",
        "UNKNOWN",
        "DEFERRED",
        "BLOCKED",
    )
    assert _enum_members(SEMANTIC_FACTS, "ProjectModuleCandidateBucketStatus") == (
        "CONCRETE",
        "UNKNOWN",
        "DEFERRED",
        "BLOCKED",
        "ABSENT",
        "AMBIGUOUS",
    )


def test_graph_provenance_recursion_correlation_and_optimizer_laws_are_exact() -> None:
    graph = _normalized(
        _section(_read(), "Graph Topology Analysis And Verifier Boundary")
    )
    for evidence in (
        "Current canonical Project topology is acyclic",
        "Direct typed node/output/use/slot edges are authority",
        "never select a hidden first/latest/nearest/best winner",
        "validate initial construction and every later transformation",
        "does not trust a potentially stale cache",
        "Slice 1 builds neither optimizer nor pass manager",
    ):
        assert evidence in graph

    provenance = _normalized(
        _section(_read(), "Provenance Snapshot And Persistent Identity")
    )
    for evidence in (
        "primary origin supporting origins rewrite witness",
        "One `SourceSpan` cannot forever represent complete transformation provenance",
        "snapshot-local occurrence identity != persistent incremental-cache key",
        "creates no persistent/cross-build identity system",
    ):
        assert evidence in provenance

    recursion = _normalized(_section(_read(), "Recursion Readiness"))
    for evidence in (
        "future recursion != arbitrary graph cycle",
        "explicit scoped fixpoint / recursive region",
        "recursive reference != ordinary relation dependency edge",
        "seed, iterative body, exact recursive binder, set/bag mode",
        "working-table iteration, semi-naive/delta evaluation, keyed recursion, and "
        "differential dataflow",
        "assigns recursion no phase number",
    ):
        assert evidence in recursion

    correlation = _normalized(
        _section(_read(), "Correlation Nested And Grain Readiness")
    )
    for evidence in (
        "free_bindings = empty",
        "exact relation and field anchors",
        "Lexical distance, `steps_out`, bare string names",
        "Correlation is not itself a grain transition",
        "Nested relation syntax/results",
        "no operator borrows an ambient fact/grain context",
    ):
        assert evidence in correlation

    optimizer = _normalized(
        _section(_read(), "Canonical IR Optimizer And Target Separation")
    )
    assert "CanonicalProjectIR != OptimizationMemo != ChosenTargetPlan" in optimizer
    for evidence in (
        "bag multiplicity",
        "effects/error behavior",
        "evaluation count",
        "policy context",
        "required capabilities",
        "provenance traceability",
    ):
        assert evidence in optimizer


def test_exact_route_later_owners_reader_closure_and_gate_are_locked() -> None:
    route = _tables(_section(_read(), "Exact 12-slice Route"))[0][1:]
    assert tuple((row[0], row[1]) for row in route) == ROUTE
    assert all(row[2] for row in route)
    assert "exactly 12 slices" in _normalized(_section(_read(), "Exact 12-slice Route"))

    expansion = _normalized(_section(_read(), "Route Expansion Rule"))
    assert "ARCHITECTURE_DECISION_REQUIRED" in expansion
    assert "do not justify silent expansion" in expansion

    later = _tables(_section(_read(), "Later Owner Ledger"))[0][1:]
    assert tuple(row[0] for row in later) == (
        "Phase 62",
        "Phase 63",
        "Phase 64",
        "Phase 65",
        "Phase 66",
        "Phase 67",
        "Phase 68",
        "Phase 69",
        "Phase 70",
        "Dedicated later owner, phase unassigned",
        "Future incremental owner, phase unassigned",
    )
    assert all(row[1] for row in later)

    readers = _normalized(_section(_read(), "Reader Closure And Changed-path Lock"))
    assert "frozen Slice 1 changed-path set is exactly" in readers
    assert "A2/M6/D0" in readers
    assert "sole direct reader" in readers
    assert "ninth changed path is `READER_CLOSURE_DRIFT`" in readers

    compatibility = _normalized(
        _section(_read(), "Compatibility Non-goals And Production Zero-delta")
    )
    for evidence in (
        "no speculative production architecture",
        "no RelationIR migration",
        "no set-vs-bag mistake",
        "no definition/use/execution conflation",
        "no plan-node/output/use/input-slot conflation",
        "no exact-property/estimate conflation",
        "no let-as-operator assumption without evidence",
        "no arbitrary-cycle recursion readiness",
    ):
        assert evidence in compatibility

    gate = _normalized(_section(_read(), "Gate Lifecycle Publication And Next Owner"))
    for evidence in (
        "at most one root-cause repair batch",
        "fresh rereview",
        "UV_PYTHON=3.13 uv run python scripts/validate.py --timings",
        "one ordinary commit",
        "one fast-forward push",
        "without rerun or dispatch",
        "Add Phase 61 Project IR route lock",
        "PASS — PHASE61_SLICE1_PROJECT_IR_ARCHITECTURE_SOURCE_AUDIT_ROUTE_LOCK_END_TO_END",
        "Phase 61 Slice 2 — Scope, Stages, Plan/Value/Use Occurrences, Anchors, "
        "And Construction States",
        "Slice 2 is not implemented or authorized",
    ):
        assert evidence in gate


def test_existing_exact_resolution_and_phase59_ref_domains_remain_separate() -> None:
    resolution = _read(RELATION_RESOLUTION)
    for evidence in (
        "Relation symbol buckets cannot select a winner.",
        "Relation AST lookup buckets must be unambiguous.",
        "Relation environments must follow dependency order.",
        "Return every local/imported symbol retaining one nominal target.",
    ):
        assert evidence in resolution

    graph = _read(PACKAGE_GRAPH)
    for class_name in (
        "PackageGraphPackageRef",
        "PackageGraphDependencyRef",
        "PackageGraphRequirementRef",
        "PackageGraphSelectorRef",
        "PackageGraphModuleRef",
        "PackageGraphDeclarationRef",
        "PackageGraphFieldRef",
        "PackageGraphLetRef",
        "PackageGraphNamedWindowRef",
    ):
        assert f"class {class_name}:" in graph
    assert "class PackageGraphScope:" in graph
    assert "content_digest" in graph
