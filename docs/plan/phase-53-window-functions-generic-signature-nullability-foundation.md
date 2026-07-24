# Phase 53 — Window Functions, Generic Signature Compatibility, And Nullability Foundation

## Status And Slice 1 Lifecycle

Phase 52 is `COMPLETED` at the trusted baseline. Phase 53 is `UNSTARTED` throughout Slice 1 Gate 2. Slice 1 is static tests/docs/roadmap persistence only: it records authority, compatibility, ownership, validation, publication, and STOP boundaries, but it neither starts Phase 53 nor implements any Phase 53 behavior.

Gate 2 may leave the exact authorized result uncommitted and unstaged. Phase 53 becomes `ACTIVE` only after a separately authorized `Phase 53 Slice 1 Gate 3` stages exactly that result, creates exactly one commit, performs exactly one normal push to `main`, and observes the unique natural `CI / push / main` attempt 1 complete successfully with `headSha` exactly equal to that commit. No post-CI status-flip commit is planned or required. Persistence of this plan or either roadmap is not phase activation and grants no automatic implementation authority to Slice 2 or any later slice.

## Trusted Phase 52 Baseline And Controlling Evidence

The trusted `main` / `origin/main` baseline is commit `b8029699ccc51bfa500856155b18e666898cb883`, parent `36e466535d923f708a0201ae15a5708f06f2b1f8`, tree `dc7686d7afcfb00cd41f72d2f7fb69f245edf3c5`, and subject `Complete Phase 52 core type system capability foundation`. Natural `CI / push / main` run `29642838835`, attempt 1, completed successfully with matching `headSha=b8029699ccc51bfa500856155b18e666898cb883`; both Python 3.12 and 3.13 jobs reported `6167 passed`, generated inventory 8, goldens 37, package smoke PASS, and installed CLI `pietto 0.1.0` from depth-one checkouts.

The controlling evidence chain is the Phase 53 grounding audit, the first Gate 0/Gate 1 STOP report, the revised Gate 0/Gate 1 STOP report, and the conditional validation-closure and Gate 2 authority. The later authority corrects validation closure without reopening the already approved Phase 53–70 product, release, or Rust direction. Live repository facts remain authoritative when they can drift.

## Phase Identity And Product Scope

Phase 53 owns a bounded Pietto-native window-function production foundation plus the generic signature-compatibility and symbolic nullability foundations required to express that behavior deterministically. Its exact window inventory is `row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile`, `lag`, and `lead`.

The phase is not a general SQL window implementation. Phase 53 excludes frames, named windows and inheritance, aggregate-as-window behavior, `first_value`, `last_value`, `nth_value`, `QUALIFY`, same-select window dependencies, nested window calls, and window use in filter, grouping, aggregate arguments, or `satisfying`. Phase 60 owns advanced windows and Phase 63 owns `QUALIFY` lowering. Slice 1 itself is static-only and changes none of the phase's future compiler behavior.

## Exact Sixteen-slice Route

1. Scope, Authority, Phase 53–70 Roadmap, Global Window Keyword, And Activation
2. Pietto-native Window Syntax And Contextual Grammar Contract
3. WindowSpec, Extension-compatible WindowFunctionIdentity, And AST Contract
4. Generic Type-variable, Constraint, And Exact Compatibility Foundation
5. Nullability Algebra And Signature Result-formula Foundation
6. Private Window Semantic Carrier, WINDOW Stage, Dependency, And Result Roles
7. row_number Direct-field MVP
8. rank / dense_rank And Peer Semantics
9. percent_rank / cume_dist / ntile
10. Partition Binding, Multi-key Visibility, And Diagnostics
11. Window-local Ordering, Direction, Mandatory-order Policy, And Determinism
12. Generic lag / lead Navigation MVP
13. Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let Visibility
14. Multiple Window Outputs, Final-order Alias, Downstream Schema, And Lineage
15. Window IR, PostgreSQL/private-MySQL Lowering, WINDOW_FUNCTION Facts, And Phase 54–70 Readiness
16. Completion Audit, Status Lock, Dialect, Privacy, And No-authority Closure

This route is exact. Slices are not reordered, merged, split, widened, or automatically authorized by recording them here.

## Slice Objectives Delivery Classes And Ownership

| Slice | Objective | Delivery class | Ownership boundary |
| --- | --- | --- | --- |
| 1 | Scope, Authority, Phase 53–70 Roadmap, Global Window Keyword, And Activation | static tests/docs/roadmap only | authority, route, keyword policy, compatibility, and activation; no behavior |
| 2 | Pietto-native Window Syntax And Contextual Grammar Contract | separately gated bounded grammar foundation | source syntax, contextual grammar, generated artifacts, and parser compatibility |
| 3 | WindowSpec, Extension-compatible WindowFunctionIdentity, And AST Contract | separately gated compiler foundation | immutable AST preservation and private identity shape |
| 4 | Generic Type-variable, Constraint, And Exact Compatibility Foundation | separately gated semantic foundation | private exact binding and ordered overload compatibility only |
| 5 | Nullability Algebra And Signature Result-formula Foundation | separately gated semantic foundation | private symbolic formulas and deterministic evaluation only |
| 6 | Private Window Semantic Carrier, WINDOW Stage, Dependency, And Result Roles | separately gated semantic/project foundation | private legality carriers, stage, dependency, provenance, and result role |
| 7 | row_number Direct-field MVP | separately gated bounded behavior | first ranking function over the approved direct-field subset |
| 8 | rank / dense_rank And Peer Semantics | separately gated bounded behavior | peer-aware ranking semantics |
| 9 | percent_rank / cume_dist / ntile | separately gated bounded behavior | distribution and bucket functions only |
| 10 | Partition Binding, Multi-key Visibility, And Diagnostics | separately gated bounded behavior | partition binding and deterministic diagnostics |
| 11 | Window-local Ordering, Direction, Mandatory-order Policy, And Determinism | separately gated bounded behavior | local order, `asc`/`desc`, and deterministic ordering policy |
| 12 | Generic lag / lead Navigation MVP | separately gated bounded behavior | exact generic navigation subset and nullability formulas |
| 13 | Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let Visibility | separately gated bounded behavior | approved GROUP-to-WINDOW inputs only |
| 14 | Multiple Window Outputs, Final-order Alias, Downstream Schema, And Lineage | separately gated bounded behavior | independent outputs, compatible aliases, and private propagation |
| 15 | Window IR, PostgreSQL/private-MySQL Lowering, WINDOW_FUNCTION Facts, And Phase 54–70 Readiness | separately gated compiler/backend foundation | canonical IR and independently proven backend lowering |
| 16 | Completion Audit, Status Lock, Dialect, Privacy, And No-authority Closure | static completion audit | exact completion evidence and unchanged authority boundaries |

Each later slice needs its own Gate 0/Gate 1 authority. Catalog presence, AST preservation, capability evidence, or one backend's lowering does not authorize compiler acceptance, another backend, or a public projection.

## Phase 54–70 Dependency And Readiness Handoff

