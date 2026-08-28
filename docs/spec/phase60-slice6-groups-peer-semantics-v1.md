# Phase 60 Slice 6 GROUPS And Peer-Group Semantics v1

## Answer And Scope

Slice 6 establishes one canonical peer authority and consumes it for GROUPS
and RANGE CURRENT ROW:

```text
resolved window ordering
-> typed adjacent comparison evidence
-> maximal contiguous PeerGroupPartition
-> GROUPS logical/group intervals
-> RANGE CURRENT ROW peer boundaries
```

It adds authored GROUPS but no comparison evaluator, peer sorting, EXCLUDE,
frame IR, SQL renderer, legal frame-sensitive caller, capability, lineage,
Project IR, or public schema.

The published predecessor is commit
`41e1771f45a2a883510b6a519fec3693b16819cf`, tree
`dd149ffcb72ec59fb808bceca19d2fb4184761ca`, with successful natural
exact-head CI `33199855664`.

## Canonical Peer Law

The exact law is:

```text
peer(a, b) iff every resolved ordering-key comparison is EQUAL
```

`PeerComparisonEvidence` covers one adjacent row pair and one exact ordered
window key. A complete matrix is pair-major then key-major and must cover every
adjacent row pair across every key. No primary key, missing key, duplicate
slot, reordered slot, or winner is accepted.

Outcomes are `EQUAL`, `NOT_EQUAL`, or `UNRESOLVED`. Any `NOT_EQUAL` key proves
the adjacent rows are not peers even when another key is unresolved. Otherwise
an `UNRESOLVED` outcome produces `PeerGroupConstructionFailure` with every
blocking unresolved comparison and no partial groups.

The evidence contains positions, exact `OrderItem`, and typed outcome only.
It never compares row values with Python `==`, hash, repr, display text, or
object identity.

## Phase 64 Comparison Boundary

Phase 64 owns typed comparison, collation, NULL, NaN, and coercion details,
including native mappings and special values. It can supply the comparison
outcomes without changing Slice 6 grouping laws. Comparison evidence is not
part of package, module, declaration, field, or window occurrence identity.

Ordering direction remains exact evidence but does not redefine equality. The
same EQUAL/NOT_EQUAL matrix produces identical peer boundaries under ASC and
DESC; direction still controls ordering-domain movement elsewhere.

## Peer Groups And No ORDER BY

`PeerGroupPartition` retains partition size, the exact complete ordering tuple,
the complete comparison tuple, and maximal nonempty `PeerGroupInterval`
values. Each interval carries group index and half-open row boundaries;
`positions` is a lazy `range`. Rows are never sorted again, deduplicated, or
copied into group-owned lists.

With no ORDER BY there are no comparison slots and no physical-row
distinction: no ORDER BY produces one partition-wide peer group.

## Authored GROUPS And Staged Semantics

The shared frame grammar accepts:

```text
GROUPS <bound>
GROUPS BETWEEN <start> AND <end>
```

All existing bound, shorthand/BETWEEN, offset-expression, omission, and
exclusion provenance flows through the one AST and Slice 2/3 model. GROUPS is
a contextual identifier elsewhere.

Current functions remain `FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN`; authored
GROUPS is recognized/modelled and then rejected with `PIE-S2104` naming
explicit GROUPS inadmissibility.

## GROUPS Semantics And Clipping

GROUPS bounds move over group indexes:

```text
UNBOUNDED PRECEDING -> first group
k PRECEDING         -> current group - k
CURRENT ROW         -> current group
k FOLLOWING         -> current group + k
UNBOUNDED FOLLOWING -> last group
```

GROUPS CURRENT ROW selects the complete current peer group. GROUPS offsets
count peer groups, not rows; unequal group sizes never change offset distance.
Offsets use only exact nonnegative integer `LiteralExpr` evidence.

Raw inclusive group bounds are converted to a half-open interval and
intersected with `[0, group_count)`. Fully-before and fully-after requests are
empty and do not invent an edge group. Selected groups contribute the one
contiguous lazy row-position range spanning their exact group boundaries.
Legal empty GROUPS remains distinct from structural invalidity.

## RANGE Integration

The temporary Slice 5 peer-position carrier is removed. RANGE CURRENT ROW
consumes the same `PeerGroupPartition` as GROUPS:

```text
start CURRENT ROW -> current group start
end CURRENT ROW   -> current group stop - 1
```

RANGE CURRENT ROW consumes the same PeerGroupPartition. No-order RANGE uses
the canonical whole-partition group. Slice 5 direction, single-order-key, and
Phase 64 arithmetic requirement laws remain unchanged.

ROWS CURRENT ROW remains one exact physical position and consumes no peer
authority.

## EXCLUDE Readiness

The canonical peer authority exposes the exact current row position, current
group interval, and other positions in that interval. This is sufficient for
Slice 7 to distinguish current row, current group, and ties without adding an
EXCLUDE-specific list. Slice 7 owns EXCLUDE effects; Slice 6 removes nothing.

## Canonical GROUPS Lowering Contract

Slice 9 must activate:

```text
SHORTHAND -> GROUPS <bound>
BETWEEN   -> GROUPS BETWEEN <start> AND <end>

UNBOUNDED_PRECEDING -> UNBOUNDED PRECEDING
OFFSET_PRECEDING    -> <expression SQL> PRECEDING
CURRENT_ROW         -> CURRENT ROW
OFFSET_FOLLOWING    -> <expression SQL> FOLLOWING
UNBOUNDED_FOLLOWING -> UNBOUNDED FOLLOWING
```

The retained expression uses existing lowering/rendering after its evidence is
available. No successful explicit-frame SQL occurrence is required before
Slice 9, so no GROUPS IR, SQL renderer, or fake caller is introduced.

## Compatibility And Ownership

ROWS semantics, RANGE direction/offset laws, existing SQL/CLI/Project Explain,
current function policy, packages, and Phase 59 identities remain zero-delta.

Slice 6 owns peers and GROUPS. Slice 7 owns EXCLUDE effects. Slice 9 owns the
first legal frame-sensitive callers and SQL activation. Slice 10 owns backend
capability gating. Phase 64 owns advanced comparison/type details and Phase 65
owns aggregate-as-window semantics.

## Assurance And Changed Paths

Focused assurance covers complete multi-key matrices, unresolved evidence,
no-order grouping, maximal runs, direction independence, every GROUPS bound,
whole-group CURRENT ROW, unequal group sizes, group clipping/empty cases,
offset evidence, shared RANGE boundaries, independent ROWS behavior, EXCLUDE
readiness, all current policy rejections, contextual GROUPS, absence of IR/SQL
changes, and static lowering/ownership locks.

The frozen changed-path allowlist is exactly:

```text
docs/language.md
docs/roadmap.md
docs/spec/phase60-slice6-groups-peer-semantics-v1.md
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
tests/test_phase60_slice6_groups_peer_semantics.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M17/D0`. Generated inventory remains eight paths and
`generated/__init__.py` remains unchanged. No IR, SQL, lowerer, golden,
package metadata, dependency, workflow, validator, public schema, or Phase 59
path changes. A required twenty-first path after freeze is
`READER_CLOSURE_DRIFT`.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1-5 completed, Slice 6 current,
and Slice 7 next/unstarted. Successful natural exact-head CI makes Slice 6
completed and leaves Slice 7 next/unstarted without a status-only follow-up
commit. Slice 7 is neither implemented nor authorized here.

The exact ordinary commit subject is:

```text
Add Phase 60 GROUPS and peer semantics
```
