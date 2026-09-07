# Phase 64 Slice 3 Generic ON Condition Semantics And Authority Separation v1

## Gate 0 and decisions

Baseline `317ae65440447997740b58bb4eac774aa7df19b8`, tree
`8d6adc6f3056d6c578291c68d4da534482836446`, parent
`ac32bd5d8f98c7952f4276f8ba2a8c7bdc332c73`; natural CI `34102086024`,
push/main/attempt 1/success, Python jobs `101678602445` and `101678602679`.
Live remote and local main matched; index/worktree/untracked inventory clean,
no active Git operation or NUL. D01–D08, N=11 and E01–E12 remain fixed.

The existing use ledger owns binding and traversal acquisition. A private
downstream condition set consumes that exact ledger, existing base conditions
and input outputs. It is retained by completed semantic roots and contributes
only additive condition diagnostics to the existing final projection. Existing
full-operation availability diagnostics and concrete JOIN/IR guards remain.
Condition readiness is separate from operation availability.

M1/M2 keep their existing relationship uses. M3 has GENERIC_JOIN_MATCH scope,
no relationship discovery or base guarantee. M4 retains one exact directed
base condition and a JOIN_LOCAL_ON_REFINEMENT: effective matching is base AND
refinement, without synthesizing an expression. CROSS has neither ON nor VIA;
new kinds are direct binary, and multi-hop VIA plus ON is rejected.

The pre-match environment uses exact available binding/input-field occurrences.
Earlier supported JOIN null-extension is retained; this JOIN's output is never
constructed or used. Current LET/projection/aggregate/window/outer captures
are unavailable; exported existing upstream fields are ordinary inputs. Reuse
the reference-leaf walker, Project-field conversion and infer_row_expression.
Unknown/forward/unavailable/ambiguous buckets retain all candidates in order.
Nullable Bool matches only TRUE. Ordered top-level AND preserves occurrences;
OR remains intact. Conservative null-rejection proofs cover direct strict
comparisons, direct Bool and IS NOT NULL, never arbitrary referenced fields.
C04 disjunction has no unconditional key proof. The C03 adapter retains exact
base AT_MOST_ONE evidence and drops coverage, without changing the base facts.

Every new fact is derived from its constructor's exact retaining root, with
membership checked by object identity; derived positive fields are init=False.
Completed semantic roots are the current consumer and reconstruction from a
changed semantic result is the rebuild trigger. Base conditions never import
uses, paths or guarantees. No completed query block, JOIN output or SELECT AST
is fabricated. Effective-input extension and positive generic INNER/LEFT
completion belong to Slice 4; new kinds, sets and lowering retain later owners.

## Gate 1 exact path freeze

The following ACTIVE paths were selected before the first repository edit.

| Path | Direct purpose |
| --- | --- |
| docs/spec/phase64-slice3-generic-on-condition-semantics-authority-separation-v1.md | Contract, activation and corrective accounting |
| tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py | Real authored condition, authority and admission regressions |
| src/pietto/_project/project_relationship_conditions.py | Distinct generic scope and shared ordered conjunct decomposition |
| src/pietto/_project/project_relationship_uses.py | Exact pre-match binding acquisition and structural mode rules |
| src/pietto/_project/project_join_conditions.py | One new private current condition/use consumer and typed facts |
| src/pietto/_project/project_relationship_match_guarantees.py | Narrow C03 refinement bound adapter only |
| src/pietto/_project/project_completed_semantics.py | Retain condition root and exact additive diagnostics |
| docs/status.md | Prospective Slice-3 publication lifecycle |
| docs/roadmap.md | Slice 4 NEXT; no later implementation |
| docs/language.md | Condition readiness versus remaining full-operation boundary |
| docs/spec/diagnostics.md | Additive condition/combination diagnostics |
| tests/test_active_phase_lifecycle.py | Sole mutable lifecycle reader |
| tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py | Sole whole-repository Python inventory owner |
| tests/test_phase62_slice3_exact_field_correspondences_on_where_equality_null_behavior_constraint_scope_boundary.py | Preserve historical scope members while allowing generic scope |

CONTINGENCY paths are frozen below. Activation requires recording its causal
need here before mutation; no unlisted substitution is authorized.

