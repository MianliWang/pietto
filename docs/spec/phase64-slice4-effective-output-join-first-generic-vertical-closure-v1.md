# Phase 64 Slice 4 Effective-Output JOIN And First Generic Vertical Closure v1

## Gate 0 and scope

Baseline `dae18c78ab38e4d6fbe517218b92d6f2506da489`, tree
`42ac5a3eb9810bfeab0d1696086f51ab6f627152`, parent
`317ae65440447997740b58bb4eac774aa7df19b8`, subject
`Add Phase 64 JOIN condition semantics`. Local/main/origin/main and live remote
were rebound before editing. Natural CI `34165657512` is push/main/attempt 1 /
success, with jobs `101876063245` (3.12) and `101876063201` (3.13) successful.
Index/worktree/untracked inventory were empty; no Git operation or NUL existed.
This is a new Slice with fresh counters, independent of Slice-3 history.

D01–D08, N=11 and E01–E12 remain fixed. This owner closes supported generic
INNER/LEFT and single-VIA refinement through effective inputs and the existing
SELECT-body tail to explicit-module project check. Existing M1/M2 behavior is
retained. New kinds, multi-hop refinement, set/DISTINCT/single-match semantics,
SQL, non-SELECT output construction and whole-phase combined IR/inspection
remain with their approved later owners. E05/E10 are not claimed fully closed.

## Construction audit and selected integration

The historical completed-root builder constructs Phase-62 verification, then
Slice-3 conditions, base completion, and batch tail sets before final replay.
The current row-source sum has only existing and VERIFIED historical variants;
generic inputs must get a distinct variant. Existing binary construction
requires a path and directional guarantee, which M3 does not possess. Existing
scalar bindings and row-property/lineage bridges also assume the historical
variant. The tail already has per-owner builders, but its set membership must
explicitly support an owner-local invocation. Final-output completion already
walks the exact completion schedule and is the integration owner for available
producer results. This is not a new dependency graph or retry/fixed-point pass.

The implementation will preserve the historical base and unchanged objects,
extend the existing scheduled final-output construction, and rebuild only
affected conditions through the Slice-3 analyzer using exact current inputs.
Historical evidence and the final operative condition tuple are distinguished.
No pointer targets an incompletely initialized completed result. A small nominal
input adapter separates completed-field ownership from low-level JOIN types;
the existing expression-leaf walker can move to its lower conversion module to
avoid a condition -> scalar environment -> query block -> JOIN import cycle.

Current binary/prefix structures retain actual input and condition roots, BAG
pairing, LEFT nulling and allocation membership without a relationship proof.
Nested input-factor occurrences must retain their prior occurrence provenance;
flattening them to base factors would merge repeated self-use. Existing property
kernels apply only under their actual premises. C04 OR proves no unconditional
equality/non-nullness; C03 keeps applicable upper bounds and drops coverage.
Aggregate-safety evidence stays at the existing aggregate consumer.

The same tail builders handle current owner-local inputs; no duplicate scalar,
aggregate, window, QUALIFY or projection implementation is introduced. The final
SELECT identity factory stays canonical. New observation/IR requests remain
typed unavailable until their integration owner. Temporary admission errors may
be retired only by exact successful owner/cause/Diagnostic membership; other
same-code errors and historical ProjectSemanticResult.ok retain their meaning.

| Fact / producer | Exact root and membership | Current consumer / rebuild | Failure and counterexample |
| --- | --- | --- | --- |
| Module resolution and completion dependencies | Existing resolution target, binding and dependency occurrence tuples | Scheduled input acquisition; rebuild from changed semantic snapshot | Unknown/ambiguous target and true cycle terminals; foreign dependency with equal owner rejected |
| Available effective input adapter | Exact earlier scheduled producer entry/output and complete ordered fields, plus consumer dependency/binding role | Slice-3 condition environment and current JOIN; rebuild when producer output changes | Upstream failure has no placeholder; stale or equal-looking foreign producer/field rejected |
| Operative ON/refinement facts | Historical use identity plus explicit current pre-match input root; all references and conjuncts retained | Current INNER/LEFT builder and completed roots; input changes rebuild the condition | Invalid Bool/reference/context remains typed; old READY environment cannot receive grafted fields |
| Current JOIN row and properties | Exact owner, input uses, condition, output fields and allocation; nested input occurrences remain distinct | Extended query-block sum and existing scalar/tail bridges | No invented path/guarantee/verification; wrong input role, output root or allocation rejected |
| Owner-local tail | Exact current row source and existing stage-to-stage membership, with explicit local scope | Existing filter/aggregate/window/QUALIFY/final SELECT builders | Real errors retain exact causes; failed owners publish no partial completed output |
| Final overlay and diagnostics | Existing topology/schedule, exact canonical entries, current tail roots and successful admission causes | Real explicit-module check and downstream named inputs | Foreign/stale current root rejected; unrelated branch/errors survive; unsupported IR/SQL/Explain stay negative |

