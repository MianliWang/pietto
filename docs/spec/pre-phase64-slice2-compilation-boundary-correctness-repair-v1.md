# Pre-Phase64 Slice-2 Compilation Boundary Correctness Repair v1

## Authority and scope

Unnumbered prerequisite repair of F01/F02 and the identified F03 guide text.
Baseline `691245e48c387357f700d19b9f7318bbf79f3045`, tree
`b87a62318156e5c9f574446b365debee1fa1bdbf`, parent
`f483d2d3a73edbfd6b203fb3014758095e398e23`; natural CI `34077572865`,
push/main/attempt 1/success, Python jobs `101606592867` and `101606593025`.
Gate 0 rebound synchronized clean main, no active operation, and absent NUL.
Both original Phase-64 heads remain historical successful publications.
D01–D08, 11 Slices, E01–E12 and Slice 2 NEXT / NOT IMPLEMENTED are unchanged.

## Design recorded before production mutation

F01 rejects authored QUALIFY in `_lower_relation` after the existing JOIN guard
and before projection lowering, using `_MissingSemanticFact`/`PIE-I1000` at the
QUALIFY span. `build_ir` already discards the entire partial ScriptIR on such
errors. Parsing and completed Project QUALIFY are unchanged; no renderer patch.

F02 keeps `_dependencies` as the sole FROM/JOIN-binding acquisition owner,
including exact targets of blocked bindings and repeated use occurrences.
The old module-local FROM cycle evidence and PIE-S2302 diagnostics are reusable
evidence, but the module-import SCC and single-FROM analysis do not cover this
combined relation-use graph. A private topology rooted in the exact VERIFIED
Phase-62 input derives iterative SCCs and bounded real-edge witnesses from the
existing completion dependencies. Cyclic components retain canonical complete
members/internal edges. A per-owner immutable blocker retains reachable cycle
components and causal dependencies, without terminal-to-terminal backlinks.

`schedule` remains an actual dependency-first order: it contains only owners
unaffected by cycles, with byte-for-byte old ordering on DAGs. Cycle members and
their transitive dependents are separately retained in canonical reporting
order. Their ledger entries are non-recoverable terminals, never concrete or
no-JOIN replay. Unaffected owners continue normally. Direct consumers preserve
all-owner ledgers while allocating/evaluating only scheduled owners. The private
IR verifier and pure observer accept this exact partial schedule only when its
omitted owners are cycle-blocked terminals; structural validity is not check
success. Existing acyclic private format markers and bytes are unchanged.

Existing precise cycle Diagnostic instances are forwarded by identity; newly
detected cycles use PIE-S2302 and an actual closing FROM/JOIN span. All causes
remain private; a bounded witness suffices for a public message. No content
deduplication or generic fallback substitutes for available cycle evidence.
Exact roots, complete inventories, canonical edges and corrupt-object rejection
remain enforced. This supersedes the all-owner acyclic scheduling assumption
only for user-cycle failures, not for successful construction.

## Frozen initial path activation

Each path below is activated before its first mutation; additional activations
require a direct dependency and an entry here before editing.

| Path | Direct responsibility |
| --- | --- |
| `src/pietto/ir/builder.py` | Shared QUALIFY admission |
| `src/pietto/_project/project_completion.py` | Dependency topology, cycle evidence, schedule and terminals |
| `src/pietto/_project/project_completed_semantics.py` | Exact terminal diagnostic projection |
| `src/pietto/_project/project_final_outputs.py` | Preserve blocked base entries outside evaluation schedule |
| `src/pietto/_project/project_query_block_ir.py` | Retain blocked semantic owners as zero-allocation IR terminals |
| `src/pietto/_project/project_query_block_ir_verification.py` | Verify partial schedule and blocked-root correspondence |
| `src/pietto/_project/project_query_block_ir_pure_boundary.py` | Validate exact omitted cycle-blocked terminal domain using retained dependency records |
| `tests/test_compilation_boundary_qualify_admission.py` | New focused F01 direct/public regression family |
| `tests/test_completion_dependency_cycles.py` | New focused F02 topology/diagnostic/downstream regression family |
| `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` | Sole inventory owner; two added Python test files |
| `docs/language.md` | Identified stale JOIN/final-output/IR support text |
| `docs/project-package.md` | Identified remote/solver/Rust owners |
| `docs/spec/phase64-flat-relational-algebra-product-phase-initiation-gate-v3-source-audit-architecture-route-lock-v1.md` | Residual phase-wide additive-private statement |
| `docs/status.md` | Unnumbered repair publication/handoff only |
| `docs/roadmap.md` | Unnumbered repair prerequisite/handoff only |
| `tests/test_active_phase_lifecycle.py` | Sole mutable lifecycle reader for the repair note |
| `docs/spec/pre-phase64-slice2-compilation-boundary-correctness-repair-v1.md` | This bounded contract and final accounting |

