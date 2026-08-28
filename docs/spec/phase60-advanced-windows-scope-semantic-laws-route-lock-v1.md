# Phase 60 Advanced Windows Scope, Semantic Laws, And Route Lock v1

## Answer And Static Scope

Phase 60 owns exactly:

```text
Advanced Windows And Phase 51–60 Readiness Checkpoint
```

Slice 1 activates that owner and freezes the semantic architecture and exact
13-Slice route. It is documentation and static assurance only. It does not add
accepted syntax, AST fields, semantic carriers, IR fields, SQL, diagnostics,
capability facts, lineage facts, public output, or package behavior.

| Slice 1 surface | Contract |
| --- | --- |
| Production changes | `0` |
| Public behavior changes | `0` |
| Public schema changes | `0` |
| Grammar/generated changes | `0` |
| Golden changes | `0` |
| Package/build metadata changes | `0` |
| Workflow/validator changes | `0` |
| Slice 2 implementation | `FORBIDDEN` |
| Current version | `0.1.0` |

The semantic model is not reduced to the feature intersection of PostgreSQL
and MySQL. Pietto defines one target-independent meaning first and admits SQL
lowering only through exact target capability evidence.

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `852568c33ed4a6ad7d311d776f68f5971ab90dd5` |
| Tree | `7f479de3b76e49cb028fb4463f0de86b66f1329c` |
| Parent | `ca26320ad8d754d6d00c607c0334e911a8b3c014` |
| Subject | `Bump actions/setup-java from 5.7.0 to 6.0.0` |
| Natural exact-head CI | `33158588908`, `push`, `main`, successful |
| Interlude completion commit | `e6da1fbe6b18ad88ae3c09568ba1f7d0e76817d1` |
| Interlude completion subject | `Complete validation performance interlude` |
| Interlude completion CI | `33155753995`, `push`, `main`, successful |
| Divergence | `0/0` |

Successful natural CI on that exact Interlude Slice 6 head establishes:

```text
Phase 59 = COMPLETED
Validation/Test Performance Optimization Interlude = COMPLETED
Phase 60 = NEXT / NOT IMPLEMENTED
```

## Live Existing Window Authority Audit

The live authority is a bounded, frame-free inline window implementation. The
table classifies primary owners; generic compiler callers remain readers and
do not become duplicate semantic authority.

| Existing authority | Exact live owners | Slice 1 finding |
| --- | --- | --- |
| Source grammar and parsed identity | `grammar/Pietto.g4`; `src/pietto/ast_nodes.py`; `src/pietto/ast_builder.py`; `src/pietto/_window_identity.py` | Direct selected `window:` blocks preserve partition/order source order, duplicates, directions, spans, and exact function occurrence identity; frames and named windows are absent |
| Semantic orchestration and stages | `src/pietto/semantic/expressions.py`; `src/pietto/semantic/window_analysis.py`; `src/pietto/semantic/window_semantics.py`; `src/pietto/semantic/window_input_analysis.py` | One private `WINDOW` stage admits direct selected outputs and rejects nested or same-stage window dependencies |
| Partition, ordering, and navigation facts | `src/pietto/semantic/window_partition_analysis.py`; `src/pietto/semantic/window_order_analysis.py`; `src/pietto/semantic/window_navigation_analysis.py` | Direct-field partition/order bindings and bounded `lag`/`lead` value, offset, default, type, and nullability facts are source preserving; no frame authority exists |
| Current function capability facts | `src/pietto/semantic/capability_windows.py`; `src/pietto/semantic/capability_providers.py`; `src/pietto/semantic/capability_facts.py` | Exact private signature/lowering facts exist for `row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile`, `lag`, and `lead`; they authorize no advanced feature |
| Current IR and lowering | `src/pietto/ir/model.py`; `src/pietto/ir/lowering.py`; `src/pietto/ir/builder.py` | `WindowSpecIR` is private, inline, ordered, and explicitly frame free |
| PostgreSQL and private MySQL rendering | `src/pietto/sql/expressions.py`; `src/pietto/sql/mysql_expressions.py`; `src/pietto/sql/relations.py`; `src/pietto/sql/mysql_relations.py` | Both render only the already-validated frame-free current IR and fail closed on malformed or nested window IR |
| Project result and dependency facts | `src/pietto/_project/window_semantics.py`; `src/pietto/_project/window_persistence.py`; `src/pietto/_project/module_semantic_fact_preservation.py`; `src/pietto/_project/model.py`; `src/pietto/_project/row_dependency_graph.py`; `src/pietto/_project/row_lineage.py` | Current roles are relation input, argument, default, partition, and order; output occurrence identity and ordered duplicate-preserving dependencies are stable; no frame role exists |
| Phase 59 package-aware lineage | `src/pietto/_project/package_graph.py`; `src/pietto/_project/package_graph_inspection.py` | `PackageGraphCurrentWindowLineage` integrates current evidence without frames; package/module/declaration/field identities are already separate and must not migrate |
| Public language contract | `docs/language.md` | The current public contract still rejects frames, named windows, `QUALIFY`, and arbitrary nesting; Slice 1 does not change it |

