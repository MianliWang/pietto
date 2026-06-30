# Phase 38 Aggregate Semantics And Type Capability Consolidation

## Status And Trusted Handoff

Phase 38 Slice 1 is Aggregate Semantics And Type Capability Consolidation
Candidate Decision. Slice 1 is docs/plan/static-audit/tests-only and
implements no behavior change.

Trusted handoff:

- baseline HEAD: `d2957b773066ea009828fde079ebca5c8e6e2cbb`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 37 aggregate surface audit`;
- latest completed phase: Phase 37 Post-v0.2 Aggregate Surface Expansion MVP;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 1.

Phase 37 completed aggregate surface audit work without source/compiler
behavior changes. Phase 38 starts from that handoff and consolidates aggregate
semantics with the Phase 36 type-capability boundaries before any later
implementation slice may be considered.

Slice 1 does not update `README.md`, `AGENTS.md`, or
`docs/spec/pietto-v0.9.md`; public status housekeeping remains future dedicated
work unless separately approved.

## Candidate Decision

The selected Phase 38 Slice 1 candidate is:

**Aggregate semantics and type capability consolidation**

Slice 1 chooses a behavior-preserving planning boundary:

- record repo-derived aggregate accepted and deferred inventory;
- resolve the exact current `count(field)` posture;
- define type capability vocabulary for aggregate readiness;
- preserve Any / Json / Bytes / Enum / UUID boundaries;
- preserve Decimal precision-scale, temporal, collation, ordering, and
  distinct-readiness boundaries;
- define a seven-slice Phase 38 roadmap.

Slice 1 authorizes no source/compiler behavior change, source implementation,
grammar change, generated ANTLR change, parser or AST behavior change,
semantic behavior change, IR behavior change, SQL behavior change, CLI behavior
change, JSON v1 change, Project JSON v2 change, Semantic Metadata Artifact v1
schema or output change, diagnostic envelope change, SQL golden byte change,
fixture or golden change, script change, workflow change, package metadata
change, lockfile change, package version change, tag, release, publish/upload,
signing, or attestation.

## Repo-Derived Aggregate Inventory

The current accepted aggregate surface remains the repository-local surface
locked by Phase 37 artifacts and earlier implementation tests:

| Row | Current status | Evidence |
|---|---|---|
| `count()` | Accepted as SQL `COUNT(*)`; result is `Int not null`. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `docs/plan/phase-37-post-v02-aggregate-surface-expansion.md`, `tests/test_phase23_count_field_semantics.py`, `tests/test_phase31_aggregate_result_matrix_hardening.py` |
| `count(field)` / `count(source.field)` | Accepted for direct or supported qualified fields where the resolved field type passes current count rules. | `docs/spec/phase37-count-expression-mvp-decision-v1.md`, `tests/test_phase23_count_field_semantics.py`, `src/pietto/semantic/aggregates.py::is_supported_count_argument` |
| `count_distinct(field)` / `count_distinct(source.field)` | Accepted for `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`; result is `Int not null`. | `docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md`, `tests/test_phase31_aggregate_result_matrix_hardening.py`, `src/pietto/semantic/aggregates.py::is_supported_count_distinct_argument` |
| `count_distinct(lower/trim Text chain)` | Accepted for lower/trim chains over exactly one `Text` field leaf, including supported qualified forms. | `docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md`, `tests/test_phase37_current_aggregate_matrix.py` |
| `sum(field)` / `sum(source.field)` | Accepted for direct `Int`, `Float`, and `Decimal` field arguments. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `tests/test_phase31_aggregate_result_matrix_hardening.py`, `src/pietto/semantic/aggregates.py::is_supported_numeric_argument` |
| `avg(field)` / `avg(source.field)` | Accepted for direct `Int`, `Float`, and `Decimal` field arguments. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `tests/test_phase31_aggregate_result_matrix_hardening.py`, `src/pietto/semantic/aggregates.py::is_supported_numeric_argument` |
| `sum(...)` / `avg(...)` bounded numeric expressions | Accepted for current bounded numeric expression argument shapes. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `tests/test_phase31_aggregate_result_matrix_hardening.py`, `src/pietto/semantic/aggregates.py::_is_supported_sum_avg_numeric_expression_shape` |
| `min(field)` / `max(field)` | Accepted for direct `Int`, `Float`, `Decimal`, `Date`, and `Timestamp` field arguments; result is nullable same type. | `docs/spec/phase37-min-max-expression-boundary-v1.md`, `tests/test_phase31_aggregate_result_matrix_hardening.py`, `src/pietto/semantic/aggregates.py::is_supported_extrema_argument` |
| grouped aggregate projections | Accepted for current aggregate rows in current GROUP BY contexts. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `tests/test_phase37_grouped_aggregate_interaction_hardening.py` |
| `satisfying:` | Accepted only as current GROUP BY-only result predicate over selected output names, lowering to SQL `HAVING`. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `tests/test_phase37_grouped_aggregate_interaction_hardening.py` |
| grouped result `order by:` | Accepted only over bare selected output names for selected group-key or aggregate projection outputs. | `docs/spec/v02-aggregate-surface-freeze-v1.md`, `tests/test_phase37_grouped_aggregate_interaction_hardening.py` |

The current deferred and prohibited aggregate surface remains:

- `count(expression)`, including `count(amount + tax)`;
- `count(constant)` and `count(1)`;
- `count_if(predicate)`;
- broad `count_distinct(expression)`;
- `min(expression)` / `max(expression)`;
- aggregate filters / SQL `FILTER (WHERE ...)`;
- generic `DISTINCT` syntax such as `count(distinct field)`;
- aggregate internal ordering / `WITHIN GROUP`;
- window functions / `OVER (...)`;
- nested aggregates;
- aggregate projection composition;
- aggregate arguments over projection aliases;
- literal-only `sum(1)` / `avg(1)`;
- division or modulo aggregate expression arguments;
- relationship/fanout-safe aggregates.

These rows remain candidates or deferred surfaces only. Slice 1 changes none
of their current diagnostics.

## Exact `count(field)` Current Posture

Current `count(field)` acceptance is implementation-backed by
`src/pietto/semantic/aggregates.py::is_supported_count_argument`: the resolved
type kind must not be `ENUM` or `UNKNOWN`, and the argument must not be builtin
`Any`.

| Form | Current status | Evidence |
|---|---|---|
| `count(Any field)` | Rejected with `PIE-S2314`. | `tests/test_phase23_count_field_semantics.py::test_count_any_field_is_rejected_with_existing_unsupported_type_diagnostic`, `tests/test_phase36_any_bytes_json_support_posture.py::test_any_count_and_boundary_aggregates_fail_with_pie_s2314` |
| `count(Json field)` | Accepted and SQL-emitting through the generic count path. | `docs/spec/any-bytes-json-support-posture-v1.md`, `tests/test_phase36_any_bytes_json_support_posture.py::test_bytes_json_direct_count_remains_accepted_and_sql_emitting`, `tests/test_phase31_aggregate_result_matrix_hardening.py::test_count_field_boundary_types_are_locked_with_enum_fail_closed` |
| `count(Bytes field)` | Accepted and SQL-emitting through the generic count path. | `docs/spec/any-bytes-json-support-posture-v1.md`, `tests/test_phase36_any_bytes_json_support_posture.py::test_bytes_json_direct_count_remains_accepted_and_sql_emitting`, `tests/test_phase31_aggregate_result_matrix_hardening.py::test_count_field_boundary_types_are_locked_with_enum_fail_closed` |
| `count(Enum field)` | Rejected with `PIE-S2314`; it no longer reaches backend `PIE-B1000`. | `docs/spec/enum-support-resolution-v1.md`, `tests/test_phase36_enum_support_resolution.py::test_count_enum_field_fails_semantic_validation_with_pie_s2314` |
| `count(UUID field)` | Accepted through the current limited/frozen UUID surface. | `docs/spec/uuid-support-completion-v1.md`, `tests/test_phase31_aggregate_result_matrix_hardening.py::test_count_field_boundary_types_are_locked_with_enum_fail_closed` |

`count(field)` still means SQL non-null value counting. It is not a scalar
builtin and does not imply runtime/database execution.

## Type Capability Matrix

The following capability matrix records current repo posture only. Generic
`is null` / `is not null` typing exists in
`src/pietto/semantic/expressions.py` and is covered by
`tests/test_semantic_expressions.py::test_is_null_expression_maps_to_non_null_bool`;
that implementation returns `Bool NON_NULL` for `IsNullExpr`. This is generic
expression machinery, not type-specific Any / Json / Bytes / Enum / UUID
semantics.

| Type | Output/projectable | Null-checkable | Countable | Arithmetic | Min/max/orderable | Distinct-compatible | Text-transform |
|---|---|---|---|---|---|---|---|
| `Any` | current generic field/projection | generic `is null` expression exists, not Any-specific | no, `PIE-S2314` | no | no | no | no |
| `Json` | current generic field/projection | generic `is null` expression exists, not Json-specific | yes, direct `count(Json field)` | no | no | no | no |
| `Bytes` | current generic field/projection | generic `is null` expression exists, not Bytes-specific | yes, direct `count(Bytes field)` | no | no | no | no |
| Enum | metadata/projection readiness, not stable SQL scalar | generic expression machinery exists, no Enum-specific contract | no, `PIE-S2314` | no | no | no | no |
| `UUID` | current `limited_frozen` field/projection | generic `is null` expression exists, not UUID-specific | yes, direct `count(UUID field)` | no | no current `min/max`; ordering remains risky/deferred | yes, direct `count_distinct(UUID field)` | no |

Future capability work must define explicit contracts before changing behavior:
countable, null-checkable, lowerable, numeric, arithmetic-capable, orderable,
distinct-compatible, text-transform-capable, metadata-backed, and dialect-safe.

## Count Family Future Semantics

Slice 1 records future design direction only:

- `count()` remains all-row count and SQL `COUNT(*)`.
- `count(field)` remains SQL non-null field-value count.
- `count(expression)` remains a future candidate and must preserve SQL
  non-null expression counting semantics if later approved.
- `count(constant)` / `count(1)` remains a future compatibility candidate;
  future work should preserve render form where migration compatibility
  matters and must not silently rewrite it to `count()` unless explicitly
  approved.
- `count_if(predicate)` remains a future candidate: a later contract should
  define Bool / nullable Bool predicate typing, TRUE-count semantics,
  FALSE/NULL/UNKNOWN exclusion, `Int not null` result, SQL portability, and
  unsupported-shape diagnostics.

Slice 1 does not implement any of these future count-family behaviors.

## Any / Json / Bytes / Enum / UUID Boundary

`Any` remains a current builtin top/deferred boundary type. It is projectable
through generic field/projection paths but is not dynamic typing, runtime
casts, permissive SQL fallback, arithmetic, ordering, distinct compatibility,
or aggregate expansion.

`Json` and `Bytes` remain deferred builtin behavior surfaces. They support
field facts, projection, aliases, and direct `count(field)` through current
generic SQL paths. They do not authorize structural Json typing, JSON path
operations, binary literals, encoding policy, distinct compatibility, min/max,
arithmetic, native metadata, storage/DDL, schema introspection, or runtime
behavior.

Enum remains `metadata_only`: enum definitions, enum field facts,
`TypeKind.ENUM`, `EnumIR`, and metadata/explain readiness exist, but Enum is
not a builtin scalar and has no literals, member references, casts, native DB
enum metadata, DDL/storage, runtime/database behavior, stable ordering,
distinct compatibility, or aggregate acceptance.

`UUID` remains `limited_frozen`: field declaration, source facts, projection,
direct `count(UUID field)`, direct `count_distinct(UUID field)`, and
metadata/explain support posture are current. Stable UUID comparison, ordering,
group-key, `satisfying`, native metadata, literal, cast, storage, and `min/max`
behavior remain deferred.

## Distinct, Collation, Ordering, And Decimal Readiness

`DateTime` / `Time` / `Interval` remain unsupported/deferred. They are not
builtins and fail semantic type resolution with `PIE-S2002`.

Decimal precision-scale carrier work remains deferred. No carrier exists, and
`Decimal(12, 2)` generic `TypeExpr.arguments` do not create accepted
precision/scale semantics.

`Float` has current direct `count_distinct(Float)` and direct `min/max(Float)`
support. No Float-specific caveat is currently documented beyond the general
future portability and capability-policy boundaries.

`Text` has current direct `count_distinct(Text)` and lower/trim Text-chain
support. Text collation, Unicode normalization, locale-sensitive folding, Text
ordering expansion, and backend-specific equality rules remain outside current
behavior.

`count_distinct(expression)` remains blocked on equality, collation,
normalization, serialization, deterministic transform, dialect-portability, and
diagnostic policy.

`min/max(expression)` remains blocked on orderable capability, result typing,
nullability, collation/order semantics, dialect portability, and unsupported
type policy.

`sum/avg(expression)` expansion remains blocked on numeric/arithmetic
capability and Decimal precision-scale readiness where Decimal participation is
involved.

## Binding / Filtered Aggregate / Post-Aggregate Layer Roadmap

Projection aliases remain output naming, not automatic reusable variable
binding. Any future reusable row-level binding should be explicit and
SQL-lowering-aware, likely through a later `let:` or `with:` style contract
that defines scope, lifecycle, immutability, no cycles, hygiene, diagnostics,
and lowering.

Filtered aggregates remain deferred. A future filtered aggregate syntax must
choose Pietto source spelling, Bool predicate rules, relation scope, SQL
portability across PostgreSQL and private MySQL, diagnostics, fixture/golden
policy, and public output compatibility.

Post-aggregate expression support remains deferred. Aggregate projection
composition such as `sum(amount) + 1` and projection alias aggregation remain
blocked until a post-aggregate expression layer, relation layer IR, or subquery
lowering model is separately designed and approved.

Relationship/fanout-safe aggregate remains deferred until relationship/JOIN
and grain/fanout semantics exist.

## Phase 38 Slice Sequence

| Slice | Name | Slice posture |
|---:|---|---|
| 1 | Candidate Decision And Scope Inventory | docs/plan/static-audit/tests-only; no behavior change |
| 2 | Count Family Semantics Contract | docs/spec/static-audit first; no initial behavior change |
| 3 | Type Capability Matrix Contract | docs/spec/static-audit first; no behavior change |
| 4 | Any / Json / Bytes / Enum / UUID Capability Boundary | docs/spec/static-audit first; no initial behavior change |
| 5 | Distinct / Collation / Ordering Readiness | docs/spec/tests first; no behavior change |
| 6 | Binding / Aggregate Filter / Post-Aggregate Roadmap | docs/spec/static-audit first; no behavior change |
| 7 | Completion Audit And Public Surface Lock | audit/status; no behavior change unless a prior slice separately approved implementation |

Later slices may recommend behavior changes, but every implementation slice
requires a separate Gate 1 and Gate 2 authorization that names implementation
files, validation, SQL portability proof, fixture/golden policy, public surface
review, and release non-authorization.

## Slice 1 Public Surface Constraints

Slice 1 keeps public surfaces unchanged:

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

Forbidden surfaces for Slice 1 are:

- `README.md`;
- `AGENTS.md`;
- `docs/spec/pietto-v0.9.md`;
- `src/`;
- `grammar/`;
- `src/pietto/generated/`;
- `fixtures/`;
- `tests/fixtures/`;
- `scripts/`;
- `.github/workflows/`;
- `pyproject.toml`;
- `uv.lock`.

## Validation Plan And Gate 2 Allowlist

Approved Slice 1 Gate 2 file allowlist:

- `docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md`;
- `tests/test_phase38_candidate_decision.py`.

Validation should run:

```bash
uv run pytest tests/test_phase38_candidate_decision.py
uv run ruff format --check .
uv run ruff check .
git diff --check
```

Gate 2 evidence should be written to
`/tmp/phase38-slice1-gate2-evidence.txt` and include baseline raw output,
changed file set, `git diff --stat`, `git diff --name-status`, full diff,
no-index diff for untracked new files, untracked whitespace check, raw
validation output, and final confirmations.

Gate 2 must not stage, commit, push, start or poll CI, tag, release,
publish/upload, sign, or attest.
