# Phase 60 Slice 2 Authored-To-Resolved Window And Frame Model v1

## Answer And Scope

Slice 2 adds one private typed authored/resolved window-frame model in the
existing semantic owner. It changes no accepted Pietto source, parser, AST,
existing semantic analysis, IR, SQL, diagnostics, capability facts, lineage,
CLI, JSON, Project Explain, package behavior, or public export.

| Surface | Slice 2 result |
| --- | --- |
| Production owner | `src/pietto/semantic/window_semantics.py` |
| New production modules | `0` |
| Grammar/generated changes | `0` |
| IR/SQL changes | `0` |
| Public behavior/schema changes | `0` |
| Package/workflow/dependency changes | `0` |
| Current version | `0.1.0` |

The published predecessor is commit
`f32171af018457797bc1561b9d1c12b8561b4472`, tree
`006d4b0db0db3249c984ee7602f85c0eb80ee11d`, with successful natural
exact-head CI `33165955698`.

## Stage Boundary

`AuthoredWindowSpecification` and `ResolvedWindowSpecification` are separate
frozen/slotted private types. The authored stage retains source-located
partition/order expressions and exact frame authorship. The resolved stage
retains the authored value while carrying complete effective frame semantics
and component origins.

Slice 2 adds neither a validated nor target-lowerable carrier. It does not
claim structural legality, function admissibility, backend support, frame
membership, determinism, or semantic equivalence.

## Typed Frame Algebra

`WindowFrameUnit` is closed to:

```text
ROWS
RANGE
GROUPS
```

`WindowFrameBoundKind` is closed to:

```text
UNBOUNDED_PRECEDING
OFFSET_PRECEDING
CURRENT_ROW
OFFSET_FOLLOWING
UNBOUNDED_FOLLOWING
```

`WindowFrameBound` is a typed tagged value. Only offset variants require an
`ast_nodes.Expression`; non-offset variants forbid one. The exact expression
object is retained without copying, lowering, interpreting, folding, typing,
or creating a parallel expression model.

`WindowFrameExclusion` is closed to effective `NO_OTHERS`, `CURRENT_ROW`,
`GROUP`, and `TIES` semantics. No bound or exclusion legality is implemented.

## Explicit Authorship

`AuthoredWindowFrameKind` distinguishes:

```text
OMITTED
SHORTHAND
BETWEEN
```

The tag makes payload absence structural rather than semantic overloading:

- `OMITTED` forbids unit, bounds, and exclusion syntax;
- `SHORTHAND` requires unit/start and requires its end payload to be absent;
- `BETWEEN` requires unit, start, and explicit end.

`AuthoredWindowFrameExclusion` separately distinguishes omitted exclusion from
explicit `NO_OTHERS`, `CURRENT_ROW`, `GROUP`, and `TIES`. Therefore one tagged
value never uses bare `None` to mean whole-frame omission, shorthand-end
omission, exclusion omission, or frame non-applicability.

## Pure Effective Resolution

`resolve_authored_window_specification` is a pure private normalization. For an
applicable omitted frame, it resolves Pietto's frozen default:

```text
RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
EXCLUDE NO OTHERS
```

The exact `order_by` tuple remains in the resolved specification. Its presence
or absence is the minimum ordering context needed to interpret the default;
no peer computation or comparison occurs.

For an applicable explicit frame:

- shorthand resolves its effective end to `CURRENT_ROW`;
- `BETWEEN` retains the exact authored start/end objects;
- omitted exclusion and explicit `NO_OTHERS` both resolve to effective
  `NO_OTHERS` while their authored enums remain different;
- all other explicit exclusions retain their exact effective value.

`WindowFrameApplicability.NOT_APPLICABLE` produces a resolved frame with typed
`NOT_APPLICABLE` origin and no effective frame components. The exact authored
frame is still retained for Slice 3 function-policy analysis. It is not an
ordinary omitted/defaulted frame.

