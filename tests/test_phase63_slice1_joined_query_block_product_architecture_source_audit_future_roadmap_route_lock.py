from __future__ import annotations

from pathlib import Path
import re
import subprocess

from _pietto_repository_facts import REPOSITORY_FACTS


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md"
)
BASELINE = "d9a423fe6822ed549e3063299a4781cd7ed4b480"
SUBJECT = "Add Phase 63 joined query-block route lock"

GATE_FIELDS = (
    "Live authority",
    "User/product outcome",
    "Semantic reference model",
    "Identity model",
    "Construction states",
    "Proof posture",
    "Layer ownership",
    "Dependency direction",
    "Versioning and migration",
    "Target requirements versus provider capabilities",
    "Interchange",
    "Execution",
    "Resource lifecycle",
    "Security and trust",
    "Algorithms and data structures",
    "Complexity posture",
    "Invalidation",
    "Cache",
    "Concurrency",
    "Diagnostics",
    "Inspection",
    "UX",
    "Conformance",
    "Differential and fuzz assurance",
    "Packaging",
    "Support matrix",
    "Release, deprecation, and EOL",
    "Readiness and exact deferred owners",
    "Slice route",
    "Repair and stop conditions",
)
EXTERNAL_FIELDS = (
    "Snapshot/date",
    "Problem/constraints",
    "Semantic/identity model",
    "Layering/dependency direction",
    "Algorithms/data structures/complexity",
    "Interface/version/capability model",
    "Testing/operational lifecycle",
    "Pitfalls/migration costs",
    "Disposition",
    "WHAT_NOT_TO_COPY",
    "Pietto owner affected",
)
EXTERNAL_RECORDS = (
    ("R01", "LLVM/MLIR", "ADAPT"),
    ("R02", "PostgreSQL", "ADAPT"),
    ("R03", "Apache Calcite", "ADAPT"),
    ("R04", "Apache DataFusion", "ADAPT"),
    ("R05", "Substrait", "ADOPT"),
    ("R06", "Apache Arrow", "ADOPT"),
    ("R07", "Apache Arrow ADBC", "DEFER"),
    ("R08", "SQLAlchemy", "ADAPT"),
    ("R09", "Malloy", "ADAPT"),
    ("R10", "Cube", "ADAPT"),
    ("R11", "Android stable AIDL/VINTF/CTS", "ADAPT"),
    ("R12", "OpenHarmony architecture/XTS", "ADAPT"),
    ("R13", "MLIRSmith", "ADAPT"),
    ("R14", "SynthFuzz", "DEFER"),
    ("R15", "Differential Query Plans", "DEFER"),
    ("R16", "SQLancer++", "DEFER"),
)
PHASE63_ROUTE = (
    ("1", "Product Gate v3, Pietto/external source audit, Future Roadmap, route lock"),
    ("2", "Query-block owner bridge, row-source sum, states, mode boundary"),
    ("3", "Scalar-reference environment, resolution facts, type-kernel adapter"),
    ("4", "Bindings, visible joined fields, qualified/unqualified lookup"),
    ("5", "LET, stage namespace lattice, shadowing and alias laws"),
    ("6", "Post-JOIN row semantics, nullability, lineage and property bridge"),
    (
        "7",
        "Completion scheduling, effective-output ledger foundation, module propagation",
    ),
    ("8", "Joined row filtering"),
    ("9", "Joined grouping, aggregate, GLOBAL, satisfying and risk linkage"),
    ("10", "Generic window-computation sites and named-window reuse"),
    ("11", "QUALIFY grammar, AST, semantics and property transfer"),
    ("12", "Projection, ordering, limit, final output and ledger completion"),
    ("13", "Completed project semantic result and public check boundaries"),
    ("14", "Query-block Project IR composition, verification and invalidation"),
    (
        "15",
        "Inspection/pure boundary and real E2E/differential/metamorphic assurance",
    ),
    ("16", "Completion audit and Phase-64 handoff"),
)
FUTURE_ROADMAP = (
    ("63", "Joined Query Block semantic completion and QUALIFY"),
    (
        "64",
        "Flat relational algebra: generic ON/refinement; CROSS/RIGHT/FULL/SEMI/ANTI; DISTINCT; UNION/INTERSECT/EXCEPT; single-match enforcement",
    ),
    (
        "65",
        "Target-neutral ProjectSQLPlan, parameters, source maps, legality and capability requirements",
    ),
    ("66", "PostgreSQL/MySQL baseline multi-relation SQL and Project emit-SQL"),
    ("67", "Arrow interchange foundation and Pietto result contract"),
    (
        "68",
        "Explicit executor SPI, ADBC/DBAPI, streaming/cancellation/backpressure",
    ),
    ("69", "Public alpha release engineering and unified safe entrypoints"),
    (
        "70",
        "Open/composite plans, nonrecursive CTE/subqueries, VALUES/table functions, outer captures, EXISTS/IN, LATERAL, bounded decorrelation, effect authority",
    ),
    ("71", "NestedRelation, Collect, Unnest, flatten, outer/inner grain, nested Arrow"),
    (
        "72",
        "Advanced equality/types/nullability and temporal/range/ASOF relationships",
    ),
    (
        "73",
        "Aggregate algebra/state, grouping extensions, fanout-safe reaggregation",
    ),
    (
        "74",
        "Reusable local semantic assets, derived relationships, function/plugin SPI",
    ),
    ("75", "Formatter, LSP, editor, diagnostics, syntax editions and migrations"),
    ("76", "PostgreSQL deep adaptation"),
    ("77", "MySQL deep adaptation"),
    ("78", "SQLite deep adaptation"),
    ("79", "DuckDB deep adaptation"),
    ("80", "pandas/Polars/NumPy/SciPy/Matplotlib interoperability"),
    (
        "81",
        "High-intensity real-DB/differential/metamorphic/fuzz/performance assurance",
    ),
    ("82", "Public schemas/API/CLI/syntax/support-matrix freeze"),
    ("83", "Stable 1.0 release audit and publication"),
    ("84", "Remote assets/registry/transport/signing/trust"),
    ("85", "Dependency solver/canonical lockfile/reproducible resolution"),
    ("86", "RDKit/geospatial/sparse/DLPack/device-framework adapters"),
    ("87", "Catalog/constraints/statistics/runtime-data-quality/chase"),
    ("88", "Logical optimizer memo and join-order/hypergraph search"),
    (
        "89",
        "Physical strategies including Yannakakis/WCOJ/Free Join/predicate transfer",
    ),
    (
        "90",
        "Profiling-driven Rust kernels, PyO3/maturin, parity and wheel matrix",
    ),
)
TENTATIVE_OWNERS = (
    (
        "91",
        "Persistent incremental-cache identity and incremental/differential Project IR",
    ),
    (
        "92",
        "Recursive relations, fixpoints, iterative planning, and bounded recursive provenance",
    ),
    ("93", "Formal rewrite certification"),
    ("94", "Cloud/federation semantics, planning, and transport"),
    ("95", "DML, DDL, and migrations"),
    ("96", "Governance and security policy semantics"),
    (
        "97",
        "Continuous/streaming query semantics distinct from finite-result streaming",
    ),
)


