# v0.2 Aggregate Surface Freeze v1

## Status

Phase 29 Slice 3 is complete as an aggregate-surface freeze contract and static
audit slice only.

This freeze records the current Phase 19 through Phase 28 aggregate and
result-scope surface that belongs inside the planned v0.2 stable single-file
typed SQL authoring compiler boundary. It does not authorize implementation,
source behavior changes, grammar changes, generated ANTLR changes, AST or
parser changes, semantic behavior changes, aggregate behavior changes, IR
behavior changes, SQL lowering changes, CLI behavior changes, JSON behavior or
schema changes, diagnostic behavior changes, fixture or golden changes, script
changes, dependency changes, package metadata changes, CI changes, public API
changes, public MySQL API expansion, runtime execution, schema introspection,
project or multi-file behavior, relationship/JOIN behavior, type-system
behavior changes, JSON v2, or new aggregate features.

## Freeze Rule

For v0.2, the Phase 19 through Phase 28 aggregate surface is frozen except for
bug fixes and audit-only clarifications.

Any aggregate expansion before v0.2 must be explicitly approved by a later
slice that names the area being unfrozen. Otherwise, aggregate work before
v0.2 is limited to bug fixes that preserve the accepted surface recorded here.

## Accepted Aggregate Calls

The frozen direct aggregate vocabulary includes:

- `count()`;
- `count(field)`;
- `count(source.field)`;
- `count_distinct(field)`;
- `count_distinct(source.field)`;
- `sum(field)`;
- `sum(source.field)`;
- `avg(field)`;
- `avg(source.field)`;
- `min(field)`;
- `min(source.field)`;
- `max(field)`;
- `max(source.field)`.

`count()` remains SQL `COUNT(*)` and returns `Int not null`.

`count(field)` and `count(source.field)` count non-null field values and return
`Int not null` for the currently accepted concrete bound field types. Unknown,
unresolved, or unsupported field references remain rejected through existing
diagnostics.

`count_distinct(field)` and `count_distinct(source.field)` count unique
non-null field values and return `Int not null` for the current direct-field
subset. The direct-field subset includes the supported concrete scalar field
types already accepted by the current implementation.

`sum(field)` and `avg(field)` accept direct bare fields and supported
single-input qualified fields under the current aggregate type rules.

`min(field)` and `max(field)` accept direct bare fields and supported
single-input qualified fields under the current aggregate type rules. The
current direct-field extrema type surface includes `Int`, `Float`, `Decimal`,
`Date`, and `Timestamp`, with nullable same-type results.

## Decimal Direct-Field Aggregate Surface

The v0.2 freeze includes the current direct-field Decimal aggregate surface:

- `sum(Decimal)`;
- `avg(Decimal)`;
- `min(Decimal)`;
- `max(Decimal)`.

Decimal aggregate results remain logical Pietto `Decimal nullable` values under
the current contract. The freeze does not add Decimal precision/scale syntax,
precision/scale carriers, Decimal literal aggregate arguments, Decimal
multiplication, Decimal division, mixed Decimal promotion, casts, schema
introspection, native database type metadata, or runtime/database validation.

## Count-Distinct Text Transform Surface

The v0.2 freeze includes the current bounded `count_distinct(...)` Text
transform subset from Phase 26.

Accepted transform arguments are chains composed only of `lower(...)` and
`trim(...)` over exactly one Text field leaf:

- `count_distinct(lower(field))`;
- `count_distinct(trim(field))`;
- `count_distinct(lower(trim(field)))`;
- `count_distinct(trim(lower(field)))`;
- repeated or nested `lower` / `trim` chains over one Text field;
- single-input qualified forms such as `count_distinct(lower(source.field))`.

This subset does not generalize `count_distinct(expression)`. Unsupported forms
remain rejected, including non-Text leaves, multiple field leaves, binary
expressions, `len(...)`, `matches(...)`, arbitrary scalar calls, nested
aggregates, multiple arguments, and composition around the aggregate projection.

## Sum and Avg Numeric Expression Arguments

The freeze includes the current bounded `sum(...)` and `avg(...)` aggregate
expression argument subset from Phases 26 and 28.

Phase 26 accepted selected `sum(...)` and `avg(...)` numeric expression
arguments over current field-only numeric expression forms under the existing
type rules.