- Phase 54: Local Import / Module / Export Foundation.
- Phase 55: Semantic Package Asset Schema And Deterministic Local Loading.
- Phase 56: Capability Profile Static Schema And Declared Checking.
- Phase 57: PostgreSQL Extension Signature Catalog Foundation.
- Phase 58: Public Explain / Portability / Package Inspection Artifact v1.
- Phase 59: Local Package Graph, Attribution, Provenance, And Lineage.
- Phase 60: Advanced Window Frames And Phase 51–60 Ecosystem / Release Readiness Checkpoint.
- Phase 61: Project IR And Semantic Composition Foundation.
- Phase 62: Relationship, JOIN, Grain, And Fanout-safe Semantics.
- Phase 63: Multi-relation SQL Artifacts, Project Emit-SQL, And QUALIFY Lowering.
- Phase 64: Advanced Generic Types, Coercion, Temporal, Decimal, And Native Mapping.
- Phase 65: Advanced Aggregation And Grouping.
- Phase 66: Advanced Module And Semantic-package Assets.
- Phase 67: Remote Package Manager, Registry, Fetch, Install, Cache, And Trust Boundary.
- Phase 68: Dependency Ranges, Version Solver, Canonical Lockfile, And First Rust Kernel.
- Phase 69: Extension-specific Lowering And Additional Dialect Backend Foundation.
- Phase 70: Public Schema / Lineage / Attribution Expansion, Ecosystem Completion Audit, Rust Migration Decision, And v0.2 Release Readiness.

The route preserves unique ownership. Phase 53 hands stable window identities, generic binding, nullability formulas, stage/dependency facts, IR, and backend evidence forward only after their owning slices complete. Phase 54–59 retain their established prerequisites. Phase 60 is a bounded advanced-window production phase plus checkpoint, not a release action. Phases 61–70 own the exhaustively reconciled post-60 work and do not inherit automatic implementation authority from this plan.

## Window Syntax Identity And Global Keyword Policy

The exact lowercase `window` source spelling is a future globally reserved grammar keyword. Slice 1 records that policy only; Slice 2 owns the separately authorized grammar and generated-source migration. There is no grammar change in Slice 1. Under the current case-sensitive lexer, `Window` and `WINDOW` remain identifiers unless a later explicit case-policy gate changes that result.

`over`, `partition`, direction words, and future frame words remain contextual where practical. The eight function names remain identifiers resolved through a private semantic catalog, not grammar keywords. Pietto uses an inline unnamed `WindowSpec` compatible with its colon-and-indentation language style while leaving named-window ownership to Phase 60. Slice 1 adds no token, grammar rule, diagnostic code, parser behavior, generated artifact, fixture, or golden.

The planned global reservation is a disclosed compatibility change: a previously accepted external lowercase identifier named `window` will become a parse error when Slice 2 is separately authorized. There is no tracked positive fixture or golden requiring migration. Slice 2 must add exact positive-before/negative-after compatibility evidence and preserve the existing unsupported-clause coverage.

## Function Inventory And Behavioral Boundary

The private extension-compatible identity shape is equivalent to `WindowFunctionIdentity(namespace, name, role)`. Builtins occupy a stable builtin namespace, preserve their exact source spelling, and carry the explicit window-function role. The exact ordered identities are:

1. `row_number`
2. `rank`
3. `dense_rank`
4. `percent_rank`
5. `cume_dist`
6. `ntile`
7. `lag`
8. `lead`

The bounded phase behavior requires an explicit output alias, optional partition keys, mandatory window-local ordering unless a later slice proves an exact exception, `asc` and `desc`, grouped-result keys and aggregate-result inputs in the approved slice, multiple independent outputs, ordinary downstream derived fields, and compatible final-order aliases. It forbids same-select window dependencies, nesting, window calls in `where`, `group by`, aggregate arguments, or `satisfying`, aggregate-as-window use, frames, named windows, and `QUALIFY`.

Function identity is not signature legality. Catalog membership is not semantic acceptance, result typing, nullability, diagnostic selection, IR lowering, SQL lowering, portability, extension installation, or public exposure.

## Private Catalog And Compiler-authority Boundary

Existing procedural semantic validation remains compiler-acceptance authority until a separately authorized behavior slice changes an exact path with parity evidence. Phase 52 capability facts and lookup remain private, immutable, deterministic, descriptive evidence. `Found` plus `SUPPORTED` does not by itself accept a call, and `Absent`, `Unknown`, or `Conflict` cannot be converted into permissive behavior.

Future Phase 53 carriers and catalogs remain private unless an independently versioned public contract is later authorized. Parser recognition, AST preservation, catalog identity, semantic legality, project dependency/lineage, IR canonicalization, PostgreSQL lowering, private-MySQL lowering, and public artifact projection are separate authorities. No stage may infer another stage's support.

## Generic Compatibility Foundation

The bounded private foundation uses explicit type variables such as `T`; exact same-type binding; only evidence-backed `Scalar`, `Comparable`, `Orderable`, and `Numeric` constraint tags; binding-referenced results; optional arguments; immutable ordered overload tuples; deterministic ordered overload selection; a unique exact match; and a fail-closed ambiguity result.

It performs no implicit coercion, no LUB search, promotion, common-supertype or least-upper-bound search, typeclass/trait inference, row polymorphism, Decimal precision fusion, temporal conversion, backend-native mapping, or legality inference from descriptive capability lookup. Argument positions, variable occurrences, constraint membership, and result references must be validated at carrier construction and evaluated in deterministic order. No set or mapping iteration may decide an overload winner.

## Nullability Formula Foundation

Symbolic signature nullability is a distinct private formula tree. It does not mutate or overload the existing concrete `EffectiveNullability` states. The exact ordered formula inventory is:

1. `NON_NULL`
2. `NULLABLE`
3. `SAME_AS_ARG(i)`
4. `ANY_NULLABLE(args)`
5. `ALWAYS_NULLABLE`
6. `NULLABLE_IF_DEFAULT_OMITTED`
7. bounded deterministic Boolean composition

Construction validates every argument index and formula shape. Evaluation consumes ordered argument facts, preserves unknown rather than treating it as nullable or SQL `NULL`, and fails closed on malformed or unsupported forms. `lag` and `lead` may later express input- and default-dependent results through these formulas without changing existing public semantic carriers.

## Phase 64 Exclusion Boundary

Phase 64 remains the sole owner of promotion, coercion, common-supertype and least-upper-bound search, temporal coercion, DateTime/Time/Interval expansion, Decimal precision fusion and overflow/rounding formulas, `Money/Currency/units`, domains, refinements, and backend-native mapping. Phase 53 cannot claim these behaviors through a generic constraint, overload row, nullability formula, capability fact, or backend implementation.

Exact same-type compatibility in Phase 53 is not a partial implementation of Phase 64. Evidence-backed `Scalar`, `Comparable`, `Orderable`, and `Numeric` tags are bounded private constraints, not a general trait system or final cross-type compatibility matrix.

## Window Stage Dependency Result-role And Lineage Boundary

Phase 52 reserves private expression stage `WINDOW` but assigns it to no current expression. Phase 53 Slice 6 later owns an explicit private window semantic carrier, assignment of legal window expressions to `WINDOW`, and a distinct `WINDOW_RESULT` project result role. Relation identity, cardinality, grain, row-schema availability, GROUP results, and final query ordering remain distinct concepts.

Later authorized slices preserve argument, partition, window-order, relation-input, derived-origin, and result-role dependencies. They must keep same-select window dependencies and nesting fail-closed, preserve source order, use stable serialized occurrence identities at cross-language boundaries, and distinguish concrete, unknown, deferred, and blocked project-schema states. Slice 1 creates or changes none of these carriers or facts.

## PostgreSQL And Private-MySQL Evidence Boundary