## Gate 1 frozen exact paths

All paths below are selected before the first repository edit. ACTIVE paths
are initial implementation owners. CONTINGENCY paths require a recorded causal
activation here before mutation; unused counts never authorize another path.

### ACTIVE core production

| Path | Direct purpose |
| --- | --- |
| src/pietto/_project/project_query_block.py | Distinct current joined row-source variant and exact root checks |
| src/pietto/_project/project_completion.py | Reuse dependency/topology authority and factor current readiness acquisition |
| src/pietto/_project/project_ir_joins.py | Share truthful INNER/LEFT field/property kernels without fabricated guarantees |
| src/pietto/_project/project_join_conditions.py | Rebuild operative conditions over current exact inputs through the existing analyzer |
| src/pietto/_project/project_completed_semantics.py | Retain final operative conditions and exact successful diagnostic retirement |
| src/pietto/_project/project_final_outputs.py | Scheduled effective-input adaptation, existing SELECT-tail completion and canonical output membership |

### Additional existing production: 20 exact reservations

| State | Path | Direct purpose |
| --- | --- | --- |
| ACTIVE | src/pietto/_flat_relational_admission.py | Typed owner/cause evidence for temporary availability diagnostics |
| ACTIVE | src/pietto/_project/module_semantic_fact_preservation.py | Retain exact admission causes and actual SELECT occurrences without positive historical facts |
| CONTINGENCY | src/pietto/_project/project_relationship_uses.py | Existing binding/use acquisition checks if current-input adaptation requires factoring |
| ACTIVE | src/pietto/_project/project_scalar_references.py | Current row-source dispatch; preserve the lower reference-walker API |
| ACTIVE | src/pietto/_project/row_expression_type_facts.py | Lower shared reference traversal to avoid the demonstrated runtime cycle |
| ACTIVE | src/pietto/_project/project_scalar_bindings.py | Current binding introductions and complete visible field membership |
| CONTINGENCY | src/pietto/_project/project_scalar_namespaces.py | Current row-source namespace compatibility without new LET semantics |
| ACTIVE | src/pietto/_project/project_joined_row_semantics.py | Current input field/provenance/property bridge without historical attribution grafts |
| ACTIVE | src/pietto/_project/project_joined_row_filter.py | Explicit owner-local current readiness and existing WHERE invocation |
| ACTIVE | src/pietto/_project/project_joined_aggregation.py | Current grain/multiplicity safety bridge, preserve grouping/satisfying kernels |
| CONTINGENCY | src/pietto/_project/project_joined_windows.py | Necessary current owner-local tail dispatch only |
| ACTIVE | src/pietto/_project/project_joined_qualify.py | Factor the shared tail orchestration used by historical and current owners |
| CONTINGENCY | src/pietto/_project/project_ir_relational_properties.py | Existing input/output extension and property-kernel type adaptation |
| ACTIVE | src/pietto/_project/project_grain.py | Preserve nested effective-input factor occurrences without flattening self-use |
| ACTIVE | src/pietto/_project/project_multifact.py | Truthful current region grain/risk adapter for existing aggregate consumers |
| ACTIVE | src/pietto/_project/project_query_block_ir.py | Deliberate typed rejection for current JOIN composition pending Slice 10 |
| CONTINGENCY | src/pietto/_project/project_query_block_ir_verification.py | Exact negative-terminal compatibility only |
| CONTINGENCY | src/pietto/_project/project_query_block_ir_pure_boundary.py | Existing negative observation compatibility, no format or positive integration |
| CONTINGENCY | src/pietto/_project/project_query_block_ir_inspection.py | Preserve typed rejection at the direct observer if necessary |
| CONTINGENCY | src/pietto/_project/module_attribution.py | Current input lineage factoring only if required; no fake historical attribution |

### New private production reservations: 2

| State | Path | Direct purpose |
| --- | --- | --- |
| ACTIVE | src/pietto/_project/project_current_join_inputs.py | Current effective-input ownership adapter and low-level input facts; break completed-output/JOIN coupling |
| ACTIVE | src/pietto/_project/project_current_joins.py | Minimal current INNER/LEFT binary/prefix construction and safety checks |

### Tests and guides

