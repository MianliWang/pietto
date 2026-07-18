# Phase 52 — Core Type-System Capability Foundation

## Status And Slice 1 Lifecycle

Phase 52 is the Core Type-System Capability Foundation. Slice 1, Scope Architecture, Authority Boundary, And Active-roadmap Lock, is tests/docs/status-only. Before its separately authorized Gate 3 completion condition, Phase 52 remains UNSTARTED. Gate 2 records architecture and static compatibility evidence only; it neither completes Slice 1 nor starts Phase 52.

Slice 1 is tests/docs/status-only.

## Trusted Phase 51 Baseline And Controlling Recon

The trusted baseline is Phase 51 completion commit `3adf96bbdd4724d19eaa58c05417b3f6b36d9076`, whose parent is `5138d28ee2d0a258076a68a6f98c74ce15a93bf8` and subject is `Complete Phase 51 aggregate grouped output schema audit`. Its natural `CI / push` run `29386923175` completed / success with matching `headSha=3adf96bbdd4724d19eaa58c05417b3f6b36d9076`.

This plan implements the architecture ratified by recovery Gate 1 (`d967fb99c8502da78d9b95ed199e0865220bd63233b90cabf8a5f699c729ec45`), the stopped architecture Gate 1 (`9e8b18083976b868eb3587ec8d5e3c80dd8e18cc6dbf9283c10e8060df226126`), and the handoff recon (`d32127b3fbfac31c5b89d16fba08fdb80ac30559ac233f1ef7fa39c22c0b0de4`). Recovery changes validation procedure only; it does not reopen the architecture, route, authority, lookup, stage, fact-family, lifecycle, or public-contract decisions.

## Phase Identity And Scope Architecture

Phase 52 establishes a private, exact-current read-model architecture for later, separately authorized capability work. Its phase delivery remains `MINIMUM_PRODUCTION_FOUNDATION`, but Slice 1 is only tests/docs/status. It is not a declarative type checker, a second semantic engine, a public capability API, or a behavior migration. Its bounded outputs are plans, scope locks, static audits, and, only in later authorized slices, private evidence facts.

## Read-model-first Authority And Evidence Boundary

Existing procedural semantic validation remains the sole compiler-acceptance authority. Existing declarative catalogs retain only their exact current authority. Phase 52 facts are private, deterministic, exact-current evidence/read models: they describe observed facts without accepting or rejecting expressions or queries.

Facts cannot determine result type or nullability, emit or suppress diagnostics, determine SQL lowering, rescue a backend failure, become project-propagation authority, alter IR, alter CLI JSON v1, alter Semantic Metadata Artifact v1, alter Project JSON v2, or become a public Python API. No declarative-authority cutover occurs in Phase 52. Any future cutover needs a separately authorized gate with behavioral, diagnostic, IR, SQL, and public-contract parity evidence.

## Exact Nine-slice Route

1. Scope Architecture, Authority Boundary, And Active-roadmap Lock
2. Private Capability Key, Disposition, Evidence, And Fact Foundation
3. Fail-closed Lookup And Absent/Unknown/Conflict Semantics
4. Logical Type, Literal, Parameter, And Nullability Inventory
5. Scalar Function And Operator Signature Facts
6. Expression Stage And Clause Capability Facts
7. Aggregate Signature And Algebra Facts
8. Parity, Privacy, Cross-phase Readiness, And Drift Closure
9. Completion Audit And Status Lock

The route is exact: slices are neither reordered, merged, split, nor expanded.

## Slice Objectives Delivery Classes And Ownership

