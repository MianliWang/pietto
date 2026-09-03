# Phase 63 Slice 7 Completion Scheduling Effective-Output Ledger Module Propagation v1

## Decision And Live Authority

Phase 63 Slice 7 adds one private snapshot-local completion product containing
an exact relation-owner inventory, retained dependency occurrences, a
dependency-first construction schedule, and one effective-output ledger entry
per owner. It does not begin Slice 8.

The live starting authority was rebound before mutation:

```text
commit b3e31fa697919155396e7437e9bfe8d52866dc70
tree   7ccaa64f281f91cb4537d45db2b77dd0ca01ceec
CI     33725329642
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Exact Owner Inventory And Dependencies

The owner inventory is exactly `ProjectIRProjectPlan.fragments` in canonical
semantic order. Every fragment contributes its exact retained
`ProjectDeclarationOccurrence`; owner names and nominal identity alone never
identify ledger entries.

Sources have no relation-input dependency. A join-free Table/Query retains its
exact `ProjectResolvedModuleRelationReference` and exact target occurrence. A
JOIN-bearing owner retains one dependency occurrence for every exact targeted
`ProjectRelationBindingOccurrence` in ledger order, including binding position
0 for the base input. The FROM spelling is not independently reinterpreted or
duplicated. Repeated bindings to the same target remain separate occurrences.

Dependencies are an ordered tuple of existing use evidence, not a new graph or
name-derived edge domain.

## Dependency-First Schedule

A stable Kahn/FIFO schedule is derived with `deque`. Canonical owner order seeds
zero-indegree readiness, and retained dependency order controls successor
processing. Complexity is `O(V + E)`.

The schedule is an immutable operational construction order, not semantic
identity, precedence, or a winner. It contains every exact owner once and
places every exact target before its consumer. A residual cycle is root
incoherence and fails closed rather than being broken.

No `ProjectCompletionGraph`, third normative dependency graph, persistent
cache, or graph resolver exists.

## Effective-Output Ledger

The ledger retains one entry per exact owner in canonical inventory order:

```text
number of entries == number of owners
concrete output XOR non-concrete terminal
```

An existing concrete fragment entry retains the exact fragment, root relation
output, and matching existing `ProjectIROutputRelationalProperties` by object
identity. No output or property is rebuilt.

A terminal carries `output = None`, its exact historical non-concrete fragment,
complete owner-local dependency occurrences, and only the blocker evidence
allowed by its closed reason. A linear exact-owner lookup is sufficient. No
name-keyed normative map is retained:

```text
compiled index != normative fact
```

## Joined Completion Readiness

For a JOIN owner whose dependencies do not require future effective outputs,
Slice 7 locates its exact retained Phase-62 region and calls the already
published Slice-2 through Slice-6 builders.

A concrete `ProjectConcreteJoinedRowSemantics` is retained unchanged as joined
completion readiness, but its binary JOIN output is not ledger output:

```text
concrete post-JOIN row authority != concrete relation-final effective output
```

The ledger reason is `JOINED_TAIL_PENDING` and `output` remains absent until
Slice 12. Query-block or Slice-6 non-concrete evidence is retained as
`JOINED_COMPLETION_NON_CONCRETE`, also without partial output.

## No-JOIN Module Propagation

A join-free historical terminal is `UPSTREAM_EFFECTIVE_OUTPUT_PENDING` only
when its exact state is `DEFERRED / UPSTREAM_DEFERRED`, it retains exactly one
resolved FROM dependency, and that target entry is `JOINED_TAIL_PENDING` or an
already recoverable propagation terminal.

The terminal retains the exact resolution occurrence, exact scheduling
dependency, exact upstream ledger entry, and exact historical fragment. Chains
such as joined A -> no-JOIN B -> no-JOIN C therefore propagate in schedule
order without completing B or C.

Imported and re-exported local spellings remain lookup surfaces. Existing
module relation resolution supplies the original target
`ProjectDeclarationOccurrence`, so cross-module propagation creates no module
graph or alias identity.

UNKNOWN, BLOCKED, unrelated DEFERRED, unresolved, or independently non-concrete
historical states remain `HISTORICAL_NON_CONCRETE`.

## Effective-Upstream JOIN Boundary

If a JOIN-bearing owner depends on a recoverable pending effective output, its
terminal is `EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED`. It retains every exact
pending dependency and upstream terminal but does not run a replacement
relationship/path construction.

Pending or future completed effective outputs do not become relationship
endpoints, Phase-62 path nodes, or inputs to a reconstructed JOIN model. Generic
JOIN over arbitrary effective row sources remains Phase 64.

## Root Historical And Later-Stage Boundary

The completion product retains one exact VERIFIED Phase-62 root and its exact
Project plan. Equal-looking foreign roots are rejected, and any changed root
requires full reconstruction.

Existing semantic facts, `AUTHORED_JOIN_DEFERRED`, Project IR fragments and
cross-relation edges, module attribution, JOIN ledgers/regions/properties, and
Slice-2 through Slice-6 products remain unchanged.

Slice 7 adds no WHERE/filtering, grouping, aggregate-over-JOIN behavior,
window/QUALIFY, projection, ordering, limit, final joined relation output,
effective-output completion, Project IR unary tail, SQL, Arrow, executor, or
public behavior. Slice 8 begins joined filtering; Slice 12 owns final output and
ledger completion.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_completion.py` |
| `A` | `docs/spec/phase63-slice7-completion-scheduling-effective-output-ledger-module-propagation-v1.md` |
| `A` | `tests/test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation.py` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

The closure is exactly seven paths, `A3/M4/D0`. The mechanical Python
inventory transition is production `168 -> 169` and tests `411 -> 412`.

The frozen 16-Slice route, public contracts, grammar/generated output,
package/dependency/workflow/version state, and every Phase-64+ implementation
remain unchanged.

## Assurance And Publication

Hermetic assurance covers complete owner/ledger inventory, deterministic
dependency-first order, same/cross-module and re-export resolution, repeated
JOIN dependencies, exact existing outputs/properties, joined readiness without
premature output, A->B->C propagation, unrelated non-concrete states,
effective-upstream JOIN rejection, historical preservation, and later-stage
negatives. The principal test reads no mutable lifecycle document.

After focused tests, targeted Pyright, Ruff, format checks, and one complete
rereview, the authoritative local validator runs exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 completion foundation`, one normal fast-forward push to `main`,
and natural exact-head CI. A failed head is preserved and never rerun.

## Slice 8 Handoff

Successful natural exact-head CI completes Slice 7 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–7 are
`COMPLETED / PUBLISHED`; Slice 8 becomes `NEXT / NOT IMPLEMENTED`; Slices 9–16
remain `NOT IMPLEMENTED`.

The exact next owner is Phase 63 Slice 8 — Joined Row Filtering. Slice 8 is not
begun here.
