from __future__ import annotations

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
SLICE6_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-slice6-completion-benchmark-phase60-readiness-v1.md"
)
PHASE60_SLICE1_SPEC = (
    REPO_ROOT
    / "docs/spec/phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md"
)
PHASE61_SLICE1_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-project-ir-architecture-source-audit-route-lock-v1.md"
)
PHASE61_SLICE2_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice2-project-ir-scope-stages-occurrences-anchors-construction-states-v1.md"
)
PHASE61_SLICE3_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice3-project-ir-row-output-properties-effects-estimate-boundary-v1.md"
)
PHASE61_SLICE4_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice4-project-ir-current-logical-operator-algebra-exact-property-transfer-v1.md"
)
PHASE61_SLICE5_IDENTITY_CONTINUATION_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice5-output-identity-authority-readiness-continuation-v1.md"
)
PHASE61_SLICE5_DATAFLOW_CONTINUATION_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice5-intra-relation-dataflow-readiness-continuation-v1.md"
)
PHASE61_SLICE5_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice5-canonical-single-relation-project-ir-construction-v1.md"
)
PHASE61_SLICE6_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice6-cross-module-relation-composition-acyclic-project-plan-dag-v1.md"
)
PHASE61_SLICE7_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice7-aggregate-window-evaluation-context-policy-effect-no-ambient-authority-v1.md"
)
PHASE61_SLICE8_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice8-integrity-verifier-analysis-invalidation-semantic-equivalence-optimizer-recursion-readiness-v1.md"
)
PHASE61_SLICE9_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice9-private-inspection-query-canonical-serialization-pure-boundary-v1.md"
)
PHASE61_SLICE10_SPEC = (
    REPO_ROOT
    / "docs/spec/phase61-slice10-real-authored-multi-module-project-ir-e2e-v1.md"
)
PHASE61_SLICE11_SPEC = (
    REPO_ROOT / "docs/spec/phase61-slice11-differential-compatibility-v1.md"
)
PHASE61_COMPLETION_SPEC = (
    REPO_ROOT / "docs/spec/phase61-completion-audit-phase62-handoff-v1.md"
)
PHASE62_SLICE1_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-relationship-join-keys-fd-grain-fanout-multifact-architecture-source-audit-route-lock-v1.md"
)
PHASE62_SLICE2_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice2-relationship-declaration-identity-endpoint-roles-module-local-resolution-construction-states-v1.md"
)
PHASE62_SLICE3_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice3-exact-field-correspondences-on-where-equality-null-behavior-constraint-scope-boundary-v1.md"
)
PHASE62_SLICE4_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice4-unique-null-policy-evidence-trust-strict-lax-row-uniqueness-candidate-keys-v1.md"
)
PHASE62_SLICE5_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice5-strict-lax-value-fd-basis-compact-indexes-targeted-closure-v1.md"
)
PHASE62_SLICE6_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice6-factorized-intrinsic-grain-basis-dependencies-optional-factors-global-grain-v1.md"
)
PHASE62_SLICE7_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice7-existing-operator-key-fd-grain-transfer-grain-comparison-v1.md"
)
PHASE62_SLICE8_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice8-referential-coverage-match-simple-full-directional-match-guarantees-v1.md"
)
PHASE62_SLICE9_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice9-explicit-relationship-paths-fanout-survival-null-effects-join-shape-analysis-v1.md"
)
PHASE62_SLICE10_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice10-authored-join-traversal-syntax-semantic-uses-v1.md"
)
PHASE62_SLICE11_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice11-project-ir-binary-join-region-multi-input-topology-null-extension-property-transfer-v1.md"
)
PHASE62_SLICE12_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice12-per-aggregate-fact-locality-chasm-detection-multi-fact-alignment-v1.md"
)
PHASE62_SLICE13_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice13-integrity-verifier-analysis-invalidation-bounded-bag-null-semantic-oracle-v1.md"
)
PHASE62_SLICE14_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice14-private-inspection-winner-free-query-pure-canonical-boundary-v1.md"
)
PHASE62_SLICE15_SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice15-real-authored-e2e-python-differential-metamorphic-join-assurance-v1.md"
)
PHASE62_SLICE16_SPEC = (
    REPO_ROOT / "docs/spec/phase62-completion-audit-phase63-handoff-v1.md"
)
PHASE63_SLICE1_SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md"
)
PHASE63_ARCHITECTURE_PREREQUISITE_SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-repository-architecture-authority-extraction-prerequisite-v1.md"
)
PHASE63_SLICE2_SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice2-query-block-owner-bridge-row-source-sum-states-mode-boundary-v1.md"
)
PHASE63_SLICE3_SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice3-scalar-reference-environment-resolution-facts-type-kernel-adapter-v1.md"
)
PHASE63_SLICE4_SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice4-bindings-visible-joined-fields-qualified-unqualified-lookup-v1.md"
)
PHASE63_SLICE5_SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice5-let-stage-namespace-lattice-shadowing-alias-laws-v1.md"
)
PHASE63_SLICE6_SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice6-post-join-row-semantics-nullability-lineage-property-bridge-v1.md"
)
PUBLISHED_INTERLUDE = (
    (
        "cc9884d1f24c9f1a8199fbdf0e20d48533e056d4",
        "ec0d5086f45ef72c49403a718ed45c45a8c44c30",
        "6a3d5d54ce728b60985718ed7b867721a1680f13",
        "33070069266",
        "Establish validation performance baseline",
    ),
    (
        "b6191d790040233a5ad62de7549c36bc0a555d9c",
        "874511592c4eee2b6ef024146b0017c335cd4ab4",
        "cc9884d1f24c9f1a8199fbdf0e20d48533e056d4",
        "33121173872",
        "Optimize differential probe execution",
    ),
    (
        "3f35fd31a1799bb12b8b74108ade64438c85b435",
        "a1a96e1d9a1b2f1ff2692661e773573711475091",
        "b6191d790040233a5ad62de7549c36bc0a555d9c",
        "33139945770",
        "Reuse repository fact acquisition",
    ),
    (
        "333f5ec5b8ef4e2cc1b5f79b108ee1857b1fe842",
        "e7bbd107151db075d63fe1742650eb1fd37dcbd7",
        "3f35fd31a1799bb12b8b74108ade64438c85b435",
        "33146266899",
        "Record static analysis no-gain closure",
    ),
    (
        "df7fe30381aa0c690b132b829627a11e971c0c59",
        "6f9aff8ddcf6e51fc28161ba18b5e1da55816de6",
        "333f5ec5b8ef4e2cc1b5f79b108ee1857b1fe842",
        "33151724681",
        "Adopt resource-aware xdist scheduling",
    ),
)
INTERLUDE_COMPLETION = (
    "e6da1fbe6b18ad88ae3c09568ba1f7d0e76817d1",
    "16d5618006e5c84a202300f0c69ea462dc9d8084",
    "df7fe30381aa0c690b132b829627a11e971c0c59",
    "33155753995",
    "Complete validation performance interlude",
)