| Slice | Objective | Delivery class | Ownership boundary |
| --- | --- | --- | --- |
| 1 | Scope Architecture, Authority Boundary, And Active-roadmap Lock | tests/docs/status-only | Phase 52 architecture and Reconciliation 2 only |
| 2 | Private Capability Key, Disposition, Evidence, And Fact Foundation | separately gated minimum foundation | private key, disposition, evidence, and private reason-code member selection |
| 3 | Fail-closed Lookup And Absent/Unknown/Conflict Semantics | separately gated minimum foundation | private lookup evidence only |
| 4 | Logical Type, Literal, Parameter, And Nullability Inventory | separately gated minimum foundation | exact-current inventory only |
| 5 | Scalar Function And Operator Signature Facts | separately gated minimum foundation | exact-current scalar/operator facts only |
| 6 | Expression Stage And Clause Capability Facts | separately gated minimum foundation | descriptive stage and clause facts only |
| 7 | Aggregate Signature And Algebra Facts | separately gated minimum foundation | descriptive aggregate facts only |
| 8 | Parity, Privacy, Cross-phase Readiness, And Drift Closure | readiness contract only | parity and public/privacy closure only |
| 9 | Completion Audit And Status Lock | readiness contract only | audit and status lock only |

Each later slice requires its own authorization. No slice owns compiler, backend, public API, or release behavior merely because it documents facts.

## Prerequisites And Phase 53–60 Dependency Handoff

Phase 51 is the trusted predecessor. The planned handoff is: Phase 53 follows Phase 51 and Phase 52; Phase 55 follows Phase 52 and Phase 54; Phase 56 follows Phase 52 and Phase 55; Phase 57 follows Phase 56; Phase 58 follows Phase 51, Phase 55, Phase 56, and Phase 57; Phase 59 follows Phase 49, Phase 55, and Phase 58; Phase 60 requires completed, CI-proven Phases 51–59. Phase 54 retains its deterministic current catalog and legacy flat-project compatibility prerequisite.

Research or contract drafting never satisfies a prerequisite or starts a phase. Phase 53–60 titles, delivery classes, prerequisites, and owner assignments remain unchanged. No owner is added, removed, transferred, or left anonymous by Slice 1.

## Capability Key Evidence And Disposition Vocabulary

Future private evidence uses a capability key, evidence, current-support posture, and independent roadmap disposition. A key identifies the observed question; evidence records exact-current support boundaries; disposition records roadmap ownership. This vocabulary is private and descriptive, not a compiler contract. Concrete private reason-code member vocabulary belongs to Slice 2, and no reason code becomes a public diagnostic or API identifier in Slice 1.

## Lookup Algebra And Fail-closed Semantics

The private lookup algebra is `Found(fact)`, `Absent(key)`, `Unknown(reason)`, and `Conflict(reason, evidence)`. ABSENT is first-class: Absent does not mean unsupported. Unsupported is an evidenced fact. Unknown does not mean Absent, nullable, SQL `NULL`, SQL three-valued truth, or unresolved roadmap ownership.

Conflict retains all evidence, selects no winner, and fails closed. Only a Found record with `SUPPORTED` establishes exact-current support. The algebra is descriptive evidence and does not replace procedural semantic validation.

## Current-support And Roadmap-disposition Orthogonality

Current support is one of `SUPPORTED` or `EXPLICITLY_UNSUPPORTED`. Roadmap disposition is independently `NONE`, `DEFERRED(owner, reason)`, or `OUT_OF_SCOPE(owner, reason)`. Roadmap disposition remains orthogonal to lookup and support. Support does not imply portability; semantic acceptance does not imply backend lowering; and one-dialect backend support does not imply cross-dialect support.

## Logical Type Literal Parameter And Nullability Inventory Boundary

Slice 4 may inventory exact-current logical type, literal, parameter, and nullability evidence. The current builtin registry has source-order `Any`, `Bool`, `Bytes`, `Date`, `Decimal`, `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`. `Enum` is declaration-backed rather than builtin; aliases retain declared identity/canonical expansion; shapes are schema/type definitions rather than scalar builtins; `UNKNOWN` is non-concrete; and `Null` has no canonical scalar fact.

This is evidence only: it creates no new type, literal, cast, coercion, promotion, Decimal fusion, native mapping, broad numeric/comparable/orderable classification, result typing, nullability propagation, parameter behavior, SQL three-valued logic, or diagnostic policy. Unknown remains distinct from nullable and SQL `NULL`.

## Scalar Function And Operator Signature Boundary

Slice 5 may record exact-current scalar function and operator signature evidence. `FunctionSignatureFact` covers exact current scalar functions only. `OperatorSignatureFact` covers unary operators, binary operators, comparisons, and null tests. These facts do not implement overload resolution, select an operator result, accept a call, or alter diagnostics or lowering.

