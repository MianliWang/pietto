# Phase 60 Slice 7 EXCLUDE Semantics v1

## Answer And Scope

Slice 7 implements post-clipping EXCLUDE semantics across every frame unit:

```text
authored frame
-> EXCLUDE syntax and AST
-> resolved and validated frame
-> ROWS / RANGE / GROUPS clipped base membership
-> ExcludedFrameMembershipView
```

The published predecessor is commit
`e3230673061312261955b3eafa239d04923488e1`, tree
`331b16d1eb13554930a58e66e679921325ef77d2`, with successful natural
exact-head CI `33203129112`.

This Slice adds no named-window lookup, frame IR, production SQL renderer,
legal frame-sensitive function, capability fact, lineage fact, Project IR,
public schema, NULL treatment, value-function modifier, or aggregate-as-window
behavior.

## Authored And Resolved Surface

EXCLUDE is accepted only after an authored ROWS, RANGE, or GROUPS frame:

```text
EXCLUDE NO OTHERS
EXCLUDE CURRENT ROW
EXCLUDE GROUP
EXCLUDE TIES
```

The parser maps these forms into the existing
`AuthoredWindowFrameExclusion` values. Omission remains
`AuthoredWindowFrameExclusion.OMITTED`; explicit `EXCLUDE NO OTHERS` remains
`AuthoredWindowFrameExclusion.NO_OTHERS`. Both resolve to effective
`WindowFrameExclusion.NO_OTHERS` without merging their authored evidence.

`EXCLUDE`, `NO`, `OTHERS`, and `TIES` remain contextual identifiers outside
the frame clause. Standalone EXCLUDE has no grammar route.

## Evaluation Order And Truth Table

The exact order is:

```text
partition -> ordering -> peer groups -> base frame bounds -> partition clipping -> EXCLUDE -> function evaluation
```

For clipped base membership `B`, physical current row `c`, and the canonical
current peer group `G`:

```text
NO OTHERS  -> B
CURRENT ROW -> B - {c}
GROUP       -> B - G
TIES        -> B - (G - {c})
```

Every operation is intersection or removal against `B`. TIES retains `c`
only when `c` was already in `B`; no exclusion can add a row, rewrite a bound,
rerun clipping, or modify the canonical peer partition.

## Lazy Post-Clipping Membership

`ExcludedFrameMembershipView` retains the exact validated specification,
partition size, already clipped base `range`, physical current position,
required canonical peer authority, and a source-ordered tuple of nonempty
retained `range` spans. Its `positions` iterator uses the standard library and
does not allocate a row list. Physical positions preserve row multiplicity;
no row value, hash, equality, repr, or deduplication participates.

ROWS continues to compute physical-position base intervals. RANGE continues
to own logical direction, arithmetic requirements, and peer boundaries.
GROUPS continues to compute peer-group-index base intervals. Their base
helpers accept every validated exclusion but never apply it. The generic view
receives only their already clipped contiguous membership, so equal base
membership, current position, peer evidence, and exclusion produce equal
results regardless of the frame unit.

CURRENT ROW may split one base span into left and right fragments. GROUP may
retain fragments before and after the current peer group. TIES may additionally
retain the current singleton between peer fragments. Empty output is an empty
span tuple, not a materialized list or structural failure.

## Peer Authority And No ORDER BY

GROUP and TIES consume only the Slice 6 `PeerGroupPartition`. A
`PeerGroupConstructionFailure` with unresolved typed comparisons is returned
unchanged and no partial exclusion view exists. Missing, wrong-partition, or
wrong-order peer authority fails closed. Python equality is never a fallback.

NO OTHERS and CURRENT ROW do not consume peer groups. Even if an upstream
caller already holds unresolved peer evidence, these modes can determine
their exact removals without blocking on that evidence.

With no ORDER BY, Slice 6 supplies one whole-partition peer group. Therefore:

```text
GROUP -> empty
TIES  -> current row when current row is in B, otherwise empty
```

CURRENT ROW still removes only the physical current row.

