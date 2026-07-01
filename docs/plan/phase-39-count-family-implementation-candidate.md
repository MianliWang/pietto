# Phase 39 Count Family Implementation Candidate

## Status And Trusted Handoff

Phase 39 Slice 1 is Candidate Decision And Implementation Readiness Scope.
Slice 1 is docs/plan/static-audit/tests-only and implements no behavior
change.

Trusted handoff:

- baseline HEAD: `ee254bc48237a11cb6fb17493d5838a04fdce6d5`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 38 aggregate semantics audit`;
- latest completed phase: Phase 38 Aggregate Semantics And Type Capability
  Consolidation;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 1.

Phase 38 completed count-family and aggregate capability consolidation without
source/compiler behavior changes. Phase 39 starts from that handoff and decides
whether a narrow count-family behavior implementation is ready to be planned
after the Phase 38 documentation, specification, and static-audit boundary.

Slice 1 does not update `README.md`, `AGENTS.md`, or
`docs/spec/pietto-v0.9.md`; public status housekeeping remains future dedicated
work unless separately approved.

The older Phase 37 planning note that named "Phase 39: Public Developer
Experience And Example Gallery MVP" is historical roadmap text only. This
Phase 39 plan supersedes that old future label for current work and does not
edit locked Phase 37 artifacts.

## Candidate Decision

The selected Phase 39 Slice 1 candidate is:

**Count family implementation candidate and aggregate semantics implementation
readiness**

Slice 1 chooses a behavior-preserving readiness boundary:

- confirm Phase 38 final artifacts and the current aggregate implementation
  surface;
- classify count-family implementation candidates by readiness and risk;
- identify `count(expression)` as the only plausible narrow later behavior
  candidate;
- reject or defer broader aggregate, filter, post-aggregate, and relation-layer
  work;
- define a five-slice Phase 39 roadmap.

Slice 1 authorizes no source/compiler behavior change, source implementation,
grammar change, generated ANTLR change, parser or AST behavior change,
semantic behavior change, IR behavior change, SQL behavior change, CLI behavior
change, JSON v1 change, Project JSON v2 change, Semantic Metadata Artifact v1
schema or output change, diagnostic envelope change, SQL golden byte change,
fixture or golden change, script change, workflow change, package metadata
change, lockfile change, package version change, tag, release, publish/upload,
signing, or attestation.

## Phase 38 Artifact Handoff

Phase 39 Slice 1 relies on the completed Phase 38 artifact inventory:

| Artifact | Path |
|---|---|
| Phase 38 plan | `docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md` |
| Count-family contract | `docs/spec/phase38-count-family-semantics-contract-v1.md` |
| Type capability matrix | `docs/spec/phase38-type-capability-matrix-contract-v1.md` |
| Boundary type capability contract | `docs/spec/phase38-boundary-types-capability-contract-v1.md` |
| Distinct/collation/ordering readiness | `docs/spec/phase38-distinct-collation-ordering-readiness-v1.md` |
| Binding/filter/post-aggregate roadmap | `docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md` |
| Phase 38 static audits | `tests/test_phase38_*.py` |

The Phase 38 completion audit records Phase 38 as complete
docs/plan/spec/static-audit and tests-only work. It also keeps these deferred
boundaries deferred:

- `count(expression)`, `count(constant)`, `count(1)`, and
  `count_if(predicate)`;
- broad `count_distinct(expression)`;
- `min/max(expression)`;
- broad `sum/avg(expression)`;
- aggregate filters, SQL-style modifiers, `WITHIN GROUP`, and window
  functions;
- post-aggregate expression composition, relation-layer IR, subquery lowering,
  and CTE insertion;
- relationship-aware aggregate rewrites, fanout warnings, grain inference,
  endpoint-qualified lookup, relation composition, and JOIN behavior;
- runtime/database execution, schema introspection, db pull, raw SQL escape
  hatches, public MySQL API expansion, package release, publication, upload,
  signing, and attestation.

## Repo-Derived Implementation Inventory

The current implementation has enough aggregate plumbing to support a later
narrow `count(expression)` slice, but not enough to implement it safely in
Slice 1:

| Area | Current repo-derived fact |
|---|---|
| Semantic aggregate names | `src/pietto/semantic/aggregates.py` recognizes `count`, `count_distinct`, `sum`, `avg`, `min`, and `max` for semantic aggregate checks. |
| `count` arity | `expected_semantic_aggregate_arities("count")` accepts `0` or `1`; direct `count(field)` is already semantic behavior. |
| Direct count type rule | `is_supported_count_argument` accepts non-Enum, non-Unknown, non-`Any` direct fields. |
| Count expression semantic MVP | Slice 3 accepts narrow field-bearing `count(expression)` arguments semantically; literal-only and unsupported shapes remain `PIE-S2315`. |
| Projection validation | `src/pietto/semantic/relation_schemas.py` and `src/pietto/semantic/group_by.py` validate direct aliased aggregate projections and reject composition/nesting. |
| IR lowering | `src/pietto/ir/lowering.py` lowers aggregate calls only when semantic value type and row schema projection facts agree. |
| Aggregate IR | `AggregateCallIR` carries expression arguments, but `RelationIR` has no `RelationLayerIR` or approved post-aggregate layer. |
| PostgreSQL SQL | `src/pietto/sql/expressions.py` renders `COUNT(*)` and direct resolved field counts; non-field `COUNT(arg)` raises before SQL output. |
| private MySQL SQL | `src/pietto/sql/mysql_expressions.py` mirrors the direct resolved field count guard. |
| Grammar/generated | `grammar/Pietto.g4` already parses ordinary call arguments; generated ANTLR files remain unchanged and SQL-like aggregate modifiers remain parser-rejected. |
| CLI/JSON/explain | `src/pietto/cli.py`, `src/pietto/cli_json.py`, `src/pietto/_metadata/`, and `src/pietto/_project/` remain public-output compatibility surfaces and are not changed by Slice 1. |
| Fixtures/goldens | current aggregate SQL bytes are covered in `tests/fixtures/phase19` through `tests/fixtures/phase24` and `tests/fixtures/golden/*aggregate*`. |
| Package/workflows | `pyproject.toml`, `uv.lock`, `.github/workflows/`, and validation/package-smoke scripts remain unchanged. |

## Candidate Readiness Matrix

| Candidate | Slice 1 decision | Readiness and risk |
|---|---|---|
| `count(expression)` | Later narrow behavior candidate only. | Best candidate after Phase 38. It needs a separate contract for expression shape, known concrete result type, field-leaf policy, nullness semantics, semantic validation, IR lowering, PostgreSQL/private MySQL rendering, CLI/JSON compatibility, and fixture/golden policy. |
| `count(1)` / `count(constant)` | Defer. | Useful for SQL migration compatibility, but distinct from idiomatic `count()` and needs source-preservation, warning/lint, and literal policy. |
| `count_if(predicate)` | Defer. | Requires new aggregate name, Bool/nullable Bool contract, TRUE-only counting, SQL portability, and diagnostics. |
| `count(Enum field)` | Defer/reject for now. | Current `PIE-S2314` fail-closed behavior is intentional; Enum remains metadata-only, not a stable SQL scalar. |
| `count(Any field)` | Reject for now. | `Any` remains opaque/top/deferred, not dynamic typing or permissive SQL fallback. |
| current `count(Json/Bytes/UUID field)` | Hardening only; no behavior change. | Existing direct-count behavior remains accepted and should be protected, not widened by analogy. |
| broad `count_distinct(expression)` | Defer. | Requires equality, distinct compatibility, collation, normalization, serialization, deterministic transform, and dialect policy. |
| `min/max(expression)` | Defer. | Requires known concrete orderable result type, nullable same-type result policy, field-leaf policy, ordering semantics, and SQL portability. |
| broad `sum/avg(expression)` | Defer. | Current bounded numeric expression support remains enough; broader support needs numeric/arithmetic capability and Decimal precision-scale policy. |
| aggregate filters | Defer. | Requires source syntax, Bool predicate rules, relation scope, IR representation, SQL portability, diagnostics, fixtures/goldens, and public output review. |
| post-aggregate expressions / `RelationLayerIR` | Defer. | Requires an approved relation-layer or subquery model before aggregate composition, projection alias aggregation, CTE insertion, or post-aggregate expression lowering. |

## Future `count(expression)` Candidate Boundary

If a later slice separately approves `count(expression)`, the candidate should
start with this narrow MVP:

- direct aliased aggregate projections only;
- no-GROUP and grouped contexts only;
- expression must include at least one resolved direct input field leaf;
- expression result type must be known, concrete, non-`Any`, non-Enum, and
  non-Unknown;
- SQL semantics count non-`NULL` expression results;
- `Bool` expressions, if admitted by the later contract, count both non-`NULL`
  `TRUE` and non-`NULL` `FALSE`;
- result remains `Int not null`;
- current `count()` and direct `count(field)` SQL bytes remain compatible;
- unsupported shapes fail closed before SQL rendering.

The candidate explicitly excludes `count(1)`, literal-only expressions,
projection aliases as aggregate argument leaves, nested aggregates, aggregate
composition, aggregate filters, generic `DISTINCT`, `count(distinct field)`,
window functions, internal aggregate ordering, relationship/JOIN/fanout-aware
contexts, public MySQL API expansion, runtime/database execution, package
release, publication, upload, signing, and attestation.

## Phase 39 Slice Sequence

| Slice | Name | Slice posture |
|---:|---|---|
| 1 | Candidate Decision And Implementation Readiness Scope | docs/plan/static-audit/tests-only; no behavior change |
| 2 | Count Expression MVP Contract | docs/spec/static-audit first; no behavior change unless separately approved |
| 3 | Count Expression Semantic MVP | semantic acceptance only for the approved narrow `count(expression)` boundary |
| 4 | Count Expression IR Lowering MVP | IR lowering for the semantically approved `count(expression)` subset |
| 5 | Count Expression SQL Lowering MVP | PostgreSQL/private MySQL lowering for the approved IR subset |
| 6 | Count Expression CLI / JSON / Golden Compatibility | CLI, JSON, fixture, and golden compatibility for the approved behavior |
| 7 | Count Family Boundary Regression Matrix | regression matrix for count-family acceptance and exclusions |
| 8 | Completion Audit And Status Lock | audit/status; no new behavior unless a prior slice separately approved implementation |

Later phases or separately approved slices must handle `count(1)`,
`count_if(predicate)`, broad `count_distinct(expression)`, `min/max(expression)`,
broad `sum/avg(expression)`, aggregate filters, post-aggregate expressions, and
`RelationLayerIR`.

## Slice 1 Public Surface Constraints

Slice 1 keeps public surfaces unchanged:

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

- `docs/plan/phase-39-count-family-implementation-candidate.md`;
- `tests/test_phase39_candidate_decision.py`.

Validation should run:

```bash
uv run pytest tests/test_phase39_candidate_decision.py
uv run ruff format --check .
uv run ruff check .
git diff --check
```

Gate 2 evidence should be written to
`/tmp/phase39-slice1-gate2-evidence.txt` and include baseline raw output,
changed file set, `git diff --stat`, `git diff --name-status`, full diff,
no-index diff for untracked new files, untracked whitespace check, raw
validation output, and final confirmations.

Gate 2 must not stage, commit, push, start or poll CI, tag, release,
publish/upload, sign, or attest.