def _read(path: Path = SPEC) -> str:
    return path.read_text(encoding="utf-8")


def _python(relative: str) -> str:
    return REPOSITORY_FACTS.python(REPO_ROOT / relative).text


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table(document: str, heading: str) -> tuple[tuple[str, ...], ...]:
    section = _section(document, heading)
    rows = tuple(
        tuple(cell.strip().strip("`") for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )
    assert rows
    return rows[1:]


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def _external_record_blocks(
    document: str,
) -> tuple[tuple[str, str, tuple[str, ...], str], ...]:
    section = _section(document, "External Reference Review Protocol")
    matches = tuple(re.finditer(r"^### (R\d{2}) (.+)$", section, flags=re.MULTILINE))
    records: list[tuple[str, str, tuple[str, ...], str]] = []
    for position, match in enumerate(matches):
        end = (
            matches[position + 1].start()
            if position + 1 < len(matches)
            else len(section)
        )
        block = section[match.end() : end]
        labels = tuple(
            line[2:].split(":", 1)[0]
            for line in block.splitlines()
            if line.startswith("- ")
        )
        disposition = next(
            line.split("`", 2)[1]
            for line in block.splitlines()
            if line.startswith("- Disposition:")
        )
        records.append((match.group(1), match.group(2), labels, disposition))
    return tuple(records)


def test_product_phase_initiation_gate_v3_is_complete_and_fail_closed() -> None:
    rows = _table(_read(), "Product/Phase Initiation Gate v3")
    assert tuple(row[1] for row in rows) == GATE_FIELDS
    assert tuple(row[0] for row in rows) == tuple(str(index) for index in range(1, 31))
    assert all(len(row) == 4 for row in rows)
    for row in rows:
        state = row[3]
        assert "owner=" in state
        if state.startswith("NOT_APPLICABLE"):
            assert "reason=" in state
        else:
            assert state.startswith("PASS")
    assert sum(row[3].startswith("NOT_APPLICABLE") for row in rows) == 9


def test_external_reference_records_have_exact_snapshots_and_decisions() -> None:
    records = _external_record_blocks(_read())
    assert tuple((record[0], record[1], record[3]) for record in records) == (
        EXTERNAL_RECORDS
    )
    assert all(record[2] == EXTERNAL_FIELDS for record in records)
    snapshots = tuple(
        line
        for line in _section(_read(), "External Reference Review Protocol").splitlines()
        if line.startswith("- Snapshot/date:")
    )
    assert len(snapshots) == len(EXTERNAL_RECORDS) == 16
    assert all("2026-09-02" in snapshot for snapshot in snapshots)
    for required in (
        "dd7236de4812ff2c4dc28e2b2948e3f35586d33b",
        "e073b64d33215d4bfded1366549b96580a402c06",
        "aaf565457f85c6221bf6c4a925320f0339792e1b",
        "d2b626cc93616b5bf80b7ca2a079e9859d992e32",
        "88280b1290d5146288572e02387fe7ac1dad57dc",
        "f69ec05524b0d6ed44c3fa804377332dfc085fac",
        "f1d6412b809784a882ad1c971018e4401c91aecd",
        "a4cb8dbb8499c9238f3207794a2d3f36cea36aae",
        "ad563d014444a6ef54c7c79d89e224789180151d",
        "1842d93a305a4fe0a4923c64be0aefe852dcef3a",
        "10.1109/ASE56229.2023.00120",
        "10.1109/ICSE55347.2025.00037",
        "10.1145/3654991",
        "10.1145/3779212.3790215",
    ):
        assert required in _read()
    assert _read().count("- WHAT_NOT_TO_COPY:") == 16
    assert "No test fetches these links" in _read()


def test_current_relation_body_and_scalar_analyzers_match_the_audit() -> None:
    grammar = _read(REPO_ROOT / "grammar/Pietto.g4")
    table_body = grammar[grammar.index("tableBody\n") : grammar.index("\nfromClause")]
    clauses = (
        "fromClause",
        "joinClause",
        "letClause",
        "whereClause",
        "groupByClause",
        "selectClause",
        "namedWindowDeclaration",
        "satisfyingClause",
        "orderByClause",
        "limitClause",
    )
    positions = tuple(table_body.index(clause) for clause in clauses)
    assert positions == tuple(sorted(positions))
    builder = _python("src/pietto/ast_builder.py")
    assert "tuple(self.visit(item) for item in ctx.joinClause())" in builder
    assert "tuple(self.visit(item) for item in ctx.namedWindowDeclaration())" in builder

    expressions = _python("src/pietto/semantic/expressions.py")
    lets = _python("src/pietto/semantic/let_bindings.py")
    preservation = _python("src/pietto/_project/module_semantic_fact_preservation.py")
    assert "Resolve one two-part field reference against the sole relation input." in (
        expressions
    )
    assert "len(expression.parts) != 2 or expression.parts[0] != field_qualifier" in (
        expressions
    )
    assert "field_qualifier=definition.from_clause.source_name" in lets
    assert "prior_names=set(scope_values)" in lets
    assert "Let binding cannot reference itself" in lets
    assert "Let binding cannot reference a later binding" in lets
    assert "if len(dotted.parts) == 2 and dotted.parts[0] == relation_qualifier" in (
        preservation
    )


def test_current_identity_schema_and_occurrence_ledgers_match_the_audit() -> None:
    semantic_model = _python("src/pietto/semantic/model.py")
    project_model = _python("src/pietto/_project/model.py")
    preservation = _python("src/pietto/_project/module_semantic_fact_preservation.py")
    windows = _python("src/pietto/semantic/window_semantics.py")
    window_analysis = _python("src/pietto/semantic/window_analysis.py")
    joined = _python("src/pietto/_project/project_ir_properties.py")
    join_builder = _python("src/pietto/_project/project_ir_joins.py")

    assert "fields: Mapping[str, RowField]" in semantic_model
    assert "fields: Mapping[str, ProjectRowField]" in project_model
    assert "fields: tuple[ProjectIRJoinedRowField, ...]" in joined
    assert "class ProjectModuleExpressionReferenceFact:" in preservation
    assert "container_ordinal: int" in preservation
    assert "dependency_ordinal: int" in preservation
    assert "let_candidates: tuple[LetBinding, ...]" in preservation
    assert "selected_output_candidates: tuple[SelectItem, ...]" in preservation
    assert "class ProjectModuleSelectFact:" in preservation
    assert "selected_output_ordinal: int" in preservation
    assert "Select references must retain the exact source ledger." in preservation

    source_paths = tuple((REPO_ROOT / "src/pietto").rglob("*.py"))
    assert (
        sum(
            "class QueryBlockOccurrence:" in REPOSITORY_FACTS.python(path).text
            for path in source_paths
        )
        == 1
    )
    assert "class NamedWindowOccurrence:" in windows
    assert "query_block: QueryBlockOccurrence" in windows
    assert "def _query_block_occurrence(" in windows
    assert "class WindowOccurrenceIdentity:" in windows
    assert "selected_output_ordinal: int" in windows
    assert "occurrence = WindowOccurrenceIdentity(" in window_analysis

    for evidence in (
        "field_position: int",
        "introduction_use: ProjectIRJoinInputUseOccurrence",
        "nulling_joins: tuple[ProjectIRPlanNodeRef, ...]",
        "effective_nullability: ProjectRowFieldNullability",
    ):
        assert evidence in joined
    assert "fields=(*left_fields, *right_fields)" in join_builder
    assert "introduction_use=input_uses[1]" in join_builder
    assert "nulling_joins=right_nulling" in join_builder


def test_current_deferred_graph_mode_and_project_check_boundaries_match_audit() -> None:
    project_model = _python("src/pietto/_project/model.py")
    preservation = _python("src/pietto/_project/module_semantic_fact_preservation.py")
    row_graph = _python("src/pietto/_project/row_dependency_graph.py")
    composition = _python("src/pietto/_project/project_ir_composition.py")
    verification = _python("src/pietto/_project/project_ir_verification.py")
    phase62_verification = _python(
        "src/pietto/_project/project_phase62_verification.py"
    )
    carrier = _python("src/pietto/_project/module_carrier.py")
    cli = _python("src/pietto/cli.py")

    assert 'AUTHORED_JOIN_DEFERRED = "authored_join_deferred"' in project_model
    assert 'AUTHORED_JOIN_DEFERRED = "authored_join_deferred"' in row_graph
    assert "Authored JOIN semantic facts cannot publish a concrete state." in (
        preservation
    )
    assert "class ProjectRelationDependencyGraph:" in project_model
    assert "class ProjectIRProjectPlan:" in composition
    assert "Project IR actual-use graph must be acyclic." in composition
    assert "class ProjectIRAnalysisBundle:" in verification
    assert "reverse_uses: tuple[ProjectIRReverseUseEntry, ...]" in verification
    assert "class ProjectPhase62AnalysisBundle:" in phase62_verification
    assert "combined_reverse_uses:" in phase62_verification
    assert "Verified combined actual-use graph must remain acyclic." in (
        phase62_verification
    )

    assert 'LEGACY_FLAT = "legacy_flat"' in carrier
    assert 'EXPLICIT_MODULES = "explicit_modules"' in carrier
    assert 'PACKAGE_ROOT = "package_root"' in carrier
    assert "Explicit-module project semantics require all module sidecars." in (
        project_model
    )
    assert "Legacy-flat project semantics forbid module sidecars." in project_model
    assert "Package-root project semantics forbid source and module facts." in (
        project_model
    )
    semantic_result = project_model[
        project_model.index("class ProjectSemanticResult:") : project_model.index(
            "def build_empty_project_semantic_result("
        )
    ]
    assert "module_semantic_facts:" in semantic_result
    assert "effective_outputs" not in semantic_result
    assert "semantic_result = build_empty_project_semantic_result(parse_result)" in cli


def test_frozen_architecture_reconciles_all_mandatory_boundaries() -> None:
    architecture = " ".join(
        _section(_read(), "Frozen Phase-63 Architecture").split()
    ).replace("`", "")
    for evidence in (
        "ProjectDeclarationOccurrence = project declaration owner identity",
        "QueryBlockOccurrence = source and named-window scope identity",
        "third query-block identity = forbidden",
        "closed semantic sum",
        "there is no second joined expression type system",
        "unqualified candidate count 0 = ABSENT",
        "unqualified candidate count 1 = CONCRETE",
        "unqualified candidate count >1 = AMBIGUOUS with the complete bucket",
        "LET is the first post-JOIN scalar scope",
        "not name-visible without an authored binding",
        "AUTHORED_JOIN_DEFERRED is neither removed nor rewritten",
        "exactly one concrete output or one non-concrete terminal per relation owner",
        "no third normative dependency graph exists",
        "do not automatically become relationship endpoints or Phase-62 path nodes",
        "Generic JOIN ... ON over arbitrary effective row sources belongs to Phase 64",
        "Explicit reusable derived relationships belong to Phase 74",
        "retains Phase-62 fanout, chasm, alignment, and risk evidence",
        "QUALIFY is a distinct semantic stage after window evaluation and before final projection",
        "TRUE retains; FALSE and UNKNOWN drop",
        "without migrating selected-output-based WindowOccurrenceIdentity",
        "Window ordering does not establish final relation ordering",
        "no second final-field identity exists",
        "publishes no partial completed output",
        "without exposing private carriers or changing Project JSON v2",
        "Single-file, LEGACY_FLAT, and PACKAGE_ROOT JOIN paths remain typed fail-closed",
        "unary tail after the binary JOIN region",
        "JOIN remains binary, not a hidden unary operator",
    ):
        assert evidence in architecture


def test_owner_transfer_future_roadmap_and_exact_route_are_complete() -> None:
    document = _read()
    migration = _table(document, "Old-Owner To Future Roadmap v6 Migration Ledger")
    assert len(migration) == 53
    assert len({row[1] for row in migration}) == len(migration)
    assert {row[0] for row in migration if row[0].startswith("old Phase")} == {
        f"old Phase {phase}" for phase in range(63, 71)
    }
    assert {int(row[2]) for row in migration} == set(range(63, 98))
    assert all(row[3].startswith(("RETAINED", "ADDED")) for row in migration)
    normalized = " ".join(
        _section(document, "Old-Owner To Future Roadmap v6 Migration Ledger").split()
    )
    for retained in (
        "Additional JOIN kinds",
        "Single-match enforcement",
        "Multi-relation SQL",
        "Project emit-SQL",
        "Correlation and outer captures",
        "Nested results",
        "Null-safe, collation, NaN, and coercive equality",
        "Aggregate algebra and state",
        "Relationship import/export",
        "Remote packages/assets",
        "Dependency solver and canonical lockfile",
        "Optimizer memo",
        "Physical JOIN strategies",
        "Public Project-IR/nested/lineage schemas",
        "Persistent incremental-cache identity",
        "Formal rewrite certification",
        "Cloud/federation semantics",
        "Governance and security policy semantics",
        "Continuous/streaming query semantics distinct from finite result streaming",
    ):
        assert retained in normalized

    assert _table(document, "Future Roadmap v6") == FUTURE_ROADMAP
    assert _table(document, "Tentative Later Owners") == TENTATIVE_OWNERS
    assert _table(document, "Exact Phase-63 Route") == PHASE63_ROUTE
    assert "No numbered Phase-64+ Slice route is frozen here." in document
    assert "Slice 2 and all later Slices are unimplemented." in " ".join(
        document.split()
    )


def test_slice1_delta_is_exact_and_has_zero_production_behavior() -> None:
    document = _read()
    expected = _table(document, "Reader Closure And Changed-Path Lock")
    assert len(expected) == 6
    assert tuple(row[0] for row in expected).count("A") == 2
    assert tuple(row[0] for row in expected).count("M") == 4
    assert len({row[1] for row in expected}) == 6

    head = _git("rev-parse", "HEAD")
    available = tuple(
        line.split("\0", 1)
        for line in _git("log", "--first-parent", "--format=%H%x00%s").splitlines()
    )
    matches = tuple(commit for commit, subject in available if subject == SUBJECT)
    if matches:
        assert len(matches) == 1
        actual = tuple(
            tuple(line.split("\t", 1))
            for line in _git(
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "-r",
                matches[0],
            ).splitlines()
        )
    elif head == BASELINE:
        actual = tuple(
            (
                "A" if status == "??" else status,
                path,
            )
            for line in _git("status", "--short", "--untracked-files=all").splitlines()
            for status, path in (line.split(maxsplit=1),)
        )
    else:
        assert _git("rev-parse", "--is-shallow-repository") == "true"
        return

    assert len(actual) == 6
    assert len(set(actual)) == 6
    assert frozenset(actual) == frozenset(expected)

    assert not any(
        path.startswith(("src/", "grammar/", ".github/", "scripts/"))
        for _status, path in expected
    )
    for evidence in (
        "A2/M4/D0",
        "production 0",
        "grammar/generated 0",
        "public schema 0",
        "package/dependency/workflow/version 0",
        "SQL/Arrow/executor 0",
        "Phase-63 Slice-2 implementation 0",
        "UV_PYTHON=3.13 uv run python scripts/validate.py --timings",
        "PASS — PHASE63_SLICE1_JOINED_QUERY_BLOCK_PRODUCT_ARCHITECTURE_SOURCE_AUDIT_FUTURE_ROADMAP_ROUTE_LOCK_END_TO_END",
        "Phase 63 Slice 2 = NEXT / NOT IMPLEMENTED",
        "Do not begin Slice 2.",
    ):
        assert evidence in document
