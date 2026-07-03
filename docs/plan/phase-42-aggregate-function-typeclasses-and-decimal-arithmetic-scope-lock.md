# Phase 42 Aggregate Function Typeclasses And Decimal Arithmetic Scope Lock

## Status And Trusted Handoff

Phase 42 Slice 1 is Aggregate Function Typeclasses And Decimal Arithmetic
Scope Lock. Slice 1 is docs/spec/deferred-register/static-audit work only and
implements no behavior change.

Trusted Phase 41 handoff:

- baseline HEAD: `b6e7651f9bec69caa3d953602dfdb74cc292950e`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 41 decimal precision-scale MVP audit`;
- latest completed phase: Phase 41 Decimal Precision-Scale MVP;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 1.

Slice 1 updates only the approved Phase 42 plan, the Phase 42 scope-lock spec,
the deferred-feature register, and one focused static-audit test. It does not
update `README.md`, `AGENTS.md`, `docs/spec/pietto-v0.9.md`, production
source, generated artifacts, fixtures, goldens, examples, scripts, workflows,
package metadata, lockfiles, release files, or CI configuration.

## Candidate Decision

The selected Phase 42 Slice 1 candidate is:

**Scope-lock and audit for aggregate typeclasses, Decimal arithmetic, and
literal-only aggregate boundaries**

Phase 42 Slice 1 authorizes no source/compiler behavior change. Production
semantic work, if approved later, begins in Slice 2 or later.

Slice 1 records these decisions:

- keep `1.23` as current `Float` literal behavior;
- do not infer exact Decimal from Python float-like source values;
- keep exact Decimal literals future-only until explicit syntax and AST raw
  token preservation are approved;
- keep `Float` and `Decimal` mixed arithmetic fail-closed unless an explicit
  conversion design is later approved;
- treat Slice 3 `Int` and `Decimal` `+` / `-` arithmetic as logical Decimal
  only, without precision propagation;
- treat Decimal precision/scale expression fusion as future work requiring
  computed expression-level Decimal facts;
- keep Decimal division out of Phase 42 Slice 1 behavior;
- keep literal-only aggregate arguments such as `sum(1 + 2)` future-only until
  semantic, IR, and SQL renderer guard changes are approved together;
- preserve SQL aggregate constants as `SUM(constant)` if implemented later;
- keep Decimal aggregate results logical `Decimal NULLABLE` unless a future
  aggregate/type propagation phase proves a safe precision result contract;
- keep dialect precision caveats docs/deferred-only because no lint framework
  exists today.

Slice 1 explicitly rejects grammar/generated changes, public output schema
changes, SQL output changes, warning/lint infrastructure, new diagnostic codes,
Decimal literal syntax, cast syntax, runtime/database behavior, project or
multi-file execution behavior, and relationship/JOIN behavior.

## Current Aggregate Validation Map

Current aggregate recognition is implemented in
`src/pietto/semantic/aggregates.py`.

`AGGREGATE_NAMES` contains `count`, `sum`, and `avg` for the original
IR-facing aggregate vocabulary. `SEMANTIC_AGGREGATE_NAMES` adds
`count_distinct`, `min`, and `max` for current semantic aggregate validation.

The current validation surface is:

| Aggregate form | Current behavior |
|---|---|
| `count()` | Accepted; result is `Int NON_NULL`; SQL is `COUNT(*)`. |
| `count(field)` / `count(source.field)` | Accepted for concrete non-`Any` fields except Enum and Unknown. Bytes, Json, and UUID remain current accepted direct count fields. |
| `count(expression)` | Accepted only for approved field-bearing shapes with at least one direct input field leaf. Literal-only and predicate-only forms remain fail-closed. |
| `sum(field)` / `avg(field)` | Accepted for direct or supported qualified `Int`, `Float`, and `Decimal` fields. |
| `sum(expression)` / `avg(expression)` | Accepted only for the current field-bearing numeric expression subset. Int/Float literal leaves require at least one field leaf. Decimal remains limited to current field-only `+` and `-` expression behavior. |
| `count_distinct(field)` | Accepted for `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID` direct or qualified fields. |
| `count_distinct(lower/trim Text chain)` | Accepted for current lower/trim chains over one Text field leaf. |
| `min(field)` / `max(field)` | Accepted for direct or supported qualified `Int`, `Float`, `Decimal`, `Date`, and `Timestamp` fields. |

Current fail-closed aggregate diagnostics remain unchanged:

- `PIE-S2308` for aggregate calls outside direct aliased select projections;
- `PIE-S2309` for wrong aggregate arity;
- `PIE-S2310` for aggregate projection composition;
- `PIE-S2311` for nested aggregates;
- `PIE-S2312` for mixed no-GROUP aggregate and row projections;
- `PIE-S2313` for missing aggregate projection aliases;
- `PIE-S2314` for unsupported direct field argument types;
- `PIE-S2315` for deferred aggregate argument expression shapes.

Projection-shape validation remains in
`src/pietto/semantic/relation_schemas.py::_aggregate_projection_diagnostics`
and `src/pietto/semantic/group_by.py::_aggregate_output_field`. Expression
typing remains in `src/pietto/semantic/expressions.py::_call_argument_types`
and `_aggregate_value_type`. IR lowering remains guarded by
`src/pietto/ir/lowering.py::_is_valid_aggregate_projection`.

## Current Numeric Expression Typing Map

Current literal typing is in `src/pietto/semantic/expressions.py`:

- `bool` literals type as `Bool`;
- string literals type as `Text`;
- integer literals type as `Int`;
- dotted numeric literals type as Python `float` and type as `Float`.

Current arithmetic typing is:

- `Int`/`Float` binary `+`, `-`, and `*` are accepted; any Float operand
  promotes the result to `Float`, otherwise the result is `Int`;
- `Decimal + Decimal` and `Decimal - Decimal` are accepted and return logical
  `Decimal UNKNOWN`;
- `Decimal + Int`, `Int + Decimal`, `Decimal - Int`, and `Int - Decimal`
  are accepted and return logical `Decimal UNKNOWN`;
- Decimal multiplication, mixed `Decimal`/`Float`, and mixed `Float`/`Decimal`
  arithmetic fail closed with `PIE-S2105` in ordinary scalar contexts;
- `/` currently returns Unknown without a diagnostic;
- `%` is accepted only for `Int`/`Int`, otherwise `PIE-S2105`;
- unary `+` and `-` currently treat only `Int` and `Float` as numeric.

Aggregate contexts may suppress lower-level scalar diagnostics for unsupported
aggregate argument shapes and preserve aggregate-level `PIE-S2315`.

## Decimal Precision-Scale Carrier Findings

Phase 41 implemented a private type-expression-level Decimal carrier:

- `src/pietto/semantic/model.py::DecimalPrecisionScale`;
- `SemanticModel.decimal_precision_scales`;
- `SemanticModel.decimal_precision_scale_for(type_expr)`;
- `src/pietto/semantic/analyzer.py::_decimal_precision_scale_fact`;
- safe alias-chain propagation through
  `_propagate_decimal_precision_scale_aliases`.

The carrier remains private and non-public:

- `DecimalPrecisionScale` is not exported from `pietto.semantic`;
- `ResolvedType`, `ValueType`, and `TypeRefIR` have no precision/scale fields;
- CLI JSON v1, Project JSON v2, explain text/JSON, Semantic Metadata Artifact
  v1, SQL output, and IR output expose no precision/scale fields.

Facts exist only at type-expression sites. There is no expression-level
precision/scale map keyed by `Expression`, no `ValueType` precision/scale, and
no IR precision/scale in Slice 1. Phase 42 Slice 5 supersedes that Slice 1
posture with a private expression-level fact carrier scaffold for direct
`Decimal(p,s)` field references only. Decimal precision fusion still requires
a later design for computed expression facts, fusion helpers, overflow
handling, and unknown-fact fallback.

Safe type-alias aggregate canonicalization remains future work. Existing
alias-chain facts are safe metadata, but current aggregate argument validation
uses declared expression `ResolvedType` facts and therefore keeps
`sum(money)` fail-closed when `money` has alias type `Money = Decimal(12, 2)`.

## Literal And Constant Findings

The current grammar has only `NUMBER : DIGIT+ ('.' DIGIT+)?`. There is no
Decimal literal token or exact decimal literal syntax.

`LiteralExpr` stores only a parsed Python value, not raw token text. The AST
builder converts dotted numeric source text with `float(text)`, so exact source
spellings such as trailing zeros are not recoverable from the AST.

`AstBuilder._fold_binary` folds parse-tree precedence into left-associative
`BinaryExpr` nodes. It does not evaluate constants. No scalar constant folding
or unsafe aggregate constant rewrite exists today.

Literal-only aggregate arguments are parseable and representable as expression
trees, but current semantic validation rejects them before aggregate IR:
`sum(1)`, `sum(1 + 2)`, `sum(1.23)`, `avg(1.23)`, `count(1)`, and
`count_distinct(1)` remain fail-closed.

General IR and SQL literal rendering can render `LiteralIR`, `UnaryIR`, and
`BinaryIR`. However, PostgreSQL and private MySQL aggregate renderers also
guard numeric aggregate argument shapes and currently reject literal-only
numeric aggregates. Later literal-only aggregate support must update semantic,
IR, PostgreSQL, and private MySQL guardrails together and must preserve
`SUM(constant)` instead of rewriting to `constant * COUNT(*)`.

## Alias Aggregate Findings

Projection aliases remain output names only. They do not become same-select
expression leaves or aggregate argument leaves.

Relation-local `let:` names are deliberately invisible to aggregate arguments
today. `type_relation_expressions` passes no let scope into direct aggregate
projection argument typing, and IR lowering passes empty `let_expansions` while
lowering aggregate arguments.

Safe future alias canonicalization is limited to declared type aliases on
direct input fields or supported qualified direct input fields. It must not
make projection aliases, let names, unresolved names, same-select aliases,
hidden CTEs, hidden subqueries, relation layers, or relationship/JOIN traversal
visible to aggregate argument validation.

## Warning And Lint Findings

The current diagnostic model supports `Severity.ERROR` and `Severity.WARNING`.
Warning-only compiler results can be successful, and checked-mode warnings
exist for current semantic posture such as implicit nullability or untyped
sources.

There is no standalone lint framework, warning policy registry, dialect caveat
channel, suppression mechanism, or non-fatal portability advisory layer.
Dialect precision caveats for Decimal therefore remain docs/deferred-only in
Slice 1. Slice 1 adds no warning/lint infrastructure.

## Phase 42 Slice Sequence

| Slice | Name | Slice posture |
|---:|---|---|
| 1 | Aggregate Function Typeclasses And Decimal Arithmetic Scope Lock | docs/spec/deferred-register/static-audit only; no behavior change |
| 2 | Aggregate Typeclass Vocabulary Or Tests-First Matrix | future behavior-preserving semantic capability vocabulary or tests-first lock, if approved |
| 3 | Exact Decimal/Int Arithmetic Candidate | future semantic behavior slice, if approved |
| 4 | Decimal Precision Fusion Readiness Lock | tests-first readiness lock; no production behavior |
| 5 | Private Decimal Expression Precision Fact Carrier Scaffold | private direct-field expression fact carrier only; no fusion or public output |
| 6 | Literal-only Aggregate Argument Candidate | future semantic/IR/SQL renderer guard slice, if approved |
| 7 | Completion Audit And Status Lock | future completion-audit/status-lock slice |

Sequence may change only through a later Gate 1. Slice 2 should not start
literal-only `SUM(constant)` unless PostgreSQL and private MySQL aggregate
renderer guard changes are explicitly approved in the same slice.

## Slice 1 Gate 2 Allowlist

Phase 42 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-42-aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock.md`;
- `docs/spec/aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock-v1.md`;
- `docs/spec/v02-deferred-feature-register-v1.md`;
- `tests/test_phase42_aggregate_typeclasses_decimal_scope_lock.py`.