| State / category | Path | Direct purpose |
| --- | --- | --- |
| ACTIVE required | docs/spec/phase64-slice4-effective-output-join-first-generic-vertical-closure-v1.md | This authority/consumer/path/repair contract |
| ACTIVE required | tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py | Small real vertical controls, then principal composition acceptance |
| CONTINGENCY new focused 1 | tests/test_phase64_slice4_effective_join_authority_and_failures.py | Root grafts, stale inputs, cycles and precise blockers if a separate focused family is needed |
| CONTINGENCY new focused 2 | tests/test_phase64_slice4_effective_join_tail_and_entrypoints.py | Tail/import/re-export/entrypoint matrix if a separate family is needed |
| ACTIVE existing focused 1 | tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py | Preserve condition laws; transfer temporary complete-operation rejection assertions |
| ACTIVE existing focused 2 | tests/test_phase64_slice2_generic_on_join_kinds_set_operation_grammar_ast_spans.py | Preserve syntax and unsupported entrypoints; update exact explicit-module admission |
| CONTINGENCY existing focused 3 | tests/test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation.py | Current supported effective-input behavior without weakening cycle/identity laws |
| CONTINGENCY existing helper 4 | tests/_pietto_phase63_query_block_ir_differential_probe.py | Existing negative-only observer acquisition compatibility |
| ACTIVE guide | docs/status.md | Prospective Slice-4 publication / Slice-5 NEXT |
| ACTIVE guide | docs/roadmap.md | Preserve 11-Slice route and Slice-10 outstanding work |
| ACTIVE guide | docs/language.md | Exact new success and retained negative boundaries |
| CONTINGENCY guide | docs/project-package.md | Project check versus Explain/package boundary documentation |
| ACTIVE guide | docs/spec/diagnostics.md | Exact temporary admission supersession and real failure diagnostics |
| ACTIVE lifecycle | tests/test_active_phase_lifecycle.py | Sole mutable lifecycle reader |
| ACTIVE inventory | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py | Sole whole-repository Python inventory owner |

### Historical/static-reader CONTINGENCY reservations: 12

| Path | Direct compatibility purpose |
| --- | --- |
| tests/test_phase63_slice2_query_block_owner_bridge_row_source_sum_states_mode_boundary.py | Historical two-variant/absence claims; preserve old behavioral constructors |
| tests/test_phase63_slice3_scalar_reference_environment_resolution_facts_type_kernel_adapter.py | Shared lower walker and additive row-source reader |
| tests/test_phase63_slice4_bindings_visible_joined_fields_qualified_unqualified_lookup.py | Historical binding-root-only source claims |
| tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py | Historical property/lineage bridge shape claims |
| tests/test_phase63_slice8_joined_row_filtering.py | Explicit owner-local set/readiness extension |
| tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py | Current risk-carrier compatibility while preserving aggregate safety |
| tests/test_phase63_slice11_qualify_grammar_ast_semantics_property_transfer.py | Shared tail orchestration reader |
| tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py | Exact current overlay extension and immutable old boundary claims |
| tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py | Additive operative-root/diagnostic ownership readers |
| tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py | Preserve historical accepted IR and new explicit negative terminals |
| tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py | Negative-only existing-format observer compatibility |
| tests/test_phase63_slice16_completion_audit_phase64_handoff.py | Bind historical absence/retained-later claims to historical authority |

Published Slice-1/2/3 contracts, grammar/AST/generated/golden artifacts, public
formats, dependency/lock/workflow/validator/version files are outside mutation.
No additional exact path may be introduced after this freeze.

## Checkpoints and accounting

Begin with real source/config fixtures using `schema_version = 2`, `CheckMode`,
`analyze(..., mode_override=...)`, `build_ir(script, model)`, explicit nullable
fields, indented LET and existing window syntax. First establish red generic
INNER/LEFT and single-VIA refinement completion, with old M1/M2 controls; run
production and test Pyright before expanding the matrix. Then verify exact
completed right/base inputs, downstream replay/JOIN, tail variants and failures.

Fresh counters: corrective batches 0/20; authoritative validators 0/4; initial
publication commits 0/1; natural-CI repair children 0/2. Initial implementation
is not a repair. Preserve every failed log and record independent causes before
their corrections. Required final checks include both Python principal/Slice-3/
F01/F02 runs, affected regressions, Ruff/format and both Pyright configurations,
diff, native generated/golden/package gates, full foreground review and
`UV_PYTHON=3.13 uv run python scripts/validate.py --timings`.

Seal only the reviewed and validated candidate. One ordinary commit, normal
main fast-forward push and successful natural exact-head push/main/attempt 1 CI
with both Python jobs establish publication. No rewrite, rerun, dispatch,
signing, attestation or status-only follow-up. Only then is Slice 4 COMPLETED /
PUBLISHED and Slice 5 NEXT / NOT IMPLEMENTED; Phase 64 stays ACTIVE.