EXPECTED_STATUS = (
    ("Package and CLI", "`0.1.0`"),
    ("Phase 55", "`COMPLETED`"),
    ("Phase 56", "`COMPLETED`"),
    ("Phase 57", "`COMPLETED`"),
    ("Phase 58", "`COMPLETED`"),
    ("Phase 59", "`COMPLETED`"),
    ("Validation/Test Performance Optimization Interlude", "`COMPLETED`"),
    ("Phase 60", "`COMPLETED`"),
    ("Phase 61", "`COMPLETED`"),
    ("Phase 62", "`COMPLETED`"),
    ("Phase 63", "`ACTIVE`"),
    ("Slice 1", "`COMPLETED / PUBLISHED`"),
    ("Slice 2", "`COMPLETED / PUBLISHED`"),
    ("Slice 3", "`COMPLETED / PUBLISHED`"),
    ("Slice 4", "`COMPLETED / PUBLISHED`"),
    ("Slice 5", "`COMPLETED / PUBLISHED`"),
    ("Slice 6", "`COMPLETED / PUBLISHED`"),
    ("Slice 7", "`NEXT / NOT IMPLEMENTED`"),
    ("Slice 8", "`NOT IMPLEMENTED`"),
    ("Slice 9", "`NOT IMPLEMENTED`"),
    ("Slice 10", "`NOT IMPLEMENTED`"),
    ("Slice 11", "`NOT IMPLEMENTED`"),
    ("Slice 12", "`NOT IMPLEMENTED`"),
    ("Slice 13", "`NOT IMPLEMENTED`"),
    ("Slice 14", "`NOT IMPLEMENTED`"),
    ("Slice 15", "`NOT IMPLEMENTED`"),
    ("Slice 16", "`NOT IMPLEMENTED`"),
    (
        "Next",
        "`Phase 63 Slice 7 — Completion Scheduling, Effective-Output Ledger Foundation, And Module Propagation`",
    ),
)
EXPECTED_PHASE58_STATE = "All 17 slices are completed. Phase 58 is complete."
EXPECTED_PHASE59_STATE = (
    "Phase 59 and all 12 Phase 59 Slices are completed. The Validation/Test\n"
    "Performance Optimization Interlude is also completed by successful natural\n"
    "exact-head CI on its Slice 6 commit, which activates Phase 60. The published\n"
    "Phase 59 route has exactly 12 slices."
)
EXPECTED_PHASE59_OWNER = "Local package graph, attribution, provenance, and lineage"
EXPECTED_PHASE60_STATE = (
    "Phase 60 and all 13 Slices are completed by live Git and successful natural\n"
    "exact-head CI. Phase 61 is active. The published Phase 60 route has exactly 13\n"
    "slices."
)
EXPECTED_PHASE60_OWNER = "Advanced Windows And Phase 51–60 Readiness Checkpoint"
EXPECTED_PHASE61_STATE = (
    "Phase 61 and all 12 numbered Slices are completed by live Git and successful\n"
    "natural exact-head CI. Both unnumbered Slice 5 prerequisites are also\n"
    "completed. Phase 62 is active, its Slice 1 route-lock publication candidate is\n"
    "current, and the completed Phase 61 route remains exactly 12 numbered slices."
)
EXPECTED_PHASE61_OWNER = (
    "Private target-independent Project Logical IR, exact semantic composition, "
    "and verifiable analysis boundary"
)
EXPECTED_PHASE62_STATE = (
    "Phase 62 and all 16 numbered Slices are completed by live Git and successful\n"
    "natural exact-head CI. Phase 63 is active, and the completed Phase-62 route\n"
    "remains exactly 16 numbered Slices."
)
EXPECTED_PHASE62_OWNER = (
    "Private occurrence-safe relationships and INNER/LEFT logical JOIN, typed "
    "key/FD/coverage evidence, factorized intrinsic grain, directional fanout, "
    "and multi-fact alignment analysis"
)
EXPECTED_PHASE63_STATE = (
    "Phase 63 is **Joined Query Block Semantic Completion And QUALIFY**. Slices 1–6\n"
    "are `COMPLETED / PUBLISHED`; Slice 7 is `NEXT / NOT IMPLEMENTED`; Slices 8–16\n"
    "are not implemented. The published route has exactly 16 numbered Slices."
)
EXPECTED_PHASE58_ROUTE = (
    (
        "1",
        "Architecture/scope/route lock; artifact identity; target denominator; single-file explain compatibility",
    ),
    (
        "2",
        "Public common model and success/failure envelope; logical paths; evidence posture; request/resolution/result vocabulary",
    ),
    (
        "3",
        "Package and requirement provenance projection; `declared_by`/`requested_by`",
    ),
    (
        "4",
        "Public requirement/target compatibility matrix; evaluation states; five checked statuses and reasons",
    ),
    (
        "5",
        "Public extension-catalog evidence projection; catalog coordinate/target/digest; selection; matchability/exposure; bounded provenance",
    ),
    ("6", "Conservative requirement/project portability derivation"),
    (
        "7",
        "Cross-section composition; artifact-local references; integrity; deterministic ordering; authority separation",
    ),
    (
        "8",
        "Public JSON v1 schema; deterministic serialization; success/failure envelopes; privacy and schema-evolution locks",
    ),
    ("9", "Runtime authority architecture and evidence-backed route expansion lock"),
    ("10", "Package-owned capability requirement declaration authority"),
    (
        "11",
        "Project-owned evaluated-target, profile, and catalog-availability authority",
    ),
    ("12", "Package-owned extension-signature typed physical selector authority"),
    ("13", "Project Explain runtime authority builder and zero-context adaptation"),
    (
        "14",
        "`pietto explain --project` text/JSON integration; existing single-file explain zero-delta",
    ),
    (
        "15",
        "Reachability-aware real multi-target E2E plus structural and direct-owner assurance for currently unreachable generic states",
    ),
    (
        "16",
        "Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel",
    ),
    (
        "17",
        "Completion audit; Phase 59 handoff; Phase 60/64/67/69 readiness reconciliation",
    ),
)
EXPECTED_PHASE59_ROUTE = (
    ("1", "Graph Domains, Identity Laws, And Route Lock"),
    ("2", "Private Package Graph Model And Snapshot Identity"),
    ("3", "Canonical Package Graph Construction"),
    ("4", "Requirement And Selector Attribution"),
    ("5", "Capability, Catalog, And Typed Negative Evidence Provenance"),
    ("6", "Direct, Transitive, And Why-Not Provenance"),
    ("7", "Package-to-Module Attribution Bridge"),
    ("8", "Semantic And Field-Lineage Integration"),
    (
        "9",
        "Private Graph Integrity, Inspection, Query, And Canonical Pure Boundary",
    ),
    ("10", "Real Multi-Package Provenance And Lineage E2E"),
    ("11", "Differential Compatibility Assurance"),
    ("12", "Completion Audit And Phase 60 Handoff"),
)
EXPECTED_INTERLUDE_ROUTE = (
    ("1", "Baseline Profiling, Cost Attribution, And Route Lock"),
    ("2", "Differential Probe Runtime Decomposition And Optimization"),
    ("3", "Repository Reader Acquisition Reuse"),
    ("4", "Validator Static-Analysis Stage Optimization Investigation"),
    (
        "5",
        "Current-Suite Isolation, Resource-Aware Xdist Scheduling, And CI Parallelism Decision",
    ),
    ("6", "Completion Benchmark And Phase 60 Readiness Assurance"),
)
EXPECTED_PHASE60_ROUTE = (
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
    ("13", "Phase 51–60 Completion/Readiness Audit And Phase 61 Handoff"),
)
EXPECTED_PHASE61_ROUTE = (
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
EXPECTED_PHASE62_ROUTE = (
    (
        "1",
        "Architecture, current/mature-source audit, formal BAG/NULL semantics, semantic laws, and route lock",
    ),
    (
        "2",
        "Relationship declaration identity, endpoint roles, module-local resolution, and construction states",
    ),
    (
        "3",
        "Exact field correspondences, ON/WHERE separation, equality/null behavior, and constraint-scope boundary",
    ),
    (
        "4",
        "UNIQUE null policy, evidence trust, strict/lax row uniqueness, and candidate keys",
    ),
    ("5", "Strict/lax value-FD basis, compact indexes, and targeted closure"),
    (
        "6",
        "Factorized intrinsic grain basis, grain dependencies, optional factors, and GLOBAL grain",
    ),
    ("7", "Existing-operator key/FD/grain transfer and grain comparison"),
    (
        "8",
        "Referential coverage, MATCH SIMPLE/FULL, and directional match guarantees",
    ),
    (
        "9",
        "Explicit relationship paths, fanout/survival/null effects, and join-shape analysis",
    ),
    ("10", "Authored JOIN/traversal syntax and semantic uses"),
    (
        "11",
        "Project IR binary JOIN region, multi-input topology, null extension, and property transfer",
    ),
    (
        "12",
        "Per-aggregate fact locality, chasm detection, and multi-fact alignment",
    ),
    (
        "13",
        "Integrity/verifier, analysis invalidation, and bounded BAG/NULL semantic oracle",
    ),
    ("14", "Private inspection, winner-free query, and pure canonical boundary"),
    (
        "15",
        "Real authored E2E, Python differential compatibility, and metamorphic JOIN assurance",
    ),
    ("16", "Completion audit and Phase 63 handoff"),
)
EXPECTED_PHASE63_ROUTE = (
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
EXPECTED_FUTURE_ROADMAP_V6 = (
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
EXPECTED_TENTATIVE_LATER_OWNERS = (
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
EXPECTED_INTERLUDE_SLICE6_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/validation-performance-interlude-slice6-completion-benchmark-phase60-readiness-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
)
EXPECTED_PHASE60_SLICE1_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase60_slice1_advanced_windows_scope_semantic_laws_route_lock.py",
    "tests/test_validation_performance_interlude_slice3_repository_reader_acquisition_reuse.py",
    "tests/test_workflow_lifecycle_validation_efficiency.py",
)
EXPECTED_PHASE60_SLICE2_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase60-slice2-authored-resolved-window-frame-model-v1.md",
    "docs/status.md",
    "src/pietto/semantic/window_semantics.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase60_slice2_authored_resolved_window_frame_model.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE60_SLICE3_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase60-slice3-frame-validation-function-policy-v1.md",
    "docs/status.md",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/semantic/window_navigation_analysis.py",
    "src/pietto/semantic/window_semantics.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase60_slice2_authored_resolved_window_frame_model.py",
    "tests/test_phase60_slice3_frame_validation_function_policy.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE60_SLICE4_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/phase60-slice4-rows-semantics-lowering-v1.md",
    "docs/status.md",
    "grammar/Pietto.g4",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "src/pietto/ast_builder.py",
    "src/pietto/ast_nodes.py",
    "src/pietto/ir/lowering.py",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/semantic/window_semantics.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase60_slice4_rows_semantics_lowering.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE60_SLICE5_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/phase60-slice5-range-semantics-lowering-v1.md",
    "docs/status.md",
    "grammar/Pietto.g4",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "src/pietto/ast_builder.py",
    "src/pietto/semantic/window_semantics.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase60_slice4_rows_semantics_lowering.py",
    "tests/test_phase60_slice5_range_semantics_lowering.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE60_SLICE6_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/phase60-slice6-groups-peer-semantics-v1.md",
    "docs/status.md",
    "grammar/Pietto.g4",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/ast_builder.py",
    "src/pietto/semantic/window_semantics.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase60_slice4_rows_semantics_lowering.py",
    "tests/test_phase60_slice5_range_semantics_lowering.py",
    "tests/test_phase60_slice6_groups_peer_semantics.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE60_SLICE7_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/phase60-slice7-exclude-semantics-v1.md",
    "docs/status.md",
    "grammar/Pietto.g4",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/ast_builder.py",
    "src/pietto/semantic/window_semantics.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase60_slice4_rows_semantics_lowering.py",
    "tests/test_phase60_slice5_range_semantics_lowering.py",
    "tests/test_phase60_slice7_exclude_semantics.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE60_SLICE8_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/diagnostics.md",
    "docs/spec/phase60-slice8-query-local-named-windows-v1.md",
    "docs/status.md",
    "grammar/Pietto.g4",
    "src/pietto/_project/module_semantic_fact_preservation.py",
    "src/pietto/_project/window_semantics.py",
    "src/pietto/ast_builder.py",
    "src/pietto/ast_nodes.py",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "src/pietto/ir/lowering.py",
    "src/pietto/semantic/expressions.py",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/semantic/window_semantics.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase54_semantic_fact_preservation.py",
    "tests/test_phase60_slice8_query_local_named_windows.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE60_SLICE9_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/phase60-slice9-value-navigation-modifiers-v1.md",
    "docs/status.md",
    "grammar/Pietto.g4",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "src/pietto/ast_builder.py",
    "src/pietto/ast_nodes.py",
    "src/pietto/semantic/model.py",
    "src/pietto/semantic/analyzer.py",
    "src/pietto/semantic/expressions.py",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/semantic/window_navigation_analysis.py",
    "src/pietto/semantic/window_semantics.py",
    "src/pietto/semantic/capability_windows.py",
    "src/pietto/ir/model.py",
    "src/pietto/ir/lowering.py",
    "src/pietto/sql/expressions.py",
    "src/pietto/sql/mysql_expressions.py",
    "src/pietto/_project/window_semantics.py",
    "src/pietto/_project/module_semantic_fact_preservation.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase60_slice9_value_navigation_modifiers.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
    "tests/test_ir_completion_audit.py",
    "tests/test_phase12_order_by.py",
    "tests/test_phase17_relation_schema_hardening_completion_audit.py",
    "tests/test_phase51_private_result_role_output_identity.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase56_slice3_canonical_capability_providers.py",
    "tests/test_phase56_slice10_completion_audit_phase57_handoff.py",
    "tests/test_phase57_slice1_postgresql_extension_signature_catalog_scope_lock.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase54_semantic_fact_preservation.py",
    "tests/test_phase60_slice3_frame_validation_function_policy.py",
    "tests/test_phase60_slice4_rows_semantics_lowering.py",
    "tests/test_phase60_slice5_range_semantics_lowering.py",
    "tests/test_phase60_slice7_exclude_semantics.py",
    "tests/test_phase60_slice8_query_local_named_windows.py",
)
EXPECTED_PHASE60_SLICE10_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/phase60-slice10-capability-lineage-inspection-integration-v1.md",
    "docs/status.md",
    "src/pietto/semantic/capability_windows.py",
    "src/pietto/semantic/model.py",
    "src/pietto/semantic/analyzer.py",
    "src/pietto/semantic/expressions.py",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/semantic/window_semantics.py",
    "src/pietto/ir/model.py",
    "src/pietto/ir/lowering.py",
    "src/pietto/ir/builder.py",
    "src/pietto/sql/window_strategy.py",
    "src/pietto/sql/expressions.py",
    "src/pietto/sql/mysql_expressions.py",
    "src/pietto/sql/relations.py",
    "src/pietto/sql/mysql_relations.py",
    "src/pietto/_project/window_semantics.py",
    "src/pietto/_project/window_persistence.py",
    "src/pietto/_project/module_semantic_fact_preservation.py",
    "src/pietto/_project/package_graph.py",
    "src/pietto/_project/package_graph_inspection.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
    "tests/test_phase17_relation_schema_hardening_completion_audit.py",
    "tests/test_phase51_private_result_role_output_identity.py",
    "tests/test_phase52_fail_closed_capability_lookup.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase52_private_capability_fact_foundation.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    "tests/test_phase54_semantic_fact_preservation.py",
    "tests/test_phase60_slice8_query_local_named_windows.py",
    "tests/test_phase60_slice9_value_navigation_modifiers.py",
    "tests/test_ir_completion_audit.py",
    "tests/test_phase59_slice2_private_package_graph_model_snapshot_identity.py",
    "tests/test_phase59_slice8_semantic_field_lineage_integration.py",
    "tests/test_phase59_slice9_private_graph_integrity_inspection_query_canonical_pure_boundary.py",
    "tests/test_phase59_slice11_differential_compatibility_assurance.py",
    "tests/test_phase59_slice12_completion_audit_phase60_handoff.py",
    "tests/test_phase60_slice10_capability_lineage_inspection_integration.py",
)
EXPECTED_PHASE60_SLICE11_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase60-slice11-real-authored-advanced-window-e2e-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase60_slice11_real_authored_advanced_window_e2e.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE60_SLICE12_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase60-slice12-differential-compatibility-v1.md",
    "docs/status.md",
    "tests/_pietto_phase60_window_differential_probe.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase60_slice12_differential_compatibility.py",
    "tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE60_SLICE13_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase60-completion-readiness-audit-phase61-handoff-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase60_slice13_completion_readiness_audit_phase61_handoff.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE1_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-project-ir-architecture-source-audit-route-lock-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice1_project_ir_architecture_source_audit_route_lock.py",
    "tests/test_validation_performance_interlude_slice3_repository_reader_acquisition_reuse.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
    "tests/test_workflow_lifecycle_validation_efficiency.py",
)
EXPECTED_PHASE61_SLICE2_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice2-project-ir-scope-stages-occurrences-anchors-construction-states-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice2_project_ir_scope_stages_occurrences_anchors_construction_states.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE3_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice3-project-ir-row-output-properties-effects-estimate-boundary-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir_properties.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice3_project_ir_row_output_properties_effects_estimate_boundary.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE4_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice4-project-ir-current-logical-operator-algebra-exact-property-transfer-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir_operators.py",
    "src/pietto/_project/project_ir_properties.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice4_project_ir_current_logical_operator_algebra_exact_property_transfer.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE5_IDENTITY_CONTINUATION_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice5-output-identity-authority-readiness-continuation-v1.md",
    "docs/status.md",
    "src/pietto/_project/model.py",
    "src/pietto/_project/module_attribution.py",
    "src/pietto/_project/module_inspection.py",
    "src/pietto/_project/module_package_neutral_identity.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py",
    "tests/test_phase61_slice5_output_identity_authority_readiness_continuation.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE5_DATAFLOW_CONTINUATION_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice5-intra-relation-dataflow-readiness-continuation-v1.md",
    "docs/status.md",
    "src/pietto/_project/module_semantic_fact_preservation.py",
    "src/pietto/_project/project_ir.py",
    "src/pietto/_project/project_ir_operators.py",
    "src/pietto/_project/project_ir_properties.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice1_project_ir_architecture_source_audit_route_lock.py",
    "tests/test_phase61_slice3_project_ir_row_output_properties_effects_estimate_boundary.py",
    "tests/test_phase61_slice4_project_ir_current_logical_operator_algebra_exact_property_transfer.py",
    "tests/test_phase61_slice5_intra_relation_dataflow_readiness_continuation.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE5_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice5-canonical-single-relation-project-ir-construction-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir.py",
    "src/pietto/_project/project_ir_construction.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice5_canonical_single_relation_project_ir_construction.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE6_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice6-cross-module-relation-composition-acyclic-project-plan-dag-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir.py",
    "src/pietto/_project/project_ir_composition.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice6_cross_module_relation_composition_acyclic_project_plan_dag.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE7_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice7-aggregate-window-evaluation-context-policy-effect-no-ambient-authority-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir_construction.py",
    "src/pietto/_project/project_ir_evaluation_context.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice5_canonical_single_relation_project_ir_construction.py",
    "tests/test_phase61_slice7_aggregate_window_evaluation_context_policy_effect_no_ambient_authority.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE8_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice8-integrity-verifier-analysis-invalidation-semantic-equivalence-optimizer-recursion-readiness-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir_verification.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice8_integrity_verifier_analysis_invalidation_semantic_equivalence_optimizer_recursion_readiness.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE9_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice9-private-inspection-query-canonical-serialization-pure-boundary-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir_inspection.py",
    "src/pietto/_project/project_ir_pure_boundary.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice9_private_inspection_query_canonical_serialization_pure_boundary.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE10_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice10-real-authored-multi-module-project-ir-e2e-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir_pipeline.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice10_real_authored_multi_module_project_ir_e2e.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE11_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-slice11-differential-compatibility-v1.md",
    "docs/status.md",
    "tests/_pietto_phase61_project_ir_differential_probe.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice11_differential_compatibility.py",
    "tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE61_SLICE12_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase61-completion-audit-phase62-handoff-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice12_completion_audit_phase62_handoff.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE1_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-relationship-join-keys-fd-grain-fanout-multifact-architecture-source-audit-route-lock-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase61_slice12_completion_audit_phase62_handoff.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_validation_performance_interlude_slice3_repository_reader_acquisition_reuse.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
    "tests/test_workflow_lifecycle_validation_efficiency.py",
)
EXPECTED_PHASE62_SLICE2_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice2-relationship-declaration-identity-endpoint-roles-module-local-resolution-construction-states-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_relationships.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice2_relationship_declaration_identity_endpoint_roles_module_local_resolution_construction_states.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE3_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/phase62-slice3-exact-field-correspondences-on-where-equality-null-behavior-constraint-scope-boundary-v1.md",
    "docs/status.md",
    "grammar/Pietto.g4",
    "src/pietto/_project/project_relationship_conditions.py",
    "src/pietto/ast_builder.py",
    "src/pietto/ast_nodes.py",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice3_exact_field_correspondences_on_where_equality_null_behavior_constraint_scope_boundary.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE4_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/phase62-slice4-unique-null-policy-evidence-trust-strict-lax-row-uniqueness-candidate-keys-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_row_keys.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice4_unique_null_policy_evidence_trust_strict_lax_row_uniqueness_candidate_keys.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE5_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice5-strict-lax-value-fd-basis-compact-indexes-targeted-closure-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_value_fds.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase33_cli_package_compatibility_hardening.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice5_strict_lax_value_fd_basis_compact_indexes_targeted_closure.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE6_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice6-factorized-intrinsic-grain-basis-dependencies-optional-factors-global-grain-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_grain.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice6_factorized_intrinsic_grain_basis_dependencies_optional_factors_global_grain.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE7_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice7-existing-operator-key-fd-grain-transfer-grain-comparison-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir_relational_properties.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice7_existing_operator_key_fd_grain_transfer_grain_comparison.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE8_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice8-referential-coverage-match-simple-full-directional-match-guarantees-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_relationship_match_guarantees.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice8_referential_coverage_match_simple_full_directional_match_guarantees.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE9_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice9-explicit-relationship-paths-fanout-survival-null-effects-join-shape-analysis-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_relationship_paths.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice9_explicit_relationship_paths_fanout_survival_null_effects_join_shape_analysis.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE10_CHANGED_PATHS = (
    "docs/language.md",
    "docs/roadmap.md",
    "docs/spec/phase62-slice10-authored-join-traversal-syntax-semantic-uses-v1.md",
    "docs/status.md",
    "grammar/Pietto.g4",
    "src/pietto/ast_nodes.py",
    "src/pietto/ast_builder.py",
    "src/pietto/ir/builder.py",
    "src/pietto/_project/model.py",
    "src/pietto/_project/module_relation_resolution.py",
    "src/pietto/_project/module_semantic_fact_preservation.py",
    "src/pietto/_project/row_dependency_graph.py",
    "src/pietto/_project/row_lineage.py",
    "src/pietto/_project/module_pure_boundary.py",
    "src/pietto/_project/project_ir_construction.py",
    "src/pietto/_project/project_relationship_uses.py",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase48_schema_availability_state_carrier.py",
    "tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice10_authored_join_traversal_syntax_semantic_uses.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE11_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice11-project-ir-binary-join-region-multi-input-topology-null-extension-property-transfer-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_ir.py",
    "src/pietto/_project/project_ir_properties.py",
    "src/pietto/_project/project_grain.py",
    "src/pietto/_project/project_ir_relational_properties.py",
    "src/pietto/_project/project_ir_joins.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice11_project_ir_binary_join_region_multi_input_topology_null_extension_property_transfer.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE12_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice12-per-aggregate-fact-locality-chasm-detection-multi-fact-alignment-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_multifact.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE13_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice13-integrity-verifier-analysis-invalidation-bounded-bag-null-semantic-oracle-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_phase62_verification.py",
    "src/pietto/_project/project_bag_null_oracle.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice13_integrity_verifier_analysis_invalidation_bounded_bag_null_semantic_oracle.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE14_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice14-private-inspection-winner-free-query-pure-canonical-boundary-v1.md",
    "docs/status.md",
    "src/pietto/_project/project_phase62_inspection.py",
    "src/pietto/_project/project_phase62_pure_boundary.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice14_private_inspection_winner_free_query_pure_canonical_boundary.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE15_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-slice15-real-authored-e2e-python-differential-metamorphic-join-assurance-v1.md",
    "docs/status.md",
    "tests/_pietto_phase62_join_differential_probe.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
    "tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py",
    "tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE62_SLICE16_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase62-completion-audit-phase63-handoff-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase62_slice16_completion_audit_phase63_handoff.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE63_SLICE1_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase63_slice1_joined_query_block_product_architecture_source_audit_future_roadmap_route_lock.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE63_ARCHITECTURE_PREREQUISITE_CHANGED_PATHS = (
    "AGENTS.md",
    "docs/architecture/product-architecture-v1.md",
    "docs/architecture/phase-initiation-gate-v1.md",
    "docs/architecture/identity-and-authority-laws-v1.md",
    "docs/architecture/layering-and-coupling-laws-v1.md",
    "docs/references/product-design-lessons-v1.md",
    "docs/plan/README.md",
    "docs/plan/pietto_product_plan_2026-09-02.md",
    "docs/spec/phase63-repository-architecture-authority-extraction-prerequisite-v1.md",
    "docs/roadmap.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_repository_architecture_authority_alignment.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE63_SLICE2_CHANGED_PATHS = (
    "src/pietto/_project/project_query_block.py",
    "docs/spec/phase63-slice2-query-block-owner-bridge-row-source-sum-states-mode-boundary-v1.md",
    "tests/test_phase63_slice2_query_block_owner_bridge_row_source_sum_states_mode_boundary.py",
    "docs/roadmap.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE63_SLICE3_CHANGED_PATHS = (
    "src/pietto/_project/project_scalar_references.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "docs/spec/phase63-slice3-scalar-reference-environment-resolution-facts-type-kernel-adapter-v1.md",
    "tests/test_phase63_slice3_scalar_reference_environment_resolution_facts_type_kernel_adapter.py",
    "docs/roadmap.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE63_SLICE4_CHANGED_PATHS = (
    "src/pietto/_project/project_scalar_bindings.py",
    "docs/spec/phase63-slice4-bindings-visible-joined-fields-qualified-unqualified-lookup-v1.md",
    "tests/test_phase63_slice4_bindings_visible_joined_fields_qualified_unqualified_lookup.py",
    "docs/roadmap.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE63_SLICE5_CHANGED_PATHS = (
    "src/pietto/_project/project_scalar_namespaces.py",
    "docs/spec/phase63-slice5-let-stage-namespace-lattice-shadowing-alias-laws-v1.md",
    "tests/test_phase63_slice5_let_stage_namespace_lattice_shadowing_alias_laws.py",
    "docs/roadmap.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
EXPECTED_PHASE63_SLICE6_CHANGED_PATHS = (
    "src/pietto/_project/project_joined_row_semantics.py",
    "docs/spec/phase63-slice6-post-join-row-semantics-nullability-lineage-property-bridge-v1.md",
    "tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py",
    "docs/roadmap.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table_rows(document: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in document.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )


def test_active_status_table_and_authority_prose_are_exact() -> None:
    status = _read(STATUS)
    assert _table_rows(status)[1:] == EXPECTED_STATUS
    normalized = " ".join(status.split())
    assert (
        "Phase 59 and the Validation/Test Performance Optimization Interlude are "
        "completed by live Git and successful natural exact-head CI" in normalized
    )
    assert "Phase 60 and all 13 Slices are completed" in normalized
    assert "single Slice 13 publication commit" in normalized
    assert "without a status-only follow-up commit" in normalized
    assert "Phase 61, all 12 numbered Slices" in normalized
    assert "both unnumbered Slice 5 prerequisites are completed" in normalized
    assert "single Slice 12 publication commit" in normalized
    assert "Phase61 self-owned-open = 0" in normalized
    assert "Phase 62 and all 16 numbered Slices are completed" in normalized
    assert "d9a423fe6822ed549e3063299a4781cd7ed4b480" in normalized
    assert "33598904937" in normalized
    assert "Phase62 material exits = 15/15" in normalized
    assert "Phase62 self-owned-open = 0" in normalized
    assert "Phase 63 is active" in normalized
    assert "Slice 1 is `COMPLETED / PUBLISHED`" in normalized
    assert "Product/Phase Initiation Gate v3" in normalized
    assert "external product/research source audit" in normalized
    assert "Future Roadmap v6" in normalized
    assert "complete old-owner migration ledger" in normalized
    assert "Joined Query Block Semantic Completion" in normalized
    assert "exactly 16 Phase-63 Slices" in normalized
    assert (
        "changes no production/public/SQL/CLI/JSON/package/dependency/workflow/version"
        in normalized
    )
    assert "repository architecture authority extraction" in normalized
    assert "unnumbered, documentation-only authority projection" in normalized
    assert "not a numbered Slice, not Slice 2" in normalized
    assert "not implementation of Slice 2" in normalized
    assert "no fake lifecycle-table row" in normalized
    assert "publication state remains subordinate" in normalized
    assert "Phase 63 Slice 2 is `COMPLETED / PUBLISHED`" in normalized
    assert "private query-block foundation" in normalized
    assert "existing declaration/query-block identities" in normalized
    assert "exact VERIFIED Phase-62 concrete JOIN-region final outputs" in normalized
    assert "preserves `AUTHORED_JOIN_DEFERRED`" in normalized
    assert "closed concrete or typed non-concrete construction results" in normalized
    assert "`EXPLICIT_MODULES`-only" in normalized
    assert "`LEGACY_FLAT` and `PACKAGE_ROOT` remain typed fail-closed" in normalized
    assert "Slice 2 adds no scalar lookup" in normalized
    assert "Phase 63 Slice 3 is `COMPLETED / PUBLISHED`" in normalized
    assert "private scalar-reference foundation" in normalized
    assert "exact ordinary/joined field occurrences in structural order" in normalized
    assert "duplicate spellings and effective JOIN nullability" in normalized
    assert "existing `ABSENT`/`CONCRETE`/`AMBIGUOUS` status law" in normalized
    assert "performs no name lookup or winner selection" in normalized
    assert "feed the existing `infer_row_expression` kernel" in normalized
    assert "publishes no partial root type" in normalized
    assert "Slice 3 adds no bindings, visibility, LET" in normalized
    assert "Phase 63 Slice 4 is `COMPLETED / PUBLISHED`" in normalized
    assert "private joined scalar binding foundation" in normalized
    assert (
        "exact Phase-62 binding occurrences and JOIN introduction provenance"
        in normalized
    )
    assert "Visible authored-binding fields and hidden multi-hop fields" in normalized
    assert "without copying or synthetic bindings" in normalized
    assert "Qualified lookup uses only authored binding names" in normalized
    assert "unqualified lookup retains complete ordered candidate buckets" in normalized
    assert (
        "Existing Slice-3 resolution facts and the semantic type kernel remain unchanged"
        in normalized
    )
    assert "Slice 4 adds no LET, shadowing" in normalized
    assert "Phase 63 Slice 5 is `COMPLETED / PUBLISHED`" in normalized
    assert "private joined LET namespace foundation" in normalized
    assert (
        "exact `LetBinding` occurrences and immutable `POST_JOIN_INPUT`" in normalized
    )
    assert "source-ordered `LET_BINDING(i)`, and `POST_LET` namespaces" in normalized
    assert "Complete-clause admission preserves duplicate" in normalized
    assert "binding/relation shadowing, dependency, aggregate-context" in normalized
    assert "Bare earlier LET values and exact Slice-4 fields feed" in normalized
    assert "qualified LET and projection-alias lookup remain absent" in normalized
    assert "Non-concrete results publish no `POST_LET`" in normalized
    assert "Slice 5 adds no post-JOIN property bridge" in normalized
    assert "Phase 63 Slice 6 is `COMPLETED / PUBLISHED`" in normalized
    assert "private post-JOIN row-semantic bridge" in normalized
    assert "every final joined occurrence, effective nullability" in normalized
    assert "exact upstream canonical field identity and existing concrete" in normalized
    assert "final Phase-62 relational and multi-fact property objects" in normalized
    assert "Hidden and repeated occurrences remain complete and distinct" in normalized
    assert (
        "Computed/LET/grouped/window upstreams with deferred module lineage"
        in normalized
    )
    assert "no legacy name-based lineage is substituted" in normalized
    assert (
        "Non-concrete Slice-5 roots also publish no concrete row-semantic stage"
        in normalized
    )
    assert "Historical `AUTHORED_JOIN_DEFERRED` remains unchanged" in normalized
    assert "Slice 6 adds no filtering, grouping, aggregate repair" in normalized
    assert "Phase 63 Slice 7 is `NEXT / NOT IMPLEMENTED`" in normalized
    assert "Slices 8–16 and every Phase-64+ implementation remain" in normalized
    prerequisite_target = (
        "spec/phase63-repository-architecture-authority-extraction-prerequisite-v1.md"
    )
    assert f"]({prerequisite_target})" in status
    assert (STATUS.parent / prerequisite_target).is_file()
    slice2_target = "spec/phase63-slice2-query-block-owner-bridge-row-source-sum-states-mode-boundary-v1.md"
    assert f"]({slice2_target})" in status
    assert (STATUS.parent / slice2_target).resolve() == PHASE63_SLICE2_SPEC
    assert PHASE63_SLICE2_SPEC.is_file()
    slice3_target = "spec/phase63-slice3-scalar-reference-environment-resolution-facts-type-kernel-adapter-v1.md"
    assert f"]({slice3_target})" in status
    assert (STATUS.parent / slice3_target).resolve() == PHASE63_SLICE3_SPEC
    assert PHASE63_SLICE3_SPEC.is_file()
    slice4_target = "spec/phase63-slice4-bindings-visible-joined-fields-qualified-unqualified-lookup-v1.md"
    assert f"]({slice4_target})" in status
    assert (STATUS.parent / slice4_target).resolve() == PHASE63_SLICE4_SPEC
    assert PHASE63_SLICE4_SPEC.is_file()
    slice5_target = (
        "spec/phase63-slice5-let-stage-namespace-lattice-shadowing-alias-laws-v1.md"
    )
    assert f"]({slice5_target})" in status
    assert (STATUS.parent / slice5_target).resolve() == PHASE63_SLICE5_SPEC
    assert PHASE63_SLICE5_SPEC.is_file()
    slice6_target = "spec/phase63-slice6-post-join-row-semantics-nullability-lineage-property-bridge-v1.md"
    assert f"]({slice6_target})" in status
    assert (STATUS.parent / slice6_target).resolve() == PHASE63_SLICE6_SPEC
    assert PHASE63_SLICE6_SPEC.is_file()
    assert not any(
        marker in status for marker in ("TO" + "DO", "FIX" + "ME", "T" + "BD")
    )


def test_active_roadmap_current_owner_sentence_and_routes_are_exact() -> None:
    roadmap = _read(ROADMAP)
    roadmap_normalized = " ".join(roadmap.split())
    phase58 = _section(roadmap, "Phase 58 route").lstrip()
    phase59 = _section(roadmap, "Phase 59 route").lstrip()
    phase60 = _section(roadmap, "Phase 60 route").lstrip()
    phase61 = _section(roadmap, "Phase 61 route").lstrip()
    phase62 = _section(roadmap, "Phase 62 route").lstrip()
    phase63 = _section(roadmap, "Phase 63 route").lstrip()
    phase60_normalized = " ".join(phase60.split())
    assert phase58.startswith(f"{EXPECTED_PHASE58_STATE}\n")
    assert phase58.count(EXPECTED_PHASE58_STATE) == 1
    assert _table_rows(phase58)[1:] == EXPECTED_PHASE58_ROUTE
    assert phase59.startswith(f"{EXPECTED_PHASE59_STATE}\n")
    assert phase59.count(EXPECTED_PHASE59_STATE) == 1
    assert phase59.count(EXPECTED_PHASE59_OWNER) == 1
    assert _table_rows(phase59)[1:] == EXPECTED_PHASE59_ROUTE
    assert phase60.startswith(f"{EXPECTED_PHASE60_STATE}\n")
    assert phase60.count(EXPECTED_PHASE60_STATE) == 1
    assert phase60.count(EXPECTED_PHASE60_OWNER) == 1
    assert _table_rows(phase60)[1:] == EXPECTED_PHASE60_ROUTE
    assert "phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md" in phase60
    assert "phase60-slice2-authored-resolved-window-frame-model-v1.md" in phase60
    assert "phase60-slice3-frame-validation-function-policy-v1.md" in phase60
    assert "phase60-slice4-rows-semantics-lowering-v1.md" in phase60
    assert "phase60-slice5-range-semantics-lowering-v1.md" in phase60
    assert "phase60-slice6-groups-peer-semantics-v1.md" in phase60
    assert "phase60-slice7-exclude-semantics-v1.md" in phase60
    assert "phase60-slice8-query-local-named-windows-v1.md" in phase60
    assert "phase60-slice9-value-navigation-modifiers-v1.md" in phase60
    assert "phase60-slice10-capability-lineage-inspection-integration-v1.md" in phase60
    assert "phase60-slice11-real-authored-advanced-window-e2e-v1.md" in phase60
    assert "phase60-slice12-differential-compatibility-v1.md" in phase60
    assert "phase60-completion-readiness-audit-phase61-handoff-v1.md" in phase60
    assert "private frozen authored/resolved window-frame model" in phase60
    assert "private validated semantic stage" in phase60
    assert "authored ROWS grammar/AST path" in phase60
    assert "Slice 9 introduces the first legal frame-sensitive" in phase60
    assert "authored RANGE" in phase60
    assert "canonical peer authority" in phase60
    assert "lazy post-clipping physical-membership view" in phase60
    assert "collection-first exact namespaces" in phase60
    assert "zero Phase-60 self-owned-open subjects" in phase60_normalized
    assert "Phase 61 — Project IR And Semantic Composition" in phase60_normalized
    assert "fresh architecture/source audit" in phase60_normalized
    assert "did not start Phase 61" in phase60

    assert phase61.startswith(f"{EXPECTED_PHASE61_STATE}\n")
    assert phase61.count(EXPECTED_PHASE61_STATE) == 1
    phase61_normalized = " ".join(phase61.split())
    assert not any(
        marker in phase61 for marker in ("TO" + "DO", "FIX" + "ME", "T" + "BD")
    )
    assert phase61_normalized.count(EXPECTED_PHASE61_OWNER) == 1
    assert _table_rows(phase61)[1:] == EXPECTED_PHASE61_ROUTE
    for evidence in (
        "phase61-project-ir-architecture-source-audit-route-lock-v1.md",
        "phase61-slice2-project-ir-scope-stages-occurrences-anchors-construction-states-v1.md",
        "existing script-level `RelationIR`",
        "Project semantic facts",
        "bag semantics",
        "provided properties, required input properties, estimates, and effects",
        "no Project IR production carrier",
        "`src/pietto/_project/project_ir.py`",
        "opaque snapshot scope",
        "four nominally distinct local ref domains",
        "constrained concrete/non-concrete relation-subject sum",
        "adds no operator kind",
        "phase61-slice3-project-ir-row-output-properties-effects-estimate-boundary-v1.md",
        "`src/pietto/_project/project_ir_properties.py`",
        "separate private semantic-property layer",
        "current scalar and BAG relation-row outputs",
        "conservative unknown effects",
        "empty estimate boundary",
        "adds no operator, property transfer",
        "phase61-slice4-project-ir-current-logical-operator-algebra-exact-property-transfer-v1.md",
        "`src/pietto/_project/project_ir_operators.py`",
        "exact eight-kind current logical operator algebra",
        "conservative exact preservation/establishment transfer proofs",
        "narrow consumer-side row-shape compatibility result",
        "adds no canonical builder, ref allocation",
        "phase61-slice5-output-identity-authority-readiness-continuation-v1.md",
        "decouples exact relation-output field occurrence identity",
        "`ProjectModuleRowFieldIdentity` as the sole row-field identity domain",
        "complete semantic relation-output attribution",
        "grouped/aggregate/window lineage to remain deferred",
        "adds no Project IR builder, new identity domain",
        "phase61-slice5-intra-relation-dataflow-readiness-continuation-v1.md",
        "semantic `INPUT`, `BASE_RESULT`, and `FINAL` row checkpoints",
        "plan-local stage fields/scalars",
        "exact operator-flow uses",
        "operator tuple order agrees",
        "adds no allocator, canonical builder",
        "phase61-slice5-canonical-single-relation-project-ir-construction-v1.md",
        "`src/pietto/_project/project_ir_construction.py`",
        "explicit immutable snapshot allocation state",
        "one row output per operator",
        "Non-concrete relations retain typed zero-allocation terminals",
        "phase61-slice6-cross-module-relation-composition-acyclic-project-plan-dag-v1.md",
        "`src/pietto/_project/project_ir_composition.py`",
        "dependency-environment/source order",
        "exact resolved relation-row use",
        "owner-local semantic source order",
        "derives acyclicity only from actual uses",
        "phase61-slice7-aggregate-window-evaluation-context-policy-effect-no-ambient-authority-v1.md",
        "`src/pietto/_project/project_ir_evaluation_context.py`",
        "One context per concrete `GROUP_AGGREGATE`",
        "exact stream input and semantic `BASE_RESULT` checkpoint",
        "existing stage-local scalar, window policy, and effect objects",
        "Global aggregates remain valid evaluation contexts",
        "phase61-slice8-integrity-verifier-analysis-invalidation-semantic-equivalence-optimizer-recursion-readiness-v1.md",
        "`src/pietto/_project/project_ir_verification.py`",
        "typed `VERIFIED` or `INVALID` result",
        "fresh complete reverse-use",
        "semantic-equivalence candidate analyses",
        "verification always requires rerun",
        "Unknown current evidence blocks rewrite readiness",
        "Ordinary cycles remain invalid",
        "phase61-slice9-private-inspection-query-canonical-serialization-pure-boundary-v1.md",
        "`src/pietto/_project/project_ir_inspection.py`",
        "`src/pietto/_project/project_ir_pure_boundary.py`",
        "verified-only private inspection",
        "Queries accept typed runtime refs",
        "sole canonical encoder",
        "Equal bytes remain distinct",
        "phase61-slice10-real-authored-multi-module-project-ir-e2e-v1.md",
        "`src/pietto/_project/project_ir_pipeline.py`",
        "exact existing `ProjectSemanticResult`",
        "explicit `ProjectIRAllocationState`",
        "`INVALID` stops before analysis",
        "two-hop re-export route",
        "full current eight-stage relation path",
        "phase61-slice11-differential-compatibility-v1.md",
        "`tests/_pietto_phase61_project_ir_differential_probe.py`",
        "One reviewed common manifest",
        "Python 3.12/3.13",
        "four fixed hash seeds",
        "normal/reverse file creation",
        "isolated installed wheel",
        "controlled verifier corruption",
        "phase61-completion-audit-phase62-handoff-v1.md",
        "13 already published Phase 61 units",
        "13/13 exit ledger",
        "Phase61 self-owned-open = 0",
        "Phase 62 readiness",
        "NEXT / NOT IMPLEMENTED",
        "Phase 62 Slice 1 has now rebound that authority",
        "frozen its route",
    ):
        assert evidence in phase61_normalized

    assert phase62.startswith(f"{EXPECTED_PHASE62_STATE}\n")
    assert phase62.count(EXPECTED_PHASE62_STATE) == 1
    phase62_normalized = " ".join(phase62.split())
    assert not any(
        marker in phase62 for marker in ("TO" + "DO", "FIX" + "ME", "T" + "BD")
    )
    assert phase62_normalized.count(EXPECTED_PHASE62_OWNER) == 1
    assert _table_rows(phase62)[1:] == EXPECTED_PHASE62_ROUTE
    for evidence in (
        "phase62-relationship-join-keys-fd-grain-fanout-multifact-architecture-source-audit-route-lock-v1.md",
        "current Pietto relationship and authored `UNIQUE` authority",
        "target-independent finite-BAG and SQL-NULL reference model",
        "relationship/endpoint/traversal/path/JOIN identity",
        "value FDs",
        "row uniqueness/keys",
        "grain dependencies",
        "referential coverage",
        "directional match guarantees",
        "multi-fact alignment",
        "documentation/static assurance only",
        "changes no grammar, AST",
        "portability-repair child completed Slice 1",
        "`src/pietto/_project/project_relationships.py`",
        "phase62-slice2-relationship-declaration-identity-endpoint-roles-module-local-resolution-construction-states-v1.md",
        "existing `ProjectSemanticResult`",
        "existing `check_relationship_metadata` semantic owner",
        "UNKNOWN/BLOCKED/AMBIGUOUS terminals",
        "adds no grammar, public `SemanticModel`",
        "publication commit completes Slice 2",
        "optional authored relationship `on` clause",
        "`src/pietto/_project/project_relationship_conditions.py`",
        "phase62-slice3-exact-field-correspondences-on-where-equality-null-behavior-constraint-scope-boundary-v1.md",
        "exact local/imported Project field",
        "TRUE-only/NULL-rejecting semantics",
        "no partial correspondence facts",
        "adds no public relationship semantic field, key/FD",
        "publication commit completes Slice 3",
        "`src/pietto/_project/project_row_keys.py`",
        "phase62-slice4-unique-null-policy-evidence-trust-strict-lax-row-uniqueness-candidate-keys-v1.md",
        "trusted `NULLS_DISTINCT` Pietto model contract",
        "all-`NON_NULL` determinants produce STRICT evidence",
        "nullable/unknown determinants remain LAX",
        "complete non-dominated antichain",
        "adds no grammar, public semantic field, FD, grain",
        "`src/pietto/_project/project_value_fds.py`",
        "phase62-slice5-strict-lax-value-fd-basis-compact-indexes-targeted-closure-v1.md",
        "one direct STRICT/LAX value FD per non-trivial candidate key",
        "one exact ordered field universe",
        "LHS-incident worklists",
        "epistemic `PROVEN`/`NOT_PROVEN`",
        "exact candidate premise and all of its authored supports",
        "adds no grammar, public semantic field, authored/general/catalog FD",
        "`src/pietto/_project/project_grain.py`",
        "phase62-slice6-factorized-intrinsic-grain-basis-dependencies-optional-factors-global-grain-v1.md",
        "concrete Source creates one distinct FACTORIZED intrinsic domain",
        "actual zero-key aggregate contexts create GLOBAL with zero factors",
        "distinct basis-local typed factor kernel",
        "non-constructible before logical JOIN/nulling authority",
        "adds no grammar, public semantic field, operator grain/key/FD transfer",
        "Phase 62 Slice 7 — Existing-Operator Key/FD/Grain Transfer And Grain Comparison",
        "completed Slice 6 without a status-only follow-up commit and handed off",
        "`project_ir_relational_properties.py`",
        "phase62-slice7-existing-operator-key-fd-grain-transfer-grain-comparison-v1.md",
        "`project_relationship_match_guarantees.py`",
        "phase62-slice8-referential-coverage-match-simple-full-directional-match-guarantees-v1.md",
        "two occurrence-safe directions with independent lower/upper evidence",
        "current authored source explicitly lacks a positive producer",
        "Phase 62 Slice 9 — Explicit Relationship Paths, Fanout/Survival/Null Effects, And Join-Shape Analysis",
        "completed it without a status-only commit and handed off",
        "`project_relationship_paths.py`",
        "phase62-slice9-explicit-relationship-paths-fanout-survival-null-effects-join-shape-analysis-v1.md",
        "exact direct-candidate index",
        "no automatic multi-hop search or winner",
        "Phase 62 Slice 10 — Authored JOIN/Traversal Syntax And Semantic Uses",
        "phase62-slice10-authored-join-traversal-syntax-semantic-uses-v1.md",
        "authored INNER/LEFT JOIN clauses",
        "`AUTHORED_JOIN_DEFERRED`",
        "zero-allocation non-concrete Project IR terminal",
        "Phase 62 Slice 11 — Project IR Binary JOIN Region, Multi-Input Topology, Null Extension, And Property Transfer",
        "phase62-slice11-project-ir-binary-join-region-multi-input-topology-null-extension-property-transfer-v1.md",
        "same-snapshot post-base binary JOIN-region stage",
        "one binary node per authored path step",
        "positive `NULL_EXTENSION` provenance",
        "Phase 62 Slice 12 — Per-Aggregate Fact Locality, Chasm Detection, And Multi-Fact Alignment",
        "`src/pietto/_project/project_multifact.py`",
        "phase62-slice12-per-aggregate-fact-locality-chasm-detection-multi-fact-alignment-v1.md",
        "Every concrete aggregate result becomes one occurrence-safe fact",
        "winner-free actual common-grain buckets",
        "`AMBIGUOUS_PATH` or `INSUFFICIENT_EVIDENCE`",
        "Phase 62 Slice 13 — Integrity/Verifier, Analysis Invalidation, And Bounded BAG/NULL Semantic Oracle",
        "`project_phase62_verification.py`",
        "`project_bag_null_oracle.py`",
        "phase62-slice13-integrity-verifier-analysis-invalidation-bounded-bag-null-semantic-oracle-v1.md",
        "combined actual-use DAG",
        "five detachable analyses",
        "three-valued NULL and finite-BAG multiplicity semantics",
        "verifier never invokes the oracle",
        "Phase 62 Slice 14 — Private Inspection, Winner-Free Query, And Pure Canonical Boundary",
        "`project_phase62_inspection.py`",
        "`project_phase62_pure_boundary.py`",
        "phase62-slice14-private-inspection-winner-free-query-pure-canonical-boundary-v1.md",
        "exact VERIFIED Slice-13 analysis bundle",
        "typed winner-free tuple queries",
        "`pietto.phase62-inspection.v1`",
        "canonical bytes are not semantic",
        "Phase 62 Slice 15 — Real Authored E2E, Python Differential Compatibility, And Metamorphic JOIN Assurance",
        "phase62-slice15-real-authored-e2e-python-differential-metamorphic-join-assurance-v1.md",
        "real authored two-module Project corpus",
        "Python 3.12/3.13",
        "four fixed hash seeds",
        "direct versus VIA",
        "parallel ambiguity",
        "target-UNIQUE removal",
        "INNER versus LEFT",
        "dependent non-chasm chain",
        "Phase 62 Slice 16 — Completion Audit And Phase 63 Handoff",
        "phase62-completion-audit-phase63-handoff-v1.md",
        "15 successful publication terminals",
        "three preserved failed heads",
        "`Phase62 self-owned-open = 0`",
        "Successful natural exact-head CI completed Phase 62",
        "Phase 63 is now active",
        "historical evidence",
    ):
        assert evidence in phase62_normalized

    assert phase63.startswith(f"{EXPECTED_PHASE63_STATE}\n")
    assert phase63.count(EXPECTED_PHASE63_STATE) == 1
    assert _table_rows(phase63)[1:] == EXPECTED_PHASE63_ROUTE
    phase63_normalized = " ".join(phase63.split())
    for evidence in (
        "phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md",
        "Product/Phase Initiation Gate v3",
        "12 reconciled live source findings",
        "16 exact external reference records",
        "old-owner migration ledger",
        "ProjectDeclarationOccurrence",
        "QueryBlockOccurrence",
        "no third query-block identity",
        "flattened joined `RowSchema`",
        "second expression type system",
        "third normative dependency graph",
        "partial completed output",
        "AUTHORED_JOIN_DEFERRED",
        "effective relation-output ledger",
        "EXPLICIT_MODULES",
        "no-new-JOIN blocks",
        "do not automatically become relationship endpoints",
        "`LET` is the first post-JOIN scalar scope",
        "hidden intermediate path fields remain non-nameable",
        "fanout/chasm/risk evidence",
        "`QUALIFY` is a distinct stage",
        "TRUE retains while FALSE/UNKNOWN drop",
        "selected-output window identity",
        "unary tail after the binary JOIN region",
        "Slice 4 `NEXT / NOT IMPLEMENTED`",
        "repository architecture authority extraction prerequisite",
        "unnumbered, documentation-only authority projection",
        "does not alter this 16-Slice route",
        "this roadmap owns phase-level future ownership and release milestones",
        "published phase specs own exact phase/Slice contracts",
        "`docs/plan/` remains historical",
        "phase63-slice2-query-block-owner-bridge-row-source-sum-states-mode-boundary-v1.md",
        "existing concrete relation outputs or exact VERIFIED Phase-62",
        "ordered `ProjectIRJoinedRowShape.fields` tuple and provenance",
        "without `RowSchema` or name-map flattening",
        "separate verified joined-row-source authority",
        "effective relation-output ledger remains Slice 7 ownership",
        "Positive Slice-2 construction is `EXPLICIT_MODULES`-only",
        "Slice 2 adds no scalar lookup",
        "natural exact-head CI completes Slice 2",
        "phase63-slice3-scalar-reference-environment-resolution-facts-type-kernel-adapter-v1.md",
        "exact Slice-2 row-field occurrence into one ordered scalar environment entry",
        "use effective JOIN nullability",
        "Duplicate spellings remain distinct",
        "no joined `RowSchema` or name map",
        "caller-supplied complete candidate bucket",
        "Slice 3 validates 0/1/N shape without discovering names",
        "Slice 4 still owns bindings, visibility, and qualified/unqualified lookup",
        "pre-seeded into `infer_row_expression`",
        "sole function/operator/nullability type-composition kernel",
        "publishes no partial root type",
        "Slice 3 adds no binding",
        "natural exact-head CI completes Slice 3",
        "phase63-slice4-bindings-visible-joined-fields-qualified-unqualified-lookup-v1.md",
        "exact Phase-62 binding occurrences and ledger",
        "first binary JOIN's left input use",
        "exact terminal path-step right input use",
        "Visible binding fields and hidden multi-hop intermediate fields form an exact partition",
        "receive no synthetic binding",
        "Qualified lookup matches only authored `binding.field`",
        "never the underlying `relation_name` as a fallback",
        "Unqualified lookup enumerates every visible same-spelling occurrence",
        "complete `AMBIGUOUS` results without a winner",
        "unchanged semantic type kernel",
        "Slice 4 adds no LET, shadowing",
        "natural exact-head CI completes Slice 4",
        "leaves Slice 5 `NEXT / NOT IMPLEMENTED`",
        "phase63-slice5-let-stage-namespace-lattice-shadowing-alias-laws-v1.md",
        "exact Slice-4 root",
        "source ordinal and exact AST occurrence",
        "one immutable `LET_BINDING(i)` prefix per authored occurrence",
        "without a joined `RowSchema` or normative name map",
        "invalidates every duplicate occurrence",
        "Hidden intermediate fields remain non-nameable",
        "qualified references remain Slice-4 fields only",
        "projection aliases never enter any namespace",
        "unchanged `infer_row_expression` kernel",
        "publishes no `POST_LET`",
        "Slice 5 adds no post-JOIN property bridge",
        "natural exact-head CI completes Slice 5",
        "leaves Slice 6 `NEXT / NOT IMPLEMENTED`",
        "phase63-slice6-post-join-row-semantics-nullability-lineage-property-bridge-v1.md",
        "exact Slice-5 `POST_LET` namespace",
        "Every final visible, hidden, and repeated occurrence",
        "matching final property field",
        "existing canonical upstream field identity",
        "Effective nullability and ordered `nulling_joins`",
        "exact final `ProjectIRJoinOutputProperties`",
        "`ProjectMultiFactConcreteRegion`",
        "not recomputed or interpreted",
        "computed/LET/grouped/window module lineage remains deferred",
        "typed non-concrete terminal rather than legacy name-based fallback",
        "Historical `AUTHORED_JOIN_DEFERRED` remains unchanged",
        "Slice 6 adds no filtering, grouping, aggregate repair",
        "natural exact-head CI completes Slice 6",
        "leaves Slice 7 `NEXT / NOT IMPLEMENTED`",
    ):
        assert evidence in phase63_normalized

    for target in (
        "architecture/product-architecture-v1.md",
        "architecture/phase-initiation-gate-v1.md",
        "architecture/identity-and-authority-laws-v1.md",
        "architecture/layering-and-coupling-laws-v1.md",
        "plan/README.md",
        "spec/phase63-repository-architecture-authority-extraction-prerequisite-v1.md",
        "spec/phase63-slice2-query-block-owner-bridge-row-source-sum-states-mode-boundary-v1.md",
        "spec/phase63-slice3-scalar-reference-environment-resolution-facts-type-kernel-adapter-v1.md",
        "spec/phase63-slice4-bindings-visible-joined-fields-qualified-unqualified-lookup-v1.md",
        "spec/phase63-slice5-let-stage-namespace-lattice-shadowing-alias-laws-v1.md",
        "spec/phase63-slice6-post-join-row-semantics-nullability-lineage-property-bridge-v1.md",
    ):
        assert f"]({target})" in roadmap
        assert (ROADMAP.parent / target).is_file()
    for evidence in (
        "Durable cross-phase product and architecture laws",
        "This roadmap continues to own phase-level future ownership and release milestones",
        "Published phase specs own exact phase/Slice contracts",
        "is historical planning evidence rather than current authority",
    ):
        assert evidence in roadmap_normalized

    future = _section(roadmap, "Future Roadmap v6")
    assert _table_rows(future)[1:] == EXPECTED_FUTURE_ROADMAP_V6
    future_normalized = " ".join(future.split())
    assert "replace the former broad Phase-63–70 map" in future_normalized
    assert "do not authorize a Phase-64+ Slice route or implementation" in (
        future_normalized
    )
    assert "complete old-owner -> new-owner ledger" in future_normalized

    tentative = _section(roadmap, "Tentative later ownership")
    assert _table_rows(tentative)[1:] == EXPECTED_TENTATIVE_LATER_OWNERS
    tentative_normalized = " ".join(tentative.split())
    assert "TENTATIVE / OWNER ONLY" in tentative_normalized
    assert "authorize no implementation" in tentative_normalized
    interlude = _section(
        roadmap,
        "Validation/Test Performance Optimization Interlude",
    )
    interlude_normalized = " ".join(interlude.split())
    assert (
        "Phase 59 completion -> Validation/Test Performance Optimization Interlude "
        "-> Phase 60 activation" in interlude_normalized
    )
    assert (
        "evidence-backed optimization of Pietto's test/validation runtime without "
        "weakening validation semantics or deterministic authority"
        in interlude_normalized
    )
    assert _table_rows(interlude)[1:] == EXPECTED_INTERLUDE_ROUTE
    assert "RepositoryTestIndex" not in interlude_normalized
    assert "only partially supported" in interlude_normalized
    assert "Differential Probe Runtime Decomposition And Optimization" in (
        interlude_normalized
    )
    assert "All 18 outer variants, 116 semantic CLI calls" in interlude_normalized
    assert "materially beyond observed noise" in interlude_normalized
    assert "Fresh collection is 2.99s for 10,352 tests" in interlude_normalized
    assert "serial runs have a 135.21s median" in interlude_normalized
    assert "parallel runs have a 74.60s median" in interlude_normalized
    assert "a like-for-like 44.8% reduction" in interlude_normalized
    assert "Interlude self-owned-open = 0" in interlude_normalized
    assert (
        "Successful natural exact-head CI on the single Slice 6 completion commit "
        "completed the Interlude and handed off authority" in interlude_normalized
    )
    assert "Phase 60 subsequently completed all 13 Slices" in interlude_normalized
    assert "Phase 61 is now `ACTIVE`" in interlude_normalized
    assert (
        "Slices 1–5 and both unnumbered Slice 5 prerequisites" in interlude_normalized
    )
    assert "Slice 6 cross-module composition is current" in interlude_normalized
    assert "Slice 7 remains next / unstarted" in interlude_normalized
    assert len(EXPECTED_INTERLUDE_SLICE6_CHANGED_PATHS) == 4
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_INTERLUDE_SLICE6_CHANGED_PATHS
    )
    assert not any(
        path.startswith((".github/", "src/", "scripts/", "grammar/"))
        for path in EXPECTED_INTERLUDE_SLICE6_CHANGED_PATHS
    )


def test_published_interlude_chain_matches_git_and_completion_evidence() -> None:
    document = SLICE6_SPEC.read_text(encoding="utf-8")
    for commit, tree, _parent, run_id, subject in PUBLISHED_INTERLUDE:
        for value in (commit, tree, run_id, subject):
            assert value in document

    phase60 = PHASE60_SLICE1_SPEC.read_text(encoding="utf-8")
    (
        completion_commit,
        completion_tree,
        completion_parent,
        completion_run,
        completion_subject,
    ) = INTERLUDE_COMPLETION
    for value in (completion_commit, completion_run, completion_subject):
        assert value in phase60

    if _git("rev-parse", "--is-shallow-repository") == "true":
        return

    for commit, tree, parent, _run_id, subject in PUBLISHED_INTERLUDE:
        assert _git("show", "-s", "--format=%T", commit) == tree
        assert _git("show", "-s", "--format=%P", commit) == parent
        assert _git("show", "-s", "--format=%s", commit) == subject
    assert _git("show", "-s", "--format=%T", completion_commit) == completion_tree
    assert _git("show", "-s", "--format=%P", completion_commit) == completion_parent
    assert _git("show", "-s", "--format=%s", completion_commit) == completion_subject


def test_interlude_scorecard_self_owned_open_and_phase60_handoff_are_exact() -> None:
    document = " ".join(SLICE6_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "Interlude self-owned-open = 0",
        "2.99s",
        "132.55s",
        "137.86s",
        "135.21s",
        "79.39s",
        "69.80s",
        "74.60s",
        "60.61s, or 44.8%",
        "116 -> 58",
        "2412 -> 483",
        "1661 -> 484",
        "53.13s -> 52.94s / 0.36%",
        "not owned; not adopted",
        "Phase 60 — Advanced Windows And Phase 51–60 Readiness Checkpoint",
        "Phase 60 implementation = NOT STARTED",
    ):
        assert evidence in document

    forbidden_markers = ("TO" + "DO", "FIX" + "ME")
    interlude_specs = tuple(
        sorted(
            (REPO_ROOT / "docs/spec").glob("validation-performance-interlude-slice*.md")
        )
    )
    assert len(interlude_specs) == 6
    assert not any(
        marker in path.read_text(encoding="utf-8")
        for path in interlude_specs
        for marker in forbidden_markers
    )
    assert EXPECTED_PHASE60_OWNER == (
        "Advanced Windows And Phase 51–60 Readiness Checkpoint"
    )
    assert EXPECTED_FUTURE_ROADMAP_V6[0] == (
        "63",
        "Joined Query Block semantic completion and QUALIFY",
    )


def test_phase61_activation_rebinds_exact_phase60_completion_authority() -> None:
    document = " ".join(PHASE61_SLICE1_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "bf4eeb06507f84374b9d97070423face3e54d929",
        "1ca3542b1f373cdce6b7035b33000eda474ae39d",
        "0b87e603c783b203a70155238c6327e182c7e440",
        "Complete Phase 60 advanced windows",
        "33295132391",
        "Phase 60 = COMPLETED",
        "Phase 61 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in document


def test_phase61_slice2_rebinds_exact_slice1_publication_authority() -> None:
    document = " ".join(PHASE61_SLICE2_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "6445ac9e5a844f8ac5b71fb01ffc573f5bc35de2",
        "c82cfb9e4c5ab7549619b6c1505be6d2fad6bd71",
        "bf4eeb06507f84374b9d97070423face3e54d929",
        "Add Phase 61 Project IR route lock",
        "33303992201",
        "Phase 61 = ACTIVE",
        "Slice 1 = COMPLETED",
        "Slice 2 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in document


def test_phase61_slice3_rebinds_exact_slice2_publication_authority() -> None:
    document = " ".join(PHASE61_SLICE3_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "a9725d46b1c4c79d5e1c78d79a0e042522e1edd3",
        "ef4db5396f1a1ce436d003454d99f314c2cfcae1",
        "6445ac9e5a844f8ac5b71fb01ffc573f5bc35de2",
        "Add Phase 61 Project IR structural model",
        "33305962868",
        "Phase 61 = ACTIVE",
        "Slice 2 = COMPLETED",
        "Slice 3 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in document


def test_phase61_slice4_rebinds_exact_slice3_publication_authority() -> None:
    document = " ".join(PHASE61_SLICE4_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "be984f7ae9c0821cfa14229da99bf9c8da97a048",
        "c0d4bc91aa1883065427244d5572ba3e2d424b67",
        "a9725d46b1c4c79d5e1c78d79a0e042522e1edd3",
        "Add Phase 61 Project IR property model",
        "33308020119",
        "Phase 61 = ACTIVE",
        "Slices 1-3 = COMPLETED",
        "Slice 4 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in document


def test_phase61_slice5_identity_continuation_rebinds_slice4_authority() -> None:
    document = " ".join(
        PHASE61_SLICE5_IDENTITY_CONTINUATION_SPEC.read_text(encoding="utf-8").split()
    )
    for evidence in (
        "6359867c7e9c51d9b59bd23642d7bd2492b24862",
        "ba3d57d0b7217cbf4ec47c2ec6b4fae40c8a3d02",
        "be984f7ae9c0821cfa14229da99bf9c8da97a048",
        "Add Phase 61 Project IR operator algebra",
        "33317947197",
        "Slices 1-4 = COMPLETED",
        "Slice 5 = NEXT / UNSTARTED",
        "This publication is an unnumbered prerequisite",
    ):
        assert evidence in document


def test_phase61_slice5_dataflow_continuation_rebinds_identity_authority() -> None:
    document = " ".join(
        PHASE61_SLICE5_DATAFLOW_CONTINUATION_SPEC.read_text(encoding="utf-8").split()
    )
    for evidence in (
        "cce7709f143de4eb5f9989cbbbd804fe08e71d74",
        "e8bb0c2c2150d21692ac1da346d88b610eefa4fa",
        "6359867c7e9c51d9b59bd23642d7bd2492b24862",
        "Add complete Project relation output identities",
        "33321099987",
        "output-identity prerequisite = COMPLETED",
        "intra-relation dataflow prerequisite = COMPLETED",
        "Slice 5 remains next / unstarted",
    ):
        assert evidence in document


def test_phase61_slice5_rebinds_both_prerequisite_authorities() -> None:
    document = " ".join(PHASE61_SLICE5_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "1ac00344554967ba30f2e3bdff553ec63c2a4c12",
        "c73d5c93c2c037f8258beab4ba5587e4873c3319",
        "cce7709f143de4eb5f9989cbbbd804fe08e71d74",
        "Add Project IR intra-relation dataflow readiness",
        "33335654061",
        "output-identity authority readiness = COMPLETED",
        "intra-relation dataflow readiness = COMPLETED",
        "Slice 5 = NEXT / UNSTARTED",
    ):
        assert evidence in document


def test_phase61_slice6_rebinds_exact_slice5_publication_authority() -> None:
    document = " ".join(PHASE61_SLICE6_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "b9c9e38f809f911eb429e7284d377c2c205e548b",
        "4273b06c631db9e609d0915d3880bc6b4ea3aaa6",
        "1ac00344554967ba30f2e3bdff553ec63c2a4c12",
        "Add Phase 61 single-relation Project IR builder",
        "33337635343",
        "Slices 1-5 = COMPLETED",
        "both Slice 5 prerequisites = COMPLETED",
        "Slice 6 = NEXT / UNSTARTED",
    ):
        assert evidence in document


def test_phase61_slice7_rebinds_exact_slice6_publication_and_repair_authority() -> None:
    document = " ".join(PHASE61_SLICE7_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "21b478569029dbae43aa6cbddecfa0c3709abe5d",
        "351a5ee5dfc709c9f46a7fecd4112f05a01c9c53",
        "b9c9e38f809f911eb429e7284d377c2c205e548b",
        "Add Phase 61 Project IR composition DAG",
        "33340163436",
        "GLOBAL_AGGREGATE_LOCAL_GRAIN_OVERPUBLICATION",
        "A3/M6/D0",
        "repair batches = 1",
        "Slice 8 = NEXT / UNSTARTED",
    ):
        assert evidence in document


def test_phase61_slice8_rebinds_exact_slice7_publication_authority() -> None:
    document = " ".join(PHASE61_SLICE8_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "455629a9edc93622180788ff4cba8b76776c4e9f",
        "6b9bfe44d00de3de112214515f3682131696967a",
        "21b478569029dbae43aa6cbddecfa0c3709abe5d",
        "Add Phase 61 Project IR evaluation contexts",
        "33342737233",
        "Slices 1-7",
        "A3/M4/D0",
        "verification itself is never preservable",
        "Slice 9 = NEXT / UNSTARTED",
    ):
        assert evidence in document


def test_phase61_slice9_rebinds_exact_slice8_publication_authority() -> None:
    document = " ".join(PHASE61_SLICE9_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "577511b9dd6dbf14dbd5dc3710bee0a3d86b92be",
        "c4bc106f54d31939c4681d4d1dd6bb10d519f78c",
        "455629a9edc93622180788ff4cba8b76776c4e9f",
        "Add Phase 61 Project IR verifier",
        "33349469530",
        "Slices 1-8",
        "A4/M4/D0",
        "pietto.project-ir-inspection.v1",
        "Slice 10 = NEXT / UNSTARTED",
    ):
        assert evidence in document


def test_phase61_slice10_rebinds_exact_slice9_publication_authority() -> None:
    document = " ".join(PHASE61_SLICE10_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "edf68678b2a766302e654202f3fe0798c3386ffd",
        "71002ac6c2836805e544340eb7052c76f249620a",
        "577511b9dd6dbf14dbd5dc3710bee0a3d86b92be",
        "Add Phase 61 Project IR inspection",
        "33353818947",
        "Slices 1-9",
        "A3/M4/D0",
        "build_project_ir_pipeline",
        "Slice 11 = NEXT / UNSTARTED",
    ):
        assert evidence in document


def test_phase61_slice11_rebinds_exact_slice10_publication_authority() -> None:
    document = " ".join(PHASE61_SLICE11_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "6607e7a7b127562e5f24490a0135bd7e14134744",
        "700df2d796a30852e2076c75af5b60411e8feeea",
        "edf68678b2a766302e654202f3fe0798c3386ffd",
        "Add Phase 61 Project IR end-to-end pipeline",
        "33355551275",
        "Slices 1-10",
        "A3/M5/D0",
        "production delta = 0",
        "Slice 12 = NEXT / UNSTARTED",
    ):
        assert evidence in document


def test_phase61_completion_rebinds_exact_slice11_publication_authority() -> None:
    document = " ".join(PHASE61_COMPLETION_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "34a9f48811101b0df66119db94277ff2fbfd9d23",
        "7024668474203c59bf4c4acf7cd4bfb5f38a34ea",
        "6607e7a7b127562e5f24490a0135bd7e14134744",
        "Add Phase 61 differential compatibility assurance",
        "33357860140",
        "13 rows are one exact single-parent first-parent chain",
        "Phase 61 exit criteria = 13",
        "PHASE61_SELF_OWNED_OPEN = 0",
        "Phase 62 = NEXT / NOT IMPLEMENTED",
        "A2/M4/D0",
    ):
        assert evidence in document


def test_phase62_slice1_rebinds_exact_phase61_completion_authority() -> None:
    document = " ".join(PHASE62_SLICE1_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "7f78077d45bad378c1fb01561455a15ec95309b9",
        "398e68027e1259bd191d571af9df99436d2782fc",
        "34a9f48811101b0df66119db94277ff2fbfd9d23",
        "Complete Phase 61 Project IR",
        "33359859544",
        "Phase 61 = COMPLETED",
        "Phase61 self-owned-open = 0",
        "Phase 62 = NEXT / NOT IMPLEMENTED",
        "A2/M7/D0",
        "Production changes | `0`",
        "Phase 62 = ACTIVE",
        "Slice 1 = CURRENT / PUBLICATION CANDIDATE",
        "Slices 2-16 = NOT STARTED",
    ):
        assert evidence in document


def test_phase62_slice2_rebinds_exact_slice1_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE2_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "998eaa5655bbe64d4ae13b8ac03f413ce84343ff",
        "d3a698a3a4916cac39a0852bb43ef4243876b18e",
        "5fe550481b5de34977a59078e1f5ba9b5c90d0b0",
        "Fix Phase 61 completion test portability",
        "33463294917",
        "Phase 61 = COMPLETED",
        "Slice 1 = COMPLETED / PUBLISHED",
        "Slice 2 = NEXT / NOT IMPLEMENTED",
        "A3/M5/D0",
        "src/pietto/_project/project_relationships.py",
        "Slice 2 = CURRENT / PUBLICATION CANDIDATE",
        "Slices 3-16 = NOT STARTED",
    ):
        assert evidence in document


def test_phase62_slice3_rebinds_exact_slice2_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE3_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "18baeb56b3c27488a4fc4791ff274213386c43f9",
        "f96c34da8b4b7345babe0a8567433f88fec92971",
        "998eaa5655bbe64d4ae13b8ac03f413ce84343ff",
        "Add Phase 62 relationship identity foundation",
        "33466301585",
        "Phase 61 = COMPLETED",
        "Slice 1 = COMPLETED / PUBLISHED",
        "Slice 2 = COMPLETED / PUBLISHED",
        "Slice 3 = NEXT / NOT IMPLEMENTED",
        "A3/M12/D0",
        "src/pietto/_project/project_relationship_conditions.py",
        "Slice 3 = CURRENT / PUBLICATION CANDIDATE",
        "Slices 4-16 = NOT STARTED",
    ):
        assert evidence in document


def test_phase62_slice4_rebinds_exact_slice3_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE4_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "933a13ea6ecb5e2701f7360fc5220ed3884ace18",
        "2fb40f3c3b64ef68ecc00156621f94b02cd3db21",
        "18baeb56b3c27488a4fc4791ff274213386c43f9",
        "Add Phase 62 relationship field correspondences",
        "33469961091",
        "Phase 61 = COMPLETED",
        "Slice 1 = COMPLETED / PUBLISHED",
        "Slice 2 = COMPLETED / PUBLISHED",
        "Slice 3 = COMPLETED / PUBLISHED",
        "Slice 4 = NEXT / NOT IMPLEMENTED",
        "A3/M6/D0",
        "src/pietto/_project/project_row_keys.py",
        "Slice 4 = CURRENT / PUBLICATION CANDIDATE",
        "Slices 5-16 = NOT STARTED",
    ):
        assert evidence in document


def test_phase62_slice5_rebinds_exact_slice4_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE5_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "b38247f6d115e1cbcf24b47b4d60322fa68e0fa4",
        "11f0b216e4a7273bd2fef6f8a8357443ecb6923e",
        "933a13ea6ecb5e2701f7360fc5220ed3884ace18",
        "Add Phase 62 row uniqueness and candidate keys",
        "33477493108",
        "Phase 61 = COMPLETED",
        "Slices 1-4 = COMPLETED / PUBLISHED",
        "Phase 62 Slice 5 = NEXT / NOT IMPLEMENTED",
        "A3/M6/D0",
        "src/pietto/_project/project_value_fds.py",
        "Slice 5 = CURRENT / PUBLICATION CANDIDATE",
        "Slices 6-16 = NOT STARTED",
    ):
        assert evidence in document


def test_phase62_slice6_rebinds_exact_slice5_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE6_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "d33a3e81d3405b95879becf6bcccebb433ea298f",
        "e4ab46583b1dc9f6aa2649f67bd073d99f1e027d",
        "b38247f6d115e1cbcf24b47b4d60322fa68e0fa4",
        "Add Phase 62 value functional dependencies",
        "33488399817",
        "Slices 1–5 completed/published",
        "Slice 6 next/not implemented",
        "A3/M5/D0",
        "src/pietto/_project/project_grain.py",
        "Slice 6 current/publication candidate",
        "Slices 7–16 not started",
    ):
        assert evidence in document


