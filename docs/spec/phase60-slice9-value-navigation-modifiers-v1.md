# Phase 60 Slice 9 Value / Navigation Modifiers v1

## Answer And Scope

Slice 9 adds the exact use-local value/navigation layer:

```text
authored modifiers
-> exact identity/signature/applicability
-> resolved modifiers and validated concrete frame
-> post-EXCLUDE candidate semantics
-> persisted validated analysis
-> target-neutral inline frame/modifier IR
-> exact backend lowering or fail-closed rejection
```

The published predecessor is commit
`8a488d857a6b299e64f45bf70cc2c59372ff47ed`, tree
`1bfbce2caed7d6cb7070871c2516b0b44256ff24`, with successful natural
exact-head CI `33268604829`.

Slice 9 owns `first_value`, `last_value`, `nth_value`, NULL treatment, and
`nth_value` FROM direction. It adds no named-window IR/SQL, named Project or
lineage facts, Project IR, aggregate-as-window behavior, public schema, or
Phase 64 coercion/refinement.

## Authored Syntax And Defaults

The exact order is:

```text
call [FROM FIRST | FROM LAST] [RESPECT NULLS | IGNORE NULLS] window-use
```

`FROM` applies only to `nth_value`; NULL treatment applies only to `lag`,
`lead`, `first_value`, `last_value`, and `nth_value`. Reverse modifier order is
parser-negative. The new words remain contextual identifiers.

Omitted NULL treatment resolves to `RESPECT NULLS`; omitted nth direction
resolves to `FROM FIRST`. Explicit default-equivalent spellings retain exact
source spans and authorship while sharing effective semantics with omission.
Modifiers belong to a concrete use and never to a named template.

## Function And Frame Policy

| Family | Identities | NULL treatment | FROM | Frame |
| --- | --- | --- | --- | --- |
| Ranking/distribution | `row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile` | forbidden | forbidden | not applicable |
| Offset navigation | `lag`, `lead` | RESPECT/IGNORE | forbidden | not applicable |
| Frame value | `first_value`, `last_value` | RESPECT/IGNORE | forbidden | frame-sensitive |
| Nth frame value | `nth_value` | RESPECT/IGNORE | FIRST/LAST | frame-sensitive |

`first_value(T)` and `last_value(T)` return nullable `T`; `nth_value(T, N)`
requires an exact positive Int literal `N >= 1` and returns nullable `T`.
Every frame-value call requires nonempty resolved ORDER, including ORDER
inherited from a named template. Inherited explicit frames are legal for these
three identities. Existing lag/lead argument, offset, default, and
frame-insensitive behavior remains unchanged.

## Candidate Semantics

The evaluation order is:

```text
partition -> ordering -> peers -> bounds -> clipping -> EXCLUDE
-> NULL treatment -> function selection
```

RESPECT retains every post-EXCLUDE position. IGNORE skips only positions whose
evaluated value is NULL; it never changes frame membership, peer groups,
bounds, exclusion, or ordering. First/last select the first/last candidate.
Nth counts from the selected end without reversing ORDER. Missing candidates
produce NULL.

For lag/lead, the current row remains the anchor. Positive offsets count
physical candidates under RESPECT and non-NULL directional candidates under
IGNORE. Offset zero always selects the current row regardless of NULL
treatment. Missing positive-offset candidates use the existing default.

## Validated Analysis And IR

`SemanticModel.window_expression_analyses` retains exact successful private
`WindowExpressionAnalysis` values bound to the exact source use and result
type. Lowering consumes this validated authority; it does not re-resolve or
revalidate frames or modifiers.

Inline `WindowCallIR` carries effective NULL treatment and nth direction with
explicitness. `WindowSpecIR` carries an optional concrete `WindowFrameIR` with
unit, effective bounds, exclusion, authored/default frame evidence,
shorthand/BETWEEN evidence, and exclusion explicitness. Frame-sensitive
functions require concrete frame IR;
all frame-insensitive functions require absent frame IR. No named-window
identity/reference enters IR.

## Backend Boundary

