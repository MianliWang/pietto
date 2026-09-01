# Phase 62 Slice 6 Factorized Intrinsic Grain Basis, Dependencies, Optional Factors, And GLOBAL Grain v1

## Answer And Exact Owner

Slice 6 adds the smallest private intrinsic-grain foundation:

```text
exact Source row domain or exact GROUP_AGGREGATE occurrence
-> intrinsic grain origin
-> FACTORIZED or GLOBAL GrainBasis
-> separate typed factor-dependency kernel
-> exact deterministic derivation witness
```

```text
intrinsic grain != visible key fields != Value FD != row uniqueness != cardinality
```

Slice 6 owns grain origins and the factor/dependency model. Slice 7 owns
operator propagation and comparison.

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD / `main` / `origin/main` | `d33a3e81d3405b95879becf6bcccebb433ea298f` |
| Tree | `e4ab46583b1dc9f6aa2649f67bd073d99f1e027d` |
| Parent | `b38247f6d115e1cbcf24b47b4d60322fa68e0fa4` |
| Subject | `Add Phase 62 value functional dependencies` |
| Natural exact-head CI | `33488399817`, `push`, `main`, attempt `1`, successful |
| Divergence / worktree / active operation | `0/0` / clean / none |

The predecessor establishes Phase 61 completed, Phase 62 active, Slices 1–5
completed/published, and Slice 6 next/not implemented.

## Frozen Reader And Changed-path Closure

```text
docs/roadmap.md
docs/spec/phase62-slice6-factorized-intrinsic-grain-basis-dependencies-optional-factors-global-grain-v1.md
docs/status.md
src/pietto/_project/project_grain.py
tests/test_active_phase_lifecycle.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_phase62_slice6_factorized_intrinsic_grain_basis_dependencies_optional_factors_global_grain.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M5/D0`. The active lifecycle test remains the sole mutable
roadmap/status reader. Slice-1 live-source assurance acknowledges the delivered
private grain owner. Validator inventory accounts for one production and one
test file. Existing dynamic workflow/repository readers need no change. A
ninth path is `READER_CLOSURE_DRIFT`.

## Grain States And Origin Boundaries

The closed basis vocabulary is `FACTORIZED`, `GLOBAL`, `UNKNOWN`, `CONFLICT`.

```text
UNKNOWN != GLOBAL
CONFLICT != UNKNOWN
```

Concrete Slice-6 origins construct only FACTORIZED or GLOBAL. UNKNOWN and
CONFLICT are reserved semantic states, not fabricated test data.

True current origins are exactly:

```text
concrete Source row domain
non-empty-key GROUP_AGGREGATE result
actual zero-key aggregate result
```

No factor is created for filter, result filter, projection, window, ordering,
or limit. Plain nongrouped derived outputs create no local origin and are not
labelled unknown.

## Source-domain Identity And Witness

Every concrete Source creates one FACTORIZED basis with one required
`ProjectSourceGrainFactorIdentity`. Identity retains the exact declaration
occurrence, exact concrete semantic row authority, and source-domain kind.
Names, fields, keys, FD closure, hashes, bytes, and object addresses are not
factor identity.

The source witness retains the exact `ProjectModuleRelationSemanticFacts` and
its exact Slice-5 `ProjectValueFDBasis`. The factor exists with no candidate
key or non-trivial FD and regardless of field nullability.

```text
absence of visible key != unknown intrinsic grain
```

Two Source declarations using the same Shape remain distinct domains.

## Grouped And GLOBAL Authority

A non-empty-key exact `ProjectIRAggregateEvaluationContext` creates one new
group-domain factor tied to its exact plan-node occurrence and relation owner.
The witness retains the same context, exact BASE_RESULT output, and ordered
`GroupByItem` tuple by object identity. Equal-looking group keys in different
relations remain distinct origins. SQL grouping/NULL-equal semantics do not
become relationship standard equality.

An exact context with no group keys creates GLOBAL only when its retained
`aggregate_results` is non-empty. GLOBAL has zero factors and an exact context
witness.

```text
GLOBAL grain != empty candidate key != max-one-row != LIMIT 1
```

No syntax-string or row-count inference participates.

## GrainBasis And Domain Factors

`ProjectGrainBasis` is an immutable value containing state, ordered local
factor universe, exact dependency facts/index, and one derivation witness.
`ProjectConcreteGrainOrigin` separately carries source/group/global occurrence
identity.

```text
GrainBasis value/structure != occurrence identity
intrinsic grain-domain factor != future factor-use occurrence
```

Current FACTORIZED origins have exactly one factor; GLOBAL has zero. No global
mutable interning or per-stage row-axis graph exists.

## Typed Grain-dependency Kernel

Grain dependency is independently typed:

```text
FactorSet -> FactorSet
```

```text
FieldSet -> FieldSet != GrainFactorSet -> GrainFactorSet
```

`ProjectGrainDependencyFact`, its compiled rule/index, and targeted closure do
not reuse `ProjectValueFDFact` or `ProjectCompiledValueFDRule`. Positions and
arbitrary-width Python-int masks are local to one exact factor universe.

```text
factor bit position != grain-factor identity
```

