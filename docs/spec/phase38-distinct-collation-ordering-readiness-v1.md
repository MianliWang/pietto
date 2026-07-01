# Phase 38 Distinct Collation Ordering Readiness v1

## Status And Non-Behavior-Change Guardrail

Phase 38 Slice 5 is Distinct / Collation / Ordering Readiness. Slice 5 is
docs/spec/static-audit/tests-only and authorizes no behavior change.

This document consolidates current distinct-compatible, collation-dependent,
and ordering readiness boundaries. It records repo-derived behavior and future
prerequisites only. It does not add or change source/compiler behavior,
grammar, generated ANTLR files, parser behavior, AST behavior, semantic
behavior, IR behavior, SQL lowering, CLI behavior, JSON v1, Project JSON v2,
Semantic Metadata Artifact v1, diagnostic envelope shape, SQL golden bytes,
fixtures/goldens, public status docs, scripts, workflows, package metadata,
lockfiles, package version, release operations, tags, publish/upload, signing,
or attestation.

Package version remains `0.1.0`.

## Current Repo-Derived Distinct-Compatible Posture

Current distinct-compatible behavior is narrow:

| Surface | Current behavior | Evidence |
|---|---|---|
| `count_distinct(field)` | Accepted for direct fields whose resolved type is `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, or `UUID`; result is `Int not null`. | `docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md`, `src/pietto/semantic/aggregates.py::is_supported_count_distinct_argument`, `tests/test_phase31_aggregate_result_matrix_hardening.py` |
| `count_distinct(source.field)` | Accepted for supported single-input qualified direct fields in the same direct-field subset; result is `Int not null`. | `docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md`, `tests/test_phase37_count_distinct_expression_widening_boundary.py` |
| `count_distinct(lower/trim Text chain)` | Accepted for chains made only of `lower(...)` and `trim(...)` over exactly one `Text` field leaf, including supported qualified field leaves; result is `Int not null`. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md`, `tests/test_phase37_count_distinct_expression_widening_boundary.py` |
| broad `count_distinct(expression)` | Deferred and fail-closed outside the direct-field and lower/trim Text-chain subset. | `docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md`, `tests/test_phase37_current_aggregate_matrix.py` |
| `count_distinct(Json/Bytes/Any/Enum)` | Rejected with `PIE-S2314`; `Unknown` has no stable capability. | `docs/spec/any-bytes-json-support-posture-v1.md`, `docs/spec/enum-support-resolution-v1.md`, `tests/test_phase31_aggregate_result_matrix_hardening.py` |
| SQL-style `count(distinct field)` | Not Pietto source syntax; parser-rejected with `PIE-P1000`. | `docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md`, `tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py` |

The source helper `is_supported_count_distinct_argument` currently names the
direct-field subset `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`,
`Timestamp`, and `UUID`. PostgreSQL and private MySQL SQL emitters preserve the
same direct subset and the same lower/trim Text-chain guard.

## Current Repo-Derived Ordering And Min-Max Posture

Current ordering/min-max behavior is also narrow:

| Surface | Current behavior | Evidence |
|---|---|---|
| `min(field)` / `max(field)` | Accepted for direct fields whose resolved type is `Int`, `Float`, `Decimal`, `Date`, or `Timestamp`; result is nullable same type. | `docs/spec/phase37-min-max-expression-boundary-v1.md`, `src/pietto/semantic/aggregates.py::is_supported_extrema_argument`, `tests/test_phase31_aggregate_result_matrix_hardening.py` |
| `min(source.field)` / `max(source.field)` | Accepted for supported single-input qualified direct fields in the same direct-field subset; result is nullable same type. | `docs/spec/phase37-min-max-expression-boundary-v1.md`, `tests/test_phase37_min_max_expression_boundary.py` |
| `min/max(Text|Bool|UUID|Enum|Json|Bytes|Any|Unknown)` | Rejected/deferred with unsupported-type posture, generally `PIE-S2314`. | `docs/spec/phase37-min-max-expression-boundary-v1.md`, `docs/spec/any-bytes-json-support-posture-v1.md`, `docs/spec/enum-support-resolution-v1.md`, `tests/test_phase31_aggregate_result_matrix_hardening.py` |
| `min/max(expression)` | Future only; broad expression forms remain deferred and fail closed with `PIE-S2315` for unsupported expression shapes. | `docs/spec/phase37-min-max-expression-boundary-v1.md`, `tests/test_phase37_min_max_expression_boundary.py` |