def test_phase62_slice7_rebinds_exact_slice6_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE7_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "88dbfb51a35504b0b753e299c6c90b6303a8e450",
        "724f2b8ce113bf01072e83f7cd4792cae4a9d8be",
        "33491899112",
        "A3/M5/D0",
        "project_ir_relational_properties.py",
    ):
        assert evidence in document


def test_phase62_slice8_rebinds_exact_slice7_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE8_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "01e3c910ec29f85a4b31e4d1a9dcfa6571d19af1",
        "35f040a8c12d2244d8007dd3b367be67a81344bf",
        "33498869865",
        "A3/M5/D0",
        "project_relationship_match_guarantees.py",
    ):
        assert evidence in document


def test_phase62_slice9_rebinds_exact_slice8_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE9_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "6dd7dec031bb23d4d675ecf03542186b6df5f371",
        "ec3c885527968f4fad65b619bc4fccd5253392dd",
        "33502717286",
        "A3/M5/D0",
        "project_relationship_paths.py",
    ):
        assert evidence in document


def test_phase62_slice10_rebinds_exact_slice9_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE10_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "dc74cee6a0f6a67e396f12b4583a0d88d79ad130",
        "c32444755f191a45f68c7d9207979976ffc275dd",
        "33505927423",
        "A3/M26/D0",
        "project_relationship_uses.py",
        "AUTHORED_JOIN_DEFERRED",
    ):
        assert evidence in document