The existing static assurance is concentrated in the Phase 53 window tests,
especially syntax/AST, semantic stage and dependency roles, partition/order,
navigation, multiple-output lineage, and IR/capability lowering contracts.
Phase 59 Slice 8, 10, and 12 tests own current-window lineage and handoff
evidence. Those tests remain historical/current behavior authority rather than
being copied into a new implementation.

## Existing Phase 60 And Later Classification

| Classification | Exact boundary |
| --- | --- |
| Existing and retained | Frame-free inline specifications; eight current function identities; mandatory local ordering; source-preserved partition/order; current result occurrence identity, project dependency roles, Phase 59 current-window lineage, private capability facts, and dual-backend current SQL |
| Phase 60 | Typed `ROWS`/`RANGE`/`GROUPS` frames, all five bound forms, shorthand and `BETWEEN`, four `EXCLUDE` forms, query-local named windows and monotonic single-base DAGs, exact value/navigation modifiers, target capability gating, and window/frame lineage attachment |
| Later owner | Project IR/sharing, `QUALIFY`, advanced RANGE typing/coercion/comparison, advanced aggregation/grouping, reusable package window assets, the first Rust-kernel decision, backend/catalog expansion, and public window/lineage projection |

Current capability facts do not become proof of Phase 60 support. Historical
readiness contracts do not become behavior. Slice 1 adds no placeholder
production carrier merely to reserve a later name.

## Authored Resolved Validated Target-Lowerable Stages

The semantic pipeline has four distinct conceptual stages:

```text
Authored
-> Resolved
-> Validated
-> Target-lowerable
```

| Stage | Exact authority |
| --- | --- |
| Authored | Source-located component occurrences, omission/explicitness, names and base references, original ordering, and exact spelling |
| Resolved | Query-block namespace resolution, monotonic named-window composition, effective defaults, resolved expressions, and retained authorship provenance |
| Validated | Structural legality, function-by-frame/modifier admissibility, ordering/peer requirements, and frame-cardinality evidence |
| Target-lowerable | One exact validated specification paired with complete target capability evidence for every emitted feature |

Every transition is fail closed and total over its declared input: success
contains one complete next-stage value; rejection contains typed ordered
evidence and no partial successful value. An unresolved name, duplicate,
cycle, illegal bound, inadmissible modifier, unknown peer/type requirement, or
missing target capability cannot leak into a later stage.

Semantic validity and target support are independent. A valid Pietto window can
be not lowerable for one selected target without becoming semantically invalid.

## Authorship Provenance And Effective Defaults

These states remain distinct and must not be encoded by one overloaded
`None`:

| Authorship state | Meaning |
| --- | --- |
| Whole frame omitted | No frame component was authored |
| Shorthand end omitted | A single-bound frame was authored and its end was omitted |
| `EXCLUDE` omitted | A frame was authored without an exclusion clause |
| Explicit default-equivalent syntax | Source explicitly spells the same value Pietto would otherwise default |
| Locally authored component | The current inline or named-window occurrence authored it |
| Inherited component | It came through one resolved base-window edge |
| Resolved effective default | Pietto supplied a semantic value after full composition |
| Not-applicable frame | The function family has no frame semantics |