Generic comparison/order paths exist for some shared flows, but they are not
stable type-specific ordering contracts. This matters most for `UUID`, Enum,
`Any`, `Bytes`, `Json`, and aliases over those targets.

## Readiness Vocabulary

Slice 5 defines these terms as planning vocabulary, not behavior:

- `distinct-compatible`: eligible for the current or future
  `count_distinct` equality/distinct contract.
- `equality-comparable`: has an explicit equality policy, not merely generic
  known-child comparison typing.
- `collation-dependent`: needs Text or Enum collation/order policy before
  broad distinct or ordering behavior can be stable.
- `serialization-dependent`: needs stable serialized equality before opaque or
  structured values can be distinct-compatible.
- `orderable`: eligible for a stable `min/max` or ordering contract.
- `dialect-lowerable`: portable through the current PostgreSQL and private
  MySQL SQL emitters for an already accepted surface.
- `metadata-backed`: depends on explicit type metadata, such as Enum order or
  UUID ordering policy.
- `deterministic transform`: a transform whose equality and SQL lowering are
  stable across supported dialects.
- `normalization policy`: explicit Unicode, case, locale, or structural
  normalization rules for equality/distinct.
- `stable ordering policy`: explicit semantic ordering independent of
  accidental storage or backend-specific behavior.

`count_distinct` readiness requires equality/distinct semantics plus
collation, normalization, serialization, deterministic transform, and dialect
policy where applicable. `min/max` readiness requires stable ordering semantics
plus result type and nullability policy. Generic comparison/order paths are not
enough.

## `count_distinct` Readiness Matrix

| Type | Current behavior | Future prerequisites and caveats |
|---|---|---|
| `Bool` | Current direct `count_distinct(Bool)` accepted; result `Int not null`. | Keep equality semantics explicit before broad expression support. |
| `Int` | Current direct `count_distinct(Int)` accepted; result `Int not null`. | Keep numeric equality and dialect portability explicit before broad expressions. |
| `Float` | Current direct `count_distinct(Float)` accepted; result `Int not null`. | Future broader treatment should define NaN and signed-zero policy. |
| `Decimal` | Current direct `count_distinct(Decimal)` accepted; result `Int not null`. | Decimal precision-scale carrier and equality/normalization policy remain deferred. |
| `Text` | Current direct `count_distinct(Text)` and lower/trim Text chains accepted. | Text collation, Unicode normalization, locale-sensitive folding, and backend equality policy remain deferred. |
| `Date` | Current direct `count_distinct(Date)` accepted; result `Int not null`. | Future expression support needs temporal literal/function/cast and dialect policy. |
| `Timestamp` | Current direct `count_distinct(Timestamp)` accepted; result `Int not null`. | Future expression support needs timezone, precision, native metadata, and dialect policy. |
| `UUID` | Current direct `count_distinct(UUID)` accepted under `limited_frozen`. | UUID metadata, storage, equality portability, literal/cast, and native behavior remain deferred. |
| Enum | Current `count_distinct(Enum)` rejected with `PIE-S2314`. | Requires Enum scalar behavior, SQL portability, equality policy, and order metadata policy first. |
| `Json` | Current `count_distinct(Json)` rejected with `PIE-S2314`. | Requires Json serialization/equality, SQL `NULL` versus JSON literal `null`, structural/path, and dialect policy first. |
| `Bytes` | Current `count_distinct(Bytes)` rejected with `PIE-S2314`. | Requires Bytes serialization, encoding, binary equality, native metadata, and dialect policy first. |
| `Any` | Current `count_distinct(Any)` rejected with `PIE-S2314`. | Requires explicit refinement or operator-constrained policy; not dynamic typing. |
| `Unknown` | No stable distinct capability. | Must resolve to a supported known type before any distinct-compatible decision. |