def test_phase62_slice11_rebinds_exact_slice10_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE11_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "b26e394e5f8238f2c69d86844fb15f7bcb52362b",
        "fcbd2b5cf661ae9b8793371c9ae750768fe164e3",
        "33559281666",
        "A3/M9/D0",
        "project_ir_joins.py",
        "ProjectIRJoinInputUseOccurrence",
    ):
        assert evidence in document


def test_phase62_slice12_rebinds_exact_slice11_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE12_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "f47d33dc3dfd74315a76ef62496953c804a6515c",
        "292a20a6697856b187f92da6e67086ecbfc11c51",
        "33569455067",
        "afca8aacc22d735a678721cb9e4b3348eb505988",
        "A3/M5/D0",
        "src/pietto/_project/project_multifact.py",
        "Slice 12 is the sole current publication candidate",
        "Slice 13 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in document


def test_phase62_slice13_rebinds_exact_slice12_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE13_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "47ee4caccc0686ca609791fb76447a1d1d634069",
        "4d5e1e42f22ec87bbf439982b68a486d32201de0",
        "33574693434",
        "A4/M5/D0",
        "project_phase62_verification.py",
        "project_bag_null_oracle.py",
        "Slice 13 is the sole current publication candidate",
        "Phase 62 Slice 14 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in document