Pietto, not a target database, resolves defaults. For a frame-sensitive
function, an omitted whole frame resolves to:

```text
RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
EXCLUDE NO OTHERS
```

With no ordering, every partition row is a peer, so this effective default is
the whole partition. A single-bound shorthand resolves its omitted end to
`CURRENT ROW`. Omitted `EXCLUDE` resolves to `EXCLUDE NO OTHERS`. Omitted NULL
treatment resolves to `RESPECT NULLS`; omitted `nth_value` direction resolves
to `FROM FIRST`. Every explicit default-equivalent spelling retains explicit
authorship even when its resolved semantics are equal to an omitted form.

Named-window components are composed before defaults are resolved. Therefore
an absent base component may be filled monotonically by a derived occurrence;
a prematurely applied base default never acts like an authored component or an
override.

## Typed Lazy Frame Model

Frame units, bounds, exclusion, provenance, applicability, and validation
evidence are closed typed alternatives, never free-form strings. The bound
inventory is exactly:

```text
UNBOUNDED PRECEDING
offset PRECEDING
CURRENT ROW
offset FOLLOWING
UNBOUNDED FOLLOWING
```

The unit inventory is exactly `ROWS`, `RANGE`, and `GROUPS`. The exclusion
inventory is exactly `NO OTHERS`, `CURRENT ROW`, `GROUP`, and `TIES`.

A frame denotes a lazy view over one resolved ordered partition for the
current row. It is not a materialized tuple of member rows and Pietto remains a
compiler, not a row executor. Tests may use independent finite examples, but a
Python list or Python equality operation never becomes semantic authority.

Authored window/frame occurrences remain distinct even when their complete
resolved specifications are semantically equivalent.

## Resolution Pipeline And Unit Semantics

The semantic order is fixed:

```text
partition
-> ordering
-> peer groups
-> bounds
-> partition clipping
-> EXCLUDE
-> function evaluation
```

`ROWS` bounds count exact ordered row occurrences. `GROUPS` bounds count peer
groups. `RANGE` offset bounds describe a value-distance relative to the current
row's resolved order value and require one effective order key; `PRECEDING` and
`FOLLOWING` reverse their arithmetic direction under `DESC`. Phase 60 never
implements RANGE distance with Python arithmetic as authority.

`CURRENT ROW` is unit-sensitive:

- under `ROWS`, it is the exact current row occurrence;
- under `RANGE` and `GROUPS`, a start uses the first peer and an end uses the
  last peer.

Peer equivalence derives from the complete resolved ordering semantics,
including logical type, direction, and any future applicable comparison,
collation, or null-order facts. It is not Python `==`, object identity, source
text equality, or a target's accidental default.

After bound resolution, both ends are clipped to the current partition. Then
`EXCLUDE CURRENT ROW` removes only the exact current occurrence;
`EXCLUDE GROUP` removes it and every peer; `EXCLUDE TIES` removes its other
peers but retains the current occurrence; and `EXCLUDE NO OTHERS` removes
nothing.

## Structural Legality And Empty-frame Evidence

Structural legality is separate from cardinality. A start cannot be
`UNBOUNDED FOLLOWING` and an end cannot be `UNBOUNDED PRECEDING`. Ignoring the
numeric value inside an offset, the categorical order is exactly:

```text
UNBOUNDED PRECEDING
< offset PRECEDING
< CURRENT ROW
< offset FOLLOWING
< UNBOUNDED FOLLOWING
```

A start category after its end category is structurally invalid. Two bounds in
the same offset category are not rejected by category alone; their exact
offset relation contributes to empty-frame classification. Offset-bearing
bounds require non-null, nonnegative, admissible offset evidence. No invalid
frame reaches cardinality classification.

Phase 60 Slices 4 and 6 may use the existing exact nonnegative `Int`-literal
authority for `ROWS` and `GROUPS`. Slice 5 owns RANGE structure, direction, the
single-order-key requirement, and a typed offset seam. Numeric/Decimal/
temporal/date/timestamp/interval/timezone coercion, typed arithmetic and
overflow, comparison/peer expansion, and general constant/foldability rules
remain Phase 64. Missing Phase 64 evidence is not guessed.