PostgreSQL and private MySQL require separate fail-closed semantic, IR, rendering, diagnostic, and byte evidence. PostgreSQL support cannot establish private-MySQL support; private-MySQL support cannot establish PostgreSQL support; semantic acceptance cannot establish either backend; and catalog identity cannot rescue a backend failure.

Slice 15 owns any approved Window IR and backend lowering. It must preserve dialect-specific evidence, deterministic SQL bytes, explicit unsupported diagnostics, and the private status of the MySQL entrypoint. Slice 1 changes no IR, SQL renderer, fixture, golden, public SQL API, or dialect claim.

## Public Privacy Compatibility And No-behavior Boundary

Slice 1 changes no grammar, generated source, parser, AST, semantic implementation, capability fact, project carrier, dependency or lineage implementation, IR, PostgreSQL/private-MySQL SQL, diagnostic behavior, CLI, CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2, public Python API, runtime, database behavior, source fixture, golden, example, script, workflow, package metadata, dependency, lockfile, version, tag, release, signing, attestation, or Rust implementation.

All Phase 53 design carriers remain private unless a later explicit public contract says otherwise. Phase 58 owns its minimal public projection family and Phase 70 owns broader public schema, lineage, and attribution expansion. Neither owner is preempted by Slice 1.

## Active-roadmap Reconciliation 4 Contract

`docs/spec/pietto-roadmap-phase45-60-v1.md` remains byte-identical historical authority. The first 41,661 bytes of `docs/spec/pietto-active-roadmap-phase51-60-v1.md`, including the prior final newline, remain an exact prefix. Reconciliations 1–3 remain byte-identical and ordered.

Exactly one EOF H3 is appended: `### Reconciliation 4 — Phase 52 Completion, Phase 53–70 Current-authority Handoff, Release, And Rust Route`. It records Phase 52 completion, Phase 53 remaining `UNSTARTED` during Gate 2, the exact later activation condition, the new sole current roadmap authority, exhaustive POST60 mapping, Phase 60's bounded production/checkpoint role, release and Rust tracks, no public-schema mutation, and no automatic implementation authority.

## Phase 53–70 Current-authority Roadmap Contract

`docs/spec/pietto-active-roadmap-phase53-70-v1.md` is the sole current roadmap authority once persisted. It preserves both predecessor roadmaps as append-only historical evidence, makes the Phase 51–60 active-roadmap lineage immutable after Reconciliation 4, and uniquely owns Phase 53–70 scope, lifecycle, POST60 reconciliation, release, Rust, keyword, compatibility, validation, publication, and STOP boundaries.

New current authority does not rewrite history, activate Phase 53, complete Slice 1, authorize a later slice, or mutate a public schema. Descriptive references in Phase 50–52 remain historical facts where the newer approved ownership explicitly supersedes them.

## Release Train

An optional `TestPyPI/private preview` may be considered only after Phase 58 through a separate authorized workflow. Phase 60 Gate 3 must not tag or publish; it also must not upload, sign, or attest. A separate Release 0.1.0 workflow follows Phase 60.

Release Gate 0/1 owns readiness, license and metadata, support matrix, changelog, version decision, artifact policy, reproducibility, rollback, publication, signing, provenance, and SBOM planning. Release Gate 2 owns exact authorized version/changelog edits, reproducible sdist/wheel creation, installed smoke, clean-environment validation, hashes, and any explicitly authorized TestPyPI action, but no production publication. Release Gate 3 alone owns any exact release commit, tag, GitHub Release, PyPI publication, signatures, and attestations; it permits no implicit rerun or second publication.

After Phase 70, the target is a v0.2.0 ecosystem beta, not automatic v1.0. Roadmap persistence and Phase 53 Slice 1 Gate 3 are not release gates.

## Rust Migration Track

No big-bang migration is authorized. Phases 53–60 should establish immutable carriers, stable identities and enums, deterministic serialization, explicit procedures, stable AST/IR ownership, exact diagnostics, differential-testable inputs and outputs, no ambient callback registries, and no Python object identity across language boundaries.

`Maintenance Phase 5 — Release Engineering, Performance Baseline, And Rust Migration Readiness` remains after Phase 60. Phase 68 is the preferred first production Rust component. The preferred later order is dependency solver/graph; lineage/dependency algorithms; generic binder/nullability evaluator; IR validation/canonicalization; selected SQL helpers; and parser only after grammar stabilization.

Every migration requires a Python reference implementation or frozen corpus, differential tests, deterministic parity, explicit fallback, independent benchmark evidence, and no silent divergence. Slice 1 adds no `Cargo.toml`, Rust source, PyO3, maturin, native-wheel workflow, FFI/ABI surface, benchmark, or Rust implementation.

## Slice 1 Exact Gate 2 Scope And Allowlist

The exact Gate 2 scope is `A4/M7/D0`.

Added:

1. `docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md`
2. `docs/spec/phase53-window-functions-generic-signature-nullability-scope-lock-v1.md`
3. `docs/spec/pietto-active-roadmap-phase53-70-v1.md`
4. `tests/test_phase53_window_generic_nullability_foundation_scope_lock.py`

Modified:

1. `docs/spec/pietto-active-roadmap-phase51-60-v1.md`
2. `tests/test_phase52_core_type_system_capability_foundation_scope_lock.py`
3. `tests/test_phase52_completion_audit_and_status_lock.py`
4. `tests/test_phase52_aggregate_signature_algebra_facts.py`
5. `tests/test_phase52_expression_stage_clause_capability_facts.py`
6. `tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py`
7. `tests/test_phase52_scalar_function_operator_signature_facts.py`

Deleted: none. The index remains empty throughout Gate 2. No path outside this allowlist may change, and the four added paths remain untracked until a separately authorized Gate 3.

## Gate Workflow Lifecycle And Activation Conditions

Gate 0/Gate 1 is read-only grounding, authority, and validation-closure planning. Gate 2 is bounded implementation and evidence only; it performs no staging, commit, push, CI mutation, tag, release, publication, or activation. A successful Gate 2 leaves exact `A4/M7/D0` uncommitted and unstaged and hands off only to `Phase 53 Slice 1 Gate 3`.

A separately authorized Gate 3 must prove the exact eleven-path staged set, create one repository-conventional commit without amend, perform one normal push to `main`, and observe the unique natural `CI / push / main`, attempt 1, with exact matching `headSha` and `completed / success`. Gate 3 performs no local validation, second push, manual dispatch, rerun, cancel, tag, release, or repair. Natural CI failure stops the gate and hands off to a separate read-only CI Repair Gate 1.

## Validation Evidence And Depth-one CI Workflow

Gate 2 requires exact dirty-state and allowlist proof before validation, then one write-mode Ruff format pass over the exact seven test paths, `uv lock --check`, repository Ruff format-check and lint, production Pyright, test Pyright, exact Tier 1, exact dirty-worktree Tier 2, `git diff --check`, and final diff/index/status/protected-boundary evidence.

The direct authority-reader partition remains exactly 41: active-roadmap readers are `27 = 23 dirty-compatible + 4 clean-only`, and Phase 50 historical readers are `14 = 13 dirty-compatible + 1 clean-only`. The one Phase 50 clean-only node remains `tests/test_phase50_window_function_readiness.py::test_compatibility_guards_protected_surfaces_and_dirty_set_are_locked` and is not placed in dirty Tier 1.

