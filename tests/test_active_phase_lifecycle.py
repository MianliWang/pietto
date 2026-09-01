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
    ("Phase 62", "`ACTIVE`"),
    ("Slice 1", "`COMPLETED`"),
    ("Slice 2", "`COMPLETED`"),
    ("Slice 3", "`COMPLETED`"),
    ("Slice 4", "`COMPLETED`"),
    ("Slice 5", "`COMPLETED`"),
    ("Slice 6", "`COMPLETED`"),
    ("Slice 7", "`COMPLETED`"),
    ("Slice 8", "`COMPLETED`"),
    ("Slice 9", "`CURRENT / PUBLICATION CANDIDATE`"),
    ("Slice 10", "`NOT STARTED`"),
    ("Slice 11", "`NOT STARTED`"),
    ("Slice 12", "`NOT STARTED`"),
    ("Slice 13", "`NOT STARTED`"),
    ("Slice 14", "`NOT STARTED`"),
    ("Slice 15", "`NOT STARTED`"),
    ("Slice 16", "`NOT STARTED`"),
    (
        "Next",
        "`Phase 62 Slice 10 — Authored JOIN/Traversal Syntax And Semantic Uses`",
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
    "Phase 62 is active. Slices 1–8 are completed by successful natural exact-head\n"
    "CI, Slice 9 is the current publication candidate, Slices 10–16 are not started,\n"
    "and the frozen route has exactly 16 numbered slices."
)
EXPECTED_PHASE62_OWNER = (
    "Private occurrence-safe relationships and INNER/LEFT logical JOIN, typed "
    "key/FD/coverage evidence, factorized intrinsic grain, directional fanout, "
    "and multi-fact alignment analysis"
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
EXPECTED_RETAINED_LATER_OWNERS = (
    (
        "63",
        "Additional logical JOIN forms and single-match enforcement; multi-relation SQL; correlation, nested results, open plans/outer bindings, Collect/Unnest, LATERAL/decorrelation, and QUALIFY",
    ),
    (
        "64",
        "Null-safe/collation/NaN/coercive equality; temporal/range/as-of relationships; advanced types, Decimal/time/interval comparison, record/container typing, and nullability",
    ),
    (
        "65",
        "Aggregate algebra/state, symmetric/fanout-safe aggregates, aggregate-as-window, multi-stage aggregation/reaggregation, automatic aggregate/grain repair, and first_value(aggregate_output_alias)",
    ),
    (
        "66",
        "Relationship import/export; reusable relationship/key/FD/grain declarations and libraries; reusable relation/nested semantic assets",
    ),
    ("67", "Remote packages/assets, transport, registry, and trust"),
    (
        "68",
        "Dependency solver, canonical lockfile, and first profiling-driven Python-to-Rust kernel decision",
    ),
    (
        "69",
        "Catalog constraints and statistics; optimizer memo, join-order/hypergraph search, outer-join reordering, predicate transfer/factorized/WCOJ execution, physical join strategies, and broad backend/catalog capabilities",
    ),
    (
        "70",
        "Public relationship/key/FD/grain/fanout/alignment and Project-IR/nested/lineage schemas, versioned representation, and release readiness",
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
    assert "Phase 62 is active" in normalized
    assert "Slice 1 architecture, formal BAG/NULL laws" in normalized
    assert "exact 16-Slice route" in normalized
    assert "completed by successful natural exact-head CI" in normalized
    assert "portability-repair child" in normalized
    assert "Slice 2 relationship identity/module-resolution" in normalized
    assert "completed by successful natural exact-head CI" in normalized
    assert (
        "Slice 3 authored base-match/private exact-field correspondence" in normalized
    )
    assert "completed by successful natural exact-head CI" in normalized
    assert "Slices 4–8 key/FD/grain/match-guarantee authorities" in normalized
    assert "Slice 9 is the current private explicit relationship-path" in normalized
    assert "fanout/survival/null-potential publication candidate" in normalized
    assert "adds no grammar, public schema, JOIN IR/SQL, multi-fact" in normalized
    assert "natural exact-head CI completes Slice 9" in normalized
    assert "Slices 10–16 are not started" in normalized
    assert "Slice 10 is the sole next owner" in normalized
    assert not any(
        marker in status for marker in ("TO" + "DO", "FIX" + "ME", "T" + "BD")
    )


def test_active_roadmap_current_owner_sentence_and_routes_are_exact() -> None:
    roadmap = _read(ROADMAP)
    phase58 = _section(roadmap, "Phase 58 route").lstrip()
    phase59 = _section(roadmap, "Phase 59 route").lstrip()
    phase60 = _section(roadmap, "Phase 60 route").lstrip()
    phase61 = _section(roadmap, "Phase 61 route").lstrip()
    phase62 = _section(roadmap, "Phase 62 route").lstrip()
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
        "Slice 7 is not implemented here",
        "`project_ir_relational_properties.py`",
        "phase62-slice7-existing-operator-key-fd-grain-transfer-grain-comparison-v1.md",
        "`project_relationship_match_guarantees.py`",
        "phase62-slice8-referential-coverage-match-simple-full-directional-match-guarantees-v1.md",
        "two occurrence-safe directions with independent lower/upper evidence",
        "current authored source explicitly lacks a positive producer",
        "Phase 62 Slice 9 — Explicit Relationship Paths, Fanout/Survival/Null Effects, And Join-Shape Analysis",
        "Slice 9 is not implemented here",
        "`project_relationship_paths.py`",
        "phase62-slice9-explicit-relationship-paths-fanout-survival-null-effects-join-shape-analysis-v1.md",
        "exact direct-candidate index",
        "no automatic multi-hop search or winner",
        "Phase 62 Slice 10 — Authored JOIN/Traversal Syntax And Semantic Uses",
        "Slice 10 is not implemented here",
    ):
        assert evidence in phase62_normalized

    retained = _section(roadmap, "Retained later ownership")
    assert _table_rows(retained)[1:] == EXPECTED_RETAINED_LATER_OWNERS
    retained_normalized = " ".join(retained.split())
    assert "dedicated later owner with no phase number" in retained_normalized
    assert "Persistent incremental-cache identity" in retained_normalized
    assert "Incremental/differential Project IR" in retained_normalized
    assert "formal rewrite certification" in retained_normalized
    assert "general constraint/chase reasoning" in retained_normalized
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
    assert EXPECTED_RETAINED_LATER_OWNERS[0] == (
        "63",
        "Additional logical JOIN forms and single-match enforcement; multi-relation SQL; correlation, nested results, open plans/outer bindings, Collect/Unnest, LATERAL/decorrelation, and QUALIFY",
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
