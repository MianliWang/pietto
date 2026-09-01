# Phase 62 Slice 5 Strict/Lax Value-FD Basis, Compact Indexes, And Targeted Closure v1

## Answer And Exact Owner

Slice 5 adds the smallest private Project value-functional-dependency kernel:

```text
exact concrete Source row output
+ Slice-4 candidate-key fact
-> direct STRICT/LAX value-FD theorem
-> exact field universe
-> snapshot-local Python-int compiled index
-> targeted STRICT-only closure
-> one deterministic proof witness
```

The exact owner is direct candidate-key-implied value FDs on the same Source
output, exact output-local field universes, immutable compiled masks and
incidents, strict determination, and a typed epistemic result.

```text
Value FD
!= row uniqueness
!= candidate key
!= grain dependency
```

Slice 5 consumes and retains Slice-4 authority. It does not replace or mutate
authored UNIQUE evidence or the candidate-key frontier.

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD / `main` / `origin/main` | `b38247f6d115e1cbcf24b47b4d60322fa68e0fa4` |
| Tree | `11f0b216e4a7273bd2fef6f8a8357443ecb6923e` |
| Parent | `933a13ea6ecb5e2701f7360fc5220ed3884ace18` |
| Subject | `Add Phase 62 row uniqueness and candidate keys` |
| Natural exact-head CI | `33477493108`, `push`, `main`, attempt `1`, successful |
| CI jobs | Python 3.12 successful; Python 3.13 successful |
| Downstream CI | generated, golden, and package smoke successful on both jobs |
| Divergence | `0/0` |
| Worktree/index/untracked | clean / clean / empty |
| Active Git operation | none |

The predecessor establishes:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slices 1-4 = COMPLETED / PUBLISHED
Slices 5-16 = NOT STARTED