Phase 28 accepted Int and Float numeric literal leaves inside selected
`sum(...)` and `avg(...)` numeric expression arguments when the expression still
contains at least one direct input field leaf.

The frozen accepted examples include forms such as:

- `sum(amount + tax)`;
- `avg(score * weight)`;
- `sum(amount + 1)`;
- `avg(score * 1.5)`.

The freeze does not add literal-only aggregate expressions, Decimal literal
aggregate arguments, division, modulo, casts, arbitrary scalar calls,
`count(expression)`, `min(expression)`, `max(expression)`, aggregate projection
composition, or new numeric promotion behavior.

## Grouped Aggregate And Result-Scope Surface

Grouped aggregate projections remain part of the v0.2 surface for the accepted
aggregate forms above.

Current Phase 25 `satisfying:` behavior is frozen by reference to the existing
implementation and tests:

- `where` remains row-level pre-aggregate filtering;
- `satisfying:` is GROUP BY-only result-level filtering lowered as `HAVING`;
- `satisfying:` resolves names only against selected output names;
- referenced selected outputs must be group-key projection outputs or supported
  aggregate projection outputs under the current implementation;
- renamed outputs expose the output alias, not the original input field name;
- no-GROUP `satisfying:` remains rejected;
- row-level input fields that are not selected outputs remain rejected;
- dotted references inside `satisfying:` remain rejected;
- computed scalar projection outputs inside `satisfying:` remain deferred;
- direct aggregate calls inside `satisfying:` remain rejected;
- unsupported predicate forms remain rejected.

Current Phase 27 grouped selected-output `order by` behavior is frozen by
reference to the existing implementation and tests:

- grouped `order by:` accepts bare selected output names;
- accepted selected outputs include group-key projection outputs;
- accepted selected outputs include selected direct aggregate projection
  outputs;
- accepted selected outputs include selected Phase 26 aggregate-expression
  projection outputs such as `sum(amount + tax)`, `avg(score * weight)`, and
  `count_distinct(lower(trim(status)))`;
- SQL lowering renders the underlying selected expression rather than relying
  on a SELECT alias.

This freeze does not add arbitrary grouped `ORDER BY` expressions, direct
aggregate calls inside source `order by:`, ordinal ordering, no-GROUP
projection-alias ordering, null ordering, collation controls, or broad
`ORDER BY` / `LIMIT` redesign.

## Rejected v0.2 Aggregate Expansions

The following remain outside v0.2 unless a later approved slice explicitly
unfreezes a named area:

- `count(expression)`;
- generalized `count_distinct(expression)` beyond direct fields and lower/trim
  Text transform chains over one Text field;
- `min(expression)` beyond direct fields;
- `max(expression)` beyond direct fields;
- nested aggregates;
- aggregate projection composition such as `sum(x) + 1`;
- literal-only aggregate expressions such as `sum(1)` and `avg(1)`;
- division or modulo aggregate expression arguments;
- arbitrary scalar calls inside aggregate arguments;
- window functions;
- aggregate filters;
- aggregate internal ordering;
- arbitrary grouped `ORDER BY` expressions;
- ordinal ordering;
- broad `ORDER BY` / `LIMIT` redesign;
- new aggregate functions;
- generic aggregate modifiers.

## Deferred Register Alignment

This freeze is the detailed contract behind the deferred register's aggregate
expansion entry. Aggregate expansion remains allowed before v0.2 only for bug
fixes that preserve the frozen surface. Generalized `count_distinct(expression)`
and additional aggregate expression families remain deferred.

## Explicit Non-Goals

This contract does not implement or authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- semantic implementation or semantic behavior changes;
- aggregate semantic or aggregate behavior changes;
- diagnostic behavior changes;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- CLI behavior, command, option, help, or exit-code changes;
- JSON v1 changes or JSON v2 implementation;
- fixture, golden, script, dependency, lockfile, package metadata, CI, or public
  API changes;
- public MySQL API expansion;
- runtime/database behavior, SQL execution, connector execution, schema
  introspection, project/multi-file behavior, relationship/JOIN behavior, or
  type-system behavior changes;
- DateTime, Time, timezone, Interval, Currency, or Money primitives;
- semantic annotation syntax;
- explain/audit output, LSP, playground, web UI, Arrow, or dataframe
  integration.
