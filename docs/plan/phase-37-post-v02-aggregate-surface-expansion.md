# Phase 37 Post-v0.2 Aggregate Surface Expansion MVP

## Status And Trusted Handoff

Phase 37 Slice 1 is Candidate Decision And Aggregate Surface Boundary. Slice 1
is docs/plan/static-audit only and implements no behavior change.

Trusted handoff:

- baseline HEAD: `09f05d141f165946489c9d272ad52db8139c8a5c`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 36 core type system expansion audit`;
- latest completed phase: Phase 36 Post-v0.2 Core Type System Expansion MVP;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 1.

Phase 36 completed the post-v0.2 core type-system candidate resolution work.
Its only behavior change was the Slice 5 Enum aggregate fail-closed fix:
`count(Enum field)` now fails closed in semantic aggregate validation with
`PIE-S2314`.

Slice 1 starts Phase 37 without changing the compiler. It does not update
`README.md`, `AGENTS.md`, or `docs/language.md`; public status
housekeeping remains future dedicated work.

## Candidate Decision

The selected Phase 37 Slice 1 candidate is:

**Aggregate surface boundary and candidate decision**

Phase 37 is Post-v0.2 Aggregate Surface Expansion / Aggregate Surface
Completion. The goal is not broad aggregate expansion. The goal is to organize
the current aggregate surface, classify accepted, deferred, and prohibited rows,
and recommend safe small-step slices.

Slice 1 chooses a behavior-preserving planning boundary:

- record the current accepted aggregate surface;
- record deferred and prohibited aggregate candidates;
- preserve Phase 36 type boundaries;
- keep public outputs and schemas unchanged;
- define a 10-slice aggregate-focused roadmap.

Slice 1 authorizes no source/compiler behavior change, source implementation,
grammar change, generated ANTLR change, parser or AST behavior change, semantic
behavior change, IR or SQL behavior change, CLI behavior change, JSON v1
change, Project JSON v2 change, Semantic Metadata Artifact v1 schema or output
change, diagnostic envelope change, SQL golden byte change, fixture or golden
change, script change, workflow change, package metadata change, lockfile
change, package version change, tag, release, publish/upload, signing, or
attestation.

## Goals

- Make the current aggregate surface reviewable as a matrix.
- Separate current accepted behavior from deferred and prohibited candidates.
- Keep Phase 37 aggregate-focused.
- Preserve stable SQL output, fail-closed diagnostics, and public output
  compatibility.
- Define later slices that can be implemented only after separate Gate 1 and
  Gate 2 approval.

## Non-goals

Slice 1 does not implement or authorize:

- `count(expression)`;
- broad `count_distinct(expression)`;
- `min(expression)` or `max(expression)`;
- aggregate filters, window functions, internal aggregate ordering, generic
  aggregate modifiers, or generic `DISTINCT` syntax such as
  `count(distinct field)`;
- nested aggregate support;
- aggregate projection composition such as `sum(x) + 1`;
- aggregate arguments over projection aliases;
- literal-only aggregate arguments such as `sum(1)` or `avg(1)`;
- division or modulo aggregate expression arguments;
- Decimal literal, Decimal multiplication, Decimal division, mixed Decimal
  promotion, or Decimal precision-scale carrier work;
- UUID, Enum, Any, Bytes, or Json aggregate expansion beyond the Phase 36
  boundaries;
- relationship/fanout-safe aggregates, JOIN behavior, relation composition,
  endpoint-qualified lookup, runtime/database execution, schema introspection,
  db pull, project/multi-file semantic expansion, public release work, LSP,
  Arrow, or web UI.

## Current Accepted Aggregate Surface

The current accepted surface is the repository-local aggregate surface from
Phases 19 through 28, plus later stabilization and Phase 36 Enum fail-closed
hardening.

| Row | Current status |
|---|---|
| `count()` | Accepted as SQL `COUNT(*)`; result is `Int not null`. |
| `count(field)` / `count(source.field)` | Accepted for direct field or supported single-input qualified field arguments over concrete non-`Any` builtin fields. |
| `count(Enum field)` | Rejected in semantic aggregate validation with `PIE-S2314`; this is the only Phase 36 behavior change. |
| `count_distinct(field)` / `count_distinct(source.field)` | Accepted for current direct-field subset: `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`; result is `Int not null`. |
| `count_distinct(lower/trim Text chain)` | Accepted for chains made only of `lower(...)` and `trim(...)` over exactly one `Text` field leaf, including supported qualified field leaves. |
| `sum(field)` / `sum(source.field)` | Accepted for direct `Int`, `Float`, and `Decimal` field arguments. |
| `avg(field)` / `avg(source.field)` | Accepted for direct `Int`, `Float`, and `Decimal` field arguments. |
| `sum(...)` / `avg(...)` bounded numeric expressions | Accepted for current bounded numeric expression argument shapes. |
| Int/Float literal leaves inside `sum` / `avg` | Accepted only when the expression still contains at least one direct input field leaf. |
| Decimal `+` and `-` expression participation | Accepted where already supported by current scalar and aggregate expression typing. |
| `min(field)` / `max(field)` | Accepted for direct `Int`, `Float`, `Decimal`, `Date`, and `Timestamp` field arguments; result is nullable same type. |
| grouped aggregate projections | Accepted for current aggregate rows in current GROUP BY contexts. |
| `satisfying:` | Accepted only as current GROUP BY-only result predicate over selected output names, lowering to SQL `HAVING`. |
| grouped result `order by:` | Accepted only over bare selected output names for selected group-key or aggregate projection outputs. |

Current aggregate names remain aggregate names, not scalar builtins. Current
accepted SQL output remains PostgreSQL and private MySQL output through the
existing compiler pipeline; Pietto still does not execute SQL.

## Deferred And Prohibited Aggregate Candidates

| Candidate | Slice 1 classification | Boundary |
|---|---|---|
| `count(expression)` | deferred | Requires a separate MVP decision for argument typing, nullability, SQL portability, diagnostics, and alias/projection interaction. |
| broad `count_distinct(expression)` | deferred | Current support remains direct fields plus lower/trim `Text` chains only. |
| `min(expression)` / `max(expression)` | deferred | Current support remains direct fields only. |
| aggregate filters | deferred/prohibited for Slice 1 | Requires syntax, semantic, SQL, and portability decisions. |
| window functions | deferred/prohibited for Slice 1 | Outside the current aggregate projection model. |
| generic aggregate modifiers | deferred/prohibited for Slice 1 | No generic modifier syntax or semantics is authorized. |
| generic `DISTINCT` syntax | deferred/prohibited for Slice 1 | `count_distinct(...)` remains the current spelling. |
| nested aggregates | prohibited in current behavior | Continue to fail closed through existing aggregate diagnostics. |
| aggregate projection composition | prohibited in current behavior | Direct aliased aggregate projections remain the accepted shape. |
| aggregate over projection aliases | deferred/prohibited for Slice 1 | Projection aliases remain outside aggregate argument lookup. |
| literal-only aggregate arguments | prohibited in current behavior | `sum(1)` and `avg(1)` remain rejected. |
| division or modulo aggregate arguments | deferred/prohibited for Slice 1 | Existing division/modulo boundaries remain unchanged. |
| Decimal literal/multiply/divide/mixed promotion | deferred/prohibited for Slice 1 | Preserved by Phase 36 Decimal and scalar matrix boundaries. |
| UUID/Enum/Any/Bytes/Json aggregate expansion | deferred/prohibited for Slice 1 | Preserved by Phase 36 type-candidate resolutions. |
| relationship/fanout-safe aggregates | deferred/prohibited for Slice 1 | Requires relationship/JOIN and grain/fanout work first. |

## Phase 36 Type Boundary Preservation

Slice 1 preserves the Phase 36 type-candidate resolutions:

- Decimal precision-scale carrier deferred with exact prerequisites;
- UUID remains `limited_frozen` with no behavior expansion;
- Enum remains metadata/readiness except `count(Enum field)` fails closed with
  `PIE-S2314`;
- DateTime / Time / Interval remain deferred;
- Any / Bytes / Json behavior surfaces remain unchanged and deferred where
  already deferred;
- type alias behavior is preserved;
- domain refinement remains deferred;
- Currency/Money remain deferred;
- native DB metadata remains deferred.

These boundaries are aggregate-adjacent but are not reopened by Slice 1.

## Public Surface Constraints

Slice 1 keeps public surfaces unchanged:

- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- package version remains `0.1.0`;
- no package/workflow/release metadata change;
- no tag/release/publish/upload/signing/attestation.

## Phase 37 Slice Roadmap

| Slice | Name | Slice posture |
|---:|---|---|
| 1 | Candidate Decision And Aggregate Surface Boundary | docs/plan/static-audit only; no behavior change |
| 2 | Current Aggregate Matrix And Deferred Register | tests-only/static-audit; no behavior change |
| 3 | `count(expression)` MVP Decision | docs/spec first; possible later implementation only if separately approved |
| 4 | `count_distinct(expression)` Widening Boundary | readiness/spec/tests first; no initial behavior change |
| 5 | `min/max(expression)` Boundary | readiness/spec/tests first; no initial behavior change |
| 6 | Nested Aggregate And Composition Hardening | tests-only; no behavior change |
| 7 | Aggregate Filter / DISTINCT / Modifier Syntax Deferral | docs/spec/static-audit; no behavior change |
| 8 | Decimal Aggregate Expression Boundary | docs/spec/tests; no behavior change |
| 9 | Grouped Aggregate Interaction Hardening | tests-only; no behavior change |
| 10 | Completion Audit And Public Surface Lock | audit/status; no behavior change |

Later slices may recommend implementation, but implementation requires separate
Gate 1 and Gate 2 authorization for that slice.

## Validation Plan

Slice 1 validation should run:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest tests/test_phase37_candidate_decision.py
uv run pytest tests/test_phase29_v02_aggregate_surface_freeze.py tests/test_phase31_aggregate_result_matrix_hardening.py tests/test_phase36_enum_support_resolution.py tests/test_phase36_completion_audit.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run python scripts/validate.py
git diff --check
```

If `scripts/package_smoke.py` fails only because of DNS, PyPI, name-resolution,
dependency fetch, or package-index access, the failure is environment-only.
Gate 2 evidence must record the raw failure and must not modify repository
files for that environment-only failure.

## Planning-only Future Roadmap

The following roadmap note is planning-only and authorizes no implementation in
Phase 37 Slice 1:

- Phase 38: Deferred Feature Readiness And Semantic Surface Consolidation.
- Phase 39: Public Developer Experience And Example Gallery MVP.
- Phase 40: Editor Experience MVP / VSCode Extension Readiness.
- Phase 41: Database Dialect Expansion Matrix.
- Phase 42: SQLite or DuckDB Backend MVP.
- Phase 43: LSP Diagnostics MVP.
- Phase 44: Arrow / PyArrow Schema Bridge MVP.
- Phase 45+: Semantic Graph / JOIN Readiness II.

These future labels do not change current package metadata, public output
schemas, compiler behavior, runtime/database boundaries, relationship/JOIN
boundaries, release status, or CI/release operations.
