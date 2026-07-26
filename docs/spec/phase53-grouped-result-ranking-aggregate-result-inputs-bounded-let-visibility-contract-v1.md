# Phase 53 Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let Visibility Contract v1

## Status

Phase 53 Slice 13 implements this private semantic-readiness contract. Local
completion requires successful Gate 2 evidence; publication is reserved for a
separately authorized Gate 3.

## Purpose and stage ownership

Slice 13 connects the completed GROUP result to the completed WINDOW semantic
analyzer and admits the existing field-backed `let:` subset in bounded window
slots. The stage order remains:

```text
ROW / let / where
    -> GROUP / aggregate / satisfying
    -> WINDOW
    -> final order
    -> limit
```

It adds no window IR, SQL, backend, runtime, or database behavior.

## Exact admitted grouped route

A grouped window relation requires `group by:`, at least one valid direct
aggregate projection, exactly one direct aliased selected `WindowExpr`, one of
the eight completed identities, and a concrete grouped-result input scope.
Pure grouping remains `PIE-S2320`; a no-GROUP aggregate/window mix remains
`PIE-S2312`. A valid `satisfying:` predicate may precede WINDOW but never
becomes a window input.

The immutable transient grouped scope contains only unique, concrete selected
outputs classified as `GROUP_KEY` or `AGGREGATE_RESULT`, in select order. It
does not contain the window result. Duplicate names have no winner. Invalid,
unknown, non-concrete, ordinary, computed, and unselected outputs are absent.

Partition and window-local order accept bare grouped-result names. Navigation
value/default accept those names plus the Slice 12 scalar literal forms.
Qualified grouped-result names are rejected.

## Type and nullability matrix

Group-key inputs preserve the selected output type and effective nullability.
Aggregate results preserve the established matrix:

- `count` and `count_distinct`: non-null `Int`;
- `sum(Int)`: nullable `Int`;
- `sum(Decimal)`: nullable `Decimal`;
- other supported numeric `sum`: nullable `Float`;
- `avg(Decimal)`: nullable `Decimal`;
- other supported numeric `avg`: nullable `Float`;
- `min` and `max`: nullable accepted argument type.

`lag` and `lead` reuse the exact Slice 12 generic signature and nullability
formula objects. Offset zero retains same-value nullability except all-NULL;
omitted or positive offset retains boundary nullability; a compatible explicit
non-null default removes that boundary only under the existing formula.

## Bounded let visibility

Only already-valid bare direct or chained field-backed lets are candidates.
Input fields retain priority over colliding let names.

Ungrouped admitted lets may feed partition, order, navigation value, and
navigation default slots and target private `LET_BINDING` dependencies.
Grouped admitted lets must resolve to the same input-field identity as an
already-selected supported group-key output. They inherit that output's type,
nullability, and `GROUP_KEY` identity and target its `OUTPUT_FIELD`.

Computed, literal, invalid, shadowed, forward, self, duplicate, non-concrete,
and aggregate-result lets are rejected. Qualified let references are rejected.

## Identity and structural boundaries

Slice 13 reuses exactly `row_number`, `rank`, `dense_rank`, `percent_rank`,
`cume_dist`, `ntile`, `lag`, and `lead`, including existing dispatch, arity,
signatures, policies, generic bindings, offsets, defaults, result types, and
nullability formulas.

Raw or unselected group inputs, qualified results, inline aggregates, computed
inputs, ordinary or same-select aliases, window-result aliases,
window-to-window input, nesting, windows in `where`, `group by`, aggregate
arguments, `satisfying`, or `let`, aggregate-as-window behavior, frames, named
windows, `QUALIFY`, and broader functions remain rejected.

## Diagnostic ownership

No code or message is added. Order remains identity, arity, alias, stage and
context, one-window limit, partition shape/binding, mandatory order, order
shape/binding/direction, navigation value, offset, default, generic binding,
and nullability. Missing result bindings use `PIE-S2102`; structural window
failures use `PIE-S2103`; navigation failures use `PIE-S2104`; no-GROUP mixing
uses `PIE-S2312`; duplicate outputs use `PIE-S2305`; pure grouping uses
`PIE-S2320`.

## Private project dependency contract

Role blocks remain `RELATION_INPUT`, `WINDOW_ARGUMENT`, `WINDOW_DEFAULT`,
`WINDOW_PARTITION`, and `WINDOW_ORDER`.

`WindowDependencyOccurrence` and `WindowDependencyEdge` add
`target_result_role: ProjectRowResultRole | None`. `OUTPUT_FIELD` requires
`GROUP_KEY` or `AGGREGATE_RESULT`; upstream-field, let-binding, and
relation-input targets require `None`; `ORDINARY_ROW_VALUE` and
`WINDOW_RESULT` are forbidden target roles.

Occurrences preserve duplicates and contiguous global/role ordinals. Edges
retain first `(role, target)` deduplication; conflicting roles fail closed.
Literal-only and zero-argument facts retain relation-input fallback, while an
argument/default field dependency suppresses it. Result identity remains
`WINDOW_RESULT` with `DERIVED_EXPRESSION` provenance.

Both project routes invoke and discard the transient builder. Grouped project
row state remains non-concrete until Slice 14. No schema, graph, lineage, or
model persistence is added.

## Privacy and non-goals

No serializer, metadata schema, JSON version, CLI, public API, IR, SQL,
backend, runtime, database, package, dependency, version, workflow, fixture,
golden, generated artifact, tag, release, publish, upload, signing, or
attestation behavior changes. Frames, named windows, `QUALIFY`, lowering, and
execution remain deferred.

## Gate contract

Gate 2 is limited to `A3/M68/D0`, a 60-function/489-item Slice 13 test module,
4050 focused tests, 9884 dirty-worktree passes with 185 deselected, 10069 clean
projection passes, 8 generated checks, 37 goldens, one write-mode Ruff
invocation over 69 paths, strict offline package smoke, and installed CLI
`0.1.0`. It does not stage, commit, push, fetch, merge, publish, or mutate CI.
Gate 3 requires separate authorization.
