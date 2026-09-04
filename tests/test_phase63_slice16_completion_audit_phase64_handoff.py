from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import subprocess

import pietto
import pietto._project as project_package
from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project.project_ir_pure_boundary import PROJECT_IR_INSPECTION_FORMAT
from pietto._project.project_phase62_pure_boundary import (
    PROJECT_PHASE62_INSPECTION_FORMAT,
)
from pietto._project.project_query_block_ir_pure_boundary import (
    PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase63-completion-audit-phase64-handoff-v1.md"
ROUTE_LOCK = (
    REPO_ROOT
    / "docs/spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md"
)
PHASE63_BASE = "d9a423fe6822ed549e3063299a4781cd7ed4b480"
PHASE63_BASE_TREE = "d0c40f2a644b5cb8cff2fb5390e991ab1ec1ef31"
PHASE63_BASE_CI = "33598904937"
PHASE63_HEAD = "e1590be595f9218341c74a830f611170bfc6092a"
PHASE63_HEAD_TREE = "7708b722af9e601bee62bd852593086a6c89e802"

ROUTE = (
    (
        "1",
        "Product Gate v3, Pietto/external source audit, Future Roadmap, route lock",
    ),
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

PRODUCTS = (
    (
        "Slice 1",
        ROUTE[0][1],
        "docs/spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md",
        "tests/test_phase63_slice1_joined_query_block_product_architecture_source_audit_future_roadmap_route_lock.py",
        (),
    ),
    (
        "Slice 2",
        ROUTE[1][1],
        "docs/spec/phase63-slice2-query-block-owner-bridge-row-source-sum-states-mode-boundary-v1.md",
        "tests/test_phase63_slice2_query_block_owner_bridge_row_source_sum_states_mode_boundary.py",
        ("src/pietto/_project/project_query_block.py",),
    ),
    (
        "Slice 3",
        ROUTE[2][1],
        "docs/spec/phase63-slice3-scalar-reference-environment-resolution-facts-type-kernel-adapter-v1.md",
        "tests/test_phase63_slice3_scalar_reference_environment_resolution_facts_type_kernel_adapter.py",
        (
            "src/pietto/_project/project_scalar_references.py",
            "src/pietto/_project/row_expression_type_facts.py",
        ),
    ),
    (
        "Slice 4",
        ROUTE[3][1],
        "docs/spec/phase63-slice4-bindings-visible-joined-fields-qualified-unqualified-lookup-v1.md",
        "tests/test_phase63_slice4_bindings_visible_joined_fields_qualified_unqualified_lookup.py",
        ("src/pietto/_project/project_scalar_bindings.py",),
    ),
    (
        "Slice 5",
        ROUTE[4][1],
        "docs/spec/phase63-slice5-let-stage-namespace-lattice-shadowing-alias-laws-v1.md",
        "tests/test_phase63_slice5_let_stage_namespace_lattice_shadowing_alias_laws.py",
        ("src/pietto/_project/project_scalar_namespaces.py",),
    ),
    (
        "Slice 6",
        ROUTE[5][1],
        "docs/spec/phase63-slice6-post-join-row-semantics-nullability-lineage-property-bridge-v1.md",
        "tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py",
        ("src/pietto/_project/project_joined_row_semantics.py",),
    ),
    (
        "Slice 7",
        ROUTE[6][1],
        "docs/spec/phase63-slice7-completion-scheduling-effective-output-ledger-module-propagation-v1.md",
        "tests/test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation.py",
        ("src/pietto/_project/project_completion.py",),
    ),
    (
        "Slice 8",
        ROUTE[7][1],
        "docs/spec/phase63-slice8-joined-row-filtering-v1.md",
        "tests/test_phase63_slice8_joined_row_filtering.py",
        (
            "src/pietto/_project/project_joined_row_filter.py",
            "src/pietto/_project/project_scalar_namespaces.py",
        ),
    ),
    (
        "Slice 9",
        ROUTE[8][1],
        "docs/spec/phase63-slice9-joined-grouping-aggregate-global-satisfying-risk-linkage-v1.md",
        "tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py",
        ("src/pietto/_project/project_joined_aggregation.py",),
    ),
    (
        "Slice 10",
        ROUTE[9][1],
        "docs/spec/phase63-slice10-generic-window-computation-sites-named-window-reuse-v1.md",
        "tests/test_phase63_slice10_generic_window_computation_sites_named_window_reuse.py",
        (
            "src/pietto/_project/project_joined_windows.py",
            "src/pietto/semantic/window_analysis.py",
            "src/pietto/semantic/window_navigation_analysis.py",
            "src/pietto/semantic/window_semantics.py",
        ),
    ),
    (
        "Slice 11",
        ROUTE[10][1],
        "docs/spec/phase63-slice11-qualify-grammar-ast-semantics-property-transfer-v1.md",
        "tests/test_phase63_slice11_qualify_grammar_ast_semantics_property_transfer.py",
        (
            "grammar/Pietto.g4",
            "src/pietto/ast_nodes.py",
            "src/pietto/ast_builder.py",
            "src/pietto/_project/project_joined_qualify.py",
        ),
    ),
    (
        "Slice 12",
        ROUTE[11][1],
        "docs/spec/phase63-slice12-projection-order-limit-final-output-ledger-completion-v1.md",
        "tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py",
        (
            "src/pietto/_project/project_final_outputs.py",
            "src/pietto/_project/project_joined_qualify.py",
        ),
    ),
    (
        "Slice 13",
        ROUTE[12][1],
        "docs/spec/phase63-slice13-completed-project-semantic-result-public-check-boundaries-v1.md",
        "tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py",
        (
            "src/pietto/_project/project_completed_semantics.py",
            "src/pietto/cli.py",
        ),
    ),
    (
        "Slice 14",
        ROUTE[13][1],
        "docs/spec/phase63-slice14-query-block-project-ir-composition-verification-invalidation-v1.md",
        "tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py",
        (
            "src/pietto/_project/project_query_block_ir.py",
            "src/pietto/_project/project_query_block_ir_verification.py",
            "src/pietto/_project/project_ir_relational_properties.py",
            "src/pietto/_project/project_ir_evaluation_context.py",
            "src/pietto/_project/project_grain.py",
        ),
    ),
    (
        "Slice 15",
        ROUTE[14][1],
        "docs/spec/phase63-slice15-inspection-pure-boundary-real-e2e-differential-metamorphic-assurance-v1.md",
        "tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py",
        (
            "src/pietto/_project/project_query_block_ir_inspection.py",
            "src/pietto/_project/project_query_block_ir_pure_boundary.py",
        ),
    ),
)

PUBLICATIONS = (
    (
        "Slice 1",
        "e90e8eb5c3fcee12fb932773959e9b862968776e",
        "d8b54927e1a36840c39f6c693b2aa0cf4d1ce3fc",
        "e5b790b0b1c516bbeb2aac0833d209afe1b83811",
        "Fix Phase 63 route-lock shallow CI portability",
        "33693963322",
        "100458702267",
        "100458702526",
    ),
    (
        "Slice 2",
        "6de9f741e848443a3acee996e4a27e23d2377f2f",
        "86a9eb5269123da465cb1d646655b4ab5763d747",
        "6d9756e4c8279cd0c435f4a4cb73537604facd78",
        "Add Phase 63 query-block foundation",
        "33708448662",
        "100502606667",
        "100502606913",
    ),
    (
        "Slice 3",
        "1a2e2482870cd26eb3bae103b008d310b9bbd51f",
        "8611019db93eb520e4c6e2566da58524debac9cd",
        "6de9f741e848443a3acee996e4a27e23d2377f2f",
        "Add Phase 63 scalar reference foundation",
        "33716105707",
        "100525506665",
        "100525506857",
    ),
    (
        "Slice 4",
        "095c8e27cfc23c7fe0e520628c51c1ade884d318",
        "acd03a63aa28d303baa70b7438f052718823630d",
        "1a2e2482870cd26eb3bae103b008d310b9bbd51f",
        "Add Phase 63 joined scalar bindings",
        "33718336042",
        "100532126969",
        "100532126826",
    ),
    (
        "Slice 5",
        "b6af2573f0e10b377fea1d4b3eed2eb92dbc1ab0",
        "51fbc7b00ba1f86823d5ac94614051eb5ca6c104",
        "095c8e27cfc23c7fe0e520628c51c1ade884d318",
        "Add Phase 63 joined LET namespaces",
        "33721542236",
        "100541531022",
        "100541531143",
    ),
    (
        "Slice 6",
        "b3e31fa697919155396e7437e9bfe8d52866dc70",
        "7ccaa64f281f91cb4537d45db2b77dd0ca01ceec",
        "b6af2573f0e10b377fea1d4b3eed2eb92dbc1ab0",
        "Add Phase 63 joined row semantics",
        "33725329642",
        "100552928039",
        "100552927866",
    ),
    (
        "Slice 7",
        "9de90b395452a60f8efcdb570e2578cd40e489fb",
        "80d5b9e06fccaae8c436250e9a8fe31be828db71",
        "b3e31fa697919155396e7437e9bfe8d52866dc70",
        "Add Phase 63 completion foundation",
        "33729260966",
        "100565237673",
        "100565237795",
    ),
    (
        "Slice 8",
        "9984669e5be79d775906b18052c3e0cc16d112ea",
        "7894b6d57375e193af8d3291325b34eb5ed589b4",
        "9de90b395452a60f8efcdb570e2578cd40e489fb",
        "Add Phase 63 joined row filtering",
        "33734174516",
        "100580739912",
        "100580740172",
    ),
    (
        "Slice 9",
        "fb0e4584730d44e72598d6fb26a9afeca7e2b699",
        "c2c14dfb1e57669cf3257f904798824a0990f436",
        "adb1c7efde895f0d213ba233369ced0702e618d1",
        "Reconcile Phase 63 Slice 9 closure evidence",
        "33764259970",
        "100677973573",
        "100677973531",
    ),
    (
        "Slice 10",
        "4b984f8c8578bcd7abd42db80fa8ead294d49f8f",
        "582a4e974cc6068847edf31a68e2ffdda01c1235",
        "fb0e4584730d44e72598d6fb26a9afeca7e2b699",
        "Add Phase 63 joined window computations",
        "33778747491",
        "100726921396",
        "100726921559",
    ),
    (
        "Slice 11",
        "3f0a5435aa14d7b6ca23348b28c5b966f745c04f",
        "be7f7c7dc1f36ed0a7aed1a4561d33eb17fd21ec",
        "4b984f8c8578bcd7abd42db80fa8ead294d49f8f",
        "Add Phase 63 QUALIFY semantics",
        "33831892060",
        "100896447555",
        "100896447459",
    ),
    (
        "Slice 12",
        "0d1d66badc2cf901d35876b360a25a9c36a829b3",
        "01817712dd0cdbf7fd6ce7a1a3442dabf9bf637f",
        "3f0a5435aa14d7b6ca23348b28c5b966f745c04f",
        "Complete Phase 63 final relation outputs",
        "33845906404",
        "100937629132",
        "100937629007",
    ),
    (
        "Slice 13",
        "8b56db95ab45933d05db2123b3e89fb81b8ac2fa",
        "c07493ab11dcf308a0cde01f9ef33a567096eb3c",
        "0d1d66badc2cf901d35876b360a25a9c36a829b3",
        "Add Phase 63 completed project semantics",
        "33855263140",
        "100966972688",
        "100966972586",
    ),
    (
        "Slice 14",
        "23c9d9c4e657501b07664c7f65ee4e455ff7bb0f",
        "34e654d856463cc6aa63fbf4cc3591e788c1e493",
        "8b56db95ab45933d05db2123b3e89fb81b8ac2fa",
        "Add Phase 63 query-block Project IR",
        "33877240716",
        "101037032127",
        "101037032178",
    ),
    (
        "Slice 15",
        PHASE63_HEAD,
        PHASE63_HEAD_TREE,
        "23c9d9c4e657501b07664c7f65ee4e455ff7bb0f",
        "Add Phase 63 query-block IR inspection",
        "33903599417",
        "101123180491",
        "101123180303",
    ),
)

UNNUMBERED_PUBLICATIONS = (
    (
        "Repository architecture authority extraction",
        "9edcd34ec5526e94ad11c7be03a3329b7510a39f",
        "b7ea670b5d2fbd25b1087515be914ce330ded471",
        "e90e8eb5c3fcee12fb932773959e9b862968776e",
        "Extract repository architecture authority",
        "33700551496",
        "100478703692",
        "100478703743",
    ),
    (
        "Architecture dependency-direction correction",
        "6d9756e4c8279cd0c435f4a4cb73537604facd78",
        "8c22b8a8c5dbf6072cb6e6edd8e43f80e4bec94b",
        "9edcd34ec5526e94ad11c7be03a3329b7510a39f",
        "Correct architecture planning dependency direction",
        "33702605149",
        "100484917268",
        "100484917477",
    ),
)

FAILED_SLICE1 = (
    "e5b790b0b1c516bbeb2aac0833d209afe1b83811",
    "5134d48db2e86d1e09740d6c97937c280c6e3ae6",
    PHASE63_BASE,
    "Add Phase 63 joined query-block route lock",
    "33690102213",
    "100446638955",
    "100446639356",
    "e90e8eb5c3fcee12fb932773959e9b862968776e",
    (
        "tests/test_phase63_slice1_joined_query_block_product_architecture_source_audit_future_roadmap_route_lock.py",
    ),
)

SLICE9_INTERMEDIATE = (
    "adb1c7efde895f0d213ba233369ced0702e618d1",
    "4438cf13ad727c5aac9a9a91c5c209d9240a893d",
    "9984669e5be79d775906b18052c3e0cc16d112ea",
    "Add Phase 63 joined aggregation",
    "33742777004",
    "100608277745",
    "100608277561",
    "fb0e4584730d44e72598d6fb26a9afeca7e2b699",
    (
        "docs/spec/phase63-slice9-joined-grouping-aggregate-global-satisfying-risk-linkage-v1.md",
        "tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py",
    ),
)

EXPECTED_HISTORY = (
    FAILED_SLICE1[:4],
    PUBLICATIONS[0][1:5],
    UNNUMBERED_PUBLICATIONS[0][1:5],
    UNNUMBERED_PUBLICATIONS[1][1:5],
    *(publication[1:5] for publication in PUBLICATIONS[1:8]),
    SLICE9_INTERMEDIATE[:4],
    PUBLICATIONS[8][1:5],
    *(publication[1:5] for publication in PUBLICATIONS[9:]),
)

PRINCIPAL_TESTS = {
    PRODUCTS[0][3]: (
        "test_product_phase_initiation_gate_v3_is_complete_and_fail_closed",
        "test_current_identity_schema_and_occurrence_ledgers_match_the_audit",
    ),
    PRODUCTS[1][3]: (
        "test_owner_bridge_reuses_exact_table_and_query_occurrences",
        "test_verified_joined_row_source_retains_final_output_fields_and_history",
    ),
    PRODUCTS[2][3]: (
        "test_reference_occurrence_and_zero_one_many_resolution_are_exact",
        "test_resolution_rejects_duplicate_reordered_and_foreign_candidates",
    ),
    PRODUCTS[3][3]: (
        "test_qualified_lookup_uses_binding_name_only_and_exact_field_occurrence",
        "test_unqualified_lookup_is_complete_ordered_and_winner_free",
    ),
    PRODUCTS[4][3]: (
        "test_namespace_chain_retains_exact_root_occurrences_and_prefixes",
        "test_dependency_and_duplicate_failures_publish_no_post_let_or_winner",
    ),
    PRODUCTS[5][3]: (
        "test_exact_final_property_multifact_and_post_let_roots_are_retained",
        "test_nullability_coheres_for_original_inner_left_and_transitive_cases",
    ),
    PRODUCTS[6][3]: (
        "test_inventory_ledger_and_schedule_cover_exact_owners_deterministically",
        "test_existing_concrete_outputs_and_properties_are_retained_without_rebuild",
    ),
    PRODUCTS[7][3]: (
        "test_where_visibility_blockers_remain_complete_and_fail_closed",
        "test_preservation_witness_reuses_exact_slice6_properties_and_nulling",
    ),
    PRODUCTS[8][3]: (
        "test_real_join_fixture_builds_closed_absent_grouped_global_and_upstream_modes",
        "test_fanout_risk_and_group_key_protection_use_exact_phase62_proofs",
    ),
    PRODUCTS[9][3]: (
        "test_selected_and_hidden_site_identity_domains_are_exact",
        "test_hidden_inline_reuses_kernel_but_never_becomes_nameable",
    ),
    PRODUCTS[10][3]: (
        "test_qualify_ast_retains_exact_clause_hidden_window_and_precedence",
        "test_sql_truth_property_and_output_boundaries_are_exact",
    ),
    PRODUCTS[11][3]: (
        "test_overlay_retains_exact_slice7_roots_order_schedule_and_entry_cardinality",
        "test_final_projection_retains_select_identity_role_and_closed_source_union",
    ),
    PRODUCTS[12][3]: (
        "test_concrete_result_closes_exact_existing_chain_and_all_positive_families",
        "test_json_v2_and_public_private_boundaries_remain_exact",
    ),
    PRODUCTS[13][3]: (
        "test_snapshot_reuses_exact_roots_scope_allocation_ledger_and_verifies",
        "test_concrete_ledger_entries_retain_explicit_active_row_and_property_roots",
    ),
    PRODUCTS[14][3]: (
        "test_gate_a_private_verified_only_admission_and_exact_root_chain",
        "test_gate_c_real_authored_manifest_full_records_and_metamorphics_are_frozen",
    ),
}

PRODUCT_SYMBOLS = {
    "src/pietto/_project/project_query_block.py": (
        "ProjectQueryBlockOwnerBridge",
        "ProjectConcreteQueryBlock",
        "build_project_query_block_from_join_region",
    ),
    "src/pietto/_project/project_scalar_references.py": (
        "ProjectConcreteScalarEnvironment",
        "ProjectScalarReferenceResolution",
        "build_project_scalar_environment",
    ),
    "src/pietto/_project/project_scalar_bindings.py": (
        "ProjectVisibleJoinedBinding",
        "ProjectJoinedScalarBindingEnvironment",
        "build_project_joined_scalar_binding_environment",
    ),
    "src/pietto/_project/project_scalar_namespaces.py": (
        "ProjectScalarNamespaceStage",
        "ProjectConcreteJoinedLetNamespaces",
        "build_project_joined_let_namespaces",
    ),
    "src/pietto/_project/project_joined_row_semantics.py": (
        "ProjectJoinedRowFieldSemantics",
        "ProjectConcreteJoinedRowSemantics",
        "build_project_joined_row_semantics",
    ),
    "src/pietto/_project/project_completion.py": (
        "ProjectCompletionDependency",
        "ProjectCompletion",
        "build_project_completion",
    ),
    "src/pietto/_project/project_joined_row_filter.py": (
        "ProjectJoinedRowRetentionEffect",
        "ProjectConcreteJoinedRowFilter",
        "build_project_joined_row_filters",
    ),
    "src/pietto/_project/project_joined_aggregation.py": (
        "ProjectJoinedAggregationMode",
        "ProjectConcreteJoinedAggregation",
        "build_project_joined_aggregations",
    ),
    "src/pietto/_project/project_joined_windows.py": (
        "ProjectWindowComputationSite",
        "ProjectConcreteWindowComputation",
        "build_project_joined_window_stages",
    ),
    "src/pietto/_project/project_joined_qualify.py": (
        "ProjectJoinedPostQualifyReadiness",
        "ProjectConcreteJoinedQualify",
        "build_project_joined_qualifies",
    ),
    "src/pietto/_project/project_final_outputs.py": (
        "ProjectCompletedOutputField",
        "ProjectEffectiveOutputCompletion",
        "build_project_effective_output_completion",
    ),
    "src/pietto/_project/project_completed_semantics.py": (
        "ProjectConcreteCompletedSemanticResult",
        "build_project_completed_semantic_result",
    ),
    "src/pietto/_project/project_query_block_ir.py": (
        "ProjectIRQueryBlockSnapshot",
        "ProjectIRCompletedQueryBlockOutput",
        "build_project_query_block_ir",
    ),
    "src/pietto/_project/project_query_block_ir_verification.py": (
        "ProjectIRQueryBlockVerificationResult",
        "ProjectIRQueryBlockAnalysisBundle",
        "verify_project_query_block_ir",
    ),
    "src/pietto/_project/project_query_block_ir_inspection.py": (
        "ProjectIRQueryBlockInspection",
        "ProjectIRQueryBlockInspectionProduct",
        "build_project_query_block_ir_inspection",
    ),
    "src/pietto/_project/project_query_block_ir_pure_boundary.py": (
        "ProjectQueryBlockIRPureDocument",
        "ProjectQueryBlockIRPureOutcome",
        "evaluate_project_query_block_ir_document",
    ),
}

PHASE64_TRANSFERS = (
    "Generic JOIN over arbitrary completed/effective row sources",
    "Generic authored ON/refinement",
    "Relationship base condition vs JOIN-local refinement vs WHERE/satisfying/QUALIFY separation",
    "CROSS JOIN",
    "RIGHT JOIN",
    "FULL JOIN",
    "SEMI JOIN",
    "ANTI JOIN",
    "DISTINCT",
    "UNION",
    "INTERSECT",
    "EXCEPT",
    "Single-match enforcement",
    "EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED",
    "EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED",
)

LATER_OWNERS = (
    (
        "Phase 65",
        "Target-neutral ProjectSQLPlan、parameters、source maps、legality 与 capability requirements",
    ),
    (
        "Phase 66",
        "PostgreSQL/MySQL baseline multi-relation SQL 与 Project emit-SQL",
    ),
    ("Phase 67", "Arrow interchange foundation 与 Pietto result contract"),
    (
        "Phase 68",
        "Executor SPI、ADBC/DBAPI、streaming、cancellation 与 backpressure",
    ),
    (
        "Phase 69",
        "Public alpha/release engineering 与 unified safe entrypoints",
    ),
    (
        "Phase 70",
        "Open/composite plans、nonrecursive CTE/subqueries、VALUES/table functions、outer captures、EXISTS/IN、LATERAL、bounded decorrelation 与 effect authority",
    ),
    (
        "Phase 71",
        "NestedRelation、Collect、Unnest、flatten、outer/inner grain 与 nested Arrow",
    ),
    (
        "Phase 72",
        "Advanced equality/types/nullability 与 temporal/range/ASOF relationships",
    ),
    (
        "Phase 73",
        "Aggregate algebra/state、grouping extensions、fanout-safe reaggregation 与 AGGREGATE_ALGEBRA_REQUIRED",
    ),
    (
        "Phase 74",
        "Reusable local semantic assets、derived relationships 与 function/plugin SPI",
    ),
    (
        "Phase 75",
        "Formatter、LSP、editor、diagnostics、syntax editions 与 migrations",
    ),
    ("Phase 88", "Logical optimizer memo 与 join-order/hypergraph search"),
    (
        "Phase 89",
        "Physical strategies including Yannakakis/WCOJ/Free Join/predicate transfer",
    ),
    (
        "Tentative Phase 91",
        "Persistent incremental-cache identity 与 incremental/differential Project IR",
    ),
    (
        "Tentative Phase 92",
        "Recursive relations、fixpoints、iterative planning 与 bounded recursive provenance",
    ),
)

INHERITED_ASSETS = (
    "Product/Phase Initiation Gate v3 procedure",
    "Repository architecture and layering laws",
    "Module/declaration identities and resolution",
    "Relationship identities, paths, conditions and match guarantees",
    "Occurrence-complete joined row shapes",
    "Effective nullability and null-extension provenance",
    "Candidate keys, strict/lax FDs, value classes and FD indexes",
    "Factorized intrinsic grain and dependency kernels",
    "Fanout/chasm/multifact evidence",
    "Completed WHERE/GROUP/WINDOW/QUALIFY/final-output semantics",
    "Project-wide effective-output ledger",
    "Completed project semantic result and final diagnostics",
    "Exact active IR output/property mapping",
    "Phase-61/62/63 combined structural topology",
    "Independent verifier and invalidation",
    "Combined reverse-use/topological/reachability analyses",
    "VERIFIED-only inspection and winner-free queries",
    "Additive Phase-63 pure observation format",
    "Real-authored Python 3.12/3.13 differential harness",
    "Isolated-wheel/relocation/hash-seed assurance",
    "Fail-closed typed terminal patterns",
)


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table(document: str, heading: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in _section(document, heading).splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )[1:]


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert completed.stderr == ""
    return completed.stdout.strip()


def _python_text(path: str) -> str:
    return REPOSITORY_FACTS.python(REPO_ROOT / path).text


def _is_shallow() -> bool:
    return _git("rev-parse", "--is-shallow-repository") == "true"


def _history_rows() -> tuple[tuple[str, str, str, str], ...]:
    rows: list[tuple[str, str, str, str]] = []
    for line in _git(
        "log",
        "--first-parent",
        "--reverse",
        "--format=%H%x1f%T%x1f%P%x1f%s",
        f"{PHASE63_BASE}..{PHASE63_HEAD}",
    ).splitlines():
        commit, tree, parent, subject = line.split("\x1f", 3)
        rows.append((commit, tree, parent, subject))
    return tuple(rows)


def test_exact_route_and_complete_product_inventory_are_closed() -> None:
    route_rows = _table(ROUTE_LOCK.read_text(encoding="utf-8"), "Exact Phase-63 Route")
    assert route_rows == ROUTE
    assert len(ROUTE) == 16
    document = SPEC.read_text(encoding="utf-8")
    completion_route = _table(document, "Numbered Route Closure")
    assert tuple(row[:2] for row in completion_route) == ROUTE
    assert (
        tuple(row[2] for row in completion_route[:15])
        == ("COMPLETED / PUBLISHED",) * 15
    )
    assert completion_route[15][2] == "CURRENT / COMPLETION CANDIDATE"

    inventory = _table(document, "Complete Product Inventory")
    assert len(PRODUCTS) == len(PUBLICATIONS) == len(PRINCIPAL_TESTS) == 15
    assert len(inventory) == 15
    for product, publication, row in zip(
        PRODUCTS,
        PUBLICATIONS,
        inventory,
        strict=True,
    ):
        slice_name, owner, contract, principal, sources = product
        assert publication[0] == slice_name
        assert owner == ROUTE[int(slice_name.split()[1]) - 1][1]
        assert (REPO_ROOT / contract).is_file()
        assert (REPO_ROOT / principal).is_file()
        assert all((REPO_ROOT / path).is_file() for path in sources)
        principal_text = _python_text(principal)
        assert all(
            f"def {name}" in principal_text for name in PRINCIPAL_TESTS[principal]
        )
        _slice, commit, tree, _parent, _subject, run, _py312, _py313 = publication
        assert row[0] == slice_name.removeprefix("Slice ")
        assert row[1] == owner
        assert row[2] == f"`{contract}`"
        assert row[3] == f"`{principal}`"
        assert commit[:8] in row[5]
        assert tree[:8] in row[5]
        assert run in row[5]
        assert row[6] == "COMPLETED / PUBLISHED"

    starting = " ".join(_section(document, "Starting Authority").split())
    for evidence in (
        PHASE63_HEAD,
        PHASE63_HEAD_TREE,
        "23c9d9c4e657501b07664c7f65ee4e455ff7bb0f",
        "Add Phase 63 query-block IR inspection",
        "33903599417",
        "101123180491 / success",
        "101123180303 / success",
        "documentation/test repairs = 0/12",
        "production mutations = 0",
    ):
        assert evidence in starting


def test_corrected_first_parent_topology_is_exactly_19_single_parent_commits() -> None:
    document = SPEC.read_text(encoding="utf-8")
    authority = " ".join(
        _section(document, "Corrected First-Parent Publication Ledger").split()
    )
    for evidence in (
        "`19` 个 first-parent commits",
        "ahead/behind `19/0`",
        "failed heads = 1",
        "successful repair children = 1",
        "manual reruns = 0",
        "merge commits = 0",
        "15 final numbered Slice terminals",
        "2 unnumbered architecture publications",
        "1 preserved failed Slice-1 implementation head",
        "1 successful non-terminal Slice-9 semantic implementation",
    ):
        assert evidence in authority
    if _is_shallow():
        return
    history = _history_rows()
    assert history == EXPECTED_HISTORY
    assert len(history) == len(set(row[0] for row in history)) == 19
    assert all(len(row[2].split()) == 1 for row in history)
    assert _git("merge-base", PHASE63_BASE, PHASE63_HEAD) == PHASE63_BASE
    assert (
        _git("rev-list", "--left-right", "--count", f"{PHASE63_BASE}...{PHASE63_HEAD}")
        == "0\t19"
    )
    assert _git("show", "-s", "--format=%T", PHASE63_BASE) == PHASE63_BASE_TREE
    assert _git("show", "-s", "--format=%T", PHASE63_HEAD) == PHASE63_HEAD_TREE


def test_all_19_git_ci_rows_and_15_numbered_terminals_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    roles = (
        "Slice-1 failed implementation head",
        "Slice-1 repair child and terminal",
        "Unnumbered architecture extraction",
        "Unnumbered dependency-direction correction",
        *(f"Slice {position} terminal" for position in range(2, 9)),
        "Slice-9 successful semantic implementation",
        "Slice-9 reconciliation child and terminal",
        *(f"Slice {position} terminal" for position in range(10, 16)),
    )
    records = (
        FAILED_SLICE1[:7],
        PUBLICATIONS[0][1:8],
        UNNUMBERED_PUBLICATIONS[0][1:8],
        UNNUMBERED_PUBLICATIONS[1][1:8],
        *(publication[1:8] for publication in PUBLICATIONS[1:8]),
        SLICE9_INTERMEDIATE[:7],
        PUBLICATIONS[8][1:8],
        *(publication[1:8] for publication in PUBLICATIONS[9:]),
    )
    rows = _table(document, "Corrected First-Parent Publication Ledger")
    assert len(roles) == len(records) == len(rows) == 19
    for position, (role, record, row) in enumerate(
        zip(roles, records, rows, strict=True),
        1,
    ):
        commit, tree, parent, subject, run, py312, py313 = record
        conclusion = "failure" if position == 1 else "success"
        assert row == (
            str(position),
            role,
            commit,
            tree,
            parent,
            subject,
            run,
            f"{py312} / {conclusion}",
            f"{py313} / {conclusion}",
            f"push/main/attempt 1/{conclusion}",
        )

    terminal_rows = _table(document, "Numbered Slice Terminal Ledger")
    assert len(terminal_rows) == 15
    for publication, row in zip(PUBLICATIONS, terminal_rows, strict=True):
        slice_name, commit, tree, _parent, _subject, run, _py312, _py313 = publication
        assert row == (
            slice_name.removeprefix("Slice "),
            commit,
            tree,
            run,
            "COMPLETED / PUBLISHED",
        )


def test_two_unnumbered_publications_are_successful_and_not_fake_slices() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(document, "Unnumbered Publication Ledger")
    assert len(rows) == 2
    for publication, row in zip(UNNUMBERED_PUBLICATIONS, rows, strict=True):
        name, commit, tree, parent, _subject, run, _py312, _py313 = publication
        assert row == (
            name,
            commit,
            tree,
            parent,
            run,
            "push/main/attempt 1/success",
        )
    assert all(
        publication[1] not in {item[1] for item in PUBLICATIONS}
        for publication in UNNUMBERED_PUBLICATIONS
    )


def test_slice1_failed_head_repair_child_and_numbered_terminal_are_distinct() -> None:
    (
        failed,
        failed_tree,
        failed_parent,
        failed_subject,
        failed_run,
        failed_py312,
        failed_py313,
        child,
        repair_paths,
    ) = FAILED_SLICE1
    terminal = PUBLICATIONS[0]
    assert terminal[1] == child
    assert terminal[3] == failed
    section = " ".join(
        _section(
            SPEC.read_text(encoding="utf-8"),
            "Slice-1 Failed-Head And Repair-Child Lineage",
        ).split()
    )
    for evidence in (
        failed,
        failed_run,
        child,
        "intended single-commit publication",
        "failed head + repair child",
        "不是 amend 或 rerun",
        "Slice-1 numbered terminal 只有",
    ):
        assert evidence in section
    if _is_shallow():
        return
    history = {row[0]: row for row in _history_rows()}
    assert history[failed] == (failed, failed_tree, failed_parent, failed_subject)
    assert history[child][2] == failed
    assert tuple(_git("diff", "--name-status", failed, child).splitlines()) == tuple(
        f"M\t{path}" for path in repair_paths
    )
    assert _git("diff", "--name-only", failed, child, "--", "src", "grammar") == ""


def test_slice9_successful_intermediate_and_m2_reconciliation_are_distinct() -> None:
    (
        intermediate,
        tree,
        parent,
        subject,
        run,
        py312,
        py313,
        terminal,
        repair_paths,
    ) = SLICE9_INTERMEDIATE
    assert PUBLICATIONS[8][1] == terminal
    assert PUBLICATIONS[8][3] == intermediate
    section = " ".join(
        _section(
            SPEC.read_text(encoding="utf-8"),
            "Slice-9 Successful Intermediate And Reconciliation Lineage",
        ).split()
    )
    for evidence in (
        intermediate,
        run,
        terminal,
        "successful evidence-reconciliation child",
        "exact M2",
        "A3/M5/D0",
        "不是 failed-head repair",
    ):
        assert evidence in section
    if _is_shallow():
        return
    history = {row[0]: row for row in _history_rows()}
    assert history[intermediate] == (intermediate, tree, parent, subject)
    assert history[terminal][2] == intermediate
    assert tuple(
        _git("diff", "--name-status", intermediate, terminal).splitlines()
    ) == tuple(f"M\t{path}" for path in repair_paths)
    cumulative = _git(
        "diff",
        "--name-status",
        "9984669e5be79d775906b18052c3e0cc16d112ea",
        terminal,
    ).splitlines()
    assert sum(line.startswith("A\t") for line in cumulative) == 3
    assert sum(line.startswith("M\t") for line in cumulative) == 5
    assert not any(line.startswith("D\t") for line in cumulative)
    assert _git("diff", "--name-only", intermediate, terminal, "--", "src") == ""


def test_historical_slice_deltas_never_use_current_or_future_head() -> None:
    document = " ".join(
        _section(
            SPEC.read_text(encoding="utf-8"), "Immutable Historical Delta Law"
        ).split()
    )
    assert (
        "historical_slice_delta = immutable_slice_start..immutable_slice_terminal"
        in document
    )
    assert "historical_slice_start..current_HEAD" in document
    if _is_shallow():
        return
    starts = (
        PHASE63_BASE,
        UNNUMBERED_PUBLICATIONS[1][1],
        *(PUBLICATIONS[position][1] for position in range(1, len(PUBLICATIONS) - 1)),
    )
    terminals = tuple(publication[1] for publication in PUBLICATIONS)
    assert len(starts) == len(terminals) == 15
    assert all(
        _git("merge-base", start, terminal) == start
        for start, terminal in zip(starts, terminals, strict=True)
    )


def test_product_symbols_and_private_runtime_boundaries_are_live() -> None:
    for path, symbols in PRODUCT_SYMBOLS.items():
        text = _python_text(path)
        assert all(
            any(
                declaration in text
                for declaration in (
                    f"class {symbol}",
                    f"def {symbol}",
                    f"{symbol} =",
                )
            )
            for symbol in symbols
        )
    assert project_package.__all__ == ()
    for name in (
        "ProjectQueryBlockOwnerBridge",
        "ProjectConcreteJoinedQualify",
        "ProjectEffectiveOutputCompletion",
        "ProjectConcreteCompletedSemanticResult",
        "ProjectIRQueryBlockSnapshot",
        "ProjectIRQueryBlockInspection",
        "ProjectQueryBlockIRPureDocument",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
    assert PROJECT_IR_INSPECTION_FORMAT == "pietto.project-ir-inspection.v1"
    assert PROJECT_PHASE62_INSPECTION_FORMAT == "pietto.phase62-inspection.v1"
    assert (
        PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT
        == "pietto.phase63-query-block-ir-inspection.v1"
    )
    assert (
        len(
            {
                PROJECT_IR_INSPECTION_FORMAT,
                PROJECT_PHASE62_INSPECTION_FORMAT,
                PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT,
            }
        )
        == 3
    )
    assert not hasattr(pietto, "__version__")
    assert version("pietto") == "0.1.0"


def test_public_cli_json_sql_and_package_compatibility_exit_is_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(document, "Public And Compatibility Exit")
    assert len(rows) == 19
    assert all(row[2] not in {"DRIFT", "OPEN"} for row in rows)
    normalized = " ".join(_section(document, "Public And Compatibility Exit").split())
    for evidence in (
        "QUALIFY 是 Phase 63 唯一新增 authored clause",
        "EXPLICIT_MODULES 消费 completed project semantics",
        "ProjectSemanticResult",
        "Project JSON",
        "v2 top-level schema/keys 保持不变",
        "LEGACY_FLAT / PACKAGE_ROOT",
        "Project Explain",
        "Query-block carriers",
        "pietto.project-ir-inspection.v1",
        "pietto.phase62-inspection.v1",
        "pietto.phase63-query-block-ir-inspection.v1",
        "未启用 multi-relation SQL emission",
        "无 package/dependency/lockfile/workflow/tag/Release/signing/attestation change",
        "不需要 status-only follow-up commit",
    ):
        assert evidence in normalized

    cli_source = _python_text("src/pietto/cli.py")
    json_source = _python_text("src/pietto/_project/json_v2.py")
    assert "build_project_completed_semantic_result" in cli_source
    assert "_PROJECT_JSON_V2_VERSION = 2" in json_source
    json_keys = (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
    positions = tuple(json_source.index(f'"{key}":') for key in json_keys)
    assert positions == tuple(sorted(positions))
    assert 'AUTHORED_JOIN_DEFERRED = "authored_join_deferred"' in _python_text(
        "src/pietto/_project/model.py"
    )

    if _is_shallow():
        return
    assert (
        _git(
            "log",
            "--format=%H",
            f"{PHASE63_BASE}..{PHASE63_HEAD}",
            "--",
            "grammar/Pietto.g4",
        )
        == "3f0a5435aa14d7b6ca23348b28c5b966f745c04f"
    )
    assert (
        _git("diff", "--name-only", PHASE63_BASE, PHASE63_HEAD, "--", "src/pietto/sql")
        == ""
    )
    assert (
        _git(
            "diff",
            "--name-only",
            PHASE63_BASE,
            PHASE63_HEAD,
            "--",
            "src/pietto/_project_explain",
        )
        == ""
    )
    assert (
        _git(
            "diff",
            "--name-only",
            PHASE63_BASE,
            PHASE63_HEAD,
            "--",
            "pyproject.toml",
            "uv.lock",
            ".github",
        )
        == ""
    )


def test_material_exit_ledger_is_exactly_15_of_15() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(document, "Phase-63 Material Exit Ledger")
    assert len(rows) == 15
    assert tuple(row[0] for row in rows) == tuple(
        f"E{position:02d}" for position in range(1, 16)
    )
    assert tuple(row[2] for row in rows) == (
        "Slice 1 + two unnumbered publications",
        *(f"Slice {position}" for position in range(2, 16)),
    )
    assert all(row[3] == "SATISFIED" for row in rows)
    exits = " ".join(_section(document, "Phase-63 Material Exit Ledger").split())
    for evidence in (
        "Product Gate v3",
        "row-source sum",
        "0/1/N resolution facts",
        "winner-free unqualified lookup",
        "POST_JOIN_INPUT -> LET_BINDING(i) -> POST_LET",
        "effective nullability",
        "Dependency-first completion schedule",
        "SQL TRUE-only retention",
        "fanout/chasm risk linkage",
        "selected/hidden window sites",
        "QUALIFY grammar/AST",
        "Final projection",
        "JSON-v2 compatibility",
        "Explicit active-output/active-properties",
        "VERIFIED-only inspection",
        "Phase63 material exits = 15/15",
        "不新增 E16",
    ):
        assert evidence in exits


def test_open_markers_are_historical_typed_or_exactly_transferred() -> None:
    production_paths = tuple(
        dict.fromkeys(
            path
            for _slice, _owner, _contract, _principal, sources in PRODUCTS
            for path in sources
            if path.startswith("src/") and path.endswith(".py")
        )
    )
    production = "\n".join(_python_text(path) for path in production_paths)
    immutable_products = "\n".join(
        (REPO_ROOT / contract).read_text(encoding="utf-8") + _python_text(principal)
        for _slice, _owner, contract, principal, _sources in PRODUCTS
    )
    assert not any(
        marker in production + immutable_products
        for marker in ("TO" + "DO", "FIX" + "ME", "T" + "BD")
    )
    assert "ProjectRelationRowSchemaStatus.DEFERRED" in production
    assert "ProjectIRQueryBlockTerminal" in production
    assert 'AUTHORED_JOIN_DEFERRED = "authored_join_deferred"' in _python_text(
        "src/pietto/_project/model.py"
    )

    document = SPEC.read_text(encoding="utf-8")
    classifications = _table(document, "Open-Marker Classification")
    assert len(classifications) == 7
    assert all(row[2] != "OPEN" for row in classifications)
    assert "Phase63 self-owned-open = 0" in document
    normalized = " ".join(document.split())
    assert "`AUTHORED_JOIN_DEFERRED` 不被整体转移" in normalized
    assert "Aggregate algebra 也不转移到 Phase 64" in normalized


def test_phase64_transfer_and_other_later_owner_ledgers_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    transfers = _table(document, "Exact Phase-64 Transfers")
    assert tuple(row[0] for row in transfers) == PHASE64_TRANSFERS
    assert all(row[1:] == ("Phase 64", "NOT IMPLEMENTED") for row in transfers)
    assert _table(document, "Exact Other Later-Owner Ledger") == LATER_OWNERS


def test_phase64_inherited_assets_are_ready_but_features_are_not_implemented() -> None:
    document = SPEC.read_text(encoding="utf-8")
    inherited = _table(document, "Phase-64 Inherited Assets")
    assert tuple(row[0] for row in inherited) == INHERITED_ASSETS
    assert all(row[1] == "READY" for row in inherited)
    inherited_text = " ".join(_section(document, "Phase-64 Inherited Assets").split())
    for evidence in (
        "Generic ON",
        "additional JOIN kinds",
        "DISTINCT",
        "set operations",
        "single-match enforcement",
        "NOT IMPLEMENTED",
    ):
        assert evidence in inherited_text
    assert "## Phase 64 route" not in document


def test_phase64_mandatory_initiation_questions_remain_unanswered() -> None:
    document = SPEC.read_text(encoding="utf-8")
    questions = _section(document, "Phase-64 Mandatory Initiation Questions")
    assert sum(questions.count(f"\n{position}. ") for position in range(1, 13)) == 12
    for evidence in (
        "row-source sum",
        "generic JOIN occurrence",
        "relationship base condition",
        "CROSS、RIGHT、FULL、SEMI、ANTI",
        "BAG multiplicity",
        "DISTINCT 的 row-equivalence 与 NULL semantics",
        "UNION/INTERSECT/EXCEPT",
        "不能由 LIMIT 1 推导",
        "active-output ledger",
        "second property engine",
        "ProjectSQLPlan/backend legality",
        "adversarial、differential 与 metamorphic",
        "不回答这些 architecture questions",
        "不冻结 Phase-64 numbered route",
    ):
        assert evidence in questions


def test_slice16_zero_delta_reader_inventory_and_publication_contract_are_exact() -> (
    None
):
    document = SPEC.read_text(encoding="utf-8")
    zero_delta = " ".join(_section(document, "Zero-Delta Boundary").split())
    for evidence in (
        "production delta = 0",
        "grammar / generated delta = 0",
        "public API delta = 0",
        "CLI behavior delta = 0",
        "Project JSON schema delta = 0",
        "SQL delta = 0",
        "Arrow / executor / optimizer delta = 0",
        "package / dependency / lockfile / workflow delta = 0",
        "version delta = 0",
        "Phase-64 implementation delta = 0",
    ):
        assert evidence in zero_delta

    closure = " ".join(_section(document, "Exact Changed-Path Closure").split())
    for evidence in (
        "A2/M4/D0",
        "6 paths",
        "production Python: 179 -> 179",
        "tests: 421 -> 422",
        "没有 production、grammar/generated",
    ):
        assert evidence in closure
    reader = " ".join(_section(document, "Reader And Inventory Ownership").split())
    assert "唯一 mutable lifecycle-document reader" in reader
    assert "principal 只保留 immutable transition" in reader
    assert "不做动态 inventory scan" in reader
    assert "Tests 不访问网络" in reader

    publication = " ".join(_section(document, "Validation And Publication").split())
    for evidence in (
        "UV_PYTHON=3.13 uv run python scripts/validate.py --timings",
        "Complete Phase 63 joined query blocks",
        "ordinary non-amend commit",
        "normal fast-forward push",
        "natural exact-head CI",
        "Python 3.12/3.13 成功",
        "status-only follow-up commit",
        "PASS — PHASE63_SLICE16_COMPLETION_AUDIT_PHASE64_HANDOFF_END_TO_END",
    ):
        assert evidence in publication


def test_phase63_base_and_preaudit_terminal_objects_remain_immutable() -> None:
    if _is_shallow():
        return
    assert _git("rev-parse", PHASE63_BASE) == PHASE63_BASE
    assert _git("show", "-s", "--format=%T", PHASE63_BASE) == PHASE63_BASE_TREE
    assert _git("rev-parse", PHASE63_HEAD) == PHASE63_HEAD
    assert _git("show", "-s", "--format=%T", PHASE63_HEAD) == PHASE63_HEAD_TREE
    assert _git("show", "-s", "--format=%P", PHASE63_HEAD) == PUBLICATIONS[14][3]


def test_completion_spec_keeps_corrected_lineage_and_phase64_boundary() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "15 final numbered Slice terminals",
        "2 unnumbered architecture publications",
        "1 preserved failed Slice-1 implementation head",
        "1 successful non-terminal Slice-9 semantic implementation",
        "= 19 first-parent commits",
        "`e5b790b0b1c516bbeb2aac0833d209afe1b83811` 是保留的 failed Slice-1",
        "`e90e8eb5c3fcee12fb932773959e9b862968776e` 是普通 successful repair child",
        "Slice-1 numbered terminal 只有 `e90e8eb5...`",
        "Phase 64 = NEXT / NOT IMPLEMENTED",
        "Phase63 material exits = 15/15",
        "Phase63 self-owned-open = 0",
    ):
        assert evidence in document