Tier 1 is exactly `111 passed, 0 deselected`: 69 new static items, 23 dirty-compatible active-roadmap readers, 13 dirty-compatible Phase 50 historical readers, and 6 permanently migrated selected inventory readers. Tier 2 is exactly `6090 passed, 146 deselected`. The transformed 140-node base manifest remains byte-identical; the exact external dirty-only overlay remains 146 nodes. Gate 2 does not run unfiltered full pytest, `scripts/validate.py`, generated checks, golden checks, package smoke, builds, imports, generators, benchmarks, or profilers.

Gate 3 requires separate authorization. Its natural depth-one CI is the only clean unfiltered proof. Each Python job must produce exactly `6236 passed` and retain generated count 8, goldens 37, package smoke PASS, and installed CLI `pietto 0.1.0`. The natural run's exact `headSha`, event, branch, attempt, jobs, and conclusion are publication evidence.

## Package Version Release And Publication Boundary

Package version remains `0.1.0`. Slice 1 has no source/runtime behavior, no package metadata, no dependency, no lockfile, no version source, no workflow, no build configuration, no compatibility classifier, no changelog, no license, no artifact, no tag, no release, no publish, no signing, no attestation, no provenance, and no SBOM change.

Gate 3 publishes only the authorized repository commit and observes natural CI. It is not a package release, does not create a tag or Release, and does not authorize any release workflow. Release work remains separately gated under the Release Train.

## Stop Conditions

STOP if a controlling report, repository identity, protected fingerprint, Phase 52 baseline, remote ref, natural-CI identity, package version, tag/release state, historical prefix, heading manifest, phase route, owner mapping, selector identity, reader closure, inventory arithmetic, exact `A4/M7/D0` state, or validation count mismatches.

STOP if any path outside the allowlist changes; the index becomes non-empty; grammar, production source, generated artifacts, public schema, workflow, package, dependency, runtime, release, or Rust implementation becomes necessary; a non-routine functional failure appears; a broad bypass, extra deselection, second formatter, destructive cleanup, staging, commit, push, or GitHub mutation would be required; or Phase 53 activation would be preclaimed. Preserve the exact uncommitted state and hand off through a separately authorized gate.

## Slice 2 Pietto-native Window Syntax And Contextual Grammar Contract

Phase 53 is `ACTIVE`, and Slice 1 is `COMPLETED`. Slice 2 remains `UNSTARTED` throughout Gate 2. Gate 2 owns only the bounded grammar, generated-source, raw-CST, compatibility-reader, deterministic parser-diagnostic, documentation, and minimal fail-closed `AstBuilder` work recorded here. Slice 2 becomes `COMPLETED` only after a separately authorized Gate 3 publishes the exact Gate 2 result and the unique natural `CI / push / main`, attempt 1, succeeds at the exact new `headSha`.

The canonical Pietto-native source spelling is an explicitly aliased direct call followed by an inline unnamed `window:` block:

```pietto
query ranked:
    from rows
    select:
        rn = row_number() window:
            partition by:
                account_id
                region
            order by:
                observed_at desc
                sequence_id
```

Exact lowercase `window` is globally reserved and case-sensitive. `Window` and `WINDOW` remain identifiers. `partition` is tokenized for the bounded `partition by:` subclause and is returned through the compatibility `identifier` rule. `over`, all eight approved window-function names, and future frame vocabulary remain ordinary contextual identifiers. The syntax requires one explicit output alias and binds one `window:` suffix only to a direct `dottedName callSuffix`; it does not attach to literals, parenthesized expressions, binary expressions, nested calls, or unaliased projections.

The inline spec contains an optional nonempty `partition by:` block and an optional nonempty `order by:` block at grammar level, with at least one present. When both occur, partition precedes order, and each occurs at most once. Partition items are generic expressions, one per line. Window-local ordering reuses the existing generic-expression item plus optional `asc` or `desc`. Empty blocks, duplicates, reversed clause order, named windows, frames, `nulls first` / `nulls last`, multiple suffixes, and `qualify` remain rejected or unsupported. Function identity, arity, required-order policy, operand binding, result type, nullability, and stage legality remain later semantic work.

Slice 2 deliberately adds no `WindowSpec` AST carrier. `AstBuilder.visitSelectItem` detects a recognized `windowExpression`, locates the exact `WINDOW` token, and raises the existing `AstBuildError` with `Window syntax is recognized, but WindowSpec AST preservation starts in Phase 53 Slice 3.` The public parser therefore returns one deterministic `PIE-P1000` error rather than silently dropping the window spec or constructing an ordinary `CallExpr`. `src/pietto/parser_api.py` and `src/pietto/ast_nodes.py` remain byte-identical.

The exact Gate 2 repository scope is `A2/M67/D0`: this plan, the grammar, `AstBuilder`, seven generated ANTLR files, 57 compatibility/hash/state readers, plus the new Slice 2 specification and 16-function/70-item parser contract test. The generated inventory remains eight, and `src/pietto/generated/__init__.py` remains byte-identical. Direct and nested grammar/generated/`AstBuilder`/compiler hashes, inventory facts, and repository-state readers migrate without weakening equality or escaping that allowlist.

Future committed inventory is exactly 841 tracked files, 516 Python files, 229 Markdown files, 435 test modules, 4194 top-level test functions, 6306 collected items, 8 generated files, and 37 goldens.

Gate 2 validation is fixed at 146 focused passes from the exact 77-operand selector; `6121 passed, 185 deselected` from the exact dirty broad-suite overlay; generated inventory 8; and a clean-CI projection of 6306 passes per Python job. Gate 2 leaves all 69 paths unstaged and uncommitted with an empty index. It does not stage, commit, push, poll or mutate CI, tag, create a Release or PR, regenerate goldens, run package smoke, or change the package version from `0.1.0`.

This slice adds no semantic catalog, generic binding, nullability formula, WINDOW-stage fact, project result role, dependency or lineage, IR, SQL lowering, public schema, CLI behavior, runtime, database, package, workflow, release, or Rust behavior. Those surfaces remain owned by their later slices and require separate authorization.

## Slice 3 WindowSpec, Extension-compatible WindowFunctionIdentity, And AST Contract

Phase 53 is `ACTIVE`; Slices 1 and 2 are `COMPLETED`; Slice 3 remains `UNSTARTED` throughout Gate 2. Gate 2 owns only immutable preservation of the already accepted Slice 2 CST, a private source-preserving window-function identity, the minimum ordinary-check fail-closed guard, exact compatibility-reader migration, the Slice 3 contract/specification, and focused evidence. Slice 3 becomes `COMPLETED` only after a separately authorized Gate 3 publishes the exact result and the unique natural `CI / push / main`, attempt 1, succeeds at that commit's exact `headSha`.

The selected architecture is a dedicated `WindowExpr(Expression)` carrying `call: CallExpr`, `spec: WindowSpec`, and `identity: WindowFunctionIdentity` in that declaration order. `WindowSpec` is a frozen/slots/kw-only source AST node with exact tuple fields for source-ordered partition expressions and window-local `OrderItem` values; at least one tuple is nonempty. `CallExpr`, `SelectItem`, and `OrderItem` keep their existing shapes. Aliases remain on `SelectItem`, and integer literals remain rejected only in final relation ordering, not in a window-local order list.

