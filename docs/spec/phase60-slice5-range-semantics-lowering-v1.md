# Phase 60 Slice 5 RANGE Semantics And Lowering v1

## Answer And Scope

Slice 5 extends the infrastructure-only frame sequence through the complete
currently legal RANGE boundary:

```text
authored RANGE
-> shared frame AST
-> Authored / Resolved / Validated
-> logical ordering-domain RANGE request
-> peer and Phase 64 evidence seams
```

It adds no peer algorithm, ordering-value arithmetic, frame IR, SQL renderer,
legal frame-sensitive function identity, capability fact, lineage fact,
Project IR, or public schema.

The published predecessor is commit
`494acb103657badb76baf4d05aa7d7b73260c29d`, tree
`b5074c7f01c4f21e55d6dd98bbc871d879835217`, with successful natural
exact-head CI `33197322161`.

## Authored RANGE And Staged Semantics

The shared frame grammar accepts exactly:

```text
RANGE <bound>
RANGE BETWEEN <start> AND <end>
```

with the existing five bounds. `WindowFrameUnit.RANGE`, the exact bound
objects, offset `Expression`, shorthand/BETWEEN authorship, omitted exclusion,
partition/order tuples, and source span flow through the existing AST and
Slice 2/3 model without a second RANGE representation.

`RANGE` remains a contextual identifier outside a frame clause. GROUPS,
EXCLUDE, named-window, NULL-treatment, and FROM-direction syntax remain
unreachable.

All eight current functions still have
`FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN`. Authored RANGE is recognized and
modeled, then rejected with `PIE-S2104` naming explicit RANGE inadmissibility.
It is not rejected by parsing, function lookup, target capability, or
lowering.

## Direction-aware Ordering-domain Law

RANGE offsets never become ROWS-style signed physical indexes. The typed
orientation table is:

```text
ASC PRECEDING -> LOWER_ORDERING_VALUES
ASC FOLLOWING -> HIGHER_ORDERING_VALUES
DESC PRECEDING -> HIGHER_ORDERING_VALUES
DESC FOLLOWING -> LOWER_ORDERING_VALUES
```

`RangeOffsetArithmeticRequirement` retains the exact start/end role, bound,
offset expression, resolved `OrderItem`, normalized direction, and logical
orientation. It contains no evaluated value, compatibility result, arithmetic,
or backend mapping.

## Offset Ordering Cardinality

An offset RANGE requires exactly one resolved ordering key. Zero keys and two
or more keys return `RangeOffsetOrderingFailure` with the exact key count.
There is no nearest/best key selection.

Offset-free frames using only UNBOUNDED and CURRENT ROW do not inherit the
single-key restriction. They retain zero, one, or multiple complete ordering
keys for later peer authority.

## Phase 64 Requirement Seam

Every offset requirement is an unresolved request joining the exact offset
expression to the exact resolved ordering expression, direction, and logical
orientation. Phase 64 owns RANGE type, coercion, comparison, and arithmetic
evidence, including numeric/Decimal, temporal/interval/timezone rules,
foldability, overflow/underflow, and native mappings.

Slice 5 neither marks the request compatible nor evaluates it. A legal offset
frame remains `POSSIBLY_EMPTY` when no later evidence can prove stronger
cardinality.

## CURRENT ROW And Peer Boundary Seam

For RANGE, a start CURRENT ROW requests `FIRST_PEER`; an end CURRENT ROW
requests `LAST_PEER`. `RangePeerBoundaryEvidence` carries only explicit
partition/current/first/last positions and must contain the current position.
`resolve_range_current_row_boundary` consumes that evidence without comparing
ordering values.

With no window ordering, the view records the law that the whole partition is
one peer group and accepts only whole-partition peer evidence. Slice 6 owns
real peer computation and GROUPS semantics. It may satisfy this seam but may
not redefine RANGE direction, offset, or no-order laws. Python `==`, object
identity, source text, collation guesses, NULL ordering, and NaN behavior are
never peer authority here.

