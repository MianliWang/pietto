# Phase 52 Slice 1 Core Type-System Capability Foundation Scope Lock v1

## Purpose And Slice Identity

This contract locks Phase 52 Slice 1, Scope Architecture, Authority Boundary, And Active-roadmap Lock. Phase 52 is Core Type-System Capability Foundation. Slice 1 is tests/docs/status-only and does not create a production carrier, complete the slice, or start the phase.

## Trusted Baseline And Controlling Recon

The trusted `main` / `origin/main` baseline is commit `3adf96bbdd4724d19eaa58c05417b3f6b36d9076`, parent `5138d28ee2d0a258076a68a6f98c74ce15a93bf8`, subject `Complete Phase 51 aggregate grouped output schema audit`. Natural `CI / push` run `29386923175` was `completed / success` with `headSha` exactly `3adf96bbdd4724d19eaa58c05417b3f6b36d9076`.

This contract is controlled by recovery Gate 1 SHA-256 `d967fb99c8502da78d9b95ed199e0865220bd63233b90cabf8a5f699c729ec45`, the stopped architecture Gate 1 SHA-256 `9e8b18083976b868eb3587ec8d5e3c80dd8e18cc6dbf9283c10e8060df226126`, and handoff recon SHA-256 `d32127b3fbfac31c5b89d16fba08fdb80ac30559ac233f1ef7fa39c22c0b0de4`. At Gate 2, Phase 51 is completed and Phases 52–60 are unstarted.

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

This route is exact and is neither reordered, merged, split, nor expanded.

## Read-model-first Authority Contract

Existing semantic procedures remain the sole compiler-acceptance authority. Existing declarative catalogs retain only their exact current authority. Phase 52 facts are private, deterministic, exact-current evidence/read models. They describe evidence; they do not make declarative acceptance authoritative. No declarative-authority cutover occurs in Phase 52. A later cutover requires a separately authorized gate and behavioral, diagnostic, IR, SQL, and public-contract parity evidence.

## Authority Dimensions And Non-authority Guarantees

The separate authority dimensions are semantic acceptance, result type, nullability, diagnostics, backend lowering, project propagation, dialect evidence, public projection, expression-stage evidence, and conflict/evidence precedence.

Facts cannot accept or reject expressions or queries; determine result type or nullability; emit or suppress a diagnostic; determine SQL lowering; rescue a backend failure; become project-propagation authority; alter IR; alter CLI JSON v1, Semantic Metadata Artifact v1, or Project JSON v2; or become a public Python API. Evidence does not replace procedural semantic validation.

## Lookup Algebra Contract

The only private lookup result forms are `Found(fact)`, `Absent(key)`, `Unknown(reason)`, and `Conflict(reason, evidence)`. ABSENT is first-class: Absent does not mean unsupported. Unsupported is an evidenced fact. Unknown does not mean Absent, nullable, SQL `NULL`, SQL three-valued truth, or unresolved roadmap ownership. Conflict retains all evidence, selects no winner, and fails closed.

## Current-support And Roadmap-disposition Contract

Current support is `SUPPORTED` or `EXPLICITLY_UNSUPPORTED`. Roadmap disposition is independently `NONE`, `DEFERRED(owner, reason)`, or `OUT_OF_SCOPE(owner, reason)`. Only Found plus SUPPORTED records exact-current support. Support does not imply portability; semantic acceptance does not imply backend lowering; one-dialect backend support does not imply cross-dialect support; and roadmap disposition remains orthogonal to lookup and support.

## Private Reason-code Vocabulary Assignment

Slice 2 exclusively selects the bounded private reason-code member vocabulary. Slice 1 selects no member. No reason-code member is a public diagnostic or API identifier in Slice 1.

## Expression Stage Contract

The exact private stages are `CONSTANT`, `ROW`, `GROUP`, `WINDOW`, and `UNKNOWN`. WINDOW is reserved for Phase 53 and is assigned to no current Phase 52 expression. Global aggregate expressions are GROUP and keyed aggregate expressions are GROUP. Relation identity, cardinality, grain, `ProjectRowResultRole`, and project row-schema availability are not expression stages. Observed stage is distinct from clause-required stage. Stage evidence does not replace procedural semantic validation.

## Fact-family Responsibility Contract

The future private families are `CapabilityKey`, `CapabilityDisposition`, `CapabilityLookupResult`, `LogicalTypeCapabilityFact`, `FunctionSignatureFact`, `OperatorSignatureFact`, `ClauseCapabilityFact`, `AggregateSignatureFact`, and `ExpressionStageFact`. Their responsibilities do not overlap.

`FunctionSignatureFact` records exact current scalar functions only. `OperatorSignatureFact` records unary operators, binary operators, comparisons, and null tests. `ClauseCapabilityFact` records `where`, `satisfying`, `order by`, `group by`, required stage, required result type, expression-shape restrictions, clause scope, and alias restrictions. `AggregateSignatureFact` records aggregate identity, arity, argument logical types, argument shape, result logical type, result nullability, empty-input algebra, null elimination, GROUP stage, result role, let/group context, and dialect/backend evidence. `ExpressionStageFact` is descriptive private evidence only and performs no constraint solving. Slice 1 creates none of these carriers.