def test_phase62_slice14_rebinds_exact_slice13_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE14_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "c7d0e957affd346e976307863e0d0624c8e227ad",
        "e620535ecb20c33da11a6e2defc3edb6b0d65ac7",
        "33580406830",
        "A4/M5/D0",
        "project_phase62_inspection.py",
        "project_phase62_pure_boundary.py",
        "Slice 14 是唯一当前 publication candidate",
        "Phase 62 Slice 15 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in document


def test_phase62_slice15_rebinds_exact_slice14_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE15_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "c67b2414942974988397682e4a8a776890e38b5d",
        "15200d4207f29904d970041518209872e7e5bb75",
        "33587048578",
        "A3/M6/D0",
        "_pietto_phase62_join_differential_probe.py",
        "test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py",
        "Slice 15 是唯一 publication candidate",
        "Phase 62 Slice 16 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in document


def test_phase62_slice16_rebinds_exact_slice15_publication_authority() -> None:
    document = " ".join(PHASE62_SLICE16_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "1b11f64d0e3bc2bf040793db015f75600a9f181c",
        "23103e4c07f637cacd1f835c08c6d2f6b8375d53",
        "c67b2414942974988397682e4a8a776890e38b5d",
        "Add Phase 62 JOIN end-to-end assurance",
        "33591427553",
        "100126039679",
        "100126039576",
        "A2/M4/D0",
        "Phase 62 = ACTIVE / COMPLETION CANDIDATE",
        "Slice 16 = CURRENT / COMPLETION CANDIDATE",
        "Phase 63 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in document


def test_phase63_slice1_rebinds_exact_phase62_completion_authority() -> None:
    document = " ".join(PHASE63_SLICE1_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "d9a423fe6822ed549e3063299a4781cd7ed4b480",
        "d0c40f2a644b5cb8cff2fb5390e991ab1ec1ef31",
        "Complete Phase 62 relationships and JOIN",
        "33598904937",
        "Python 3.12 success",
        "Python 3.13 success",
        "Phase62 material exits = 15/15",
        "Phase62 self-owned-open = 0",
        "Product/Phase Initiation Gate v3",
        "Future Roadmap v6",
        "A2/M4/D0",
        "Phase 63 = ACTIVE",
        "Phase 63 Slice 1 = COMPLETED / PUBLISHED",
        "Phase 63 Slice 2 = NEXT / NOT IMPLEMENTED",
        "Do not begin Slice 2",
    ):
        assert evidence in document


def test_phase60_slice1_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE1_CHANGED_PATHS) == 7
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE1_CHANGED_PATHS
    )
    assert not any(
        path.startswith((".github/", "src/", "scripts/", "grammar/"))
        for path in EXPECTED_PHASE60_SLICE1_CHANGED_PATHS
    )


