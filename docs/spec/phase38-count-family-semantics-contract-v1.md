# Phase 38 Count Family Semantics Contract v1

## Status And Non-Behavior-Change Guardrail

Phase 38 Slice 2 is Count Family Semantics Contract. Slice 2 is
docs/spec/static-audit/tests-only and authorizes no behavior change.

This document consolidates the current `count` family posture and future
count-family semantics. It does not implement `count(expression)`, does not
implement `count(constant)` or `count(1)`, does not implement `count_if`, does
not add aliases such as `row_count()` or `count_row()`, and does not broaden
`count_distinct`.

Slice 2 changes no source/compiler behavior, grammar, generated ANTLR files,
parser behavior, AST behavior, semantic behavior, IR behavior, SQL lowering,
CLI behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1,
diagnostic envelope shape, SQL golden bytes, fixtures/goldens, public status
docs, scripts, workflows, package metadata, lockfiles, package version, release
operations, tags, publish/upload, signing, or attestation.

Package version remains `0.1.0`.

## Current Repo-Derived Count-Family Behavior

The current accepted and rejected count-family behavior remains:

| Form | Current behavior | Evidence |
|---|---|---|
| `count()` | Accepted as SQL `COUNT(*)`; result is `Int not null`. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `tests/test_phase23_count_field_semantics.py`, `src/pietto/sql/expressions.py`, `src/pietto/sql/mysql_expressions.py` |
| `count(field)` | Accepted for a direct field argument whose resolved type passes current count rules; result is `Int not null`; counts SQL non-null field values. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `tests/test_phase23_count_field_semantics.py`, `src/pietto/semantic/aggregates.py::is_supported_count_argument` |
| `count(source.field)` | Accepted for supported single-input qualified direct fields. | `tests/test_phase23_count_field_semantics.py` |
| `count(Any field)` | Rejected with `PIE-S2314`. | `tests/test_phase23_count_field_semantics.py`, `docs/spec/any-bytes-json-support-posture-v1.md` |
| `count(Json field)` | Accepted and SQL-emitting through the generic direct-field count path. | `docs/spec/any-bytes-json-support-posture-v1.md`, `tests/test_phase36_any_bytes_json_support_posture.py`, `tests/test_phase31_aggregate_result_matrix_hardening.py` |
| `count(Bytes field)` | Accepted and SQL-emitting through the generic direct-field count path. | `docs/spec/any-bytes-json-support-posture-v1.md`, `tests/test_phase36_any_bytes_json_support_posture.py`, `tests/test_phase31_aggregate_result_matrix_hardening.py` |
| `count(Enum field)` | Rejected with `PIE-S2314`; it no longer reaches backend `PIE-B1000`. | `docs/spec/enum-support-resolution-v1.md`, `tests/test_phase36_enum_support_resolution.py` |
| `count(UUID field)` | Accepted under the current `limited_frozen` UUID surface. | `docs/spec/uuid-support-completion-v1.md`, `tests/test_phase31_aggregate_result_matrix_hardening.py` |
| `count(expression)` | Deferred and fail-closed today; non-direct field arguments such as `count(amount + amount)`, `count(lower(status))`, and `count(amount + tax)` use `PIE-S2315`. | `docs/spec/phase37-count-expression-mvp-decision-v1.md`, `tests/test_phase23_count_field_semantics.py`, `src/pietto/semantic/aggregates.py::deferred_argument_expression_diagnostic` |
| `count(constant)` / `count(1)` | Not current behavior; `count(1)` is explicitly excluded from the Phase 37 future MVP and is currently a non-direct expression argument. | `docs/spec/phase37-count-expression-mvp-decision-v1.md`, `src/pietto/semantic/aggregates.py` |
| `count_if(predicate)` | No current aggregate or builtin function surface; future candidate only. | `docs/roadmap.md`, `src/pietto/semantic/aggregates.py`, `src/pietto/semantic/catalog.py` |
| `row_count()` / `count_row()` | No current function surface; `row_count` appears only as a projection alias for `count()`. | `tests/test_phase24_aggregate_expression_arguments_readiness.py`, `src/pietto/semantic/catalog.py` |
| `count_distinct(field)` | Accepted for current direct-field subset `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`; result is `Int not null`. | `docs/roadmap.md`, `src/pietto/semantic/aggregates.py`, `tests/test_phase31_aggregate_result_matrix_hardening.py` |
| `count_distinct(expression)` | Accepted only for bounded lower/trim Text chains over exactly one `Text` field leaf; broad `count_distinct(expression)` remains deferred and fail-closed. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `tests/test_phase37_current_aggregate_matrix.py`, `tests/test_phase37_grouped_aggregate_interaction_hardening.py` |
| `count(distinct field)` | Not Pietto source syntax; parser-rejected with `PIE-P1000`. | `docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md`, `tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py`, `tests/test_phase37_grouped_aggregate_interaction_hardening.py` |