## Empty Frames And Current Outside Base

EXCLUDE may empty a structurally valid base frame. In particular:

```text
ROWS CURRENT ROW EXCLUDE CURRENT ROW -> empty
GROUPS CURRENT ROW EXCLUDE GROUP -> empty
no ORDER BY + any B + EXCLUDE GROUP -> empty
```

The view retains the exact existing `ValidatedFrame`; it never changes its
structural failures or validation-time emptiness classification. A concrete
empty effective membership remains distinct from `STRUCTURALLY_INVALID`.

When the physical current row is outside `B`, CURRENT ROW leaves `B`
unchanged. GROUP removes only `B` intersected with the current group. TIES
removes only other current-group positions already present in `B` and never
inserts the absent current row.

## FILTER And Lowering Boundaries

The aggregate boundary remains:

```text
frame including EXCLUDE -> candidate rows -> aggregate FILTER selects aggregate inputs
```

Slice 7 adds no aggregate-window admission or FILTER behavior.

The canonical lowering contract is exact:

```text
NO_OTHERS  -> EXCLUDE NO OTHERS
CURRENT_ROW -> EXCLUDE CURRENT ROW
GROUP       -> EXCLUDE GROUP
TIES        -> EXCLUDE TIES
```

Omitted EXCLUDE remains distinct from authored explicit EXCLUDE NO OTHERS.
There is no legal production caller, so this contract is not installed as a
dead frame IR or SQL renderer. Slice 9 must consume it unchanged.

## Function Policy And Later Owners

All eight current window functions remain
`FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN`. A current function with an explicit
frame and EXCLUDE parses and reaches the existing function-policy rejection;
unknown-token or parser rejection is not the authority.

Slice 8 owns query-local named-window resolution and inheritance. The exact
authored frame object and resolved component origin remain available for that
composition, but Slice 7 adds no name lookup, DAG, inheritance, or override.
Slice 9 owns the first legal frame-sensitive functions and production
explicit-frame SQL activation. Slice 10 owns backend capability gating.
Phase 64 owns comparison, coercion, collation, NULL, NaN, temporal, Decimal,
and RANGE arithmetic. Phase 65 owns aggregate-as-window and aggregate FILTER.

Existing PostgreSQL/MySQL SQL, diagnostics, CLI text/JSON,
`pietto.project-explain.v1`, package behavior, Phase 59 identities, provenance,
and lineage remain zero-delta.

## Reader Closure

The frozen changed-path allowlist is exactly:

```text
docs/language.md
docs/roadmap.md
docs/spec/phase60-slice7-exclude-semantics-v1.md
docs/status.md
grammar/Pietto.g4
src/pietto/generated/Pietto.interp
src/pietto/generated/Pietto.tokens
src/pietto/generated/PiettoLexer.interp
src/pietto/generated/PiettoLexer.py
src/pietto/generated/PiettoLexer.tokens
src/pietto/generated/PiettoParser.py
src/pietto/ast_builder.py
src/pietto/semantic/window_semantics.py
tests/test_active_phase_lifecycle.py
tests/test_phase53_window_syntax_contextual_grammar_contract.py
tests/test_phase60_slice4_rows_semantics_lowering.py
tests/test_phase60_slice5_range_semantics_lowering.py
tests/test_phase60_slice7_exclude_semantics.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M17/D0`. Generated inventory remains eight paths; exactly six
generated paths change and `generated/__init__.py` remains unchanged. No IR,
SQL, lowerer, golden, package metadata, dependency, workflow, validator,
public-schema, or Phase 59 path changes. A required twentieth path after
freeze is `READER_CLOSURE_DRIFT`.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1-6 completed, Slice 7 current,
and Slice 8 next/unstarted. Successful natural exact-head CI makes Slice 7
completed and leaves Slice 8 next/unstarted without a status-only follow-up
commit. Slice 8 is neither implemented nor authorized here.

The exact ordinary commit subject is:

```text
Add Phase 60 EXCLUDE semantics
```