## Expression Stage And Clause Capability Boundary

The exact private stage vocabulary is `CONSTANT`, `ROW`, `GROUP`, `WINDOW`, and `UNKNOWN`. `WINDOW` is reserved for Phase 53 and Phase 52 assigns WINDOW to no current expression. Global aggregate expressions are `GROUP`; keyed aggregate expressions are `GROUP`. Relation identity, cardinality, grain, `ProjectRowResultRole`, and project row-schema availability are not expression stages. Observed stage is distinct from clause-required stage, and stage evidence does not replace procedural semantic validation.

`ClauseCapabilityFact` may describe `where`, `satisfying`, `order by`, and `group by`, including required stage, required result type, expression-shape restrictions, clause scope, and alias restrictions. It does not change clause acceptance.

## Aggregate Signature And Algebra Boundary

Slice 7 may describe aggregate identity, arity, argument logical types, argument shape, result logical type, result nullability, empty-input algebra, null elimination, GROUP stage, result role, let/group context, and dialect/backend evidence through `AggregateSignatureFact`. That description is not aggregate implementation, semantic authority, IR lowering, SQL lowering, or portability proof.

## Fact-family Separation And Non-overlapping Responsibility

The future private fact families are `CapabilityKey`, `CapabilityDisposition`, `CapabilityLookupResult`, `LogicalTypeCapabilityFact`, `FunctionSignatureFact`, `OperatorSignatureFact`, `ClauseCapabilityFact`, `AggregateSignatureFact`, and `ExpressionStageFact`. Their responsibilities are non-overlapping: key/disposition/lookup manage identity and evidence outcome; logical-type facts record inventory; function/operator facts record signatures; clause facts record context requirements; aggregate facts record aggregate algebra; and `ExpressionStageFact` records descriptive private stage evidence only. No family performs constraint solving or becomes acceptance authority.

## Current Conflict Ledger And Uncertainty Boundary

The exact current evidence-only conflict ledger has eight entries:

1. `count(alias/Shape)`.
2. semantic `LIKE` versus PostgreSQL/private MySQL lowering.
3. `matches(Text, Text)` across PostgreSQL and private MySQL.
4. non-Decimal type arguments accepted by grammar/AST but not generally consumed semantically.
5. division `/` without a concrete semantic result rule.
6. null literal versus unresolved-expression unknown carriers.
7. generic comparison outer `Bool UNKNOWN` versus pairwise compatibility.
8. no-GROUP global aggregate post-filtering versus `satisfying`'s `GROUP BY` requirement.

The ledger is evidence only: it changes no behavior, repairs no issue, chooses no winner, claims no portability, adds no diagnostic, adds no new deferred owner without existing roadmap authority, and fails closed.

## Solver-readiness Without A Solver

Phase 52 organizes evidence so later design can distinguish facts from authority. It implements and claims no stage solver, inference variables, unification, typeclasses, traits, generic overload resolution, row polymorphism, grain lattice, shadow solver, or authoritative typed IR.

## Public Privacy And Compatibility Boundary

All Phase 52 capability facts remain private and unserialized unless a future, separately authorized public contract says otherwise. Slice 1 changes no CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2, public Python API, diagnostic envelope, project output, or compatibility promise. Phase 58 remains the separately authorized owner of any new public projection family.

## No-behavior And Protected Surface Boundary

Slice 1 creates no production capability carrier and no compiler, semantic, diagnostic, IR, SQL, CLI, JSON, public API, runtime, database, package, dependency, release, or backend behavior. It does not modify production source, grammar, generated artifacts, parser, AST, fixtures, goldens, examples, scripts, workflows, package metadata, or lockfiles.

## Deferred-owner Boundary

No new deferred owner is created. Existing roadmap owners and out-of-scope charter boundaries remain controlling. A fact that is unknown, unsupported, or in conflict does not create anonymous ownership and does not authorize implementation. Residual type work remains `POST60_ADVANCED_TYPE_NATIVE_MAPPING`; window work remains Phase 53; modules Phase 54; package assets Phase 55; profiles Phase 56; extension catalogs Phase 57; public projection Phase 58; provenance/graph Phase 59; and audit Phase 60.