`src/pietto/_window_identity.py` privately defines frozen/slots `WindowFunctionIdentity(namespace, name, role)` and the single `WindowFunctionRole.WINDOW_FUNCTION`. The final dotted call component becomes `name`; preceding components form the ordered namespace tuple; source case is preserved exactly. The identity's role records syntactic origin only and cannot establish builtin membership, semantic existence, signature legality, generic binding, result typing, nullability, mandatory ordering, portability, extension installation, backend capability, or public exposure.

`AstBuilder` now has explicit window CST visitors, a call-only span path shared with ordinary calls, and an explicit order-item ordinal policy. The full expression, call, callee, specification, partition expressions, order items, and order expressions preserve exact 1-based half-open logical spans without layout-token expansion. Canonical Slice 2 input returns a valid AST with no parser diagnostics; the temporary Slice 2 fail-closed bridge is retired only for valid syntax. The exact malformed/deferred grammar matrix and ordinary parser behavior remain unchanged.

The only downstream production protection is an early direct-return `WindowExpr` branch in `semantic/expressions.py::_infer`. It emits existing `PIE-S2103` with the ordinary unknown-function message at the call span and deliberately publishes no expression value-type fact. Existing IR lowering then returns `PIE-I1000` for the missing fact if semantic errors are bypassed. Project parse-only readers remain non-concrete and create no `WINDOW_RESULT`, dependency, lineage, IR, SQL, catalog, generic/nullability, or public serialization fact.

The exact Gate 2 repository scope is `A3/M51/D0`: this plan, three production modules, 47 compatibility readers, plus the new specification, private identity module, and 25-function/70-item focused test. Grammar, all eight generated files, parser API, package root, project implementation, IR, PostgreSQL/private-MySQL SQL, CLI, public serializers, fixtures, goldens, scripts, workflow, package metadata, dependency lock, and version remain byte-identical. Future committed inventory is 844 tracked files, 518 Python files, 230 Markdown files, 436 test modules, 4219 top-level test functions, 6376 collected items, 8 generated files, and 37 goldens.

Gate 2 uses exactly one write-mode Ruff invocation over 52 handwritten Python allowlist paths. It validates 202 focused items, then the exact dirty overlay with `6193 passed, 183 deselected`, and projects 6376 clean-CI passes per Python job. Gate 2 leaves all 54 paths unstaged and uncommitted with an empty index. It performs no ANTLR generation, stage, commit, push, CI mutation, tag, Release, PR, package upload, signing, or attestation.

Slice 4 retains generic compatibility ownership; Slice 5 retains nullability algebra; Slice 6 retains the private semantic carrier, WINDOW stage, dependency, lineage, and result roles; Slices 7–14 retain bounded window behavior; Slice 15 retains Window IR and independent backend lowering; Slice 16 retains completion audit/status lock. Parser AST preservation grants no automatic authority to any later slice. STOP on any grammar/generated need, allowlist escape, second formatter, semantic/project/IR/SQL/public widening, validation/count drift, staging/publication, or unresolved product decision.

## Slice 4 Generic Type-variable, Constraint, And Exact Compatibility Foundation

Phase 53 is `ACTIVE`; Slices 1 through 3 are `COMPLETED`; Slice 4 remains `UNSTARTED` throughout Gate 2. Gate 2 owns only a private standalone exact generic-compatibility foundation, its specification and focused tests, and the exact compatibility-reader migration. Slice 4 becomes `COMPLETED` only after a separately authorized Gate 3 publishes the exact result and the unique natural `CI / push / main`, attempt 1, succeeds at that commit's exact `headSha`.

`src/pietto/semantic/generic_compatibility.py` privately defines a source-independent `LogicalTypeIdentity(name, kind)`, exact `TypeVariable` and concrete/variable type expressions, ordered parameters and signatures, immutable binding and mismatch evidence, duplicate-preserving `OverloadSet`, and all-candidate `MATCH`, `UNSUPPORTED`, and `AMBIGUOUS` selection. Every data carrier is frozen, slotted, and keyword-only; the module exports nothing through `__all__`, owns no mutable registry or cache, and does not integrate with current analyzer, catalog, window, capability, project, IR, SQL, CLI, serializer, package, or workflow surfaces.

The four independent constraints are `SCALAR`, `COMPARABLE`, `ORDERABLE`, and `NUMERIC`. Their complete explicit matrix is grounded only in frozen current semantic evidence: all eleven current builtin identities are scalar; comparable is exactly Bool, Date, Decimal, Float, Int, Text, Timestamp, and UUID; orderable is exactly Date, Decimal, Float, Int, and Timestamp; numeric is exactly Decimal, Float, and Int. Enum, Shape, and unresolved identities fail all four constraints. Type aliases must be canonicalized by a future caller; `TYPE_ALIAS` and `UNKNOWN` are not accepted identities. Capability lookup is descriptive evidence only and is not imported or treated as compatibility authority.

Binding is exact and deterministic: validate exact tuples and member types, check arity, visit supplied parameters in position order, reject unresolved arguments, require concrete equality, record first variable bindings, require repeated equality, evaluate all constraints in first-binding/declaration order, record omitted optional suffix positions, and resolve the result only from a concrete expression or existing binding. Incompatibility returns structured evidence rather than raising. There is no coercion, promotion, subtyping, LUB, Decimal fusion, alias expansion, temporal conversion, nullability lifting, or backend conversion. Duplicate overload rows are valid and matching duplicates are ambiguous; no first-match or tie-break rule exists.

The exact Gate 2 repository scope is `A3/M49/D0`: this plan, 48 existing compatibility/hash/state readers, plus the new specification, private semantic module, and 31-function/190-item focused test. Grammar, AST, parser, all eight generated files, current semantic behavior and capability modules, project, IR, PostgreSQL/private-MySQL SQL, CLI, public serializers, fixtures, goldens, scripts, workflow, package metadata, dependency lock, and version remain byte-identical. Future committed inventory is 847 tracked files, 520 Python files, 231 Markdown files, 437 test modules, 4250 top-level test functions, 6566 collected items, 8 generated files, and 37 goldens.

Gate 2 uses exactly one write-mode Ruff invocation over 50 handwritten Python allowlist paths. It validates 427 focused items, then the exact dirty overlay with `6383 passed, 183 deselected`, and projects 6566 clean-CI passes per Python job. Gate 2 leaves all 52 paths unstaged and uncommitted with an empty index. It performs no ANTLR generation, stage, commit, push, CI mutation, tag, Release, PR, package build or smoke, golden regeneration, upload, signing, or attestation.

Slice 5 retains symbolic nullability ownership; Slice 6 retains the private window semantic carrier, WINDOW stage, dependency, lineage, and result roles; Slices 7–14 retain bounded window behavior; Slice 15 retains Window IR and independent backend lowering; Slice 16 retains completion audit/status lock; Phase 64 retains coercion, promotion, LUB, temporal, Decimal-fusion, and native-mapping work. This private foundation grants no automatic authority to any later slice. STOP on any matrix drift, capability-authority inference, current semantic integration, grammar/AST/parser/generated need, allowlist escape, second formatter, test/count drift, project/IR/SQL/public widening, staging/publication, or unresolved product decision.

## Slice 5 Nullability Algebra And Signature Result-formula Foundation

Phase 53 is `ACTIVE`; Slices 1 through 4 are `COMPLETED`; Slice 5 remains `UNSTARTED` throughout Gate 2. Gate 2 owns only a private standalone symbolic result-nullability foundation, its specification and focused tests, and exact compatibility-reader migration. Slice 5 becomes `COMPLETED` only after a separately authorized Gate 3 publishes the exact result and the unique natural `CI / push / main`, attempt 1, succeeds at that commit's exact `headSha`.

