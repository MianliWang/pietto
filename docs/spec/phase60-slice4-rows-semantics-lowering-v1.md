# Phase 60 Slice 4 ROWS Semantics And Lowering v1

## Answer And Scope

Slice 4 implements the infrastructure-only ROWS boundary authorized by the
architecture continuation:

```text
authored ROWS syntax
-> AST
-> AuthoredWindowSpecification
-> ResolvedWindowSpecification
-> ValidatedWindowSpecification
-> lazy physical-position ROWS interval
```

Current ranking, distribution, and offset-navigation functions still reject
every explicit frame. Slice 4 introduces no successful explicit-frame SQL
occurrence, frame IR, SQL renderer branch, frame-sensitive identity, generic
extension function, capability fact, lineage fact, public schema field, or
Project IR.

The published predecessor is commit
`1cbc6028f32e973e002b80556638df7aafb26850`, tree
`3b3c518cc1a3a9c59868ede19aaba3bb2cd9dda9`, with successful natural
exact-head CI `33191566950`.

## Architecture Sequencing Decision

The 13-slice route unchanged rule remains authoritative. Slices 4-7 establish
frame semantics and canonical lowering contracts. No successful explicit-frame
SQL occurrence is required before Slice 9.

Slice 9 introduces the first legal frame-sensitive value-function callers:
`first_value`, `last_value`, and `nth_value`. It also activates the already
specified frame SQL emission with its modifier semantics, without redefining
ROWS, RANGE, GROUPS, or EXCLUDE. Slice 10 owns backend capability gating.
Slice 11 owns broad real authored advanced-window E2E. Aggregate-as-window
admission remains Phase 65-owned.

This is sequencing authority, not permission to move later identities or
accept explicit frames on the current eight functions.

## Authored ROWS Grammar And AST

The window body accepts exactly:

```text
ROWS <frame-bound>
ROWS BETWEEN <frame-bound> AND <frame-bound>
```

The bound inventory is unchanged:

```text
UNBOUNDED PRECEDING
<expression> PRECEDING
CURRENT ROW
<expression> FOLLOWING
UNBOUNDED FOLLOWING
```

`ROWS`, `CURRENT`, `ROW`, `UNBOUNDED`, `PRECEDING`, and `FOLLOWING` remain
contextual identifiers outside the frame clause. RANGE, GROUPS, EXCLUDE,
named-window, NULL-treatment, and FROM-direction syntax remain unreachable.

The existing `WindowFrameUnit`, `WindowFrameBoundKind`, `WindowFrameBound`,
`AuthoredWindowFrameKind`, `AuthoredWindowFrameExclusion`, and
`AuthoredWindowFrame` class objects are AST-owned and imported unchanged by
`semantic.window_semantics`. `WindowSpec.frame` carries that one model, with an
omitted-frame default for every old parsed window. No parallel parser frame
type exists.

The AST builder creates a distinct `SHORTHAND` or `BETWEEN` value and retains
the exact existing `Expression` object for every offset. The semantic bridge
retains exact span, partition tuple, order tuple, frame, bounds, offset
expression, and exclusion provenance.

## Staged Semantic And Current Function Boundary

Recognized windows now run the published stages in the existing semantic
analyzer:

```text
Authored -> Resolved -> Validated
```

Omitted frames on the current eight identities validate as typed
`NOT_APPLICABLE` and preserve all existing behavior. An explicit ROWS frame
reaches the same model and then fails with `PIE-S2104` because its exact
metadata-derived policy is `FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN`. The
diagnostic names function/frame inadmissibility; it is not a parser, unknown
function, backend, or capability failure.

Independent frame-sensitive policy evidence can validate the structural ROWS
model for Slice 4 assurance, but it does not create an authored production
function occurrence. Slice 3 remains the sole structural-legality and
function-policy authority.

## Physical ROWS Interval

`RowsFramePositionInterval` is a frozen half-open position view with only
`partition_size`, `start`, and `stop`. `positions` returns Python's lazy
`range`; no row/member list is stored.

For current position `i`, raw bounds are:

```text
UNBOUNDED PRECEDING -> 0
k PRECEDING         -> i - k
CURRENT ROW         -> i
k FOLLOWING         -> i + k
UNBOUNDED FOLLOWING -> partition_size - 1
```