def test_phase60_slice2_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE2_CHANGED_PATHS) == 7
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE2_CHANGED_PATHS
    )
    production = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE2_CHANGED_PATHS
        if path.startswith("src/")
    )
    assert production == ("src/pietto/semantic/window_semantics.py",)
    assert not any(
        path.startswith((".github/", "grammar/", "scripts/"))
        for path in EXPECTED_PHASE60_SLICE2_CHANGED_PATHS
    )


def test_phase60_slice3_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE3_CHANGED_PATHS) == 10
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE3_CHANGED_PATHS
    )
    production = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE3_CHANGED_PATHS
        if path.startswith("src/")
    )
    assert production == (
        "src/pietto/semantic/window_analysis.py",
        "src/pietto/semantic/window_navigation_analysis.py",
        "src/pietto/semantic/window_semantics.py",
    )
    assert not any(
        path.startswith((".github/", "grammar/", "scripts/"))
        for path in EXPECTED_PHASE60_SLICE3_CHANGED_PATHS
    )


def test_phase60_slice4_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE4_CHANGED_PATHS) == 22
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE4_CHANGED_PATHS
    )
    generated = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE4_CHANGED_PATHS
        if path.startswith("src/pietto/generated/")
    )
    assert len(generated) == 7
    assert "src/pietto/generated/__init__.py" not in generated
    assert not any(
        path.startswith((".github/", "scripts/"))
        for path in EXPECTED_PHASE60_SLICE4_CHANGED_PATHS
    )
    assert not any(
        path.startswith(("src/pietto/ir/model.py", "src/pietto/sql/"))
        for path in EXPECTED_PHASE60_SLICE4_CHANGED_PATHS
    )