## Checkpoint evidence and corrective history

Baseline minimal vertical tests: three expected PIE-S2334 failures, two old
M1/M2 controls passed. Early production/principal Pyright found one constructor
API mismatch: ProjectIROutputValueOccurrence has no output_ordinal parameter.
Corrective batch 1 removes that redundant argument from the new current binary
builder; the explicit output ref already supplies its occurrence identity.
Only project_current_joins.py changes. Repairs 1/20; validators 0/4.

The minimal producer/principal typing then passed. After row-source and tail
integration, whole-production Pyright found six non-exhaustive union-narrowing
reports: an exact-type test does not eliminate possible subclasses in its else
branch. Corrective batch 2 uses isinstance for dispatch after the closed root
constructors have validated exact variants. Paths: project_scalar_bindings.py
and project_joined_row_semantics.py. No historical verification is assigned to
a current row. Repairs 2/20; validators 0/4.

The minimal vertical checkpoint now passes all five tests and whole-production
Pyright. Test Pyright reports two historical-only assumptions in the frozen
Phase-63 Slice-4 binding reader. Activate
tests/test_phase63_slice4_bindings_visible_joined_fields_qualified_unqualified_lookup.py
before mutation; batch 3 asserts its historical region variant before inspecting
path-step fields. All original witnesses remain. Historical activations 1/12;
repairs 3/20; validators 0/4.

Activate src/pietto/_project/project_query_block_ir_verification.py for the
planned negative consumer boundary. A completed root containing current JOIN
regions has no combined Slice-10 IR yet: its existing historical IR may be
retained, but semantic completed outputs get explicit zero-allocation
CURRENT_JOIN_COMPOSITION_UNSUPPORTED terminals citing the complete current
region tuple. This prevents independently allocated tail IR from colliding
with uncomposed current-prefix coordinates. The verifier reports that typed
availability failure and cannot publish VERIFIED/analysis/inspection for it.
Old roots without current regions keep their existing behavior and bytes.
EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED remains separately owned by Slice 10.

Checkpoint 1 passes seven real tests, including exact same-code diagnostic
retirement and rejection of a forged VERIFIED current-IR result. Production
and test Pyright both pass before expanding fixtures. Existing owner-held
helper_diagnostics already provides the needed typed syntax producer: a
ProjectCurrentJoinAdmission binds those exact objects to its successful region;
no broad code/message/span filtering or new diagnostic registry is used.
Checkpoint 2 now adds completed joined/GROUPED producers in both input roles,
ordinary replay and another generic JOIN, using verified existing fixture syntax.

Checkpoint-2 red evidence contains four expected effective-input failures. The
current adapter retains completed fields and their original stage graph directly;
historical attribution/source-root projections are explicitly unavailable for
that variant, rather than fabricated. First production typing reports one
nominal-adapter variance mismatch. Corrective batch 4 types its entry through a
TYPE_CHECKING-only import of the existing concrete-entry union, preserving the
acyclic runtime dependency direction. Only project_current_join_inputs.py changes.
Repairs 4/20; authoritative validators 0/4.

Checkpoint 2 passes all eleven minimal/composition tests and production Pyright.
Activate the frozen historical reader
tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py:
four test-typing reports need explicit historical-lineage presence before old
path assertions. Batch 5 adds those assertions, retaining all witnesses.
Historical reader activations 2/12; repairs 5/20; validators 0/4.

Activate src/pietto/_project/project_relationship_uses.py for the planned mixed
M1/M2/current-prefix bridge. Reuse existing discovery/path construction and exact
retained VIA steps, allowing only proven earlier binding availability to replace
the historical unsupported-prefix blocker. Changed effective outputs are never
promoted to relationship endpoints; generic/refinement guards stay intact.

Early mixed-path typing identified two independent local causes. Batch 6 names
the per-input property variable separately from the collected JOIN-property
list in project_current_joins.py. Batch 7 makes historical/current region
dispatch explicit for hidden introductions in project_scalar_bindings.py.
Neither changes accepted semantics. Repairs 7/20; validators 0/4.

Mixed-path execution passed 13 checks and found one exact-identity level mismatch:
the hidden-field guard compared an output occurrence to its row-output wrapper.
Batch 8 compares to original.output.occurrence in project_current_joins.py,
retaining the same strict identity/provenance requirement. Repairs 8/20;
validators 0/4. The failed checkpoint log remains preserved.