For `ROWS` and `GROUPS`, an exact zero `Int` offset is semantically equivalent
to `CURRENT ROW` while retaining its authored offset-bound provenance. RANGE
zero equivalence requires the Phase 64 type-specific zero evidence and is never
inferred from Python. Before that evidence exists, Slice 5 can validate and
lower offset-free RANGE forms using `UNBOUNDED` and `CURRENT ROW`; an
offset-bearing RANGE form stops before `Validated` with typed missing-evidence
rejection rather than becoming a partial validated or target-lowerable frame.

Every analyzed frame result carries exactly one classification; a structurally
invalid result contains no validated effective frame:

| Classification | Meaning |
| --- | --- |
| Structurally invalid | No validated frame exists |
| Guaranteed nonempty | Every admissible current-row evaluation retains at least one member after clipping and exclusion |
| Possibly empty | Partition position, peer cardinality, offsets, or exclusion can leave zero members |
| Always empty | Bound algebra plus exclusion leaves zero members for every admissible current-row evaluation |

Both bounds and exclusion participate. For example,
`ROWS BETWEEN CURRENT ROW AND CURRENT ROW` is guaranteed nonempty before
exclusion, the same frame with `EXCLUDE CURRENT ROW` is always empty, and
`RANGE`/`GROUPS BETWEEN CURRENT ROW AND CURRENT ROW EXCLUDE GROUP` is always
empty. Empty-frame result nullability/type refinement remains Phase 64; the
classification evidence itself is Phase 60-owned and must survive lowering and
lineage inspection.

## Function Frame And Modifier Admissibility

Function-by-frame and function-by-modifier policy is typed and fail closed.
Explicit frame syntax on a frame-insensitive function is rejected rather than
silently ignored, including when that frame is inherited from a named window.

| Function family | Exact identities | Frame policy | NULL treatment | `FROM` policy |
| --- | --- | --- | --- | --- |
| Ranking/distribution | `row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile` | Not applicable; explicit/effective authored frame rejected | Rejected | Rejected |
| Offset navigation | `lag`, `lead` | Not applicable; explicit/effective authored frame rejected | `RESPECT NULLS` or `IGNORE NULLS` | Rejected |
| Frame value | `first_value`, `last_value` | Frame-sensitive | `RESPECT NULLS` or `IGNORE NULLS` | Rejected |
| Nth frame value | `nth_value` | Frame-sensitive | `RESPECT NULLS` or `IGNORE NULLS` | `FROM FIRST` or `FROM LAST` |
| Aggregate-as-window | Phase 65-admitted aggregate identities only | Frame-sensitive input contract; no new Phase 60 aggregate admission | Existing aggregate-owned NULL behavior, not NULL treatment syntax | Rejected |

The current eight identities retain their mandatory nonempty resolved local
ordering. Phase 60's three frame-value identities also require nonempty
resolved ordering, supplied locally or through a named window. Slice 9 owns
the private `first_value`, `last_value`, and `nth_value` identities together
with their modifiers; `nth_value` reuses an exact positive `Int`-literal
position until Phase 64 authorizes broader constant/foldability evidence.

NULL treatment never changes frame membership, peer groups, bounds, or
exclusion. `RESPECT NULLS` retains every candidate row even when its value is
NULL. `IGNORE NULLS` removes only candidate rows whose evaluated value is NULL
before the function counts candidates; it does not remove rows from the frame
or partition.

For `lag`/`lead`, the offset counts that partition candidate sequence and an
out-of-range lookup evaluates the existing default relative to the current
row. For frame-value functions, candidates come from the post-exclusion frame;
`first_value` and `last_value` select its first or last candidate, while
`FROM FIRST/LAST` changes only the direction in which `nth_value` counts.
An absent candidate or absent requested position yields NULL. Phase 64 owns
static empty-frame/result nullability refinement, not this runtime meaning.

## Named-window Scope And Monotonic DAG

A named-window declaration has query-block-scoped occurrence identity using
its owning query block plus declaration position and source location. A bare
name string is lookup syntax, not identity. Names do not cross query blocks,
modules, packages, imports, or aliases.