The raw inclusive interval is converted to a half-open interval and
intersected with `[0, partition_size)`. Boundary clipping operates on interval
boundaries, so a frame wholly before the partition becomes `[0, 0)` and a
frame wholly after it becomes `[partition_size, partition_size)`. A legal raw
start after raw end remains an empty range; it is not structural invalidity.

ROWS has no peer input. `CURRENT ROW` therefore means exactly one physical
position and equal ordering keys cannot widen it. No tie breaker or
determinism evidence is inferred.

## Offset And EXCLUDE Boundaries

The parser and authored/resolved model retain any existing `Expression` in an
offset bound. Concrete ROWS interval evaluation narrowly accepts only an exact
nonnegative integer `LiteralExpr`, reusing the repository's existing bounded
static-integer authority. It adds no evaluator, folding, coercion, Decimal,
temporal, overflow, or general type system.

The helper computes only `EXCLUDE NO OTHERS` base frames. Any other effective
exclusion fails closed rather than being treated as no exclusion. Slice 7
still owns EXCLUDE membership.

## Canonical ROWS Lowering Contract

Slice 9 must activate exactly these renderings:

```text
SHORTHAND -> ROWS <bound>
BETWEEN   -> ROWS BETWEEN <start> AND <end>

UNBOUNDED_PRECEDING -> UNBOUNDED PRECEDING
OFFSET_PRECEDING    -> <expression SQL> PRECEDING
CURRENT_ROW         -> CURRENT ROW
OFFSET_FOLLOWING    -> <expression SQL> FOLLOWING
UNBOUNDED_FOLLOWING -> UNBOUNDED FOLLOWING
```

`<expression SQL>` means the retained expression lowered and rendered through
the existing expression authorities; it is never source-text interpolation or
a new evaluator. Authored shorthand versus BETWEEN remains the selection
authority even when their resolved effective bounds match.

There is no legal production caller in Slice 4, so no frame IR or SQL renderer
branch is added. The existing lowerer explicitly rejects a forged explicit
frame instead of silently dropping it. Slice 9 activation must consume this
contract; it may not redesign it.

## Compatibility And Later Owners

Existing frame-free SQL, PostgreSQL/MySQL rendering, CLI output,
`pietto.project-explain.v1`, diagnostics, and package behavior remain
zero-delta. No package/module/declaration/field/current-window occurrence
identity, equality, hash, ordering, dependency role, provenance, or lineage is
changed.

`first_value`, `last_value`, and `nth_value` remain absent from current
semantic/IR/SQL catalogs. Aggregate-as-window remains absent. RANGE is Slice
5-owned, GROUPS/peers Slice 6, EXCLUDE Slice 7, named windows Slice 8, legal
frame-sensitive callers and modifiers Slice 9, capability gating Slice 10,
and broad real authored E2E Slice 11.

## Assurance And Changed Paths

Focused assurance covers every bound in shorthand and both BETWEEN positions,
exact expression/provenance identity, structural invalidity, shorthand versus
BETWEEN, the required clipping examples, physical CURRENT ROW, peer
independence, legal empty intervals, nonnegative offset evidence, later-owned
exclusions/units, all eight current policy rejections, lowerer non-dropping,
contextual keyword compatibility, absence of frame IR/render helpers, and the
Slice 9/10/11/Phase 65 sequencing boundary.

The frozen changed-path allowlist is exactly:

```text
docs/language.md
docs/roadmap.md
docs/spec/phase60-slice4-rows-semantics-lowering-v1.md
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
src/pietto/ir/lowering.py
src/pietto/semantic/window_analysis.py
src/pietto/semantic/window_semantics.py
tests/test_active_phase_lifecycle.py
tests/test_phase53_window_spec_function_identity_ast_contract.py
tests/test_phase53_window_syntax_contextual_grammar_contract.py
tests/test_phase60_slice4_rows_semantics_lowering.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M20/D0`. Generated inventory remains the same eight paths;
`generated/__init__.py` remains empty and unchanged. No golden, package
metadata, dependency, workflow, validator, IR-model, SQL-renderer, public
schema, or lineage path changes. A required twenty-third path after freeze is
`READER_CLOSURE_DRIFT`.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1-3 completed, Slice 4 current,
and Slice 5 next/unstarted. Successful natural exact-head CI makes Slice 4
completed and leaves Slice 5 next/unstarted without a status-only follow-up
commit. Slice 5 is neither implemented nor authorized here.

The exact ordinary commit subject is:

```text
Add Phase 60 ROWS semantics infrastructure
```