`src/pietto/semantic/nullability_formulas.py` privately defines seven frozen, slotted, keyword-only symbolic variants: `NON_NULL`, `NULLABLE`, `SAME_AS_ARG`, `ANY_NULLABLE`, `ALWAYS_NULLABLE`, `NULLABLE_IF_DEFAULT_OMITTED`, and binary `ANY_OF`. `NULLABLE` and `ALWAYS_NULLABLE` remain structurally and evidentially distinct while both evaluate to concrete `EffectiveNullability.NULLABLE`. The bounded tree has maximum depth 2, maximum 3 nodes, exactly two composition children, and at most two ordered argument-reference occurrences; `ALL_OF`, `NOT`, arbitrary operators, normalization, and mutable registries do not exist.

The selected sibling `SignatureResultFormula` preserves Slice 4's exact `GenericSignature` value and validates formula bounds, argument positions, and optional omitted-default references at construction. `NullabilityEvaluationContext` consumes an ordered supplied prefix plus the exact omitted suffix. Evaluation preserves all three concrete nullability states, produces immutable recursive evidence, and returns structured private unsupported results for incompatible contexts. It performs no type binding, overload selection, runtime default execution, analyzer, catalog, or backend work.

The readiness-only navigation formula is `ANY_OF(ANY_NULLABLE((0, 2)), NULLABLE_IF_DEFAULT_OMITTED(2))` over required value `T`, optional offset `Int`, optional default `T` marked `ParameterDefault.OMITTED`, and result `T`. An omitted default forces a nullable result; a supplied default joins value/default nullability; offset nullability does not contribute. This is construction and differential-test readiness only and does not register or implement `lag` or `lead`.

The exact Gate 2 repository scope is `A3/M50/D0`: this plan, 49 existing compatibility/hash/state readers, plus the new specification, private semantic module, and 38-function/145-item focused test. Grammar, AST, parser, all eight generated files, Slice 4 generic compatibility, concrete `EffectiveNullability`, current analyzer and window behavior, capability modules, project, dependency, lineage, IR, PostgreSQL/private-MySQL SQL, CLI, public serializers, fixtures, goldens, scripts, workflow, package metadata, dependency lock, and version remain byte-identical. Future committed inventory is exactly 850 tracked files, 522 Python files, 232 Markdown files, 438 test modules, 4288 top-level test functions, 6711 collected items, 8 generated files, and 37 goldens.

Gate 2 uses exactly one write-mode Ruff invocation over 51 handwritten Python allowlist paths. It validates 607 focused items, then the exact dirty overlay with `6528 passed, 183 deselected`, and projects 6711 clean-CI passes per Python job. Gate 2 leaves all 53 paths unstaged and uncommitted with an empty index. It performs no ANTLR generation, stage, commit, push, CI mutation, tag, Release, PR, package build or smoke, golden regeneration, upload, signing, or attestation.

Slice 6 retains the private window semantic carrier, WINDOW stage, dependency, lineage, and result roles; Slices 7–14 retain bounded window behavior; Slice 15 retains Window IR and independent backend lowering; Slice 16 retains completion audit/status lock; Phase 64 retains coercion, promotion, LUB, temporal, Decimal-fusion, and native-mapping work. This private foundation grants no automatic authority to a later slice. STOP on formula-kind or bound drift, UNKNOWN collapse, generic/concrete semantic change, analyzer/window integration, allowlist escape, reader edge escape, second formatter, test/count drift, project/IR/SQL/public widening, staging/publication, or unresolved product decision.

## Slice 6 Private Window Semantic Carrier, WINDOW Stage, Dependency, And Result Roles

Phase 53 is `ACTIVE`; Slices 1 through 5 are `COMPLETED`; Slice 6 remains `UNSTARTED` throughout Gate 2. Gate 2 owns only the private semantic/project carrier split, the inert WINDOW stage and WINDOW_RESULT role, ordered dependency occurrence and edge evidence, immediate derived provenance, its specification and focused tests, and exact reader migration. Slice 6 becomes `COMPLETED` only after a separately authorized Gate 3 publishes the exact result and the unique natural `CI / push / main`, attempt 1, succeeds at that commit's exact `headSha`.

`src/pietto/semantic/window_semantics.py` privately owns structural window occurrence identity, the standalone `WindowExpressionStage.WINDOW`, concrete/unknown/deferred/blocked result availability, an inert `WindowExpressionSemanticFact`, and structured unavailable evidence. A concrete result carries only an already known existing `ValueType` with `NON_NULL` or `NULLABLE` effective nullability. No carrier binds a generic, evaluates a nullability formula, grants legality, changes current stage inference, registers a function, or creates a diagnostic.

`src/pietto/_project/window_semantics.py` privately owns explicit result identity, the ordered dependency roles `RELATION_INPUT`, `WINDOW_ARGUMENT`, `WINDOW_DEFAULT`, `WINDOW_PARTITION`, and `WINDOW_ORDER`, duplicate-preserving dependency occurrences, deterministic first-occurrence-deduplicated edges, and one atomic project fact using existing `DERIVED_EXPRESSION` provenance. Non-relation dependencies accept only upstream-field or let-binding targets, so same-select output and nested-window dependencies remain non-representable. Zero-argument ranking readiness requires exactly one relation-input occurrence and edge; nonzero-argument readiness forbids relation input. No project model, checker, graph, schema, lineage, or serializer is populated.

The only existing production-module semantic change appends inert private `ProjectRowResultRole.WINDOW_RESULT = "window_result"` after the existing three roles. No current builder assigns it. Grammar, all eight generated files, AST, builder, parser API, window identity, Slice 4 generic compatibility, Slice 5 nullability formulas, analyzer, catalog, capability facts and lookup, IR, PostgreSQL/private-MySQL SQL, CLI, public serializers, fixtures, goldens, scripts, workflow, package metadata, lockfile, version, runtime, and database behavior remain byte-identical.

The exact Gate 2 repository scope is `A4/M54/D0`: this plan, the private result-role owner, 52 compatibility/hash/state readers including the reconciled escaping Slice 5 reader, plus the new specification, two private source modules, and 36-function/156-item focused test. Future committed inventory is exactly 854 tracked files, 525 Python files, 233 Markdown files, 439 test modules, 4324 top-level test functions, 6867 collected items, 86 compiler files, 30 semantic files, 27 Phase-15 subset files, 17 private project files, 8 generated files, and 37 goldens.

Gate 2 uses exactly one write-mode Ruff invocation over 56 handwritten Python paths. It validates 775 focused items, then the exact dirty overlay with `6682 passed, 185 deselected`, and projects 6867 clean-CI passes per Python job. Gate 2 leaves all 58 paths unstaged and uncommitted with an empty index. It performs no ANTLR operation, staging, commit, push, CI mutation, tag, Release, PR, package build or smoke, golden regeneration, upload, signing, or attestation.

Slices 7–14 retain bounded function-semantic behavior; Slice 15 retains Window IR and independent backend lowering; Slice 16 retains completion audit/status lock; Phase 60 retains frames; Phase 64 retains coercion, promotion, LUB, temporal, Decimal-fusion, and native-mapping work. This private foundation grants no automatic authority to a later slice. STOP on another path, stage, result role, dependency role, provenance kind, occurrence identity, analyzer/catalog/capability integration, project-model population, same-select/nested representability, grammar/AST/parser/generated/IR/SQL/public widening, second formatter, test/count/selector drift, staging/publication, or unresolved product decision.