Forward and backward references are both legal. Resolution requires an exact
local namespace and rejects duplicate declarations, dangling references, and
cycles without selecting a winner or publishing a partial resolved namespace.
Every declaration or inline composition has zero or one base.

Composition is monotonic across the three components `PARTITION`, `ORDER`, and
`FRAME`: a local occurrence may add only a component absent from its fully
resolved base. Repeating an inherited component is an error even when the local
component would be semantically equivalent. There is no override precedence,
shadow winner, multiple inheritance, fallback, or best-match selection.
Dependency traversal may precede a forward declaration internally, but
resolved declarations and uses retain query source order; resolution never
sorts or deduplicates authored occurrences.

Direct reference and composition authorship remain different:

```text
direct reference to w
!=
composition from w plus locally authored components
```

They may resolve to semantically equivalent specifications without merging
their use occurrences or declaration provenance.

## Occurrence Identity And Semantic Equivalence

Current `WindowOccurrenceIdentity` remains the identity root for one selected
window result. Phase 60 may attach authored/resolved window-spec, named-window,
frame, modifier, capability, and lineage facts without changing its existing
source/relation/output-ordinal/span identity.

Semantic equivalence is a separate future-stable relation over complete
resolved semantic components and their typed expressions. It excludes source
locations, authored omission/explicitness, named-window declaration identity,
reference path, and target rendering choice. It never rewrites equality or
hashing of authored occurrences.

Phase 61 may use this equivalence seam for physical Project IR sharing, but
equivalent occurrences remain distinct provenance and lineage facts.

## Cross-domain Stage Boundaries

The following distinctions are mandatory:

```text
aggregate argument ORDER BY != window ORDER BY
frame membership != NULL treatment
frame membership precedes aggregate FILTER application
package dependency != semantic visibility
current-window/frame evidence != Phase 59 identity migration
```

Window evaluation remains after row filtering, grouping, and admitted
non-window aggregate results. A window call cannot contain a nested window
call, and a window input cannot resolve to another output in the same window
stage. Forward/backward named-window references do not authorize forward/
backward same-stage result dependencies.

Aggregate internal ordering, `FILTER`, generic modifiers, and deeper aggregate
argument semantics remain Phase 65. `QUALIFY` and post-window filtering remain
Phase 63. Package loading or dependency edges grant no module/name/window
visibility and reusable package window assets remain Phase 66.

## Capability-gated Lowering And Lineage Attachment

Target lowerability requires exact complete evidence for the selected target
and every used atom: function identity, unit, bound forms, shorthand/default
projection, exclusion, named-window rendering or proven exact composition,
NULL treatment, `FROM` direction, expression/type requirements, and backend
SQL shape. Dialect name alone, current eight-function facts, target parser
acceptance, or another backend's support is not evidence.

Lowering consumes the validated resolved specification. It does not re-resolve
names, re-run semantic validation, delegate defaults to the database, omit an
unsupported clause, or emulate an unsupported shape by a best-effort rewrite.
Any semantics-preserving named-window inlining optimization requires its own
explicit capability and byte-level assurance; Slice 1 authorizes none.

Frame inputs and modifier inputs attach through typed source-ordered roles to
the existing window result occurrence and Phase 59 lineage roots. Repeated
input occurrences remain repeated; derived edges may deduplicate only under
the existing role/target rule while retaining first exact witnesses. No new
frame fact changes package, module, declaration, field, let, or current-window
occurrence identity.

Slice 10's private inspection preserves query/declaration/use/component source
order, authored versus inherited/default provenance, validation/cardinality
evidence, capability terminals, and repeated occurrences. It contains no
runtime address or owner token, performs no semantic-equivalence deduplication,
and creates no public or canonical cross-version compatibility commitment.

## Phase 51–60 Checkpoint Boundary

Slice 13 audits the completed chain without reopening prior owners:

| Phase | Published input to the checkpoint |
| ---: | --- |
| 51 | Aggregate / Grouped Project Output-Schema Foundation |
| 52 | Core Type-System Capability Foundation |
| 53 | Window Function Syntax And Capability Contract |
| 54 | Import / Module / Export Readiness |
| 55 | Semantic Package Asset Schema |
| 56 | Capability Profile Static Schema And Declared Checking |
| 57 | PostgreSQL Extension Signature-Catalog Readiness |
| 58 | Project Explain / Portability / Public Metadata Readiness |
| 59 | Package Graph And Lineage / Provenance Integration |
| 60 | Advanced Windows And Phase 51–60 Readiness Checkpoint |

The checkpoint verifies current live contracts, zero unresolved Phase
60-owned subjects, compatibility evidence, later-owner transfers, and Phase 61
readiness. It is not a release, backend expansion, public schema expansion,
historical authority rewrite, or permission to repair unrelated prior phases.

## Exact 13-slice Route

| Slice | Owner | Boundary |
| ---: | --- | --- |
| 1 | Scope / Semantic Laws / Route Lock | Documentation/static assurance; no production |
| 2 | Authored-To-Resolved Window And Frame Model | Typed authored/resolved carriers, provenance, defaults, and no lowering |
| 3 | Structural Legality, Function-Frame Policy, Empty-Frame Classification, And Stage/Nesting Rules | Fail-closed validated stage; no unit-specific SQL |
| 4 | ROWS Semantics And Lowering | Exact row-occurrence bounds and capability-gated lowering |
| 5 | RANGE Semantics, Direction-Aware Bounds, Structural ORDER BY/Type Seam, And Lowering | No Phase 64 advanced typing/coercion |
| 6 | GROUPS And Peer-Group Semantics And Lowering | Resolved peer-group authority, not Python equality |
| 7 | EXCLUDE Semantics Across All Units | Post-clipping exclusion and cardinality evidence |
| 8 | Query-Local Named-Window Scope And DAG Inheritance | Exact namespace, forward/back references, single-base monotonic composition |
| 9 | Value/Navigation Modifiers | Exact NULL-treatment family and `nth_value` FROM direction |
| 10 | Capability-Gated Lowering, Lineage, Determinism/Private Inspection, And Semantic-Equivalence Readiness | Preserve Phase 59 identity and public zero-delta |
| 11 | Real Authored Advanced-Window E2E | Real parser-to-SQL paths, not hand-built final authority |
| 12 | Differential Compatibility | Python 3.12/3.13, hash seeds, relocation, installed wheel, serial/xdist, and backend-capability negative cases |
| 13 | Phase 51–60 Completion/Readiness Audit And Phase 61 Handoff | Completion closure; no Phase 61 implementation |

## Route Expansion Rule

The published route has exactly 13 slices. Expansion requires one genuinely
independent Phase 60-owned product or compatibility authority that is necessary
for the exact owner, cannot fit any existing Slice, and is not already assigned
to a later phase. Reader omissions, review findings, validator failures,
fixture size, backend limitations, implementation convenience, optional public
output, and speculative performance work do not justify expansion.

If live evidence proves such an independent owner, work stops with
`ARCHITECTURE_DECISION_REQUIRED`; the route is never changed silently.

## Later-owner And Readiness Ledger

| Phase | Exact later owner | Phase 60 boundary |
| ---: | --- | --- |
| 61 | Project IR and semantic composition | Consume validated resolved window specs; physical sharing may use semantic equivalence without merging occurrences |
| 62 | Relationship, JOIN, grain, and fanout-safe semantics | Window evidence implies no JOIN, relationship, grain, cardinality, or fanout behavior |
| 63 | Multi-relation SQL, project emit-SQL, and `QUALIFY` | Own post-window `QUALIFY`; Phase 60 adds no project SQL layer |
| 64 | Advanced RANGE-offset typing/coercion and result refinement | Own numeric/Decimal/temporal/date/timestamp/interval/timezone semantics, comparison/peers, ASC/DESC typed arithmetic/overflow, constant/foldability, and empty-frame result nullability/type refinement |
| 65 | Advanced aggregation and grouping | Own aggregate-window admission, aggregate `FILTER`, internal ordering, grouping, and deeper aggregate-argument semantics |
| 66 | Advanced module and semantic-package assets | Own reusable window assets, ownership/import/export/re-export/alias/version/visibility/provenance |
| 67 | Remote package manager and trust boundary | Window names and assets grant no remote lookup, transport, installation, or trust expansion |
| 68 | Dependency solver, canonical lockfile, and first Rust-kernel decision | Own the first Rust-kernel decision; Phase 60 adds no Rust |
| 69 | Backend/catalog capability expansion and implementation limits | Own release-aware backend/core/extension catalogs, additional dialects, and implementation-limit evidence |
| 70 | Public schema/lineage expansion and release readiness | Own public window/frame/lineage projection; private Phase 60 facts are not public fields |