def test_phase60_slice5_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE5_CHANGED_PATHS) == 19
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE5_CHANGED_PATHS
    )
    generated = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE5_CHANGED_PATHS
        if path.startswith("src/pietto/generated/")
    )
    assert len(generated) == 7
    assert "src/pietto/generated/__init__.py" not in generated
    assert not any(
        path.startswith((".github/", "scripts/", "src/pietto/ir/", "src/pietto/sql/"))
        for path in EXPECTED_PHASE60_SLICE5_CHANGED_PATHS
    )


def test_phase60_slice6_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE6_CHANGED_PATHS) == 19
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE6_CHANGED_PATHS
    )
    generated = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE6_CHANGED_PATHS
        if path.startswith("src/pietto/generated/")
    )
    assert len(generated) == 6
    assert "src/pietto/generated/__init__.py" not in generated
    assert not any(
        path.startswith((".github/", "scripts/", "src/pietto/ir/", "src/pietto/sql/"))
        for path in EXPECTED_PHASE60_SLICE6_CHANGED_PATHS
    )


def test_phase60_slice7_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE7_CHANGED_PATHS) == 19
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE7_CHANGED_PATHS
    )
    generated = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE7_CHANGED_PATHS
        if path.startswith("src/pietto/generated/")
    )
    assert len(generated) == 6
    assert "src/pietto/generated/__init__.py" not in generated
    assert not any(
        path.startswith((".github/", "scripts/", "src/pietto/ir/", "src/pietto/sql/"))
        for path in EXPECTED_PHASE60_SLICE7_CHANGED_PATHS
    )


def test_phase60_slice8_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE8_CHANGED_PATHS) == 23
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE8_CHANGED_PATHS
    )
    generated = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE8_CHANGED_PATHS
        if path.startswith("src/pietto/generated/")
    )
    assert generated == (
        "src/pietto/generated/Pietto.interp",
        "src/pietto/generated/PiettoParser.py",
        "src/pietto/generated/PiettoVisitor.py",
    )
    project = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE8_CHANGED_PATHS
        if path.startswith("src/pietto/_project/")
    )
    assert project == (
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/window_semantics.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "scripts/",
                "src/pietto/ir/model.py",
                "src/pietto/sql/",
                "src/pietto/_project_explain/",
            )
        )
        for path in EXPECTED_PHASE60_SLICE8_CHANGED_PATHS
    )