## Slice 7 row_number Direct-field MVP

Phase 53 is `ACTIVE`; Slices 1 through 6 are `COMPLETED`; Slice 7 remains `UNSTARTED` throughout Gate 2. Gate 2 owns only the exact lowercase `row_number()` Direct-field MVP, private semantic analysis, a transient project-fact bridge, its contract and focused tests, and exact compatibility-reader migration. Slice 7 becomes `COMPLETED` only after separately authorized Gate 3 publication and the unique natural `CI / push / main`, attempt 1, succeeds at that exact head.

The selected subset requires an explicit alias, exact source-preserved `row_number` identity with empty namespace and `WINDOW_FUNCTION` role, zero arguments, zero partition expressions, exactly one bare or immediate-qualified direct order field, omitted direction, and at most one window output per relation. `TableDef` and `QueryDef` may consume a concrete direct source or concrete immediate upstream relation. One window output may coexist with any currently legal non-window, non-aggregate selected items. Grouping, any selected semantic aggregate, satisfying, let, multiple/nested/same-select windows, transitive qualifiers, computed ordering, partitioning, explicit direction, and additional order keys remain fail closed under existing diagnostics.

`pietto.semantic.window_analysis` owns a zero-variable/zero-parameter signature returning builtin `Int`, a `NonNullFormula`, exact direct-field binding through existing `infer_row_expression`, and private `WindowExpressionSemanticFact | WindowExpressionUnsupported` results. `type_relation_expressions` invokes it only for direct selected windows and stores no `WindowExpr` value-type fact. The project row-schema path constructs and discards a `WindowResultProjectFact` with `RELATION_INPUT` then `WINDOW_ORDER` dependencies, `WINDOW_RESULT` identity, and immediate `DERIVED_EXPRESSION` provenance. No semantic or project model, row schema, dependency graph, lineage, or serializer persists the fact.

The exact Gate 2 scope is `A3/M57/D0`: the plan, three existing production modules, 54 compatibility/hash/state readers, plus the new specification, private semantic module, and 41-function/168-item focused test. Future inventory is 857 tracked files, 527 Python files, 234 Markdown files, 440 test modules, 4365 top-level test functions, 7035 collected items, 87 compiler files, 31 semantic files, 28 Phase-15 semantic-subset files, 17 private project files, 8 generated files, and 37 goldens.

Gate 2 uses exactly one write-mode Ruff invocation over 58 handwritten Python paths. It validates 943 focused items, then the exact dirty overlay with `6850 passed, 185 deselected`, and projects 7035 clean-CI passes per Python job. It leaves all 60 paths unstaged and uncommitted with an empty index and performs no ANTLR operation, staging, commit, push, CI mutation, tag, Release, PR, package build or smoke, golden regeneration, upload, signing, or attestation.

Slices 8 through 14 retain broader window behavior and row-schema/downstream ownership; Slice 15 retains Window IR and independent backend lowering; Slice 16 retains completion audit/status lock; Phase 60 retains frames; Phase 64 retains generic coercion and promotion. STOP on an allowlist escape, additional production/public path, second formatter, count or selector drift, semantic/project persistence, grammar/AST/parser/generated/IR/SQL/public widening, staging/publication, or unresolved product decision.

## Slice 8 rank / dense_rank And Peer Semantics

Phase 53 is `ACTIVE`; Slices 1 through 7 are `COMPLETED`; Slice 8 remains `UNSTARTED` throughout Gate 2. Gate 2 owns only exact lowercase `rank()` and `dense_rank()` in the completed Slice 7 direct-field subset, one private immutable sibling ranking-semantics fact, one private `RankingAdvancePolicy` enum, generic semantic/project entrypoints with retained `row_number` compatibility wrappers, its contract and focused tests, and exact compatibility-reader migration. Slice 8 becomes `COMPLETED` only after separately authorized Gate 3 publication and the unique natural `CI / push / main`, attempt 1, succeeds at that exact head.

The accepted subset keeps exact `NameExpr` identity, empty namespace, `WINDOW_FUNCTION`, zero arguments, an explicit selected alias, ungrouped and nonaggregate `TableDef` or `QueryDef`, maximum window outputs per relation=1, empty partitioning, one bare or immediate-qualified direct order field, omitted direction, and a concrete direct or immediate-upstream input schema. `row_number` is peer-insensitive with `PER_ROW`; `rank` is peer-sensitive with `GAPPED_PEER_RANK`; `dense_rank` is peer-sensitive with `DENSE_PEER_RANK`. The shared signature/formula remains object-identical `Int / NON_NULL / WINDOW`, and the one existing `infer_row_expression` resolver supplies the structural peer key without runtime comparison, collation, null ordering, direction, or backend behavior.

The generic semantic analyzer constructs the unchanged transient `WindowExpressionSemanticFact` plus private `RankingWindowSemanticFact`; the generic project builder extracts only the core fact and retains `WINDOW_RESULT`, `RELATION_INPUT` then `WINDOW_ORDER`, first-occurrence edge order, and `DERIVED_EXPRESSION`. Both integration seams still discard their results. No semantic or project model, row schema, dependency graph, lineage, same-select/final-order/downstream alias, serializer, public export, IR, or SQL lowering persists or publishes ranking evidence; IR and both SQL paths remain fail closed through `PIE-I1000`.

The exact Gate 2 scope is `A2/M60/D0`: this plan, five private production modules, 54 compatibility/hash/state readers, plus the new specification and 45-function/279-item focused test. Future inventory is exactly 859 tracked files, 528 Python files, 235 Markdown files, 441 test modules, 4410 top-level test functions, 7314 collected items, 87 compiler files, 31 semantic files, 28 Phase-15 semantic-subset files, 17 private project files, 8 generated files, and 37 goldens.

Gate 2 uses exactly one write-mode Ruff invocation over the exact ordered 60-path handwritten Python manifest. It validates 1222 focused items, proves real collection of 7314, then runs the dirty overlay with 7129 passed and 185 deselected, and projects 7314 passes in each clean-CI Python job. It leaves all 62 paths unstaged and uncommitted with an empty index and performs no ANTLR operation, staging, commit, push, CI mutation, tag, Release, PR, package build or smoke, golden regeneration, upload, signing, or attestation.

Slices 9 and 12 retain later ranking/navigation identities; Slices 10 and 11 retain partitioning, multiple keys, direction, determinism, null ordering, and collation; Slices 13 and 14 retain grouped/let visibility, multiple outputs, alias visibility, downstream schema, persistence, and lineage; Slice 15 retains Window IR and independent backend lowering; Slice 16 retains completion audit/status lock. STOP on an allowlist escape, another identity/policy/diagnostic/resolver, runtime peer evaluation, persistent facts, row-schema/public/IR/SQL widening, second formatter, count/selector drift, nonempty index, publication, or unresolved decision. Recommended next authorization: `Phase 53 Slice 8 Gate 3`, with commit subject `Add Phase 53 rank and dense-rank peer semantics`.

## Slice 9 percent_rank / cume_dist / ntile

