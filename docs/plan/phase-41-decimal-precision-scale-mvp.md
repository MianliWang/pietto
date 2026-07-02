# Phase 41 Decimal Precision-Scale MVP

## Status And Trusted Handoff

Phase 41 Slice 1 is Candidate Decision And Scope Lock. Slice 1 is
docs/plan/static-audit/tests-only and implements no behavior change.

Phase 41 theme: Decimal precision-scale MVP.

Trusted Phase 40 handoff:

- baseline HEAD: `0244eb9cdb00a5fa97d9533377a059a2c25757b0`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 40 let binding implementation audit`;
- latest completed phase: Phase 40 Let Binding Model;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 1.

Phase 40 implemented row-level `let:` only and explicitly did not start Phase
41. Current deferred let work is aggregate/grouped/result-scope integration,
not basic let implementation. Phase 41 starts from the trusted Phase 40
handoff and decides the Decimal precision-scale direction before any
production compiler behavior is authorized.

Slice 1 does not update `README.md`, `AGENTS.md`,
`docs/spec/pietto-v0.9.md`, the deferred register, or status-lock files.
Status housekeeping remains future dedicated work unless separately approved.

## Candidate Decision

The selected Phase 41 candidate is:

**Minimal fail-closed compiler-internal Decimal precision-scale MVP**

Phase 41 is not a docs-only phase. Unless a later Gate 1 finds a concrete repo
blocker, production implementation begins in Slice 2.

Slice 1 chooses this MVP direction:

- accept `Decimal(precision, scale)` as a semantic Decimal type form in a later
  approved implementation slice;
- preserve plain `Decimal` and all current plain Decimal behavior;
- store validated precision-scale facts in internal compiler type facts;
- reject invalid precision-scale forms fail-closed;
- keep SQL expression output unchanged;
- keep CLI JSON v1 and Semantic Metadata Artifact v1 schemas unchanged;
- keep Decimal literals, full numeric promotion, casts, native DB metadata, and
  SQL DDL/native type output out of Phase 41.

Slice 1 authorizes no source/compiler behavior change, source implementation,
grammar change, generated ANTLR change, parser or AST behavior change,
semantic behavior change, IR behavior change, SQL behavior change, CLI
behavior change, CLI JSON v1 change, Project JSON v2 change, Semantic Metadata
Artifact v1 schema or output change, diagnostic envelope change, SQL golden
byte change, fixture or golden change, example change, script change, workflow
change, package metadata change, lockfile change, package version change, tag,
release, publish/upload, signing, or attestation.

## Repo-Derived Decimal Precision-Scale Readiness

The current repository has enough parser and type-system scaffolding to plan a
Decimal precision-scale MVP without a Slice 1 grammar/generated change.

| Area | Current repo-derived fact |
|---|---|
| Parser syntax | `grammar/Pietto.g4` already allows generic type arguments through `typeReference: identifier typeArguments?`. |
| AST shape | `TypeExpr` already stores `arguments: tuple[TypeArgument, ...]`. |
| AST builder | `visitTypeExpression` preserves parsed type arguments through `ctx.typeArguments().typeArgument()`. |
| Current Decimal argument behavior | `Decimal(12, 2)` can parse as generic `TypeExpr.arguments`, but current semantic resolution ignores those arguments. |
| Current semantic type carrier | `ResolvedType` carries only `name`, `kind`, and optional `definition`; `ValueType` carries `resolved_type`, `nullability`, and `kind`. |
| Current plain Decimal representation | Plain `Decimal` is a builtin scalar name in `BUILTIN_TYPE_NAMES`. |
| Current precision-scale carrier | No precision-scale carrier exists in semantic, IR, SQL, CLI JSON, Project JSON v2, or Semantic Metadata Artifact v1 models. |
| Current SQL posture | PostgreSQL and private MySQL expression renderers use logical type names for fail-closed checks and do not render `DECIMAL(p, s)` or `NUMERIC(p, s)`. |
| Current metadata posture | Semantic Metadata Artifact v1 exposes type status, kind, canonical identity, nullability, and support posture only. |
| Current diagnostics posture | Existing type diagnostics cover duplicate names, unknown types, alias cycles, implicit nullability, and semantic recursion; no current diagnostic specifically owns invalid type arguments. |

Therefore Slice 2 should start in semantic validation and carrier ownership,
not grammar regeneration.

## MVP Boundary

If a later slice separately approves implementation, the first behavior slice
should use these constraints:

- `Decimal(p, s)` accepts exactly two positional integer literal arguments;
- `p` is precision and `s` is scale;
- `p` and `s` must be valid compile-time metadata, not runtime expressions;
- invalid arity, named arguments, non-integer arguments, negative values, or
  inconsistent precision-scale values fail closed with a type diagnostic;
- plain `Decimal` remains accepted and unchanged;
- non-Decimal generic type arguments remain current behavior unless a Slice 2
  diagnostic policy explicitly closes them;
- type aliases preserve declared and canonical type facts;
- expression typing and aggregate typing continue to use logical Decimal
  compatibility unless a later slice explicitly adds precision propagation;
- SQL renderers keep rendering expressions from existing IR without
  `DECIMAL(p, s)` or `NUMERIC(p, s)` output;
- public JSON schemas keep their current field sets.

The MVP explicitly excludes:

- Decimal literal typing;
- full numeric promotion matrix;
- Float/Decimal mixing behavior beyond preserving current fail-closed posture;
- Decimal multiplication or division expansion except boundary tests;
- cast syntax;
- SQL DDL/native type output;
- public JSON schema expansion;
- Semantic Metadata Artifact v1 schema expansion;
- relationship/JOIN behavior;
- project/multi-file behavior;
- runtime/database execution;
- package version, workflow, tag, release, publish/upload, signing, or
  attestation changes.

## Deferred Inventory Impact

Phase 41 touches only Decimal precision-scale type metadata ownership. Related
deferred items have these dispositions:

| Item | Phase 41 disposition | Prerequisite / owner |
|---|---|---|
| Decimal precision-scale carrier | Implement in Phase 41 after Slice 1 scope lock. | Slice 2 semantic validation and approved carrier ownership. |
| Invalid Decimal precision-scale diagnostics | Implement in Phase 41 fail-closed. | Slice 2 diagnostic policy. |
| Plain `Decimal` | Unaffected. | Existing behavior must remain byte and type compatible. |
| Decimal aggregate precision propagation | Still deferred. | Later precision propagation phase after internal carrier is stable. |
| Decimal literals | Explicitly rejected in Phase 41. | Phase 42 numeric/literal work. |
| Full Int/Float/Decimal promotion matrix | Explicitly rejected in Phase 41. | Phase 42 numeric promotion work. |
| Decimal `*` and `/` | Still deferred. | Later numeric operator matrix expansion. |
| SQL `DECIMAL(p, s)` / native DB metadata / DDL | Still deferred. | Later native database metadata and dialect contract. |
| Public JSON precision-scale fields | Explicitly rejected in Phase 41. | Future schema-versioned output contract. |
| Broad aggregate features | Unaffected. | Future aggregate phases with separate approval. |

## Phase 41 Slice Sequence

| Slice | Name | Slice posture |
|---:|---|---|
| 1 | Candidate Decision And Scope Lock | docs/plan/static-audit/tests-only; no behavior change |
| 2 | Decimal Precision-Scale Semantic Validation | semantic validation and fail-closed diagnostics for `Decimal(p, s)` |
| 3 | Internal Type Carrier MVP | private/internal precision-scale type facts while preserving plain `Decimal` |
| 4 | IR Compatibility Carrier Boundary | preserve SQL compatibility and only pass internal facts where explicitly approved |
| 5 | Aggregate / Numeric Boundary Hardening | prove existing Decimal aggregate and numeric behavior remains stable |
| 6 | Metadata / CLI JSON / Explain Compatibility | prove public JSON and metadata schemas do not expand |
| 7 | Docs, Deferred Register, And Package Smoke Readiness | update approved docs/tests without release or package changes |
| 8 | Completion Audit And Status Lock | final completion audit/status lock only |

Later phases must handle Decimal literals, full numeric promotion, SQL native
type output, public precision-scale metadata fields, native DB metadata,
domain annotations, Money/Currency semantics, and runtime/database behavior.

## Slice 1 Gate 2 Allowlist

Phase 41 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-41-decimal-precision-scale-mvp.md`;
- `tests/test_phase41_decimal_precision_scale_candidate.py`.

No other file is approved. If an existing status doc, deferred register,
static-audit helper, hash-lock, generated file, fixture, golden, package file,
workflow, or release file appears necessary, stop and request a Repair Gate 1
and allowlist expansion.

## Slice 1 Validation Focus

Slice 1 validation should prove:

- the two-file allowlist is the complete changed surface;
- the plan records the trusted Phase 40 handoff;
- the candidate is implementation-oriented, with production beginning in Slice
  2;
- no grammar/generated, production semantic/IR/SQL/metadata/CLI JSON, public
  schema, fixture, golden, example, package, workflow, or release surface is
  changed;
- package version remains `0.1.0`.