Phase 60 may create stable private attachment and capability seams required by
its own route, but it does not implement any later owner in this ledger.

## Future Test Compatibility Contract

Every Phase 60 test must be:

```text
xdist-compatible by default
serial fallback compatible
isolated in temp/env/Git/build surfaces
independent of execution order
shared repository fact acquisition where eligible, owner-local policy interpretation
paired CLI probe infrastructure where applicable
```

One genuinely non-parallel-safe case requires the narrowest evidence-backed
isolation. It must not add a suite-wide serial switch, shared fixed checkout
output, persistent PASS cache, test-order dependency, or policy-changing
generic repository scan.

Future differential tests retain Python 3.12/3.13, hash seeds, relocation,
source/wheel import origin, independent semantic constructions, command-order
equivalence, non-success propagation, and backend-capability negative cases.

## Reader Closure And Changed-path Lock

Fixed-point reader closure found two compatibility readers beyond the standard
five architecture paths: the lifecycle policy must include Phase 60 product
tests, and the Interlude Slice 3 static test owns that policy's exact glob
inventory. The frozen Slice 1 allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md
docs/status.md
tests/test_active_phase_lifecycle.py
tests/test_phase60_slice1_advanced_windows_scope_semantic_laws_route_lock.py
tests/test_validation_performance_interlude_slice3_repository_reader_acquisition_reuse.py
tests/test_workflow_lifecycle_validation_efficiency.py
```

This is `A2/M5/D0`. `tests/test_active_phase_lifecycle.py` remains the sole
direct reader of mutable `docs/status.md` and `docs/roadmap.md`. The Phase 60
product test reads only this immutable Slice 1 specification and live stable
source authorities. A required eighth path after this freeze is
`READER_CLOSURE_DRIFT`.

## Public Compatibility Release And Non-goals

Slice 1 changes no public PostgreSQL emitter, private MySQL behavior, CLI,
JSON, Semantic Metadata Artifact v1, Project Explain v1, diagnostics, grammar,
generated parser, AST, semantic model, IR, SQL, capability provider, package
graph, lineage model, fixture, golden, package metadata, dependency, workflow,
or validator behavior. Current advanced-window source remains rejected.

Phase 60 owns no database execution, optimizer, materialized row engine,
connection, introspection, package visibility rule, remote transport, solver,
lockfile, public graph/window schema, tag, GitHub Release, package publication,
signing, or attestation. Version remains `0.1.0`.

## Gate Workflow Lifecycle And Publication Subject

Gate 2 runs focused Slice 1, lifecycle, sole-reader, Phase 53 frame-absence,
Phase 59 current-window lineage, and Interlude reader-compatibility checks plus
changed-file Ruff and diff checks. It then performs one foreground Ponytail
FULL review, permits at most one causal repair generation followed by a fresh
rereview, and starts exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

A validator failure is terminal for this candidate. Generated, golden, and
package-smoke auxiliaries are not locally required because their input surfaces
have zero delta. A clean candidate is sealed, staged exactly once, committed
once, pushed once by normal fast-forward, and proven by natural exact-head
`push/main` CI on Python 3.12 and 3.13. No rerun, dispatch, amend, rebase,
squash, force push, or status-only follow-up commit is authorized.

The candidate records Phase 59 and the Interlude completed, Phase 60 active,
Slice 1 current, and Slice 2 next/unstarted. Successful natural exact-head CI
makes Slice 1 completed and leaves Slice 2 next/unstarted without a status-only
commit. Slice 2 is not implemented or authorized by Slice 1.

The exact ordinary commit subject is:

```text
Add Phase 60 advanced window route lock
```