The current semantic helper rule is exact: `count(field)` accepts only when the
resolved type kind is not `ENUM` or `UNKNOWN` and the field is not builtin
`Any`.

## `count()` Semantics

`count()` is the preferred Pietto spelling for all-row count.

Contract:

- counts input rows, not values of a field;
- lowers to SQL `COUNT(*)`;
- returns `Int not null`;
- returns `0` for an empty input;
- does not inspect any field;
- remains distinct from `count(field)`;
- remains an aggregate name, not a scalar builtin.

## `count(field)` Semantics

`count(field)` and `count(source.field)` count SQL non-null field values under
the current direct-field aggregate projection model.

Contract:

- counts non-`NULL` values of the selected field expression;
- returns `Int not null`;
- differs from `count()` because it excludes rows where the field value is SQL
  `NULL`;
- remains limited to direct field and supported single-input qualified direct
  field arguments;
- keeps current diagnostics for unsupported types, unknown fields, expression
  arguments, nested aggregates, aggregate composition, invalid contexts, and
  missing aliases.

## SQL `NULL` Versus JSON Literal `null`

For `count(Json field)`, the relevant nullness is SQL nullness of the field.

Slice 2 documents this distinction without adding Json semantics:

- SQL `NULL` field values are not counted by `count(Json field)`;
- a backend JSON value that encodes JSON literal `null` is not automatically the
  same thing as a SQL `NULL` field value;
- Pietto currently has no JSON literal syntax, JSON path extraction, structural
  Json typing, JSON operators, native DB JSON metadata, storage/DDL behavior,
  schema introspection, runtime JSON processing, or dialect-specific JSON
  semantics;
- future Json countability changes must define SQL-null versus JSON-null policy
  explicitly before behavior changes.

## `count(expression)` Future Semantics

`count(expression)` remains a future candidate only. Slice 2 does not implement
it.

If a later slice separately approves `count(expression)`, its intended semantic
meaning should be SQL-style non-null expression result counting:

- the expression is evaluated in the already selected relation scope;
- Rows whose expression result is SQL `NULL` are not counted;
- Rows whose expression result is non-`NULL` are counted;
- a Bool expression counts both `TRUE` and `FALSE` when non-`NULL`;
- `count(expression)` is not the same as `count_if(predicate)`;
- result is `Int not null`;
- unsupported shapes must fail closed before SQL lowering.

Future implementation prerequisites include exact expression shape policy,
field-leaf policy, known type policy, nullability policy, diagnostics, IR/SQL
lowering, PostgreSQL/private MySQL portability, fixture/golden policy, and
public output compatibility review.

## `count(constant)` / `count(1)` Migration Compatibility Posture

`count(constant)` and `count(1)` are not current behavior. They remain future SQL
migration compatibility candidates only.

Slice 2 recommends:

- idiomatic new Pietto code should use `count()` for all-row count;
- compatibility-preserving Pietto may later accept `count(1)` or other constant
  forms only after a separate contract;
- non-idiomatic but SQL-valid forms should not become accepted accidentally;
- future compatibility lowering should preserve the source's SQL form when that
  matters for migration review;
- default behavior must not silently rewrite `count(1)` to `count()` unless a
  later slice explicitly approves that compatibility policy;
- future warning, lint, or strict-mode treatment must be separate from semantic
  acceptance.

## `count(NULL)` Posture

Slice 2 does not introduce a `NULL` literal just to support `count(NULL)`.

If a future Pietto NULL literal is approved, aggregate semantics for
`count(NULL)` must be explicit. That later contract should decide whether the
form is accepted, whether it preserves SQL `COUNT(NULL)` behavior, whether it is
warned as non-idiomatic, and how diagnostics interact with literal-only
aggregate arguments.

## `count_if(predicate)` Future Semantics

`count_if(predicate)` remains a future candidate only. Slice 2 does not add a
new aggregate function.

If a later slice separately approves `count_if(predicate)`, the contract should
be:

- predicate argument must be `Bool` or nullable `Bool`;
- `TRUE` counts;
- `FALSE`, SQL `NULL`, and SQL three-valued `UNKNOWN` do not count;
- result is `Int not null`;
- no matching rows returns `0`;
- unsupported shapes fail closed before SQL lowering;
- PostgreSQL/private MySQL lowering must be portable without requiring backend
  execution, schema introspection, or native metadata.