| Path | Direct contingency purpose |
| --- | --- |
| src/pietto/_flat_relational_admission.py | Negative availability/condition diagnostic distinction |
| src/pietto/_project/project_scalar_references.py | Lower-level occurrence walker factoring if necessary |
| src/pietto/_project/project_scalar_bindings.py | Existing reference consumer compatibility if factoring requires it |
| src/pietto/_project/row_expression_type_facts.py | Preserve field conversion callers if factoring requires it |
| src/pietto/_project/project_ir_joins.py | Share existing pre-match null-extension rule, no new positive kinds |
| src/pietto/_project/module_semantic_fact_preservation.py | Exact additive diagnostic retention if upstream projection requires it |
| src/pietto/_project/project_phase62_pure_boundary.py | Existing negative use decoder compatibility only |
| src/pietto/_project/project_query_block_ir_pure_boundary.py | Existing negative completed-result decoder compatibility only |
| src/pietto/semantic/analyzer.py | Explicit condition versus operation diagnostic admission if necessary |
| tests/test_phase64_slice2_generic_on_join_kinds_set_operation_grammar_ast_spans.py | Focused syntax/admission controls, preserve old codes/messages |
| tests/test_phase62_slice10_authored_join_traversal_syntax_semantic_uses.py | Focused old authored use controls |
| tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py | Private completed-result shape reader compatibility |
| tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py | Completed-root reader compatibility |
| tests/test_phase63_slice16_completion_audit_phase64_handoff.py | Historical absence/reader claims bind historical authority |
| tests/test_phase62_slice16_completion_audit_phase63_handoff.py | Historical condition owner claims bind historical authority |
| tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py | Old differential reader compatibility |
| tests/test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation.py | Existing construction-chain reader compatibility |
| tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py | Historical future-owner absence claims |
| tests/test_phase64_slice1_flat_relational_algebra_product_phase_initiation_gate_v3_source_audit_architecture_route_lock.py | Immutable route and retained scope reader compatibility |
| tests/test_validation_performance_interlude_ii_slice4_completion_benchmark_phase64_readiness_assurance.py | Immutable historical readiness claims |
| tests/_pietto_phase62_join_differential_probe.py | Existing observation acquisition compatibility |
| tests/_pietto_phase63_query_block_ir_differential_probe.py | Existing completed-result observation compatibility |

Reservations: one new private module; six additional production readers total
(completed semantics active plus five contingencies); two existing focused
tests; twelve historical/static readers (one active plus eleven contingencies).
Unused reservations do not grant any additional path authority.

## Validation and publication accounting

Initial planned implementation is not a corrective batch. Fresh counters:
corrective batches 0/12; authoritative validators 0/4; initial commits 0/1;
natural-CI repair children 0/2. Preserve every failed log outside the repository.
Baseline red behavior tests and old M1/M2 controls precede production mutation.
Focused principal/F01/F02 run on Python 3.12 and 3.13, old JOIN/window/QUALIFY
and observer regressions, Ruff/format/Pyright/diff, generated reproducibility,
golden audit and installed-package smoke precede sealing. Final authoritative
command: `UV_PYTHON=3.13 uv run python scripts/validate.py --timings`.
Single foreground complete-chain/Ponytail review; no separate review runtime
or subagent. Ordinary initial commit and main fast-forward push, then natural
exact-head push/main/attempt 1 CI including both Python jobs close publication.
Slice 3 becomes COMPLETED / PUBLISHED prospectively; Slice 4 remains NEXT /
NOT IMPLEMENTED and Slices 5–11 remain NOT IMPLEMENTED.

Baseline red evidence: nine expected missing-condition-root failures and two
old M1/M2 controls passed. Corrective batch 1 fixes the new proof dataclass's
`field` attribute shadowing the dataclasses helper during class construction
(initial focused collection failure). Batch 2 corrects the Bool consumer call
to its existing keyword-only interface, found while inspecting that failure.
Both affect only the new condition module. Counters: repairs 2/12, validators
0/4, commits 0/1, CI children 0/2. Failed logs remain external evidence.

Corrective batch 3 makes reference union/cardinality narrowing explicit after
Pyright reported four errors. No semantics or path activation changed.
Counters: repairs 3/12, validators 0/4. The first eleven behavior checks pass.

The expanded matrix produced 47 passes and 34 failures. Independent causes
are accounted separately: batch 4 corrects the new test's JOIN-stage allocation
access to `structural.nodes`; batch 5 explicitly authors nullable fixture fields
(omitted nullability means UNKNOWN); batch 6 uses existing indented LET syntax;
batch 7 uses existing CheckMode/mode_override and build_ir(script, model) APIs.
These four batches change only the principal. Batch 8 closes the new consumer's
foreign-input acceptance: core use acquisition rebinds every retained binding
against exact existing module resolution and final output authority before
condition construction. Its real separately constructed root graft now must
fail. Paths: relationship uses and the new condition module. Repairs 8/12;
validators 0/4. No prior builder's admission semantics are broadened.