## Current Conflict Ledger Contract

The exact ledger is evidence only and has exactly eight entries:

1. `count(alias/Shape)`.
2. semantic `LIKE` versus PostgreSQL/private MySQL lowering.
3. `matches(Text, Text)` across PostgreSQL and private MySQL.
4. non-Decimal type arguments accepted by grammar/AST but not generally consumed semantically.
5. division `/` without a concrete semantic result rule.
6. null literal versus unresolved-expression unknown carriers.
7. generic comparison outer `Bool UNKNOWN` versus pairwise compatibility.
8. no-GROUP global aggregate post-filtering versus `satisfying`'s `GROUP BY` requirement.

The ledger changes no behavior, repairs no issue, chooses no winner, claims no portability, adds no diagnostic, adds no new deferred owner without existing roadmap authority, and fails closed.

## Solver-readiness Non-implementation Contract

Phase 52 implements and claims no stage solver, inference variables, unification, typeclasses, traits, generic overload resolution, row polymorphism, grain lattice, shadow solver, or authoritative typed IR.

## Slice 1 Tests Docs Status-only Contract

Slice 1 is tests/docs/status-only. Its Gate 2 work is bounded documentation, one focused static test, the active-roadmap append, and exact direct compatibility migration. It does not authorize production implementation or a lifecycle preclaim.

## No Production Carrier And No Compiler Behavior Contract

Slice 1 creates no production carrier and no compiler behavior. It does not change grammar, generated files, parser, AST, semantic acceptance, result type, nullability, literals, parameters, casts, coercion, promotion, type classifications, or diagnostics.

## IR SQL Diagnostic CLI And Runtime Non-change Contract

Slice 1 does not change IR, SQL, diagnostic behavior, CLI, JSON, runtime, database behavior, backend behavior, project propagation, or project production files.

## Public Artifact Privacy And API Contract

Facts remain private and unserialized. Slice 1 changes no public Python API, CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2, public diagnostic envelope, or public output. Any public projection requires Phase 58's separately authorized and independently versioned artifact family.

## Compiler Project Package And Release Lock Contract

The compiler boundary remains 75 static inputs with digest `2ed54ba89c64c89d9d9bfc26f83041faf0addb335f086bd2e75dc2a567be775c`, and all eight `BOUNDARY_HASH` values remain that digest. The `_project` boundary remains 16 static inputs with digest `c032a23c7f0477df58cacc9374e2882bebad346bec9a539899878da062248013`; the Phase 33 project_private lock remains exact. Package version remains `0.1.0`. Slice 1 changes no compiler/project source, dependency, workflow, package metadata, version, tag, release, publish, upload, signing, attestation, or CI operation.

## Active-roadmap Reconciliation 2 Append-only Contract

Reconciliation 1 is unchanged and is the direct predecessor. The active roadmap complete pre-Reconciliation-2 bytes, including final newline, remain an exact prefix with SHA-256 `b05e57e27afb232b897e7bcec911d8f756beed204a1d0798380b7a510b9a4f80`. Reconciliation 2 is exactly one EOF H3 append; no later heading or text may follow it. It does not edit an existing route row, owner row, title, prerequisite, or historical lifecycle wording.

## Post-CI Lifecycle And Next-slice Contract

Before the Slice 1 Gate 3 condition, Phase 52 remains UNSTARTED. After and only after the exact Slice 1 completion commit receives one normal push to main and its natural CI / push run is completed / success with headSha exactly equal to that commit, Phase 52 becomes ACTIVE and remains incomplete; Slice 1 is complete; Slices 2–9 and Phases 53–60 remain UNSTARTED. No post-CI repository status-flip commit is planned or required. The next separately authorized gate is Phase 52 Slice 2 Gate 0 and Gate 1.

## Exact Gate 2 Allowlist And Compatibility Migration

Only these ten paths may change:

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

The compatibility migrations preserve all historical Phase 51 constants and locks. They add exact Phase 52 dirty/untracked alternatives only; remove the active-roadmap protected-diff entry only from aggregate-only and selected-let; and remove only the active-roadmap plus the Phase 51 scope-lock test protected-diff entries from grouped aggregate. No broad migration or bypass is permitted.

## Validation Evidence And Gate 3 Handoff

Gate 2 uses bounded Ruff formatting, `uv lock --check`, Ruff format/lint, production/test Pyright, Tier 1 focused pytest (18 passed / 0 deselected), and the exact Tier 2 dirty-worktree broad matrix (5648 passed / 114 deselected). Gate 2 does not run a clean unfiltered suite, `scripts/validate.py`, generated checks, golden checks, or package smoke; those remain required in clean natural Gate 3 CI. Gate 2 performs no stage, commit, push, or CI operation.

## Stop Conditions

Stop if a control identity or baseline mismatches; a path outside the exact allowlist changes; behavior implementation is needed; authority/lookup/stage/route ambiguity appears; a non-routine functional failure occurs; the mandated validation policy cannot be followed; compiler or `_project` boundaries change; package/tag/release state changes; or a broad compatibility bypass would be required.