The expanded matrix passed 24 cases and found two fixture-contract errors.
Batch 9 gives the selected LET value a distinct output alias, preserving
PIE-S2329 for a LET/projection collision. Batch 10 removes satisfying from the
GLOBAL positive fixture, preserving PIE-S2323 there and retaining the GROUPED
satisfying positive. Both restrictions also gain explicit current-path negative
assertions. Only the principal changes. Repairs 10/20; validators 0/4.

The planned Slice-2/3 principal migration updates only temporary complete-operation
rejection assertions: supported explicit-module INNER/LEFT now must complete,
while historical relationship-use/IR objects remain non-concrete for ON and all
other modes/kinds/entrypoints retain their negative assertions. Effective-input
conditions must now retain a current input root. Durable AST, span, Bool,
candidate/proof and foreign-root assertions remain active. Published contracts
and all old failed logs remain unchanged.

Current principal assurance reaches 34 passing cases, including preserved nested
self-use factors, independent BAG/NULL witnesses, C03/C04, aggregate-safety
denial, exact cycle diagnostics and Explain's original schema boundary.
The principal plus Slice-2/3 and F01/F02 compatibility set previously passed
318 checks. Production Pyright passes. Ruff identifies one stale import left
by lower input-field factoring; batch 11 removes it from
project_join_conditions.py. Repairs 11/20; validators 0/4.

Fresh construction review froze three independent identity defects, each
reproduced by a failing real-root counterexample. Batch 12 binds an unavailable
input blocker to its exact dependency target, beyond prefix membership.
Batch 13 requires each pre-match prefix to be the exact operative predecessor
tuple, rejecting an equal-looking newly constructed condition. Batch 14 binds
replay materialization to the exact incoming property object, not just its output
and producer. Paths: project_current_join_inputs.py, project_current_joins.py,
project_final_outputs.py and the principal. Three red failures are preserved in
review-root-red.txt. Repairs 14/20; validators 0/4; no extra path activation.

Broad regression evidence: 990 passed, five failures and eleven shared
acquisition errors. Batch 15 narrows current normalization to authored-ON owners,
their required input ancestry and resulting changed descendants, using only a
reverse walk of the existing schedule/dependencies. This restores untouched
Phase-63 reuse/rebind/stale-JOIN records and their reviewed differential manifest;
the manifest is not rewritten. Only project_final_outputs.py changes.

Activate two frozen historical readers before mutation. Batch 16 updates
tests/test_phase63_slice3_scalar_reference_environment_resolution_facts_type_kernel_adapter.py
to check the shared lower traversal callable rather than its old source-file
placement. Batch 17 binds the two old no-property-construction claims in
tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py
to their immutable published contract, retaining live no-fabricated-attribution,
no-logical-IR/no-second-model checks. No subprocess or skipped witness is added.
Historical activations 4/12; repairs 17/20; validators 0/4.

## Final candidate review and validation handoff

The fresh foreground review covered the current input/operative-condition roots,
complete dependency/prefix/allocation inventories, mixed historical/current
JOINs, property premises, owner-local tail consumers, exact diagnostic retirement
and unsupported IR/SQL/Explain boundaries. The three construction findings and
historical normalization regression above are repaired and rereviewed. There is
no remaining material finding. Ponytail review reused the existing schedule,
condition analyzer, row/property kernels and tail builders; no separate review
agent or external review tool ran.

Fresh affected regressions pass 1,107 tests, including the unchanged historical
differential manifest. The principal now contains 37 cases. Principal/Slice-3/
F01/F02 pass 179 tests on each of Python 3.12 and 3.13. Whole-repository format
(621 files), Ruff, production/test Pyright and git diff --check pass. Native
generated verification matches all 8 tracked files byte-for-byte; the golden
audit verifies 39 fixtures; installed-package/CLI smoke passes. The independent
BAG/NULL witness is a small specified test case, not executed database evidence.

The candidate uses 34 frozen paths (A4/M30/D0). Two production contingencies and
four historical readers are activated above; optional new test modules and the
historical differential helper remain unused. Corrective batches are 17/20;
no authoritative validator, publication commit or CI repair child has started
at this handoff. Final validator results, tested/sealed Git tree and natural CI
receipts are recorded outside the repository and in Git/CI, without inventing
the future commit or adding a status-only follow-up.

Slice 5 remains NEXT / NOT IMPLEMENTED. Its current reusable inputs are the
exact final operative conditions, scheduled effective-input scopes, current
JOIN regions and canonical completed SELECT outputs. Slice 10 still owns their
combined Project IR composition, verification/invalidation and inspection/pure
integration, including the final EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED closure.
Current JOIN composition remains explicitly unavailable there; E05/E10 and the
complete E01–E12 set are not claimed closed.