def test_phase60_slice9_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE9_CHANGED_PATHS) == 52
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE9_CHANGED_PATHS
    )
    generated = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE9_CHANGED_PATHS
        if path.startswith("src/pietto/generated/")
    )
    assert len(generated) == 7
    assert "src/pietto/generated/__init__.py" not in generated
    project = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE9_CHANGED_PATHS
        if path.startswith("src/pietto/_project/")
    )
    assert project == (
        "src/pietto/_project/window_semantics.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "scripts/",
                "src/pietto/_project/model.py",
                "src/pietto/_project/row_lineage.py",
                "src/pietto/_project_explain/",
            )
        )
        for path in EXPECTED_PHASE60_SLICE9_CHANGED_PATHS
    )


def test_phase60_slice10_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE10_CHANGED_PATHS) == 43
    assert len(set(EXPECTED_PHASE60_SLICE10_CHANGED_PATHS)) == 43
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE10_CHANGED_PATHS
    )
    assert not any(
        path.startswith(("grammar/", "src/pietto/generated/", ".github/"))
        for path in EXPECTED_PHASE60_SLICE10_CHANGED_PATHS
    )
    project = tuple(
        path
        for path in EXPECTED_PHASE60_SLICE10_CHANGED_PATHS
        if path.startswith("src/pietto/_project/")
    )
    assert project == (
        "src/pietto/_project/window_semantics.py",
        "src/pietto/_project/window_persistence.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/package_graph.py",
        "src/pietto/_project/package_graph_inspection.py",
    )
    assert not any(
        path.startswith(
            (
                "src/pietto/_project/model.py",
                "src/pietto/_project/row_lineage.py",
                "src/pietto/_project/row_dependency_graph.py",
                "src/pietto/_project_explain/",
            )
        )
        for path in EXPECTED_PHASE60_SLICE10_CHANGED_PATHS
    )


def test_phase60_slice11_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE11_CHANGED_PATHS) == 6
    assert len(set(EXPECTED_PHASE60_SLICE11_CHANGED_PATHS)) == 6
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE11_CHANGED_PATHS
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in EXPECTED_PHASE60_SLICE11_CHANGED_PATHS
    )


def test_phase60_slice12_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE12_CHANGED_PATHS) == 8
    assert len(set(EXPECTED_PHASE60_SLICE12_CHANGED_PATHS)) == 8
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE12_CHANGED_PATHS
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in EXPECTED_PHASE60_SLICE12_CHANGED_PATHS
    )


def test_phase60_slice13_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE13_CHANGED_PATHS) == 6
    assert len(set(EXPECTED_PHASE60_SLICE13_CHANGED_PATHS)) == 6
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE13_CHANGED_PATHS
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in EXPECTED_PHASE60_SLICE13_CHANGED_PATHS
    )


def test_phase61_slice1_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE61_SLICE1_CHANGED_PATHS) == 8
    assert len(set(EXPECTED_PHASE61_SLICE1_CHANGED_PATHS)) == 8
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE61_SLICE1_CHANGED_PATHS
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in EXPECTED_PHASE61_SLICE1_CHANGED_PATHS
    )


def test_phase61_slice2_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE61_SLICE2_CHANGED_PATHS) == 7
    assert len(set(EXPECTED_PHASE61_SLICE2_CHANGED_PATHS)) == 7
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE61_SLICE2_CHANGED_PATHS
    )
    production = tuple(
        path
        for path in EXPECTED_PHASE61_SLICE2_CHANGED_PATHS
        if path.startswith("src/")
    )
    assert production == ("src/pietto/_project/project_ir.py",)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in EXPECTED_PHASE61_SLICE2_CHANGED_PATHS
    )


def test_phase61_slice3_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE61_SLICE3_CHANGED_PATHS) == 7
    assert len(set(EXPECTED_PHASE61_SLICE3_CHANGED_PATHS)) == 7
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE61_SLICE3_CHANGED_PATHS
    )
    production = tuple(
        path
        for path in EXPECTED_PHASE61_SLICE3_CHANGED_PATHS
        if path.startswith("src/")
    )
    assert production == ("src/pietto/_project/project_ir_properties.py",)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in EXPECTED_PHASE61_SLICE3_CHANGED_PATHS
    )


def test_phase61_slice4_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE61_SLICE4_CHANGED_PATHS) == 8
    assert len(set(EXPECTED_PHASE61_SLICE4_CHANGED_PATHS)) == 8
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE61_SLICE4_CHANGED_PATHS
    )
    production = tuple(
        path
        for path in EXPECTED_PHASE61_SLICE4_CHANGED_PATHS
        if path.startswith("src/")
    )
    assert production == (
        "src/pietto/_project/project_ir_operators.py",
        "src/pietto/_project/project_ir_properties.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in EXPECTED_PHASE61_SLICE4_CHANGED_PATHS
    )


def test_phase61_slice5_identity_continuation_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE5_IDENTITY_CONTINUATION_CHANGED_PATHS
    assert len(paths) == 11
    assert len(set(paths)) == 11
    assert all((REPO_ROOT / path).is_file() for path in paths)
    production = tuple(path for path in paths if path.startswith("src/"))
    assert production == (
        "src/pietto/_project/model.py",
        "src/pietto/_project/module_attribution.py",
        "src/pietto/_project/module_inspection.py",
        "src/pietto/_project/module_package_neutral_identity.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase61_slice5_dataflow_continuation_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE5_DATAFLOW_CONTINUATION_CHANGED_PATHS
    assert len(paths) == 13
    assert len(set(paths)) == 13
    assert all((REPO_ROOT / path).is_file() for path in paths)
    production = tuple(path for path in paths if path.startswith("src/"))
    assert production == (
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/project_ir.py",
        "src/pietto/_project/project_ir_operators.py",
        "src/pietto/_project/project_ir_properties.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase61_slice5_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE5_CHANGED_PATHS
    assert len(paths) == 8
    assert len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    production = tuple(path for path in paths if path.startswith("src/"))
    assert production == (
        "src/pietto/_project/project_ir.py",
        "src/pietto/_project/project_ir_construction.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase61_slice6_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE6_CHANGED_PATHS
    assert len(paths) == 8
    assert len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    production = tuple(path for path in paths if path.startswith("src/"))
    assert production == (
        "src/pietto/_project/project_ir.py",
        "src/pietto/_project/project_ir_composition.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase61_slice7_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE7_CHANGED_PATHS
    assert len(paths) == 9
    assert len(set(paths)) == 9
    assert all((REPO_ROOT / path).is_file() for path in paths)
    production = tuple(path for path in paths if path.startswith("src/"))
    assert production == (
        "src/pietto/_project/project_ir_construction.py",
        "src/pietto/_project/project_ir_evaluation_context.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase61_slice8_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE8_CHANGED_PATHS
    assert len(paths) == 7
    assert len(set(paths)) == 7
    assert all((REPO_ROOT / path).is_file() for path in paths)
    production = tuple(path for path in paths if path.startswith("src/"))
    assert production == ("src/pietto/_project/project_ir_verification.py",)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase61_slice9_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE9_CHANGED_PATHS
    assert len(paths) == 8
    assert len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    production = tuple(path for path in paths if path.startswith("src/"))
    assert production == (
        "src/pietto/_project/project_ir_inspection.py",
        "src/pietto/_project/project_ir_pure_boundary.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase61_slice10_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE10_CHANGED_PATHS
    assert len(paths) == 7
    assert len(set(paths)) == 7
    assert all((REPO_ROOT / path).is_file() for path in paths)
    production = tuple(path for path in paths if path.startswith("src/"))
    assert production == ("src/pietto/_project/project_ir_pipeline.py",)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase61_slice11_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE11_CHANGED_PATHS
    assert len(paths) == 8
    assert len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert not any(path.startswith("src/") for path in paths)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase61_slice12_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE61_SLICE12_CHANGED_PATHS
    assert len(paths) == 6
    assert len(set(paths)) == 6
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert not any(path.startswith("src/") for path in paths)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase62_slice1_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE1_CHANGED_PATHS
    assert len(paths) == 9
    assert len(set(paths)) == 9
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert not any(path.startswith("src/") for path in paths)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase62_slice2_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE2_CHANGED_PATHS
    assert len(paths) == 8
    assert len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_relationships.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase62_slice3_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE3_CHANGED_PATHS
    assert len(paths) == 15
    assert len(set(paths)) == 15
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/pietto/_project/")) == (
        "src/pietto/_project/project_relationship_conditions.py",
    )
    assert tuple(
        path for path in paths if path.startswith("src/pietto/generated/")
    ) == (
        "src/pietto/generated/Pietto.interp",
        "src/pietto/generated/PiettoParser.py",
        "src/pietto/generated/PiettoVisitor.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/_project_explain/",
                "src/pietto/ir/",
                "src/pietto/semantic/",
                "src/pietto/sql/",
            )
        )
        for path in paths
    )


def test_phase62_slice4_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE4_CHANGED_PATHS
    assert len(paths) == 9
    assert len(set(paths)) == 9
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_row_keys.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/generated/",
                "src/pietto/ir/",
                "src/pietto/semantic/",
                "src/pietto/sql/",
                "src/pietto/_project_explain/",
            )
        )
        for path in paths
    )


def test_phase62_slice5_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE5_CHANGED_PATHS
    assert len(paths) == 9
    assert len(set(paths)) == 9
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_value_fds.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/generated/",
                "src/pietto/ir/",
                "src/pietto/semantic/",
                "src/pietto/sql/",
                "src/pietto/_project_explain/",
            )
        )
        for path in paths
    )


def test_phase62_slice6_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE6_CHANGED_PATHS
    assert len(paths) == 8
    assert len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_grain.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/generated/",
                "src/pietto/ir/",
                "src/pietto/semantic/",
                "src/pietto/sql/",
                "src/pietto/_project_explain/",
            )
        )
        for path in paths
    )


def test_phase62_slice7_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE7_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_ir_relational_properties.py",
    )


def test_phase62_slice8_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE8_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_relationship_match_guarantees.py",
    )


def test_phase62_slice9_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE9_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_relationship_paths.py",
    )


def test_phase62_slice10_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE10_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 29
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/ir/builder.py",
        "src/pietto/_project/model.py",
        "src/pietto/_project/module_relation_resolution.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/row_dependency_graph.py",
        "src/pietto/_project/row_lineage.py",
        "src/pietto/_project/module_pure_boundary.py",
        "src/pietto/_project/project_ir_construction.py",
        "src/pietto/_project/project_relationship_uses.py",
        "src/pietto/generated/Pietto.interp",
        "src/pietto/generated/Pietto.tokens",
        "src/pietto/generated/PiettoLexer.interp",
        "src/pietto/generated/PiettoLexer.py",
        "src/pietto/generated/PiettoLexer.tokens",
        "src/pietto/generated/PiettoParser.py",
        "src/pietto/generated/PiettoVisitor.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
                "src/pietto/sql/",
                "src/pietto/_project_explain/",
            )
        )
        for path in paths
    )


def test_phase62_slice11_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE11_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 12
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_ir.py",
        "src/pietto/_project/project_ir_properties.py",
        "src/pietto/_project/project_grain.py",
        "src/pietto/_project/project_ir_relational_properties.py",
        "src/pietto/_project/project_ir_joins.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/pietto/generated/",
                "src/pietto/ir/",
                "src/pietto/semantic/",
                "src/pietto/sql/",
                "src/pietto/_project_explain/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase62_slice12_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE12_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_multifact.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/pietto/generated/",
                "src/pietto/ir/",
                "src/pietto/semantic/",
                "src/pietto/sql/",
                "src/pietto/_project_explain/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase62_slice13_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE13_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 9
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_phase62_verification.py",
        "src/pietto/_project/project_bag_null_oracle.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/pietto/generated/",
                "src/pietto/ir/",
                "src/pietto/semantic/",
                "src/pietto/sql/",
                "src/pietto/_project_explain/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase62_slice14_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE14_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 9
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_phase62_inspection.py",
        "src/pietto/_project/project_phase62_pure_boundary.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/pietto/generated/",
                "src/pietto/ir/",
                "src/pietto/semantic/",
                "src/pietto/sql/",
                "src/pietto/_project_explain/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase62_slice15_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE15_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 9
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert not any(path.startswith("src/") for path in paths)
    assert tuple(path for path in paths if path.startswith("tests/_")) == (
        "tests/_pietto_phase62_join_differential_probe.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase62_slice16_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE62_SLICE16_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 6
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase63_slice1_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE63_SLICE1_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 6
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase63_architecture_prerequisite_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE63_ARCHITECTURE_PREREQUISITE_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 14
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "src/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase63_slice2_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE63_SLICE2_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 7
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_query_block.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase63_slice3_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE63_SLICE3_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 8
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_scalar_references.py",
        "src/pietto/_project/row_expression_type_facts.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase63_slice4_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE63_SLICE4_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 7
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_scalar_bindings.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase63_slice5_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE63_SLICE5_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 7
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_scalar_namespaces.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )


def test_phase63_slice6_changed_paths_are_exact() -> None:
    paths = EXPECTED_PHASE63_SLICE6_CHANGED_PATHS
    assert len(paths) == len(set(paths)) == 7
    assert all((REPO_ROOT / path).is_file() for path in paths)
    assert tuple(path for path in paths if path.startswith("src/")) == (
        "src/pietto/_project/project_joined_row_semantics.py",
    )
    assert not any(
        path.startswith(
            (
                ".github/",
                "grammar/",
                "scripts/",
                "tests/fixtures/",
                "tests/goldens/",
            )
        )
        for path in paths
    )