## `min/max` And Ordering Readiness Matrix

| Type | Current behavior | Future prerequisites and caveats |
|---|---|---|
| `Int` | Current direct `min/max(Int)` accepted; result nullable `Int`. | Keep orderable semantics and dialect portability explicit for expressions. |
| `Float` | Current direct `min/max(Float)` accepted; result nullable `Float`. | Future broader treatment should define NaN and signed-zero ordering policy. |
| `Decimal` | Current direct `min/max(Decimal)` accepted; result nullable `Decimal`. | Decimal precision-scale carrier, precision propagation, and SQL precision guarantees remain deferred. |
| `Date` | Current direct `min/max(Date)` accepted; result nullable `Date`. | Future expressions need temporal literal/function/cast and dialect policy. |
| `Timestamp` | Current direct `min/max(Timestamp)` accepted; result nullable `Timestamp`. | Future expressions need timezone, precision, native metadata, and dialect policy. |
| `Text` | Current `min/max(Text)` rejected with `PIE-S2314`. | Requires collation-dependent ordering, Unicode/locale policy, and backend portability first. |
| `Bool` | Current `min/max(Bool)` rejected with `PIE-S2314`. | Requires explicit semantic ordering decision before any support. |
| `UUID` | Current `min/max(UUID)` rejected/deferred. | Requires UUID version/order metadata such as native, lexical, binary, time, or custom ordering. |
| Enum | Current `min/max(Enum)` rejected with `PIE-S2314`. | Requires Enum scalar behavior and declaration/native/custom order metadata first. |
| `Json` | Current `min/max(Json)` rejected with `PIE-S2314`. | Requires structural or serialized ordering policy; no Json ordering is current. |
| `Bytes` | Current `min/max(Bytes)` rejected with `PIE-S2314`. | Requires binary ordering, encoding, and native metadata policy first. |
| `Any` | Current `min/max(Any)` rejected with `PIE-S2314`. | Requires explicit refinement/orderable policy; not dynamic typing. |
| `Unknown` | No stable ordering capability. | Must resolve to a supported known orderable type before any `min/max` decision. |

Semantic ordering must remain separate from storage ordering and native backend
ordering. Metadata-backed ordering for UUID and Enum must be explicit before
any `min/max`, stable `order by`, group-key, or satisfying semantics rely on it.

## Lower/Trim Text-Chain Boundary

The current bounded `count_distinct` Text-transform surface is:

- `count_distinct(lower(field))`;
- `count_distinct(trim(field))`;
- `count_distinct(lower(trim(field)))`;
- `count_distinct(trim(lower(field)))`;
- repeated or nested `lower` / `trim` chains over exactly one `Text` field;
- supported qualified forms such as `count_distinct(lower(source.field))`.

This surface remains a deterministic-transform compatibility baseline. It does
not authorize broad `count_distinct(expression)`.

Unsupported forms remain outside Slice 5:

- `count_distinct(len(status))`;
- `count_distinct(matches(status, "x"))`;
- binary expressions such as `count_distinct(lower(status) + trim(status))`;
- multi-field expressions;
- non-Text leaves such as `count_distinct(lower(amount))`;
- literal-only forms;
- nested aggregates;
- aggregate projection composition.

## Text / Float / Decimal / UUID / Enum / Opaque Caveats

Text distinct and ordering expansion requires explicit collation, Unicode
normalization, locale-sensitive folding, case-folding, and backend equality or
ordering policy. Current direct `count_distinct(Text)` and lower/trim chains do
not define a general Text ordering contract.

Float currently participates in direct `count_distinct(Float)` and direct
`min/max(Float)`. Slice 5 does not implement a Float NaN policy, signed-zero
policy, broad Float expression distinct policy, or broad Float expression
ordering policy.

Decimal currently participates in direct `count_distinct(Decimal)` and direct
`min/max(Decimal)`. Decimal precision-scale carrier, Decimal literals,
precision propagation, SQL precision guarantees, multiplication/division, and
mixed promotion remain deferred.