## Active-roadmap Reconciliation 2 Contract

Reconciliation 2 is one EOF-only H3 append to the active roadmap. The exact pre-append file, including its final newline, remains a byte-exact prefix with SHA-256 `b05e57e27afb232b897e7bcec911d8f756beed204a1d0798380b7a510b9a4f80`. Reconciliation 1 remains unchanged as its direct predecessor. The append records the exact route, authority, lookup, stage, fact-family, conflict, and lifecycle boundaries without editing historical route, owner, or status text.

## Slice 1 Exact Gate 2 Scope And Allowlist

Gate 2 may change exactly these ten paths:

1. `docs/plan/phase-52-core-type-system-capability-foundation.md`
2. `docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md`
3. `tests/test_phase52_core_type_system_capability_foundation_scope_lock.py`
4. `docs/spec/pietto-active-roadmap-phase51-60-v1.md`
5. `tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py`
6. `tests/test_phase51_aggregate_only_project_row_schema.py`
7. `tests/test_phase51_grouped_aggregate_project_row_schema.py`
8. `tests/test_phase51_selected_let_accepted_expression_aggregate.py`
9. `tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py`
10. `tests/test_phase51_completion_audit_and_status_lock.py`

The first three are new; the remaining seven are bounded status or direct compatibility migrations. No other repository path may change.

## Gate Workflow And Completion Conditions

Gate 1 is read-only planning. Gate 2 is bounded implementation and evidence, with no stage, commit, push, or CI operation. Gate 3, if separately authorized, is the sole publish and natural-CI observation gate. Slice 1 completes only after its exact completion commit is normally pushed to `main` and its natural CI / push run is completed / success with matching `headSha`. No post-CI status flip commit is planned or required.

### Slice 9 Gate 2 Bounded Implementation Status

Slices 1–8 are complete and natural-CI proven. Slice 9 is the current, incomplete completion-audit slice; Phase 52 remains ACTIVE and incomplete, and Phases 53–60 remain UNSTARTED. Gate 2 is the exact static-only `A2/M7/D0` implementation defined by `docs/spec/phase52-completion-audit-and-status-lock-v1.md`. It changes no production source, capability fact, vocabulary, compiler consumer, public API, runtime behavior, or Phase 53 implementation.

Slice 9 and Phase 52 complete only after the exact single Slice 9 completion commit is normally pushed to `main` and its unique natural `CI / push / main`, attempt 1, is `completed / success` with an exactly matching `headSha`. After and only after that condition, Phase 52 is `COMPLETED`; Phases 53–60 remain `UNSTARTED`; Phase 53 is the next planned phase but is not automatically ACTIVE. No post-CI repository status-flip commit is planned or required. The repository-standard next handoff is `Phase 53 Slice 1 Gate 0 and Gate 1`.

## Validation And Evidence Workflow

Gate 2 uses one bounded write-mode Ruff format pass on the seven allowlisted Python paths, then `uv lock --check`, repository Ruff format/lint checks, production and test Pyright, Tier 1 focused pytest, and the controlling exact 114-node deselected dirty-worktree broad matrix. Tier 1 expects 18 passed / 0 deselected; Tier 2 expects 5648 passed / 114 deselected. It records raw output in `/tmp/pietto-phase52-slice1-gate2-evidence-and-diff.txt`. A clean unfiltered suite, `scripts/validate.py`, generated checks, golden checks, and package smoke remain reserved for natural Gate 3 CI.

## Package Version And Release Boundary

Package version remains `0.1.0`. Slice 1 authorizes no dependency, lockfile, package metadata, version, tag, release, publish, upload, signing, attestation, or CI operation. It does not make a package or release claim.

## Stop Conditions

Stop and return to a separately authorized read-only gate if a controlling identity or trusted baseline mismatches; any path outside the ten-path allowlist changes; production behavior is needed; route, authority, lookup, or stage ambiguity appears; compiler or `_project` boundary digests change; package/tag state changes; or a broad bypass, global migration, stage, commit, push, or CI operation would be required.