No other file is approved. If a production source file, grammar/generated file,
fixture, golden, example, package file, workflow, script, lockfile, release
file, public JSON/metadata surface, SQL renderer, IR model, CLI schema,
`README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md` appears necessary,
stop and request a Repair Gate 1.

## Slice 1 Validation Focus

Slice 1 validation should prove:

- the four-file allowlist is the complete changed surface;
- current aggregate validation, numeric expression typing, Decimal carrier,
  literal/constant, alias aggregate, and warning/lint findings are recorded;
- future work is deferred without behavior claims;
- no production semantic, grammar/generated, IR, SQL, CLI/JSON, metadata,
  fixture/golden/example, package, workflow, release, runtime/database,
  project/multi-file, or relationship/JOIN behavior changed;
- package version remains `0.1.0`.

## Stop Conditions

Stop and return to Repair Gate 1 if:

- branch, HEAD, package version, or clean baseline does not match the trusted
  handoff;
- any needed change falls outside the Slice 1 allowlist;
- production source, grammar/generated, SQL renderer, IR model, public
  JSON/metadata, fixture/golden/example, package/workflow/release, or CLI
  schema changes appear necessary;
- new diagnostic codes, warning/lint infrastructure, Decimal literal syntax,
  cast syntax, or raw-token AST changes appear necessary;
- meaningful static-audit coverage cannot be written without production
  behavior changes;
- targeted validation fails for reasons outside the allowlisted files;
- broader validation or hash-lock refresh appears necessary.
