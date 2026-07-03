# Aggregate Function Typeclasses And Decimal Arithmetic Scope Lock v1

## Status

Phase 42 Slice 1 is a scope-lock and static-audit slice only. It records
current aggregate validation, numeric expression typing, Decimal
precision-scale carrier posture, literal/constant posture, alias aggregate
boundaries, warning/lint posture, and the future implementation sequence.

This document does not implement aggregate typeclasses, Decimal arithmetic,
Decimal literals, casts, aggregate precision propagation, literal-only
aggregate arguments, warning/lint infrastructure, SQL output behavior, IR
shape changes, public JSON or metadata schema changes, project/multi-file
behavior, relationship/JOIN behavior, runtime/database behavior, release
operations, package metadata changes, or workflow changes.

Package version remains `0.1.0`.

## Current Aggregate Typeclass Inventory

The current codebase does not have a first-class aggregate typeclass registry.
Aggregate capability decisions are encoded as helper predicates in
`src/pietto/semantic/aggregates.py`, relation schema validation, grouped
validation, expression typing, IR lowering guards, and SQL renderer guards.

Current logical capability rows are:

| Capability | Current accepted aggregate use | Current deferred boundary |
|---|---|---|
| countable | `count()` and `count(field)` over concrete non-`Any` non-Enum known fields; current direct `Bytes`, `Json`, and `UUID` count fields remain accepted. | literal-only `count(1)`, predicate-only count expressions, unresolved aliases, and broad unsupported expression shapes. |
| distinct-compatible | `count_distinct(field)` for `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`; lower/trim Text chains over one Text field leaf. | broad `count_distinct(expression)`, literal-only forms, `Bytes`, `Json`, `Any`, Enum, collation/normalization semantics, and Decimal precision widening. |
| numeric aggregate | `sum`/`avg` over direct `Int`, `Float`, `Decimal` fields and current field-bearing expression subset. | literal-only `sum`/`avg`, Decimal literals, Decimal `*` and `/`, mixed Decimal promotion, arbitrary calls, division, modulo, and precision propagation. |
| extrema/orderable aggregate | `min`/`max` over direct `Int`, `Float`, `Decimal`, `Date`, and `Timestamp` fields. | `min/max(expression)`, Text/Bool/UUID/Enum/Any/Bytes/Json extrema, collation/order semantics expansion, and temporal arithmetic. |

Future aggregate typeclass work must preserve existing diagnostics and direct
aliased aggregate projection boundaries unless a later Gate 1 explicitly
approves a behavior change.

## Decimal Arithmetic Scope

Current numeric expression typing is intentionally narrow:

- `Int` and `Float` support binary `+`, `-`, and `*`;
- mixed `Int`/`Float` arithmetic promotes to `Float`;
- `Decimal + Decimal` and `Decimal - Decimal` return logical `Decimal`;
- Decimal multiplication remains unsupported;
- Decimal division remains deferred;
- mixed `Decimal`/`Int` and `Decimal`/`Float` arithmetic remains fail-closed;
- dotted numeric literals such as `1.23` remain `Float`.

Phase 42 future implementation may consider exact `Int`/`Decimal` arithmetic,
but Slice 1 does not implement it. `Float`/`Decimal` mixing must remain
fail-closed unless a future explicit conversion design is approved.

Future Decimal precision/scale fusion is scoped as:

- addition/subtraction candidate formula:
  `scale = max(s1, s2)`,
  `integer_digits = max(p1 - s1, p2 - s2) + 1`,
  `precision = integer_digits + scale`;
- multiplication candidate formula:
  `scale = s1 + s2`,
  `precision = p1 + p2 + 1`;
- if inferred precision is `<= 38`, a future implementation may preserve
  `Decimal(p,s)`;
- if inferred precision is `> 38`, future default behavior should degrade to
  logical `Decimal` rather than rounding or truncating; a future strict mode
  may fail closed if separately approved.

Those formulas are planning constraints only. They require expression-level
Decimal precision facts that do not exist today.