`count_if(predicate)` is different from `count(predicate)`: `count(predicate)`
would count non-null `TRUE` and non-null `FALSE` predicate values, while
`count_if(predicate)` would count only `TRUE`.

## `row_count` / `count_row` Non-Adoption

Slice 2 does not adopt `row_count()` or `count_row()`.

Aliases should not be introduced if they only duplicate `count()`. Adding an
alias increases function vocabulary, documentation, diagnostics, SQL rendering,
and compatibility surface without adding new semantics.

The existing `row_count` text in the repository is a projection alias such as
`row_count = count()`, not a function name.

## Distinction From `count_distinct`

`count_distinct(...)` remains a separate aggregate spelling.

Current accepted forms remain:

- `count_distinct(field)`;
- `count_distinct(source.field)`;
- `count_distinct(lower/trim Text chain)` over exactly one `Text` field leaf.

Slice 2 does not broaden `count_distinct(expression)` and does not introduce
generic SQL-style `count(distinct field)` syntax.

Future count-family work must keep the capability distinction clear:

- `count` depends on SQL lowerability and SQL nullness;
- `count_distinct` additionally depends on equality, distinct compatibility,
  collation, normalization, serialization, deterministic transform, and dialect
  portability.

## Count-Family Type / Capability Boundary

Broad countability is not numeric capability, arithmetic capability, orderable
capability, or distinct compatibility.

For count-family design:

- `count(expression)` should depend mainly on SQL lowerability and nullness of
  the expression result;
- `sum` / `avg` require numeric and arithmetic capability;
- `min` / `max` require orderable capability;
- `count_distinct` requires equality/distinct compatibility plus collation,
  normalization, serialization, and dialect-portability policy.

This distinction is especially important for Any, Json, Bytes, Enum, and UUID
because their current direct `count(field)` posture does not imply arithmetic,
ordering, or distinct support.

## Any / Json / Bytes / Enum / UUID Count Posture

Slice 2 preserves current behavior:

- `Any`: current `count(Any field)` rejection remains `PIE-S2314`; future
  countability could be considered only after explicit lowerable-count policy,
  not as dynamic typing or permissive SQL fallback.
- `Json`: current direct `count(Json field)` remains accepted; future design
  must keep SQL `NULL` versus JSON literal `null` explicit.
- `Bytes`: current direct `count(Bytes field)` remains accepted; no binary
  semantics, encoding policy, comparison, distinct, ordering, native metadata,
  storage/DDL, schema introspection, or runtime behavior is authorized.
- Enum: current `count(Enum field)` remains semantic `PIE-S2314`; future SQL
  non-null count is only a candidate after Enum scalar and SQL portability
  policy.
- `UUID`: current direct `count(UUID field)` remains accepted under
  `limited_frozen`; no UUID ordering, `min/max`, native behavior, literal,
  cast, storage, or dialect-specific UUID treatment is authorized.

## Diagnostics And Current Behavior Preservation

Slice 2 changes no diagnostics and adds no diagnostic code.

Current diagnostic families remain:

- `PIE-S2308` for aggregate calls in invalid contexts such as `where`;
- `PIE-S2309` for wrong aggregate arity;
- `PIE-S2310` for aggregate projection composition;
- `PIE-S2311` for nested aggregates;
- `PIE-S2313` for aggregate projections requiring explicit aliases;
- `PIE-S2314` for unsupported known aggregate argument types;
- `PIE-S2315` for deferred aggregate expression argument shapes;
- existing unresolved-field diagnostics for unknown field leaves;
- parser diagnostics such as `PIE-P1000` for SQL-like modifier syntax that is
  not Pietto source syntax.

## Future Implementation Prerequisites

Any later behavior implementation must use a separate Gate 1 and Gate 2 and
must name implementation files, validation commands, SQL portability proof,
fixture/golden policy, public output compatibility, diagnostics policy, and
release non-authorization.

Future count-family implementation work must prove no accidental expansion of:

- source syntax;
- grammar or generated parser files;
- parser or AST behavior;
- semantic, IR, or SQL behavior beyond the approved row;
- CLI text output;
- CLI JSON v1;
- Project JSON v2;
- Semantic Metadata Artifact v1;
- fixtures or golden SQL bytes;
- scripts or workflows;
- package metadata, lockfiles, package version, tags, release, publish/upload,
  signing, or attestation.

## Public Surface And Release Non-Authorization

Slice 2 keeps public surfaces unchanged:

- CLI text output unchanged;
- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- generated parser inventory unchanged;
- package version remains `0.1.0`;
- no package/workflow/release metadata change;
- no tag/release/publish/upload/signing/attestation.
