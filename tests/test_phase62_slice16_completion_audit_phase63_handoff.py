from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import subprocess

import pietto
import pietto._project as project_package
from _pietto_repository_facts import REPOSITORY_FACTS


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase62-completion-audit-phase63-handoff-v1.md"
ROUTE_LOCK = (
    REPO_ROOT
    / "docs/spec/phase62-relationship-join-keys-fd-grain-fanout-multifact-architecture-source-audit-route-lock-v1.md"
)
PHASE62_BASE = "7f78077d45bad378c1fb01561455a15ec95309b9"
PHASE62_BASE_TREE = "398e68027e1259bd191d571af9df99436d2782fc"
PHASE62_BASE_CI = "33359859544"
PHASE62_HEAD = "1b11f64d0e3bc2bf040793db015f75600a9f181c"
PHASE62_SLICE16_TERMINAL = "d9a423fe6822ed549e3063299a4781cd7ed4b480"
PHASE62_SLICE16_TERMINAL_TREE = "d0c40f2a644b5cb8cff2fb5390e991ab1ec1ef31"

ROUTE = (
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
    ("8", "Referential coverage, MATCH SIMPLE/FULL, and directional match guarantees"),
    (
        "9",
        "Explicit relationship paths, fanout/survival/null effects, and join-shape analysis",
    ),
    ("10", "Authored JOIN/traversal syntax and semantic uses"),
    (
        "11",
        "Project IR binary JOIN region, multi-input topology, null extension, and property transfer",
    ),
    ("12", "Per-aggregate fact locality, chasm detection, and multi-fact alignment"),
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

PRODUCTS = (
    (
        "Slice 1",
        ROUTE[0][1],
        "docs/spec/phase62-relationship-join-keys-fd-grain-fanout-multifact-architecture-source-audit-route-lock-v1.md",
        "tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py",
        (),
    ),
    (
        "Slice 2",
        ROUTE[1][1],
        "docs/spec/phase62-slice2-relationship-declaration-identity-endpoint-roles-module-local-resolution-construction-states-v1.md",
        "tests/test_phase62_slice2_relationship_declaration_identity_endpoint_roles_module_local_resolution_construction_states.py",
        ("src/pietto/_project/project_relationships.py",),
    ),
    (
        "Slice 3",
        ROUTE[2][1],
        "docs/spec/phase62-slice3-exact-field-correspondences-on-where-equality-null-behavior-constraint-scope-boundary-v1.md",
        "tests/test_phase62_slice3_exact_field_correspondences_on_where_equality_null_behavior_constraint_scope_boundary.py",
        (
            "grammar/Pietto.g4",
            "src/pietto/ast_nodes.py",
            "src/pietto/ast_builder.py",
            "src/pietto/_project/project_relationship_conditions.py",
        ),
    ),
    (
        "Slice 4",
        ROUTE[3][1],
        "docs/spec/phase62-slice4-unique-null-policy-evidence-trust-strict-lax-row-uniqueness-candidate-keys-v1.md",
        "tests/test_phase62_slice4_unique_null_policy_evidence_trust_strict_lax_row_uniqueness_candidate_keys.py",
        ("src/pietto/_project/project_row_keys.py",),
    ),
    (
        "Slice 5",
        ROUTE[4][1],
        "docs/spec/phase62-slice5-strict-lax-value-fd-basis-compact-indexes-targeted-closure-v1.md",
        "tests/test_phase62_slice5_strict_lax_value_fd_basis_compact_indexes_targeted_closure.py",
        ("src/pietto/_project/project_value_fds.py",),
    ),
    (
        "Slice 6",
        ROUTE[5][1],
        "docs/spec/phase62-slice6-factorized-intrinsic-grain-basis-dependencies-optional-factors-global-grain-v1.md",
        "tests/test_phase62_slice6_factorized_intrinsic_grain_basis_dependencies_optional_factors_global_grain.py",
        ("src/pietto/_project/project_grain.py",),
    ),
    (
        "Slice 7",
        ROUTE[6][1],
        "docs/spec/phase62-slice7-existing-operator-key-fd-grain-transfer-grain-comparison-v1.md",
        "tests/test_phase62_slice7_existing_operator_key_fd_grain_transfer_grain_comparison.py",
        ("src/pietto/_project/project_ir_relational_properties.py",),
    ),
    (
        "Slice 8",
        ROUTE[7][1],
        "docs/spec/phase62-slice8-referential-coverage-match-simple-full-directional-match-guarantees-v1.md",
        "tests/test_phase62_slice8_referential_coverage_match_simple_full_directional_match_guarantees.py",
        ("src/pietto/_project/project_relationship_match_guarantees.py",),
    ),
    (
        "Slice 9",
        ROUTE[8][1],
        "docs/spec/phase62-slice9-explicit-relationship-paths-fanout-survival-null-effects-join-shape-analysis-v1.md",
        "tests/test_phase62_slice9_explicit_relationship_paths_fanout_survival_null_effects_join_shape_analysis.py",
        ("src/pietto/_project/project_relationship_paths.py",),
    ),
    (
        "Slice 10",
        ROUTE[9][1],
        "docs/spec/phase62-slice10-authored-join-traversal-syntax-semantic-uses-v1.md",
        "tests/test_phase62_slice10_authored_join_traversal_syntax_semantic_uses.py",
        (
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
            "src/pietto/_project/project_relationship_uses.py",
            "src/pietto/_project/project_ir_construction.py",
        ),
    ),
    (
        "Slice 11",
        ROUTE[10][1],
        "docs/spec/phase62-slice11-project-ir-binary-join-region-multi-input-topology-null-extension-property-transfer-v1.md",
        "tests/test_phase62_slice11_project_ir_binary_join_region_multi_input_topology_null_extension_property_transfer.py",
        (
            "src/pietto/_project/project_ir.py",
            "src/pietto/_project/project_ir_properties.py",
            "src/pietto/_project/project_grain.py",
            "src/pietto/_project/project_ir_relational_properties.py",
            "src/pietto/_project/project_ir_joins.py",
        ),
    ),
    (
        "Slice 12",
        ROUTE[11][1],
        "docs/spec/phase62-slice12-per-aggregate-fact-locality-chasm-detection-multi-fact-alignment-v1.md",
        "tests/test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment.py",
        ("src/pietto/_project/project_multifact.py",),
    ),
    (
        "Slice 13",
        ROUTE[12][1],
        "docs/spec/phase62-slice13-integrity-verifier-analysis-invalidation-bounded-bag-null-semantic-oracle-v1.md",
        "tests/test_phase62_slice13_integrity_verifier_analysis_invalidation_bounded_bag_null_semantic_oracle.py",
        (
            "src/pietto/_project/project_phase62_verification.py",
            "src/pietto/_project/project_bag_null_oracle.py",
        ),
    ),
    (
        "Slice 14",
        ROUTE[13][1],
        "docs/spec/phase62-slice14-private-inspection-winner-free-query-pure-canonical-boundary-v1.md",
        "tests/test_phase62_slice14_private_inspection_winner_free_query_pure_canonical_boundary.py",
        (
            "src/pietto/_project/project_phase62_inspection.py",
            "src/pietto/_project/project_phase62_pure_boundary.py",
        ),
    ),
    (
        "Slice 15",
        ROUTE[14][1],
        "docs/spec/phase62-slice15-real-authored-e2e-python-differential-metamorphic-join-assurance-v1.md",
        "tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py",
        ("tests/_pietto_phase62_join_differential_probe.py",),
    ),
)

PUBLICATIONS = (
    (
        "Slice 1",
        "998eaa5655bbe64d4ae13b8ac03f413ce84343ff",
        "d3a698a3a4916cac39a0852bb43ef4243876b18e",
        "5fe550481b5de34977a59078e1f5ba9b5c90d0b0",
        "Fix Phase 61 completion test portability",
        "33463294917",
        "99717859796",
        "99717859640",
    ),
    (
        "Slice 2",
        "18baeb56b3c27488a4fc4791ff274213386c43f9",
        "f96c34da8b4b7345babe0a8567433f88fec92971",
        "998eaa5655bbe64d4ae13b8ac03f413ce84343ff",
        "Add Phase 62 relationship identity foundation",
        "33466301585",
        "99726762679",
        "99726762426",
    ),
    (
        "Slice 3",
        "933a13ea6ecb5e2701f7360fc5220ed3884ace18",
        "2fb40f3c3b64ef68ecc00156621f94b02cd3db21",
        "18baeb56b3c27488a4fc4791ff274213386c43f9",
        "Add Phase 62 relationship field correspondences",
        "33469961091",
        "99737529224",
        "99737529067",
    ),
    (
        "Slice 4",
        "b38247f6d115e1cbcf24b47b4d60322fa68e0fa4",
        "11f0b216e4a7273bd2fef6f8a8357443ecb6923e",
        "933a13ea6ecb5e2701f7360fc5220ed3884ace18",
        "Add Phase 62 row uniqueness and candidate keys",
        "33477493108",
        "99759721078",
        "99759720840",
    ),
    (
        "Slice 5",
        "d33a3e81d3405b95879becf6bcccebb433ea298f",
        "e4ab46583b1dc9f6aa2649f67bd073d99f1e027d",
        "b38247f6d115e1cbcf24b47b4d60322fa68e0fa4",
        "Add Phase 62 value functional dependencies",
        "33488399817",
        "99793804396",
        "99793804414",
    ),
    (
        "Slice 6",
        "88dbfb51a35504b0b753e299c6c90b6303a8e450",
        "724f2b8ce113bf01072e83f7cd4792cae4a9d8be",
        "d33a3e81d3405b95879becf6bcccebb433ea298f",
        "Add Phase 62 intrinsic grain foundation",
        "33491899112",
        "99805070940",
        "99805071223",
    ),
    (
        "Slice 7",
        "01e3c910ec29f85a4b31e4d1a9dcfa6571d19af1",
        "35f040a8c12d2244d8007dd3b367be67a81344bf",
        "88dbfb51a35504b0b753e299c6c90b6303a8e450",
        "Add Phase 62 key FD grain transfer and comparison",
        "33498869865",
        "99827280806",
        "99827281146",
    ),
    (
        "Slice 8",
        "6dd7dec031bb23d4d675ecf03542186b6df5f371",
        "ec3c885527968f4fad65b619bc4fccd5253392dd",
        "01e3c910ec29f85a4b31e4d1a9dcfa6571d19af1",
        "Add Phase 62 directional relationship match guarantees",
        "33502717286",
        "99839527550",
        "99839527316",
    ),
    (
        "Slice 9",
        "dc74cee6a0f6a67e396f12b4583a0d88d79ad130",
        "c32444755f191a45f68c7d9207979976ffc275dd",
        "6dd7dec031bb23d4d675ecf03542186b6df5f371",
        "Add Phase 62 relationship path and fanout analysis",
        "33505927423",
        "99849831378",
        "99849830995",
    ),
    (
        "Slice 10",
        "b26e394e5f8238f2c69d86844fb15f7bcb52362b",
        "fcbd2b5cf661ae9b8793371c9ae750768fe164e3",
        "dc74cee6a0f6a67e396f12b4583a0d88d79ad130",
        "Add Phase 62 authored relationship join uses",
        "33559281666",
        "100027601111",
        "100027601351",
    ),
    (
        "Slice 11",
        "f47d33dc3dfd74315a76ef62496953c804a6515c",
        "292a20a6697856b187f92da6e67086ecbfc11c51",
        "afca8aacc22d735a678721cb9e4b3348eb505988",
        "Fix Phase 62 Slice 11 Python 3.12 portability",
        "33569455067",
        "100059999528",
        "100059999761",
    ),
    (
        "Slice 12",
        "47ee4caccc0686ca609791fb76447a1d1d634069",
        "4d5e1e42f22ec87bbf439982b68a486d32201de0",
        "f47d33dc3dfd74315a76ef62496953c804a6515c",
        "Add Phase 62 multi-fact alignment analysis",
        "33574693434",
        "100075970857",
        "100075970447",
    ),
    (
        "Slice 13",
        "c7d0e957affd346e976307863e0d0624c8e227ad",
        "e620535ecb20c33da11a6e2defc3edb6b0d65ac7",
        "47ee4caccc0686ca609791fb76447a1d1d634069",
        "Add Phase 62 JOIN verification and BAG oracle",
        "33580406830",
        "100093302455",
        "100093302399",
    ),
    (
        "Slice 14",
        "c67b2414942974988397682e4a8a776890e38b5d",
        "15200d4207f29904d970041518209872e7e5bb75",
        "f688a84972696c009994849688cf9348f7398983",
        "Fix Phase 62 Slice 14 CI interpreter portability",
        "33587048578",
        "100113272299",
        "100113272108",
    ),
    (
        "Slice 15",
        PHASE62_HEAD,
        "23103e4c07f637cacd1f835c08c6d2f6b8375d53",
        "c67b2414942974988397682e4a8a776890e38b5d",
        "Add Phase 62 JOIN end-to-end assurance",
        "33591427553",
        "100126039679",
        "100126039576",
    ),
)

FAILED_PUBLICATIONS = (
    (
        "Slice 1",
        "5fe550481b5de34977a59078e1f5ba9b5c90d0b0",
        "1c431365592b53ebfa03de0d8e97ce45d39d2069",
        PHASE62_BASE,
        "Add Phase 62 relationship and grain route lock",
        "33461666637",
        "998eaa5655bbe64d4ae13b8ac03f413ce84343ff",
        ("tests/test_phase61_slice12_completion_audit_phase62_handoff.py",),
    ),
    (
        "Slice 11",
        "afca8aacc22d735a678721cb9e4b3348eb505988",
        "e97894207e534a7cd3603e7c9fd64ca31a7be40f",
        "b26e394e5f8238f2c69d86844fb15f7bcb52362b",
        "Add Phase 62 binary Project IR joins",
        "33568043743",
        "f47d33dc3dfd74315a76ef62496953c804a6515c",
        (
            "docs/spec/phase62-slice11-project-ir-binary-join-region-multi-input-topology-null-extension-property-transfer-v1.md",
            "tests/test_phase62_slice11_project_ir_binary_join_region_multi_input_topology_null_extension_property_transfer.py",
        ),
    ),
    (
        "Slice 14",
        "f688a84972696c009994849688cf9348f7398983",
        "87ed4473c6071cfd520051c58a03adb93f26cd58",
        "c7d0e957affd346e976307863e0d0624c8e227ad",
        "Add Phase 62 private inspection",
        "33585654081",
        "c67b2414942974988397682e4a8a776890e38b5d",
        (
            "docs/spec/phase62-slice14-private-inspection-winner-free-query-pure-canonical-boundary-v1.md",
            "tests/test_phase62_slice14_private_inspection_winner_free_query_pure_canonical_boundary.py",
        ),
    ),
)

PRINCIPAL_TESTS = {
    PRODUCTS[0][3]: (
        "test_phase61_inheritance_and_identity_ownership_laws_are_exact",
        "test_route_later_owners_exit_gate_and_static_delta_are_exact",
    ),
    PRODUCTS[1][3]: (
        "test_real_relationships_retain_identity_roles_resolution_and_semantics",
        "test_non_concrete_states_are_distinct_and_do_not_erase_concrete_subjects",
    ),
    PRODUCTS[2][3]: (
        "test_concrete_correspondences_retain_order_roles_fields_types_and_scopes",
        "test_non_concrete_conditions_fail_closed_without_partial_correspondences",
    ),
    PRODUCTS[3][3]: (
        "test_null_policy_strength_trust_and_enforcement_are_exact",
        "test_candidate_frontier_is_complete_non_dominated_and_support_preserving",
    ),
    PRODUCTS[4][3]: (
        "test_indexed_strict_closure_reaches_fixed_point_and_handles_composites_and_cycles",
        "test_lax_rules_remain_direct_and_are_never_used_by_strict_closure",
    ),
    PRODUCTS[5][3]: (
        "test_grouped_and_global_origins_retain_exact_evaluation_authority",
        "test_dependency_kernel_is_typed_local_finite_and_arbitrary_width",
    ),
    PRODUCTS[6][3]: (
        "test_source_and_unary_outputs_transfer_keys_fds_and_grain",
        "test_group_and_global_replace_active_grain_without_empty_keys",
    ),
    PRODUCTS[7][3]: (
        "test_directions_are_occurrence_safe_complete_and_deterministic",
        "test_target_strict_lax_composite_and_superset_keys_prove_at_most_one",
    ),
    PRODUCTS[8][3]: (
        "test_direct_index_absent_unique_ambiguous_parallel_and_self",
        "test_explicit_paths_are_ordered_contiguous_and_never_auto_selected",
    ),
    PRODUCTS[9][3]: (
        "test_join_bearing_semantics_and_project_ir_are_deferred_without_global_failure",
        "test_concrete_join_uses_bind_direct_explicit_branching_and_repeated_paths",
    ),
    PRODUCTS[10][3]: (
        "test_binary_topology_allocation_multihop_and_accumulated_left",
        "test_field_instances_nulling_provenance_self_roles_and_positive_property",
    ),
    PRODUCTS[11][3]: (
        "test_slice12_owner_is_private_and_fact_catalog_is_occurrence_complete",
        "test_independent_fact_branches_form_exact_chasm_and_multiplication_risk",
    ),
    PRODUCTS[12][3]: (
        "test_valid_phase62_root_verifies_with_fixed_empty_issue_order",
        "test_oracle_scaling_order_and_inner_swap_metamorphisms_are_bag_exact",
    ),
    PRODUCTS[13][3]: (
        "test_verified_bundle_only_admission_and_exact_runtime_closure",
        "test_typed_queries_are_scope_closed_and_return_complete_buckets",
    ),
    PRODUCTS[14][3]: (
        "test_every_environment_matches_one_reviewed_common_manifest",
        "test_real_authored_continuity_and_required_metamorphics_are_exact",
    ),
}

PRODUCT_SYMBOLS = {
    "src/pietto/_project/project_relationships.py": (
        "ProjectRelationshipDeclarationIdentity",
        "ProjectConcreteRelationshipSubject",
        "build_project_relationships",
    ),
    "src/pietto/_project/project_relationship_conditions.py": (
        "ProjectRelationshipEqualityCorrespondence",
        "ProjectConcreteRelationshipCondition",
        "build_project_relationship_conditions",
    ),
    "src/pietto/_project/project_row_keys.py": (
        "ProjectRowUniquenessEvidence",
        "ProjectCandidateKeyFact",
        "build_project_row_keys",
    ),
    "src/pietto/_project/project_value_fds.py": (
        "ProjectValueFDFact",
        "ProjectValueFDIndex",
        "strict_value_fd_closure",
    ),
    "src/pietto/_project/project_grain.py": (
        "ProjectGrainFactorIdentity",
        "ProjectGrainDependencyFact",
        "ProjectGlobalGrainWitness",
    ),
    "src/pietto/_project/project_ir_relational_properties.py": (
        "ProjectIROutputCandidateKey",
        "ProjectIROutputValueFD",
        "ProjectIRProvidedIntrinsicGrain",
    ),
    "src/pietto/_project/project_relationship_match_guarantees.py": (
        "ProjectRelationshipDirectionIdentity",
        "ProjectDirectionalRelationshipMatchGuarantee",
        "ProjectRelationshipMatchGuaranteeSet",
    ),
    "src/pietto/_project/project_relationship_paths.py": (
        "ProjectRelationshipPath",
        "ProjectRelationshipPathAnalysis",
        "ProjectRelationshipJoinShapeIndex",
    ),
    "src/pietto/_project/project_relationship_uses.py": (
        "ProjectJoinUseIdentity",
        "ProjectConcreteJoinUse",
        "ProjectNonConcreteJoinUse",
    ),
    "src/pietto/_project/project_ir_joins.py": (
        "ProjectIRBinaryJoinIdentity",
        "ProjectIRBinaryJoinOccurrence",
        "ProjectIRJoinRegionStage",
    ),
    "src/pietto/_project/project_multifact.py": (
        "ProjectAggregateFactIdentity",
        "ProjectAggregateFactJoinLocality",
        "ProjectFactChasmCandidate",
        "ProjectMultiFactAlignment",
    ),
    "src/pietto/_project/project_phase62_verification.py": (
        "ProjectPhase62VerificationResult",
        "ProjectPhase62AnalysisBundle",
        "verify_project_phase62",
    ),
    "src/pietto/_project/project_bag_null_oracle.py": (
        "ProjectFiniteBag",
        "ProjectBagNullJoinSpecification",
        "evaluate_project_bag_null_join",
    ),
    "src/pietto/_project/project_phase62_inspection.py": (
        "ProjectPhase62Inspection",
        "ProjectPhase62InspectionProduct",
        "build_project_phase62_inspection",
    ),
    "src/pietto/_project/project_phase62_pure_boundary.py": (
        "PROJECT_PHASE62_INSPECTION_FORMAT",
        "ProjectPhase62PureDocument",
        "evaluate_project_phase62_document",
    ),
}

LATER_OWNERS = (
    (
        "Phase 63",
        "Additional logical JOIN forms and single-match enforcement; multi-relation SQL/project emit-SQL; correlation; nested results; open plans/outer bindings; Collect/Unnest; LATERAL/decorrelation; QUALIFY",
    ),
    (
        "Phase 64",
        "Null-safe/collation/NaN/coercive equality; temporal/range/as-of relationships; advanced types; Decimal/time/interval comparison; record/container typing; deeper nullability",
    ),
    (
        "Phase 65",
        "Aggregate algebra/state; symmetric/fanout-safe aggregates; aggregate-as-window; multistage aggregation/reaggregation; automatic aggregate/grain repair",
    ),
    (
        "Phase 66",
        "Relationship import/export; reusable relationship/key/FD/grain declarations/libraries; reusable relation/nested semantic assets",
    ),
    ("Phase 67", "Remote packages/assets, transport, registry, and trust"),
    (
        "Phase 68",
        "Dependency solver, canonical lockfile, profiling-driven Python-to-Rust kernel decision",
    ),
    (
        "Phase 69",
        "Catalog constraints/statistics; optimizer memo; join-order/hypergraph search; outer-join reordering; predicate transfer; factorized/WCOJ execution; physical joins; broad backend/catalog capabilities",
    ),
    (
        "Phase 70",
        "Public relationship/key/FD/grain/fanout/alignment and Project-IR/nested/lineage schemas; versioned representation; release readiness",
    ),
)

UNNUMBERED_LATER_OWNERS = (
    "recursive relations/fixpoints",
    "persistent incremental-cache identity",
    "incremental/differential Project IR",
    "formal rewrite certification",
    "runtime data-quality discovery",
    "general constraint/chase reasoning",
)

EXIT_LEDGER = tuple(
    (f"E{position:02d}", product[0], "SATISFIED")
    for position, product in enumerate(PRODUCTS, 1)
)

PUBLIC_BOUNDARY_PATHS = (
    "src/pietto/__init__.py",
    "src/pietto/_project/__init__.py",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/ir/builder.py",
    "src/pietto/_project_explain/__init__.py",
    "src/pietto/_project_explain/compatibility_matrix_projection.py",
    "src/pietto/_project_explain/composition.py",
    "src/pietto/_project_explain/extension_catalog_evidence_projection.py",
    "src/pietto/_project_explain/json_v1.py",
    "src/pietto/_project_explain/model.py",
    "src/pietto/_project_explain/package_requirement_projection.py",
    "src/pietto/_project_explain/portability_projection.py",
    "src/pietto/_project_explain/runtime_builder.py",
    "src/pietto/_project_explain/text.py",
    "src/pietto/sql/__init__.py",
    "src/pietto/sql/expressions.py",
    "src/pietto/sql/model.py",
    "src/pietto/sql/mysql.py",
    "src/pietto/sql/mysql_expressions.py",
    "src/pietto/sql/mysql_relations.py",
    "src/pietto/sql/mysql_render.py",
    "src/pietto/sql/postgres.py",
    "src/pietto/sql/relations.py",
    "src/pietto/sql/render.py",
    "src/pietto/sql/window_strategy.py",
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
        f"{PHASE62_BASE}..{PHASE62_HEAD}",
    ).splitlines():
        commit, tree, parent, subject = line.split("\x1f", 3)
        rows.append((commit, tree, parent, subject))
    return tuple(rows)


def test_exact_16_slice_route_and_15_product_authorities_are_closed() -> None:
    route_rows = _table(ROUTE_LOCK.read_text(encoding="utf-8"), "Exact 16-Slice Route")
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
    assert len(PRODUCTS) == len(PUBLICATIONS) == len(PRINCIPAL_TESTS) == 15
    inventory = _table(document, "Complete Product Inventory")
    assert len(inventory) == 15
    for product, publication, row in zip(
        PRODUCTS,
        PUBLICATIONS,
        inventory,
        strict=True,
    ):
        slice_name, owner, spec, test, sources = product
        assert publication[0] == slice_name
        assert owner == ROUTE[int(slice_name.split()[1]) - 1][1]
        assert (REPO_ROOT / spec).is_file()
        assert (REPO_ROOT / test).is_file()
        assert all((REPO_ROOT / path).is_file() for path in sources)
        test_text = _python_text(test)
        assert all(f"def {name}" in test_text for name in PRINCIPAL_TESTS[test])
        _published_slice, commit, tree, _parent, _subject, run, _py312, _py313 = (
            publication
        )
        assert row[0] == slice_name.removeprefix("Slice ")
        assert row[2] == f"`{spec}`"
        assert row[3] == f"`{test}`"
        assert commit[:8] in row[5]
        assert tree[:8] in row[5]
        assert run in row[5]

    starting = " ".join(_section(document, "Starting Authority").split())
    for evidence in (
        PHASE62_BASE,
        PHASE62_BASE_TREE,
        PHASE62_BASE_CI,
        PHASE62_HEAD,
        "Phase 62 = ACTIVE / COMPLETION CANDIDATE",
        "Slice 16 = CURRENT / COMPLETION CANDIDATE",
        "Phase 63 = NEXT / NOT IMPLEMENTED",
    ):
        assert evidence in starting


def test_first_parent_history_has_exact_18_single_parent_units() -> None:
    expected = (
        FAILED_PUBLICATIONS[0][1],
        PUBLICATIONS[0][1],
        *(item[1] for item in PUBLICATIONS[1:10]),
        FAILED_PUBLICATIONS[1][1],
        PUBLICATIONS[10][1],
        PUBLICATIONS[11][1],
        PUBLICATIONS[12][1],
        FAILED_PUBLICATIONS[2][1],
        PUBLICATIONS[13][1],
        PUBLICATIONS[14][1],
    )
    if _is_shallow():
        authority = " ".join(
            _section(SPEC.read_text(encoding="utf-8"), "Starting Authority").split()
        )
        assert "18 个 first-parent single-parent commits" in authority
        assert "15 个 successful Slice terminals" in authority
        assert "3 个 preserved failed publication heads" in authority
        assert "ahead/behind 为 `18/0`" in authority
        return

    history = _history_rows()
    commits = tuple(row[0] for row in history)
    assert commits == expected
    assert len(commits) == len(set(commits)) == 18
    assert _git("merge-base", PHASE62_BASE, PHASE62_HEAD) == PHASE62_BASE
    assert (
        _git("rev-list", "--left-right", "--count", f"{PHASE62_BASE}...{PHASE62_HEAD}")
        == "0\t18"
    )
    assert all(len(row[2].split()) == 1 for row in history)
    assert _git("show", "-s", "--format=%T", PHASE62_BASE) == PHASE62_BASE_TREE


def test_15_successful_terminals_match_exact_local_git_and_ci_ledger() -> None:
    document = SPEC.read_text(encoding="utf-8")
    publication_rows = _table(document, "Successful Publication Terminals")
    assert len(publication_rows) == 15
    for publication, row in zip(PUBLICATIONS, publication_rows, strict=True):
        slice_name, commit, tree, parent, subject, run, py312, py313 = publication
        assert row == (
            slice_name.removeprefix("Slice "),
            commit,
            tree,
            parent,
            subject,
            run,
            py312,
            py313,
            "push/main/attempt 1/success",
        )
    publication_authority = " ".join(
        _section(document, "Successful Publication Terminals").split()
    )
    assert "Python 3.12 与 Python 3.13 jobs 均为 success" in publication_authority
    if _is_shallow():
        return
    history = {row[0]: row for row in _history_rows()}
    for _slice, commit, tree, parent, subject, _run, _py312, _py313 in PUBLICATIONS:
        assert history[commit] == (commit, tree, parent, subject)


def test_three_failed_heads_and_direct_terminal_children_remain_explicit() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(document, "Preserved Failed Publication Lineages")
    assert len(rows) == 3
    repair_rows = _table(document, "Authorized Child Repair Deltas")
    assert len(repair_rows) == 3
    for failed, row, repair_row in zip(
        FAILED_PUBLICATIONS,
        rows,
        repair_rows,
        strict=True,
    ):
        slice_name, commit, tree, parent, subject, run, child, repair_paths = failed
        assert row == (
            slice_name.removeprefix("Slice "),
            commit,
            tree,
            run,
            child,
            "push/main/attempt 1/failure",
            "push/main/attempt 1/success",
        )
        assert repair_row == (
            slice_name.removeprefix("Slice "),
            "<br>".join(f"`M {path}`" for path in repair_paths),
        )
        publication = PUBLICATIONS[int(slice_name.split()[1]) - 1]
        assert publication[1] == child
        assert publication[3] == commit
    normalized = " ".join(document.split())
    assert "Phase-61 completion-test portability child" in normalized
    assert "not the route-lock implementation commit" in normalized
    assert "没有 production、public 或 unrelated lifecycle 扩张" in normalized
    if _is_shallow():
        return
    history = {row[0]: row for row in _history_rows()}
    for (
        _slice,
        commit,
        tree,
        parent,
        subject,
        _run,
        child,
        repair_paths,
    ) in FAILED_PUBLICATIONS:
        assert history[commit] == (commit, tree, parent, subject)
        assert history[child][2] == commit
        assert tuple(
            _git("diff", "--name-status", f"{commit}..{child}").splitlines()
        ) == tuple(f"M\t{path}" for path in repair_paths)


def test_product_symbols_principal_tests_and_private_boundaries_are_live() -> None:
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
    assert 'AUTHORED_JOIN_DEFERRED = "authored_join_deferred"' in _python_text(
        "src/pietto/_project/model.py"
    )
    assert (
        "binary JOIN lowering for an authored relationship traversal"
        in _python_text("src/pietto/ir/builder.py")
    )
    assert "len(self.path.steps) != 1" in _python_text(
        "src/pietto/_project/project_relationship_uses.py"
    )
    assert project_package.__all__ == ()
    for name in (
        "ProjectRelationshipDeclarationIdentity",
        "ProjectIRBinaryJoinOccurrence",
        "ProjectMultiFactAlignment",
        "ProjectPhase62Inspection",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
    for path in PUBLIC_BOUNDARY_PATHS:
        text = _python_text(path)
        assert "project_phase62" not in text
        assert "project_multifact" not in text
        assert "project_ir_joins" not in text
    assert not hasattr(pietto, "__version__")
    assert version("pietto") == "0.1.0"


def test_architecture_laws_exit_ledger_and_later_owners_are_closed() -> None:
    document = SPEC.read_text(encoding="utf-8")
    architecture = " ".join(
        _section(document, "Architecture Law Reconciliation").split()
    )
    for evidence in (
        "relationship declaration != endpoint direction != relationship traversal/path != authored JOIN use != binary JOIN occurrence != joined field instance",
        "row uniqueness != candidate key != Value FD != GrainDependency",
        "aggregate fact occurrence != relation declaration != fact locality",
        "canonical bytes != occurrence identity != semantic equivalence != persistent/content identity",
        "only TRUE joins",
        "FALSE / UNKNOWN never match",
        "no first / shortest / nearest / best path winner",
        "Value FD never silently becomes GrainDependency",
        "bounded BAG/NULL oracle != verifier backend != theorem prover != runtime evaluator",
    ):
        assert evidence in architecture
    assert _table(document, "Phase-62 Material Exit Ledger") == EXIT_LEDGER
    assert all(item[2] == "SATISFIED" for item in EXIT_LEDGER)
    assert "Phase62 material exits = 15/15" in document
    assert "Phase62 self-owned-open = 0" in document
    assert _table(document, "Exact Later-Owner Ledger") == LATER_OWNERS
    normalized = " ".join(document.split())
    assert all(item in normalized for item in UNNUMBERED_LATER_OWNERS)
    assert "first_value(aggregate_output_alias)" in normalized


def test_open_markers_are_historical_typed_or_transferred_not_phase62_open() -> None:
    production_paths = tuple(
        dict.fromkeys(
            path
            for _slice, _owner, _spec, _test, sources in PRODUCTS
            for path in sources
            if path.endswith(".py") and path.startswith("src/")
        )
    )
    production = "\n".join(_python_text(path) for path in production_paths)
    immutable_evidence = "\n".join(
        ((REPO_ROOT / spec).read_text(encoding="utf-8") + _python_text(test))
        for _slice, _owner, spec, test, _sources in PRODUCTS
    )
    assert not any(
        marker in production + immutable_evidence
        for marker in ("TO" + "DO", "FIX" + "ME", "T" + "BD")
    )
    assert 'DEFERRED = "deferred"' in production
    assert "AUTHORED_JOIN_DEFERRED" in production
    assert "not_constructible_from_current_authored_source" in production
    document = SPEC.read_text(encoding="utf-8")
    classifications = _table(document, "Open-Marker Classification")
    assert classifications == (
        ("TODO/FIXME/TBD", "none", "SATISFIED"),
        (
            "typed deferred/non-concrete states",
            "retained exact runtime states",
            "SATISFIED",
        ),
        (
            "historical CURRENT/NEXT/readiness prose",
            "immutable Slice-local history",
            "SATISFIED",
        ),
        ("AUTHORED_JOIN_DEFERRED", "Phase 63", "TRANSFERRED_TO_EXACT_LATER_OWNER"),
        (
            "future/later-owner boundaries",
            "Phase 63–70 or named unnumbered owner",
            "TRANSFERRED_TO_EXACT_LATER_OWNER",
        ),
    )


def test_phase63_handoff_assets_questions_and_zero_implementation_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    handoff = " ".join(_section(document, "Phase 63 Handoff").split())
    for evidence in (
        "Phase 63 = NEXT / NOT IMPLEMENTED",
        "fresh architecture/source audit, design reconciliation, and route lock",
        "AUTHORED_JOIN_DEFERRED",
        "plan-local joined row",
        "ROW_FILTER -> GROUP_AGGREGATE -> RESULT_FILTER -> WINDOW_EVALUATION -> FINAL_PROJECTION -> RELATION_ORDERING -> LIMIT",
        "multi-relation Project IR becomes executable SQL",
        "correlated/open plans",
        "nested results / Collect / Unnest / LATERAL / decorrelation",
        "QUALIFY/post-window filtering",
        "winner-free path authority",
        "no join-order optimization",
    ):
        assert evidence in handoff
    inherited = _table(document, "Phase 63 Inherited Assets")
    assert len(inherited) == 17
    assert all(row[1] == "READY" for row in inherited)
    assert "## Phase 63 route" not in document
    assert "Phase 63 Slice 1" not in document


def test_slice16_zero_delta_and_non_circular_authority() -> None:
    if not _is_shallow():
        assert _git("rev-parse", PHASE62_SLICE16_TERMINAL) == (PHASE62_SLICE16_TERMINAL)
        assert _git("show", "-s", "--format=%T", PHASE62_SLICE16_TERMINAL) == (
            PHASE62_SLICE16_TERMINAL_TREE
        )
        assert _git("show", "-s", "--format=%P", PHASE62_SLICE16_TERMINAL) == (
            PHASE62_HEAD
        )
        assert (
            _git(
                "diff",
                "--name-only",
                PHASE62_HEAD,
                PHASE62_SLICE16_TERMINAL,
                "--",
                "src",
            )
            == ""
        )
    document = SPEC.read_text(encoding="utf-8")
    for evidence in (
        "production delta = 0",
        "public / CLI / JSON / SQL delta = 0",
        "version delta = 0",
        "Phase-63 implementation delta = 0",
        "A2/M4/D0",
        "11176 passed / 2 failed",
        "SLICE16_COMPLETION_TEST_DUPLICATES_MUTABLE_LIFECYCLE_DOCUMENT_READER_OWNERSHIP",
        "commit 0 / push 0 / CI 0",
        "continuation repair: 1",
        "final Slice-16 repairs: 1/1",
        "Complete Phase 62 relationships and JOIN",
        "PASS — PHASE62_SLICE16_COMPLETION_AUDIT_PHASE63_HANDOFF_END_TO_END",
    ):
        assert evidence in document