No target database default, dialect, environment variable, cwd, filesystem,
clock, randomness, cache, or external state participates.

## Component Origin Provenance

`WindowComponentOrigin` is closed to:

```text
LOCALLY_AUTHORED
INHERITED
EFFECTIVE_DEFAULT
NOT_APPLICABLE
```

The pure Slice 2 resolver produces local/default origins for partition,
ordering, and applicable frames, or a not-applicable frame origin. The resolved
model accepts exact inherited component evidence for the future Slice 8 owner,
but Slice 2 performs no named-window lookup, namespace resolution, forward/
backward traversal, cycle detection, or composition.

Empty partition/order tuples have `EFFECTIVE_DEFAULT` origin. Nonempty local
tuples have `LOCALLY_AUTHORED` origin and must equal the exact authored tuples.
`INHERITED` requires local omission plus a nonempty resolved component. An
inherited frame retains the exact authored frame evidence that supplied its
effective fields. This is a provenance seam, not a hidden resolver or
name-based identity.

## Equivalent Effective Semantics Preserve Authorship

The model deliberately keeps these authored pairs unequal while their
effective frame fields can match:

```text
omitted frame
!= authored evidence
explicit RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW

omitted EXCLUDE
!= authored evidence
explicit EXCLUDE NO OTHERS

single-bound shorthand
!= authored evidence
explicit BETWEEN the same start AND CURRENT ROW
```

Slice 2 defines no semantic-equivalence key/API and performs no deduplication.
Slice 10 owns that integration.

## Identity Privacy And Consumer Boundary

All new symbols remain private under `window_semantics.__all__ = ()`. They are
not exported from `pietto`, `pietto.semantic`, Project Explain, metadata, IR, or
SQL packages. No current semantic analyzer, project builder, package graph,
canonical inspection, query, lowerer, emitter, CLI, or serializer consumes the
model in Slice 2.

`WindowOccurrenceIdentity` and all Phase 59 package/module/declaration/field/
current-window identities, coordinates, equality, hashes, ordering, and
lineage remain unchanged. New frame facts are future attachable semantic
evidence only.

## Explicit Non-goals

Slice 2 implements no grammar/parser/generated change, authored `.pietto`
frame syntax, bound legality, empty-frame classification, function-by-frame
policy, ROWS/RANGE/GROUPS membership or lowering, peer semantics, EXCLUDE
membership, named-window resolution/inheritance, NULL treatment, `FROM`
direction, capability gating, determinism/inspection, lineage integration,
Project IR, `QUALIFY`, Phase 64 coercion, or Phase 66 package asset.

## Assurance And Changed Paths

Focused assurance covers every enum/tag variant, constructor invariants,
offset-expression identity, omission/default/shorthand normalization,
not-applicable state, component origins, frozen/hashable repeatability,
cwd/environment independence, private exports, predecessor identity, public
zero-delta readers, lifecycle, serial/xdist, Ruff, Pyright, and inventories.

The frozen changed-path allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase60-slice2-authored-resolved-window-frame-model-v1.md
docs/status.md
src/pietto/semantic/window_semantics.py
tests/test_active_phase_lifecycle.py
tests/test_phase60_slice2_authored_resolved_window_frame_model.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M5/D0`. Production delta is one existing private semantic module;
generated, golden, package, dependency, workflow, and validator deltas are
zero. `tests/test_active_phase_lifecycle.py` remains the sole mutable lifecycle
document reader. A required eighth path after freeze is
`READER_CLOSURE_DRIFT`.

## Lifecycle And Publication

The candidate records Phase 60 active, Slice 1 completed, Slice 2 current, and
Slice 3 next/unstarted. Successful natural exact-head CI makes Slice 2
completed and leaves Slice 3 next/unstarted without a status-only follow-up
commit. Slice 3 is neither implemented nor authorized here.

The exact ordinary commit subject is:

```text
Add Phase 60 authored window frame model
```