Phase 62 Slice 5
= NEXT / NOT IMPLEMENTED
```

## Frozen Reader And Changed-path Closure

The exact fixed-point changed-path set is:

```text
docs/roadmap.md
docs/spec/phase62-slice5-strict-lax-value-fd-basis-compact-indexes-targeted-closure-v1.md
docs/status.md
src/pietto/_project/project_value_fds.py
tests/test_active_phase_lifecycle.py
tests/test_phase33_cli_package_compatibility_hardening.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_phase62_slice5_strict_lax_value_fd_basis_compact_indexes_targeted_closure.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M6/D0`. `tests/test_active_phase_lifecycle.py` remains the sole
direct mutable roadmap/status reader. The Slice-1 live-source reader
acknowledges the delivered private FD owner without rewriting its historical
contract. Validator inventory accounts for one production and one test file.
The existing workflow and repository-fact readers already consume the
`test_phase62_slice*.py` and dynamic Python source universes. The Phase-33
historical reader now checks the exact `compile_project` Python identifier
instead of an unrelated containing substring. A tenth path is
`READER_CLOSURE_DRIFT`.

## Strict And Lax Value-FD Semantics

Slice 5 reuses the closed Slice-4 strength vocabulary:

```text
STRICT
LAX
```

For one exact row-output scope, strict:

```text
A --> B
```

means that two rows with NULL-equal values for every field in `A` have
NULL-equal values for every field in `B`. NULL-equal treats two NULL values as
equal for dependency reasoning.

Lax:

```text
A ~~> B
```

means that when ordinary standard equality over every determinant field is
TRUE, the dependent fields are NULL-equal. A NULL determinant does not satisfy
that antecedent.

```text
strict FD != lax FD
lax FD is not generally transitive
```

Only STRICT rules participate in Slice-5 transitive closure.

## Direct Candidate-key Derivation

For a trusted candidate key `K` over the exact output universe `U`, Slice 5
derives exactly one direct theorem:

```text
K -> (U - K)
```

The dependent tuple follows exact output order. Determinant order is the
candidate identity's exact output order. Trivial self-dependencies are absent.
An all-field key with `U - K = {}` remains valid Slice-4 authority but produces
no non-trivial FD fact.

```text
STRICT key -> STRICT FD
LAX key    -> LAX FD
```

The derivation is once per merged candidate fact, not once per authored UNIQUE
support. Every supporting `ProjectRowUniquenessEvidence` remains reachable
through the exact `ProjectCandidateKeyFact` premise.

Slice 5 derives no direct FD from relationship correspondences, `WHERE`,
constants, projection expressions, grouping, JOIN, names, runtime data, or
catalog metadata.

```text
relationship equality correspondence != same-row value FD
candidate-key identity != value-FD identity
```

## Exact FD Identity And Provenance

`ProjectValueFDIdentity` retains:

```text
exact ProjectExactRowOutputConstraintScope
exact determinant ProjectModuleRowFieldIdentity tuple
exact dependent ProjectModuleRowFieldIdentity tuple
STRICT/LAX strength
exact ProjectCandidateKeyIdentity premise
```

`ProjectValueFDFact` retains the exact `ProjectCandidateKeyFact` object, so all
underlying authored support occurrences remain available. Names, masks, hashes,
canonical bytes, and object addresses are not FD identity.

Every constructed fact has:

```text
origin = DERIVED_THEOREM
trust = TRUSTED
enforcement = MODEL_CONTRACT
```

```text
derived theorem != authored contract occurrence
derived trusted FD != physically verified database constraint
```

The theorem inherits model-contract posture from its trusted authored key
premise without claiming catalog or runtime enforcement.

## Exact Field Universes

Every exact concrete `SourceDef` row output owns one immutable
`ProjectValueFDFieldUniverse`:

```text
exact output scope
+ complete ordered ProjectModuleRowFieldIdentity tuple
```

Construction follows selected-module order, source declaration occurrence
order, and exact source-schema field order. It reuses existing concrete
semantic facts and row-lineage field identities.

Concrete sources without candidate keys receive a valid empty basis and index.
All-field keys likewise leave an empty non-trivial fact set. Non-concrete source
rows receive no fabricated universe or dependency and do not erase independent
concrete outputs.

```text
same bit position in different universes != same field
```

Cross-universe queries reject the exact universe mismatch before comparing
masks.

## Compact Compiled Indexes

The normative identity and provenance stay in typed FD facts. The compiled
layer contains only snapshot-local computational coordinates:

```text
field identity -> dense output-order position
direct STRICT ProjectCompiledValueFDRule tuple
direct LAX ProjectCompiledValueFDRule tuple
LHS atom position -> incident STRICT rule positions
```

Each rule uses arbitrary-width Python `int` `lhs_mask` and `rhs_mask` values.
Union, intersection, subset, difference, and `bit_count()` use ordinary Python
integer operations. There is no 64-field limit, global registry, persistent
position, hash-derived ID, or content identity.

```text
bit position != semantic identity
compiled rule/index != semantic FD fact
```

The index retains normative facts in candidate-frontier order and never merges
or discards their premise/support provenance.

## Targeted Strict Closure

Slice 5 implements `STRICT closure only`. Given a typed seed on one exact
universe, the result is the seed plus every field reachable through direct
STRICT FDs at fixed point.

The algorithm is an indexed worklist:

```text
1. initialize the closure mask and enqueue seed atoms in field order
2. initialize one unsatisfied-LHS count per direct STRICT rule
3. visit only rules incident to each newly present atom
4. fire a rule when its count reaches zero
5. enqueue only newly added RHS atoms in exact field order
6. stop when the worklist is empty
```

It does not repeatedly rescan every rule, precompute every subset closure,
store transitive closure as normative authority, or add a global memoization
cache. Composite LHS rules fire only after every determinant arrives. Cycles
terminate because each field is enqueued only when newly added.

## Lax Query Boundary

Direct LAX facts and masks remain in the same exact basis/index. There is no
general lax closure and no automatic chain across strength modes.

```text
direct lax dependency != transitive closure edge
```

Slice 5 does not silently apply:

```text
lax -> lax
strict -> lax
lax -> strict
```

Slice 7 may derive an exact operator-context upgrade when determinant non-null
authority exists. Until then, LAX facts remain direct evidence only.

## Determination Results And Proof Witnesses

`strictly_determines(...)` accepts one exact compiled index, one typed seed,
and one typed requested target set. Its closed answer is:

```text
PROVEN
NOT_PROVEN
```

```text
NOT_PROVEN != DISPROVEN
```

Absence from the current basis is lack of proof, not a counterexample.

A successful closure retains one `ProjectStrictClosureProofStep` for each
direct STRICT fact that first adds fields. Exact direct-rule order is the
tie-breaking authority; derived fields follow exact output order. An
alternative rule that adds no new field creates no duplicate proof step.

```text
one deterministic witness != every proof tree
proof witness != semantic identity
```

Proof sharing never alters a candidate premise or merges its authored support
occurrences.

## Completeness Ordering And Isolation

`ProjectValueFDBasisSet` covers every concrete Source output exactly once in:

```text
selected-module order
source occurrence order
candidate-key frontier order
exact output field order
```

No lexicographic sorting participates. One unavailable source is skipped
without changing independent bases. The basis set validates every non-trivial
candidate premise and exact complement; it derives no new candidate key and
does not choose a primary or shortest key.

```text
Slice-4 candidate frontier remains authoritative
```

## Compatibility And Production Delta

The only production addition is the standalone private
`src/pietto/_project/project_value_fds.py` owner with empty `__all__`.

There is zero delta for:

```text
UNIQUE syntax and row-key semantics
relationship declarations and conditions
grammar / AST / generated parser
public SemanticModel / ProjectSemanticResult fields
script IR / SQL
Project IR operator algebra and transfer
CLI / JSON / Project Explain
grain / cardinality / fanout / JOIN authority
package / workflow / dependencies / version
```

General authored FD declarations remain Phase 66. Catalog-derived FD evidence
remains Phase 69. Existing-operator FD derivation and transfer remain Slice 7.

## Focused Assurance

Focused tests prove:

```text
STRICT candidate key -> STRICT direct FD
LAX candidate key -> LAX direct FD
dependent tuple = exact output fields minus determinant
all-field key -> no non-trivial FD
one merged candidate with two authored supports -> one FD and both supports
exact field universe and output order
same mask in different universes never aliases
70-field arbitrary-width masks and closure
concrete source without keys -> valid empty basis/index
strict A->B and B->C -> closure(A) contains C
multiple rules reach fixed point
cycles terminate
composite determinant requires every LHS atom
direct lax fact retained but excluded from strict closure
mixed lax/strict chain is not traversed
PROVEN and epistemic NOT_PROVEN
cross-universe query rejected
deterministic one-witness rule-order tie breaking
non-concrete output cannot erase independent bases
candidate keys remain unchanged
no table/query/operator transfer or grain/cardinality/fanout/JOIN authority
private/static/public-boundary and contract closure
```

Tests use isolated temporary project roots and remain serial/xdist, order,
cwd/environment, and Python 3.12/3.13 compatible. Static assurance uses the
shared repository-fact acquisition owner.

## Slice 6 Handoff

Slice 5 leaves exact private readiness for:

```text
exact source row-output scopes
exact ordered field universes
strict/lax row-key facts
strict/lax direct value-FD basis
targeted strict closure
compact bitset indexes
exact dependency provenance
```

The sole next owner after successful publication is **Phase 62 Slice 6 —
Factorized Intrinsic Grain Basis, Grain Dependencies, Optional Factors, And
GLOBAL Grain**.

```text
Value FD kernel != GrainDependency kernel
```

Slice 6 may consume key/FD facts but must use a distinct grain-dependency
identity. Slice 6 is not implemented here.

## Review And Repair Accounting

The original Slice-5 review allowed and consumed one bounded repair batch on
the original eight-path candidate for:

```text
STRICT_CLOSURE_WITNESS_AUTHORITY_IS_NOT_CLOSED_OVER_NORMATIVE_RULE_ORDER_AND_CAUSAL_REPLAY
```

The repair makes simultaneously ready rules use normative direct-rule order
rather than seed-field queue order and makes the result carrier replay every
causal proof step to the exact fixed point.

The failed first authoritative validator then exposed one historical-reader
false positive. The corrective continuation adds only the ninth path and
authorizes exactly one additional repair batch for:

```text
PHASE33_WHOLE_SOURCE_SUBSTRING_READER_CONFUSES_INTERNAL_IDENTIFIER_SUBSTRING_WITH_FORBIDDEN_PROJECT_COMPILATION_CAPABILITY
```

The Phase-33 repair uses structured exact Python identifier detection. A real
`compile_project` definition, call, attribute, or import remains forbidden;
comments, string literals, and longer unrelated identifiers do not match.

```text
Slice 5 repair batches allowed cumulatively: 2
Slice 5 repair batches used cumulatively: 2
```

This is terminal `2/2` accounting, not a reset. A tenth path, public/grammar/
operator/grain expansion, third root, or third repair is
`ARCHITECTURE_DECISION_REQUIRED`. Recurrence after repair is
`REVIEW_RECURRENCE`.

## Gate Lifecycle And Publication

The publication candidate state is:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slices 1-4 = COMPLETED / PUBLISHED
Slice 5 = CURRENT / PUBLICATION CANDIDATE
Slices 6-16 = NOT STARTED
```

The failed preserved candidate consumed the first authoritative validator
start only on the Phase-33 historical substring reader. The corrective
continuation authorizes exactly one additional and final start:

```text
authoritative validator starts allowed cumulatively: 2
authoritative validator starts consumed before correction: 1
maximum cumulative validator accounting: 2/2
```

After focused/lifecycle/reader closure and fresh complete review, start the
second/final authoritative validator exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Gate 3 requires the exact reviewed seal, one ordinary commit, one fast-forward
push, and one natural exact-head `push/main` CI attempt without dispatch,
rerun, or cancellation. Python 3.12/3.13 plus generated, golden, and package
smoke must succeed.

The commit subject is:

```text
Add Phase 62 value functional dependencies
```

The PASS title is:

```text
PASS — PHASE62_SLICE5_STRICT_LAX_VALUE_FD_BASIS_COMPACT_INDEXES_TARGETED_CLOSURE_END_TO_END
```

Successful natural exact-head CI establishes without a status-only commit:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slices 1-5 = COMPLETED / PUBLISHED
Slices 6-16 = NOT STARTED

Phase 62 Slice 6
= NEXT / NOT IMPLEMENTED
```

Do not begin Slice 6.