UUID remains `limited_frozen`. Direct `count_distinct(UUID)` is current, but
UUID ordering, native storage, metadata, literal, cast, and `min/max(UUID)`
remain deferred.

Enum remains `metadata_only`. Enum distinct and ordering require Enum scalar
behavior, SQL portability, equality policy, and declaration/native/custom order
metadata before implementation.

Json, Bytes, and Any remain opaque or deferred boundary surfaces for distinct
and ordering. Json needs serialization/equality policy, SQL `NULL` versus JSON
literal `null` policy, and structural/path policy. Bytes needs serialization,
encoding, and binary equality/order policy. Any needs explicit refinement or
operator-constrained policy and must not become dynamic typing.

## SQL Syntax And Modifier Deferral

Slice 5 preserves existing SQL syntax and modifier deferrals:

- SQL-style `count(distinct field)`;
- generic `DISTINCT` syntax;
- aggregate filters / SQL `FILTER (WHERE ...)`;
- aggregate internal ordering;
- `WITHIN GROUP`;
- window functions / `OVER (...)`;
- `count(*)` source syntax;
- directly imported SQL modifier syntax;
- generic aggregate modifiers;
- modifier-like aggregate arguments.

Current row-level `where:` is not aggregate `FILTER`. Current `satisfying:` is
the only result-predicate user surface and is not aggregate filter syntax.
Current grouped `order by:` is result-level selected-output-name ordering, not
aggregate internal ordering.

## Deferred And Prohibited Surfaces

Slice 5 does not implement:

- broad `count_distinct(expression)`;
- `count(distinct field)`;
- generic `DISTINCT` syntax;
- `count_distinct(Json/Bytes/Any/Enum)`;
- `min/max(Text)`;
- `min/max(UUID)`;
- `min/max(Enum)`;
- `min/max(Json/Bytes/Any)`;
- `min/max(expression)`;
- new collation policy;
- new normalization policy;
- new serialization policy;
- UUID ordering metadata implementation;
- Enum ordering metadata implementation;
- Decimal precision-scale carrier;
- Float NaN/signed-zero policy implementation;
- parser/AST/grammar/generated changes;
- semantic/IR/SQL/CLI/JSON behavior changes;
- fixtures/goldens changes;
- scripts/workflows/package/release changes.

## Future Implementation Prerequisites

Any later behavior implementation requires a separate Gate 1 and Gate 2 with
approved implementation files, validation commands, SQL portability proof,
fixture/golden policy, public output compatibility, diagnostic policy, and
release non-authorization.

Future distinct, collation, and ordering work must define explicit policy for:

- direct fields versus expression arguments;
- equality compatibility;
- distinct compatibility;
- deterministic transforms;
- collation, Unicode normalization, locale, and backend equality;
- serialization for opaque or structured values;
- stable semantic ordering versus storage or native backend ordering;
- Float NaN and signed-zero behavior;
- Decimal precision-scale ownership and propagation;
- UUID version/order metadata;
- Enum declaration/native/custom order metadata;
- Json serialization/equality and SQL `NULL` versus JSON literal `null`;
- Bytes serialization and encoding;
- Any refinement or operator-constrained capability;
- diagnostics and fail-closed boundaries;
- SQL portability for PostgreSQL and private MySQL;
- public output compatibility;
- validation proving no accidental syntax, semantic, IR, SQL, JSON, metadata,
  fixture/golden, package, workflow, or release expansion.

## Public Surface And Release Non-Authorization

Slice 5 keeps public surfaces unchanged:

- source/compiler behavior unchanged;
- grammar and generated parser inventory unchanged;
- parser and AST behavior unchanged;
- semantic behavior unchanged;
- IR behavior unchanged;
- SQL behavior unchanged;
- CLI text output unchanged;
- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- scripts/workflows unchanged;
- package metadata unchanged;
- package version remains `0.1.0`;
- no package/workflow/release metadata change;
- no tag/release/publish/upload/signing/attestation.