The indexed worklist is finite, visits LHS-incident rules, stores no full
transitive authority, enumerates no factor subsets, and has no persistent
cache. Current production origins legitimately publish `dependencies = ()`;
no field-name, Value-FD, or relationship-correspondence dependency is invented.

## Optional-factor Readiness

```text
base intrinsic factor != optional/lifted factor use
optional factor = base factor + exact nulling provenance
optional factor != matched/unmatched branch expansion
```

There is no logical JOIN/nulling occurrence yet. Slice 6 therefore exposes
only `NOT_CONSTRUCTIBLE_BEFORE_LOGICAL_JOIN` readiness and creates no optional
factor, fake JOIN ref, or nulling set. Exact non-empty nulling provenance and
factor-use occurrence identity remain Slice 11-owned construction work.

## Phase-61 Local-grain Separation

Phase-61 `ProjectIRProvidedLocalGrainEvidence` remains exact non-empty group-key
evidence. It is neither removed nor redefined.

```text
existing LOCAL_GRAIN_EVIDENCE != intrinsic GrainBasis
```

Grouped contexts retain that evidence; global aggregate contexts correctly
have none. Slice 7 owns reconciliation and occurrence-owned provided-grain
properties.

## Completeness And Non-concrete Isolation

`ProjectGrainOriginSet` separately preserves Slice-5 source order and exact
Project-plan aggregate-context order. It covers every concrete Source, grouped
aggregate, and actual global aggregate origin exactly once.

Non-concrete Source facts and non-concrete aggregate readiness are retained as
typed `ProjectNonConcreteGrainSubject` objects. They receive no GrainBasis,
factor, GLOBAL fallback, or winner and cannot erase independent origins.

```text
no local origin != unknown grain
```

## Compatibility And Production Delta

The only production addition is private
`src/pietto/_project/project_grain.py` with empty `__all__`.

There is zero delta for grammar/AST/generated files, `SemanticModel`,
`ProjectSemanticResult`, Phase-61 local-grain evidence, Slice-4 keys, Slice-5
FDs, operator transfer/comparison, cardinality, fanout, relationship paths,
JOIN, Project IR structure, SQL, CLI/JSON, Project Explain, package, workflow,
dependencies, and version.

## Focused Assurance

Focused tests prove concrete keyed and unkeyed Sources produce distinct
FACTORIZED domains; same-Shape Sources remain distinct; grouped contexts create
distinct factors and retain ordered keys/BASE_RESULT; actual global aggregate
creates GLOBAL with zero factors and no positive local group evidence; LIMIT 1
and plain/unary outputs create no origin; non-concrete origins remain isolated;
current dependencies stay empty; a 70-factor synthetic local universe proves
arbitrary-width targeted closure and cross-universe rejection; optional
readiness creates no JOIN authority; public/operator/FD boundaries and contract
closure remain unchanged. Tests remain serial/xdist, order, cwd/environment,
and Python 3.12/3.13 compatible.

## Slice 7 Handoff

Slice 6 leaves source FACTORIZED bases, grouped FACTORIZED origins, GLOBAL
aggregate origins, the factor/dependency kernel, Slice-4 keys, Slice-5 FDs, and
exact existing Project IR flows/properties.

The sole next owner is **Phase 62 Slice 7 — Existing-Operator Key/FD/Grain
Transfer And Grain Comparison**. Slice 7 owns unary preservation,
group/global replacement, key/FD transfer, exact non-null upgrades, grain
comparison, and occurrence-owned provided-grain properties. Slice 7 is not
implemented here.

## Review And Repair Accounting

Slice 6 allows at most one bounded repair batch after the complete finding set
is frozen, only for the same root, owner, and eight-path closure.

```text
Slice 6 repair batches allowed: 1
Slice 6 repair batches used after complete review: 1
```

The single frozen root is:

```text
GRAIN_ORIGIN_CARRIERS_DO_NOT_CLOSE_FACTOR_WITNESS_CONTEXT_AND_NONCONCRETE_COMPLETENESS
```

The repair makes basis/origin carriers reject detached source factors, detached
group contexts, and incomplete non-concrete subject ledgers.

A ninth path, second root/repair, public/operator transfer, or grain redesign is
`ARCHITECTURE_DECISION_REQUIRED`; recurrence is `REVIEW_RECURRENCE`.

## Gate Lifecycle And Publication

The candidate state is Phase 61 completed, Phase 62 active, Slices 1–5
completed/published, Slice 6 current/publication candidate, and Slices 7–16 not
started.

After focused closure and fresh review, start exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Seal the exact reviewed tree, make one ordinary commit and fast-forward push,
then require natural exact-head `push/main` attempt 1 success for Python
3.12/3.13, generated, golden, and package smoke.

```text
Add Phase 62 intrinsic grain foundation
```

```text
PASS — PHASE62_SLICE6_FACTORIZED_INTRINSIC_GRAIN_BASIS_DEPENDENCIES_OPTIONAL_FACTORS_GLOBAL_GRAIN_END_TO_END
```

True PASS completes/publishes Slices 1–6 and leaves Slice 7 next/not
implemented. Do not begin Slice 7.