## Lazy RANGE View

`RangeFrameLogicalView` stores only the exact validated specification and the
ordered Phase 64 requirement tuple. Direction, ordering, and peer-boundary
requests are typed properties over those exact facts. It stores no rows,
members, materialized positions, current ordering value, comparison result, or
physical-index distance.

Partition clipping and membership remain future consumers of peer and Phase
64 evidence. Slice 5 does not guess them merely to make RANGE executable.

## Canonical RANGE Lowering Contract

Slice 9 must activate the exact syntax:

```text
SHORTHAND -> RANGE <bound>
BETWEEN   -> RANGE BETWEEN <start> AND <end>

UNBOUNDED_PRECEDING -> UNBOUNDED PRECEDING
OFFSET_PRECEDING    -> <expression SQL> PRECEDING
CURRENT_ROW         -> CURRENT ROW
OFFSET_FOLLOWING    -> <expression SQL> FOLLOWING
UNBOUNDED_FOLLOWING -> UNBOUNDED FOLLOWING
```

`<expression SQL>` uses the existing expression lowerer/renderer after Phase
64 evidence exists. There is no source interpolation or new evaluator.
Authored shorthand versus BETWEEN selects the output shape.

No successful explicit-frame SQL occurrence is required before Slice 9.
Slices 4-7 own semantic/lowering contracts; Slice 9 owns the first legal
frame-sensitive callers and SQL activation; Slice 10 owns backend capability
gating. No dead RANGE IR or renderer is added in Slice 5.

## Compatibility And Ownership

ROWS behavior, existing PostgreSQL/MySQL SQL, CLI, Project Explain v1,
diagnostics, packages, and current function policy remain zero-delta. No Phase
59 package/module/declaration/field/current-window identity, equality, hash,
ordering, dependency, provenance, or lineage changes.

Slice 5 owns RANGE direction/order-domain laws. Slice 6 owns real peer
computation and GROUPS semantics. Slice 7 owns EXCLUDE effects. Slice 9 owns
the first legal frame-sensitive callers and SQL activation. Slice 10 owns
backend capability gating. Phase 64 owns RANGE type, coercion, comparison, and
arithmetic evidence. Aggregate-as-window remains Phase 65-owned.

## Assurance And Changed Paths

Focused assurance covers every bound in shorthand and both BETWEEN roles,
exact expression/provenance identity, ASC/DESC orientation, the zero/one/many
ordering matrix, offset-free exceptions, Phase 64 requests, ordered/no-order
peer seams, logical laziness, current function rejections, ROWS regression,
later syntax/identity boundaries, absence of IR/SQL changes, contextual RANGE,
and static lowering/ownership rules.

The frozen changed-path allowlist is exactly:

```text
docs/language.md
docs/roadmap.md
docs/spec/phase60-slice5-range-semantics-lowering-v1.md
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
src/pietto/semantic/window_semantics.py
tests/test_active_phase_lifecycle.py
tests/test_phase53_window_syntax_contextual_grammar_contract.py
tests/test_phase60_slice4_rows_semantics_lowering.py
tests/test_phase60_slice5_range_semantics_lowering.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M17/D0`. Generated inventory remains the same eight paths and
`generated/__init__.py` remains unchanged. No IR, SQL, lowerer, golden,
package metadata, dependency, workflow, validator, public schema, or lineage
path changes. A required twentieth path after freeze is
`READER_CLOSURE_DRIFT`.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1-4 completed, Slice 5 current,
and Slice 6 next/unstarted. Successful natural exact-head CI makes Slice 5
completed and leaves Slice 6 next/unstarted without a status-only follow-up
commit. Slice 6 is neither implemented nor authorized here.

The exact ordinary commit subject is:

```text
Add Phase 60 RANGE semantics infrastructure
```