## Decimal Carrier Boundary

Phase 41 added a private type-expression-level carrier only:

- `DecimalPrecisionScale`;
- `SemanticModel.decimal_precision_scales`;
- `SemanticModel.decimal_precision_scale_for(type_expr)`;
- safe alias-chain internal fact propagation.

Slice 1 locks the current non-public boundary:

- no `DecimalPrecisionScale` export from `pietto.semantic`;
- no precision/scale fields on `ResolvedType`, `ValueType`, or `TypeRefIR`;
- no precision/scale fields in CLI JSON v1, Project JSON v2, explain output,
  Semantic Metadata Artifact v1, SQL output, or IR output;
- no expression-level Decimal precision facts.

Future Decimal fusion requires an explicit expression-level fact carrier and a
field/type-expression fact lookup design. It must not reuse public output
schemas as private propagation storage.

## Literal And Constant Boundary

Current literal facts:

- the grammar has only `NUMBER : DIGIT+ ('.' DIGIT+)?`;
- `LiteralExpr` stores parsed Python values, not raw token text;
- dotted numeric literals are converted through Python `float`;
- exact Decimal source text cannot be reconstructed from AST values today;
- no constant folding is implemented for scalar expressions;
- no aggregate constant rewrite exists.

Therefore exact Decimal literal syntax requires future grammar/AST/parser
approval or a future raw-token literal representation. Slice 1 does not
reserve syntax.

Literal-only aggregate arguments remain future work. If later approved,
`sum(1 + 2)` and `sum(1.23)` must lower and render as `SUM(constant)` or
`SUM(expression)` and must never be rewritten to `constant * COUNT(*)`, because
SQL `SUM` over empty input returns `NULL` while `COUNT(*)` returns `0`.

## Alias And Let Boundary

Projection aliases remain output names only. They do not become expression
leaves inside the same select list and do not become aggregate argument leaves.

Relation-local `let:` bindings remain row-level inline bindings only. Aggregate
arguments do not see let names in the current compiler.

Future safe canonicalization may only consider declared type aliases on direct
input fields or supported qualified direct input fields. It must not authorize
projection alias aggregation, let-name aggregate arguments, hidden CTEs,
hidden subqueries, relation-layer rewrites, relationship traversal, or
fanout-aware aggregate behavior.

## Warning And Dialect Caveat Boundary

The compiler has structured `error` and `warning` diagnostic severities, but no
standalone lint framework or dialect-caveat advisory system.

Dialect precision caveats for Decimal remain docs/deferred-only in Slice 1.
Adding warning/lint infrastructure, warning suppression, advisory categories,
or dialect precision linting requires a later Gate 1.

## Forbidden Surfaces

Slice 1 forbids:

- production source changes;
- grammar or generated ANTLR changes;
- parser or AST behavior changes;
- semantic behavior changes;
- IR model or lowering behavior changes;
- PostgreSQL or private MySQL SQL renderer behavior changes;
- SQL fixture/golden/example changes;
- CLI JSON v1, Project JSON v2, explain, or Semantic Metadata Artifact v1
  schema/output changes;
- package metadata, package version, lockfile, script, workflow, CI, release,
  tag, publish, upload, signing, or attestation changes;
- new diagnostic codes;
- warning/lint infrastructure;
- Decimal literal syntax;
- cast syntax;
- runtime/database execution;
- schema introspection or db pull;
- policy/security DSL;
- UI/LSP;
- project/multi-file execution;
- relationship/JOIN-driven query behavior.

## Acceptance Criteria For Slice 1

Slice 1 is complete when the approved plan/spec/register/test files record:

- the current aggregate validation map;
- the current numeric expression typing map;
- the Decimal precision-scale carrier boundary;
- literal and constant findings;
- alias aggregate findings;
- warning/lint findings;
- forbidden surfaces;
- next-slice sequencing;
- stop conditions;
- deferred-register classification for Phase 42-related future work.

No compiler behavior is implemented by this slice.