PostgreSQL lowers effective RESPECT NULLS and FROM FIRST through fixed backend
behavior without emitting unsupported modifier syntax. It supports ROWS and
GROUPS with exact integer-literal offsets, offset-free RANGE, and all four
EXCLUDE modes. RANGE offsets remain blocked pending Phase 64.

MySQL emits explicitly authored RESPECT NULLS and FROM FIRST. It supports ROWS
and offset-free RANGE. IGNORE NULLS, FROM LAST, GROUPS, explicit EXCLUDE, and
RANGE offsets fail closed. Omitted effective EXCLUDE NO OTHERS uses MySQL's
fixed equivalent behavior. No ORDER reversal or semantic emulation is used.

The capability inventory contains exact signatures for all eleven identities
and narrow lowering evidence for the three frame-value identities. Slice 10
still owns the general advanced-window capability, lineage, inspection, and
named-window lowering integration.

## Compatibility

Previously legal ranking/distribution SQL and lag/lead source remain stable.
Ordinary non-window calls do not gain window identity. Named semantic success
continues to defer Project integration and named IR/SQL, with zero named-window
Project or lineage facts. Phase 59 identities and public JSON schemas remain
unchanged.

## Reader Closure

The frozen changed-path allowlist is exactly:

```text
docs/language.md
docs/roadmap.md
docs/spec/phase60-slice9-value-navigation-modifiers-v1.md
docs/status.md
grammar/Pietto.g4
src/pietto/generated/Pietto.interp
src/pietto/generated/Pietto.tokens
src/pietto/generated/PiettoLexer.interp
src/pietto/generated/PiettoLexer.py
src/pietto/generated/PiettoLexer.tokens
src/pietto/generated/PiettoParser.py
src/pietto/generated/PiettoVisitor.py
src/pietto/ast_builder.py
src/pietto/ast_nodes.py
src/pietto/semantic/model.py
src/pietto/semantic/analyzer.py
src/pietto/semantic/expressions.py
src/pietto/semantic/window_analysis.py
src/pietto/semantic/window_navigation_analysis.py
src/pietto/semantic/window_semantics.py
src/pietto/semantic/capability_windows.py
src/pietto/ir/model.py
src/pietto/ir/lowering.py
src/pietto/sql/expressions.py
src/pietto/sql/mysql_expressions.py
src/pietto/_project/window_semantics.py
src/pietto/_project/module_semantic_fact_preservation.py
tests/test_active_phase_lifecycle.py
tests/test_phase60_slice9_value_navigation_modifiers.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
tests/test_ir_completion_audit.py
tests/test_phase12_order_by.py
tests/test_phase17_relation_schema_hardening_completion_audit.py
tests/test_phase51_private_result_role_output_identity.py
tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py
tests/test_phase56_slice3_canonical_capability_providers.py
tests/test_phase56_slice10_completion_audit_phase57_handoff.py
tests/test_phase57_slice1_postgresql_extension_signature_catalog_scope_lock.py
tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py
tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py
tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py
tests/test_phase53_rank_dense_rank_peer_semantics_contract.py
tests/test_phase53_window_local_ordering_direction_determinism_contract.py
tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py
tests/test_phase53_window_spec_function_identity_ast_contract.py
tests/test_phase53_window_syntax_contextual_grammar_contract.py
tests/test_phase54_semantic_fact_preservation.py
tests/test_phase60_slice3_frame_validation_function_policy.py
tests/test_phase60_slice4_rows_semantics_lowering.py
tests/test_phase60_slice5_range_semantics_lowering.py
tests/test_phase60_slice7_exclude_semantics.py
tests/test_phase60_slice8_query_local_named_windows.py
```

This is `A2/M50/D0`. Generated inventory remains eight files; exactly seven
generated paths change and `generated/__init__.py` remains unchanged. No
fixture, golden, package metadata, dependency, workflow, validator, public
schema, Phase 59 identity, or Slice 10 production path changes.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1–8 completed, Slice 9 current,
and Slice 10 next/unstarted. Natural exact-head CI owns completion without a
status-only follow-up commit. The exact ordinary commit subject is:

```text
Add Phase 60 value navigation modifiers
```