Phase 53 is `ACTIVE`; Slices 1 through 8 are `COMPLETED`; Slice 9 remains `UNSTARTED` throughout Gate 2. Gate 2 owns only exact lowercase `percent_rank()`, `cume_dist()`, and positive-integer-literal `ntile(N)` in the completed Slice 8 direct-field subset, a sibling private immutable distribution policy/fact, general semantic/project dispatchers with completed ranking compatibility wrappers, its contract and focused tests, and exact compatibility-reader migration. Slice 9 becomes `COMPLETED` only after separately authorized Gate 3 publication and the unique natural `CI / push / main`, attempt 1, succeeds at that exact head.

The selected subset keeps exact `NameExpr` identity, empty namespace, `WINDOW_FUNCTION`, an explicit selected alias, ungrouped and nonaggregate `TableDef` or `QueryDef`, exactly one window output per relation, empty partitioning, one bare or immediate-qualified direct order field, omitted direction, and a concrete direct or immediate-upstream schema. `percent_rank` and `cume_dist` have zero arguments and return builtin `Float / NON_NULL / WINDOW`; `ntile` requires one exact positive integer `LiteralExpr` and returns builtin `Int / NON_NULL / WINDOW`. `percent_rank` reuses a same-core gapped ranking fact, `cume_dist` records cumulative peer distribution, and `ntile` records only its positive bucket count and balanced-bucket policy. These are structural facts only, with no row counting, division, peer comparison, bucket assignment, collation, null ordering, direction, runtime, or backend behavior.

`pietto.semantic.window_analysis` retains the stable ranking table and adds a separate ordered distribution identity/policy/signature/formula table plus one general recognized-window dispatcher. `DistributionWindowSemanticFact` is a private sibling that preserves the core and ranking field shapes, validates exact policy combinations, and derives the complete structural order key and bounded peer key. The project general builder extracts only the unchanged core fact and retains `WINDOW_RESULT`, `RELATION_INPUT` then `WINDOW_ORDER`, first-occurrence edge order, and `DERIVED_EXPRESSION`; the `ntile` literal creates no dependency. Both integration seams still discard their transient results. No semantic/project model, row schema, graph, lineage, serializer, public export, IR, or SQL lowering persists or publishes distribution evidence; IR and both SQL paths remain fail closed through `PIE-I1000`.

The exact Gate 2 scope is `A2/M61/D0`: this plan, five private production modules, 55 compatibility/hash/state readers, plus the new specification and 54-function/424-item focused test. Future inventory is exactly 861 tracked files, 529 Python files, 236 Markdown files, 442 test modules, 4464 top-level test functions, 7738 collected items, 87 compiler files, 31 semantic files, 28 Phase-15 semantic-subset files, 17 private project files, 8 generated files, and 37 goldens.

Gate 2 uses exactly one write-mode Ruff invocation over the exact ordered 61-path handwritten Python manifest. It validates 1646 focused items, proves real collection of 7738, then runs the dirty overlay with 7553 passed and 185 deselected, and projects 7738 passes in each clean-CI Python job. It leaves all 63 paths unstaged and uncommitted with an empty index and performs no ANTLR operation, staging, commit, push, CI mutation, tag, Release, PR, package build or smoke, golden regeneration, upload, signing, or attestation.

Slices 10 and 11 retain partitioning, multiple keys, direction, determinism, null ordering, and collation; Slice 12 retains navigation/value identities; Slices 13 and 14 retain grouped/let visibility, multiple outputs, alias visibility, downstream schema, persistence, and lineage; Slice 15 retains Window IR and independent backend lowering; Slice 16 retains completion audit/status lock. STOP on an allowlist escape, another identity/type/diagnostic/resolver, nonliteral bucket argument, runtime distribution evaluation, persistent facts, row-schema/public/IR/SQL widening, second formatter, count/selector drift, nonempty index, publication, or unresolved decision. Recommended next authorization: `Phase 53 Slice 9 Gate 3`, with commit subject `Add Phase 53 percent-rank cume-dist and ntile semantics`.

## Slice 10 Partition Binding, Multi-key Visibility, And Diagnostics

Phase 53 is `ACTIVE`; Slices 1 through 9 are `COMPLETED`; Slice 10 remains
`UNSTARTED` throughout Gate 2. Gate 2 owns only arbitrary-length,
source-ordered direct-field partition tuples for the six completed window
identities, immediate-input visibility, deterministic existing diagnostics,
private transient partition/composite semantic evidence, duplicate-preserving
project occurrences with first-role-target edges, its contract and focused
tests, and the exact reader migration. Slice 10 becomes `COMPLETED` only after
separately authorized Gate 3 publication and the unique natural
`CI / push / main`, attempt 1, succeeds at that exact head.

The selected subset accepts zero or any number of bare or immediate-qualified
direct partition fields. Concrete nullable fields are structurally legal;
duplicates remain source-ordered bindings and occurrences while edges dedupe
only the first identical role/target pair. The existing row resolver owns each
field exactly once. Unknown or invalid qualifiers use `PIE-S2102`; computed or
nested partition shapes and nonconcrete schema use `PIE-S2103`. Partition
validation precedes the unchanged one-field local-order validation, and
`ntile` literal validation stays after order-field resolution.

`WindowPartitionFieldBinding` and `WindowPartitionBindingFact` are private
frozen sibling carriers. `WindowExpressionAnalysis` joins the unchanged core,
unchanged ranking/distribution siblings, and one always-present partition
sibling. Compatibility analyzers keep their successful return shapes. The
generic project builder extracts the core and creates exact role blocks:
`RELATION_INPUT`, source-ordered `WINDOW_PARTITION`, then `WINDOW_ORDER`.
Result identity, immediate derived provenance, peer/order keys, family
policies, result types, nullabilities, signatures, formulas, and `ntile`
bucket evidence remain unchanged.

The exact Gate 2 scope is `A3/M60/D0`: this plan, three private production
modules, 56 compatibility/hash/state test readers, plus the new specification,
one private semantic helper, and one 67-function/627-item focused test. Future
inventory is exactly 864 tracked files, 531 Python files, 237 Markdown files,
443 test modules, 4531 top-level test functions, 8365 collected items, 88
compiler files, 32 semantic files, 29 Phase-15 semantic-subset files, 17
private project files, 8 generated files, and 37 goldens.

Gate 2 uses exactly one write-mode Ruff invocation over the exact ordered
61-path handwritten Python manifest. It validates 2273 focused items, proves
real collection of 8365, then runs the dirty overlay with
8180 passed and 185 deselected, and projects
8365 passes in each clean-CI Python job. It leaves all
63 paths unstaged and uncommitted with an empty index and performs no ANTLR
operation, staging, commit, push, CI mutation, tag, Release, PR, package build
or smoke, golden regeneration, upload, signing, or attestation.

Slice 11 retains multiple local-order keys, direction, determinism, collation,
and null ordering; Slice 12 retains navigation/value identities; Slice 13
retains grouped/aggregate/satisfying/let visibility; Slice 14 retains multiple
outputs, aliases, downstream schema, persistence, and lineage; Slice 15
retains Window IR and independent backend lowering; Slice 16 retains completion
audit/status lock. STOP on an allowlist escape, another identity/type/code or
resolver, grammar/AST/parser/generated change, runtime evaluation, persistent
fact, row-schema/public/IR/SQL widening, second formatter, count/selector drift,
nonempty index, publication, or unresolved decision. Recommended next
authorization: `Phase 53 Slice 10 Gate 3`, with commit subject
`Add Phase 53 partition binding and diagnostics`.