Additional production activations: 4/10. New focused regression modules: 2/2.
Additional historical mechanical doc/test paths: 0/12 initially.
Corrective root-cause batches: 0/12 initially. Authoritative validator starts:
0/4 initially. The planned implementation is not a corrective batch.

## Focused evidence and corrective accounting

Baseline regressions: 21 expected failures (16 F01, five FROM/JOIN/mixed cycle
cases), five positive controls passed. After F01 admission, all 20 F01 checks
passed. The initial F02 six checks and the expanded 19-check set passed after
corrective batch 1: replace a test's invalid diagnostic-root graft with real
equal-looking independent errors, and make witness/union narrowing explicit
for Pyright. Only activated paths changed; focused formatting is mechanical.
Batch 1 = 1/12; validator starts remain 0/4. The old audit and its outputs are
preserved. Subsequent validation results are recorded below before sealing.

Complete candidate review covered F01 admission/partial results, exact SCCs
versus Kahn residual, mixed/repeated uses, unaffected owners, non-recursive
causes, precise diagnostic identity, forged roots, every direct consumer and
scope containment. Corrective batch 2 removes repeated whole-edge scanning
inside each causal BFS and removes blocked-owner iteration from grain work;
it also strengthens public envelope and real closing-span assertions. No new
path activation or product decision. Batches 2/12; validator starts 0/4.
Fresh review of these changes retains the same finding set.

Topology traversal is iterative. SCC discovery and one witness search per
component are bounded; canonical component collection scans cost
O(C * (V + E)). Per-owner cause extraction is O(V + E), and retaining all
blocked-owner causes can itself require O(B * E) evidence. No persistent cache,
cycle enumeration, name-based graph, or optimizer is introduced.

The implemented carriers are `ProjectCompletionTopology`,
`ProjectCompletionCycle`, and `ProjectCompletionCycleBlocker` in the existing
completion module. `DEPENDENCY_CYCLE` and `UPSTREAM_DEPENDENCY_CYCLE` extend the
existing terminal reason domain; both are non-recoverable. The topology derives
its owner/use collections from the retained verification root, and its read-only
validation checks canonical SCC/witness/diagnostic evidence. Final-output replay
preserves these base terminal objects. Query-block IR retains them as
`SEMANTIC_OUTPUT_NON_CONCRETE` without allocation. Inspection retains the exact
completion, terminal blockers, and every dependency; its existing pure records
carry the partial evaluation schedule and complete owner/dependency domain,
with no format marker or acyclic byte change.

Final actual closure is A3/M14/D0, 17 paths, exactly the activation table above.
Production Python remains 179; test Python is 429 -> 431. No additional
historical mechanical path was needed (0/12); additional production remains
4/10; new regression modules remain 2/2; corrective batches remain 2/12.

Fresh focused evidence includes 227 Phase-63/regression checks, 723 legacy
IR/SQL/CLI/cycle/lifecycle checks, and 81 post-review affected checks. The
historical-format/wheel check initially failed because sandbox uv could not
write its normal cache (read-only filesystem); its unchanged assertions passed
under the authorized normal-cache permissions. This was an environment failure,
not a production repair or a validator start. Both locally installed Python
3.12.13 and 3.13.13 execute the regression set. Exact logs and every authoritative
validator outcome remain external run evidence; no old PASS is counted anew.

## Validation and publication

Record baseline red tests and positive controls, separate focused F01/F02
results, relevant existing suites, Python 3.12/3.13, static checks, and one
complete candidate review before the authoritative Python-3.13 validator.
Preserve every failed attempt; never rerun unchanged failure. No generated,
package, dependency, workflow, SQLPlan or Phase-64 implementation delta.
The authorized ordinary commit subject is:
`Fix QUALIFY lowering admission and completion cycle handling`.
Natural exact-head push/main/attempt 1 CI closes publication; Slice 2 remains
NEXT / NOT IMPLEMENTED and is not started by this task.