Fresh review/expanded evidence: 97 passed, four failed. The complete finding
set is frozen as four independent causes. Batch 9 retains available fields of
ambiguous aliases through the existing exact target/output resolver, preserving
both binding and field candidate multiplicity without making the binding
concrete. Batch 10 keeps non-concrete old M1/M2 paths non-ready; endpoint checks
alone do not prove a contiguous path. Both change only the new condition module.
Batch 11 corrects the principal's window-context oracle: authored WINDOW in ON
is already a parser rejection; the current-block window alias remains a semantic
negative. Batch 12 corrects its field-type oracle: an Int alias is resolved to
the supported builtin; an enum field exercises the unavailable conversion.
These two change only the principal. Repairs 12/12; validators 0/4. Any further
corrective cause requires STOP; failed evidence is retained.

## Preserved-candidate continuation

The original STOP preserved A3/M11/D0, an empty index, baseline main and all
failed logs. Explicit continuation authorizes eight additional corrective
batches, raising only the cumulative ceiling to 20; validator/initial-commit/
CI-child ceilings remain 4/1/2. The 14 candidate files were independently
reconciled against the preserved receipt before mutation; local/main/origin/main
and live remote still equal the baseline, with natural CI 34102086024 successful
at push/main/attempt 1. No path reservation or product decision changed.

Corrective batch 13 replaces the indirect `qualified` guard at forward-binding
lookup with a direct non-empty `parts` length guard. Both expressions implement
the same runtime predicate; the direct guard also proves index validity to
Pyright inside the comprehension. Qualified/bare lookup, candidate order and
malformed-name rejection are unchanged. Analogous current-binding lookup
already checks length two before indexing. The parsed reference producer never
emits an empty dotted name. Existing bare/unknown/ambiguous/forward behavior
checks cover the affected branch; no source-spelling test is introduced.
Counters: repairs 13/20; validators 0/4; initial commits 0/1; CI children 0/2.

The repaired production chain passes Pyright; principal plus F01/F02 pass
142 checks independently on Python 3.12 and 3.13. Fresh test Pyright identifies
one shared principal defect (30 reports): positive test assertions dereference
optional facts and closed use/output variants without proving their presence
or variant. Corrective batch 14 adds those runtime assertions and stable local
bindings before the existing behavioral comparisons. It strengthens the test
oracles without casts, ignores, weakened configuration or production changes.
Only the existing principal changes. Repairs 14/20; validators remain 0/4.

## Complete candidate review and pre-validator evidence

The foreground review traced authored module occurrences through exact existing
binding resolution, input-output membership, condition construction, completed
root retention and final diagnostic projection. It rechecked all twelve prior
causes and both continuation repairs. Base conditions retain their historical
comparison domain and never import the new consumer. M3 takes no relationship
discovery branch; M4 keeps the exact directed base and independent refinement.
Input field/binding pairs preserve self-use and duplicate-name multiplicity;
prior supported JOIN nullability is derived without prefix IR allocation.
Foreign roots are rejected before typing. Reference/conjunct occurrence order
and exact diagnostic objects survive construction and projection.

The null-rejection cases require a direct sufficient conjunct proof; OR is
intact. The C03 adapter is only the subset upper-bound rule and cannot stand in
for a directional base guarantee. Existing concrete JOIN constructors and IR
admission remain unchanged. Valid conditions therefore cannot complete a new
JOIN, allocate its output, bypass F01/F02, resolve set operands or produce SQL.
Existing scalar aliases, unsupported window contexts and enum-type terminals
are tested according to their actual producer contracts. Independent valid
branches remain available. No new product, architecture or trust decision was
needed. Installed Ponytail FULL and ponytail-review guidance was applied by
direct foreground review; no separate review interface or subagent ran. No
material simplification or unresolved correctness finding remains.

Fresh principal/F01/F02 evidence is 142 passed on each Python version, including
a final Python-3.12 run after the strengthened assertions. The final
Python-3.13 regression run includes that principal and passes 830 checks across
JOIN, window/QUALIFY, private observers, IR, CLI, historical and lifecycle
readers. Formal production and test Pyright both report zero errors; whole-tree
Ruff/format and diff checks pass. Native generation reproduces all eight tracked
files; golden audit passes 39 fixtures (32 byte-exact SQL, seven structural JSON);
installed-package smoke passes. No generated/golden artifact changed.

Current closure remains A3/M11/D0 across the original 14 active paths, with no
contingency activation. Production/test Python inventories are 181/433. The
authoritative validator and Gate-2 tree seal are recorded in external run
evidence; their results are not prewritten here. The ordinary publication
subject is `Add Phase 64 JOIN condition semantics`. Git and successful natural
exact-head CI alone establish the prospective lifecycle terminal. Slice 4
receives `completed.roots.join_conditions`, rooted in the exact existing use
set, with fields, references, predicates and refinement bounds; effective-output
input integration and positive generic INNER/LEFT completion remain its work.
