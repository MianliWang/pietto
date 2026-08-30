# Phase 60 Slice 10 Capability / Lineage / Inspection Integration v1

## Answer And Scope

Slice 10 closes the temporary named-window deferral through one exact chain:

```text
validated named semantics
-> target-neutral declaration/use IR
-> typed target capability evidence
-> one relation-level lowering strategy
-> native WINDOW or exact inline SQL
-> Project result/data lineage + separate semantic provenance
-> package-graph private inspection
```

The predecessor is commit
`565652eee263f376b364509326b00192b68e8e25`, tree
`fa6c4c2f687a8704af0405e57d65ef0c006163da`, with successful natural
exact-head CI `33284480050`.

This Slice adds no grammar, generated artifact, public schema, Project IR,
aggregate-as-window behavior, QUALIFY, general backend catalog, or Slice 11
broad authored matrix.

## Target Strategy And Capability

Every relation containing named uses receives exactly one typed decision:

```text
NATIVE_PRESERVE
NATIVE_REORDER
INLINE_EXACT
NOT_LOWERABLE
```

The decision retains the exact existing inline capability fact plus typed
frame, exclusion, NULL-treatment, nth-direction, use-kind, declaration-graph,
forward-reference, framed-base, and effective-default evidence. Missing or
unsupported evidence yields `NOT_LOWERABLE`; semantic validity never implies
target support.

MySQL preserves the reachable declaration closure in source order and admits
forward/backward acyclic references. PostgreSQL uses stable source-order
tie-breaking in a base-first topological order. A PostgreSQL copied base that
carries a frame cannot use native inheritance and falls back to `INLINE_EXACT`
when every equivalent inline call is supported.

Only declarations reachable from actual named uses are emitted. Unused
declarations remain in semantic IR and private inspection evidence.

## Target-Neutral IR And Equivalence

Relation-owned declaration and use coordinates are anchored by the exact
relation occurrence plus source ordinal. Names and reference spellings remain
separate from those coordinates. `RelationIR.named_windows` preserves every
declaration in source order; `WindowCallIR.named_use` preserves direct versus
extended authorship, exact target occurrence, reference spelling, and local
components. The existing `WindowCallIR.spec` remains the complete validated
effective semantics.

No target strategy enters IR. Existing inline IR and SQL remain unchanged.
The private runtime-equivalence seam compares complete effective calls while
excluding spans, named metadata, explicitness/provenance, and source spelling;
it never merges occurrences.

## SQL Boundary

Native SQL emits `WINDOW` after `HAVING` and before relation `ORDER BY` and
`LIMIT`, quoting names through each backend's existing identifier authority.
Direct reference, copied/extended use, component order/direction, frames, and
modifiers remain distinct. Frame-sensitive named uses with an effective
Pietto default emit an exact use-local frame extension instead of delegating
to backend defaults. Inline fallback emits no `WINDOW` clause and is
byte-identical to independently authored equivalent inline source.

Slice 9 target restrictions remain authoritative for both native and inline
paths. A `NOT_LOWERABLE` relation produces the existing `PIE-B1000` terminal
diagnostic and no artifact for that relation.

## Project, Lineage, And Inspection

Successful named uses now publish normal atomic Project window-result facts.
Each fact retains its exact analysis and one target-independent
`WindowSemanticProvenance` containing function/use/target identity,
PARTITION/ORDER/FRAME origins, effective frame, exclusion, NULL treatment,
nth direction, applicability, and explicitness.

Existing ordered duplicate-preserving data dependencies remain only relation
input, argument, default, partition, and order. Inherited partition/order
locations are the exact declaration components that supplied them. Frames,
exclusions, modifiers, and named spelling never become row-dependency edges.

Phase 59 package identities remain unchanged. Separate relation-owned
`PackageGraphNamedWindow` and `PackageGraphWindowSemanticProvenance` facts are
projected into private canonical inspection records. Named base and named-use
target relationships use dedicated positive links; current data-lineage paths
remain unchanged. Target capability failure remains a typed decision and does
not remove semantic provenance.

Project Explain v1 and all public CLI/JSON/lineage schemas remain unchanged.

## Reader Closure

The exact Slice 10 changed-path allowlist is:

```text
docs/language.md
docs/roadmap.md
docs/spec/phase60-slice10-capability-lineage-inspection-integration-v1.md
docs/status.md
src/pietto/semantic/capability_windows.py
src/pietto/semantic/model.py
src/pietto/semantic/analyzer.py
src/pietto/semantic/expressions.py
src/pietto/semantic/window_analysis.py
src/pietto/semantic/window_semantics.py
src/pietto/ir/model.py
src/pietto/ir/lowering.py
src/pietto/ir/builder.py
src/pietto/sql/window_strategy.py
src/pietto/sql/expressions.py
src/pietto/sql/mysql_expressions.py
src/pietto/sql/relations.py
src/pietto/sql/mysql_relations.py
src/pietto/_project/window_semantics.py
src/pietto/_project/window_persistence.py
src/pietto/_project/module_semantic_fact_preservation.py
src/pietto/_project/package_graph.py
src/pietto/_project/package_graph_inspection.py
tests/test_active_phase_lifecycle.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
tests/test_phase17_relation_schema_hardening_completion_audit.py
tests/test_phase51_private_result_role_output_identity.py
tests/test_phase52_fail_closed_capability_lookup.py
tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py
tests/test_phase52_private_capability_fact_foundation.py
tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py
tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py
tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py
tests/test_phase54_semantic_fact_preservation.py
tests/test_phase60_slice8_query_local_named_windows.py
tests/test_phase60_slice9_value_navigation_modifiers.py
tests/test_ir_completion_audit.py
tests/test_phase59_slice2_private_package_graph_model_snapshot_identity.py
tests/test_phase59_slice8_semantic_field_lineage_integration.py
tests/test_phase59_slice9_private_graph_integrity_inspection_query_canonical_pure_boundary.py
tests/test_phase59_slice11_differential_compatibility_assurance.py
tests/test_phase59_slice12_completion_audit_phase60_handoff.py
tests/test_phase60_slice10_capability_lineage_inspection_integration.py
```

This is `A3/M40/D0`, 43 paths. Grammar/generated files, goldens, package
metadata, workflows, dependencies, public schemas, Project Explain, and
Phase 59 identity owners have zero delta.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1–9 completed, Slice 10 current,
and Slice 11 next/unstarted. Natural exact-head CI owns completion without a
status-only follow-up commit. The exact ordinary commit subject is:

```text
Integrate Phase 60 window capabilities and lineage
```
