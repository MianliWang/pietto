# Phase 62 Slice 4 UNIQUE Null Policy, Evidence Trust, Strict/Lax Row Uniqueness, And Candidate Keys v1

## Answer And Exact Owner

Slice 4 adds the smallest private Project row-key foundation:

```text
authored Shape UNIQUE declaration
-> exact UNIQUE declaration occurrence
-> exact application to one Source row output
-> trusted authored row-uniqueness evidence
-> direct non-dominated candidate-key frontier
```

The exact owner is authored `NULLS_DISTINCT`, strict/lax row uniqueness,
evidence origin/trust/enforcement, Shape-to-Source application identity, and
candidate keys derived only from direct trusted uniqueness evidence.

```text
Shape UNIQUE declaration
!= row-uniqueness evidence occurrence
!= derived candidate-key fact
```

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD / `main` / `origin/main` | `933a13ea6ecb5e2701f7360fc5220ed3884ace18` |
| Tree | `2fb40f3c3b64ef68ecc00156621f94b02cd3db21` |
| Parent | `18baeb56b3c27488a4fc4791ff274213386c43f9` |
| Subject | `Add Phase 62 relationship field correspondences` |
| Natural exact-head CI | `33469961091`, `push`, `main`, attempt `1`, successful |
| CI jobs | Python 3.12 successful; Python 3.13 successful |
| Downstream CI | generated, golden, and package smoke successful on both jobs |
| Divergence | `0/0` |
| Worktree/index/untracked | clean / clean / empty |
| Active Git operation | none |

The predecessor establishes:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slice 2 = COMPLETED / PUBLISHED
Slice 3 = COMPLETED / PUBLISHED
Slice 4 = NEXT / NOT IMPLEMENTED
```

## Frozen Reader And Changed-path Closure

The exact fixed-point changed-path set is:

```text
docs/language.md
docs/roadmap.md
docs/spec/phase62-slice4-unique-null-policy-evidence-trust-strict-lax-row-uniqueness-candidate-keys-v1.md
docs/status.md
src/pietto/_project/project_row_keys.py
tests/test_active_phase_lifecycle.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_phase62_slice4_unique_null_policy_evidence_trust_strict_lax_row_uniqueness_candidate_keys.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M6/D0`. `tests/test_active_phase_lifecycle.py` remains the sole
direct mutable roadmap/status reader. The Slice-1 live-source assurance now
acknowledges the delivered private row-key owner while preserving its
historical contract. Validator inventory accounts for one production and one
test file. A tenth path is `READER_CLOSURE_DRIFT`.

## Existing UNIQUE Admission Authority

The authored syntax remains unchanged:

```pietto
unique user_id_key on user_id
unique tenant_user_key on tenant_id, user_id
```

Slice 4 calls the existing `check_shape_structures(...)` owner once per exact
module Script. It retains returned `PIE-S2501`, `PIE-S2502`, and `PIE-S2503`
objects exactly. It does not copy the checker.

`ProjectUniqueDeclarationOccurrence` retains one exact Shape declaration
occurrence, exact shape-item position, exact `UniqueDef`, and every exact
blocking semantic diagnostic. Same-name collision diagnostics are projected
to all involved UNIQUE occurrences so a first declaration cannot become a
hidden winner. Unknown or repeated targets invalidate only their exact UNIQUE;
another admitted UNIQUE remains independently usable.

No structurally invalid UNIQUE produces concrete evidence or a partial
determinant tuple.

## Declaration Application And Evidence Identity

`ProjectUniqueDeclarationIdentity` is:

```text
exact Shape declaration occurrence identity
+ exact authored Shape-item position
```

It is not the UNIQUE name or determinant tuple. Two distinct declarations over
the same fields remain distinct.

`ProjectRowUniquenessEvidenceIdentity` adds one exact Source declaration
occurrence. Therefore one reusable Shape UNIQUE applied to two Sources yields:

```text
one UNIQUE declaration occurrence
two distinct row-uniqueness evidence occurrences
```

```text
constraint declaration != constraint application/use
UNIQUE declaration identity != determinant field set
```

Names, hashes, canonical bytes, object addresses, lexicographic order, and
field sets are not declaration or application identity.

## Shape To Source Authority Chain

Construction follows only existing authority:

```text
exact Project module catalog Shape occurrence
-> exact UniqueDef shape-item occurrence
-> exact Source occurrence
-> exact ProjectResolvedModuleSourceShapeReference
-> exact concrete ProjectModuleRelationSemanticFacts source row output
-> exact ProjectModuleSourceFieldOrigin values
-> exact ProjectRowField values
-> exact Slice-3 ProjectExactRowOutputConstraintScope
```

Imported Shapes use the existing source-shape resolution and its exact target
occurrence. There is no all-module name scan, spelling match, current-module
global, backend schema, or SQL lookup.

Direct authored Shape UNIQUE evidence is applied only to exact concrete
`SourceDef` row outputs. It is not copied to table, query, filter, projection,
grouped, JOIN, or other downstream outputs. Slice 7 owns transfer.

```text
Shape contract != relation multiplicity
source Shape contract != automatically transferred downstream key
```

## Pietto UNIQUE NULL Policy

The closed private vocabulary is:

```text
NULLS_DISTINCT
NULLS_NOT_DISTINCT
```

Current authored syntax constructs only `NULLS_DISTINCT`. This is a Pietto
language law independent of PostgreSQL/MySQL defaults, selected dialect,
runtime catalog, or physical index behavior. No grammar is added for
`NULLS_NOT_DISTINCT`.

```text
authored UNIQUE null policy != backend UNIQUE implementation
```

## Strict And Lax Row Uniqueness

`NULLS_DISTINCT` provides standard-equality/lax row uniqueness while any exact
determinant nullability is `NULLABLE` or `UNKNOWN`. NULL-containing determinant
tuples do not necessarily violate the authored contract.

It upgrades to effective `STRICT` only when every determinant's exact scoped
source-row `ProjectRowFieldNullability` is `NON_NULL`:

```text
NULLS_DISTINCT + all determinant fields NON_NULL -> STRICT
NULLS_DISTINCT + any determinant NULLABLE/UNKNOWN -> LAX
```

Unknown is never interpreted as non-null. Lax evidence is retained; it remains
a future at-most-one premise for ordinary standard equality, where NULL never
produces TRUE.

The exact determinant tuple retains authored target order, exact Shape field,
exact Shape-field identity, exact source-row identity, exact semantic field,
type/nullability, exact output scope, and source-shape provenance.

```text
strict row uniqueness != lax row uniqueness
nullable/lax UNIQUE != unusable evidence
```

## Evidence Origin Trust And Enforcement

Origin is closed over:

```text
AUTHORED_CONTRACT
CATALOG_CONSTRAINT
DERIVED_THEOREM
RUNTIME_OBSERVATION
UNVERIFIED_HINT
```

Trust is closed over `TRUSTED`, `UNTRUSTED`, and `CONFLICT`. Enforcement is
separate as `MODEL_CONTRACT`, `CATALOG_ENFORCED`, or `RUNTIME_OBSERVED`.

Slice 4 constructs exactly:

```text
origin      = AUTHORED_CONTRACT
trust       = TRUSTED
enforcement = MODEL_CONTRACT
```

This trust does not vary across loose/checked/strict modes. Successful authored
semantic admission makes a trusted Pietto model premise; it does not claim
database verification or runtime observation.

```text
trusted model premise != empirically verified database fact
model contract != catalog-enforced constraint != runtime-observed property
```

## Exact Row-output Scope And Determinants

Each concrete evidence occurrence binds one
`UNCONDITIONAL_ON_EXACT_ROW_OUTPUT` scope from Slice 3 whose owner and semantic
root are the exact source occurrence. Conditional scope vocabularies remain
unconstructed.

Raw target strings are never the normative determinant representation.
`ProjectUniqueDeterminantField` retains the exact authored position, Shape
`FieldDef`, `ProjectModuleSourceFieldOrigin`, source and Shape field identities,
and exact `ProjectRowField`. No duplicate elimination occurs; duplicates were
already rejected by the existing semantic checker.

No bitset or dense index is needed in Slice 4. A future compiled set may use
positions, but a bit position is never field identity.

## Non-concrete Subjects

`ProjectNonConcreteRowUniquenessSubject` preserves typed `UNKNOWN`,
`DEFERRED`, `BLOCKED`, or `AMBIGUOUS` outcomes for:

```text
invalid authored UNIQUE
unknown/ambiguous/blocked source Shape resolution
unknown/deferred/blocked source row schema
missing/conflicting determinant authority
missing/conflicting exact source semantic authority
```

An unresolved source Shape has no fabricated UNIQUE application identity.
Resolved invalid applications retain exact UNIQUE diagnostics. Resolved source
failures retain their exact resolution and semantic roots when available.
Every non-concrete state/reason pair is derived from that exact causal root;
mixed diagnostics, resolution issues, row states, and determinant failures are
rejected.

One failed application never removes a valid UNIQUE on the same source or a
valid application on another source. No partial determinant evidence is
published.

## Candidate-key Facts And Frontier

A candidate key is one derived non-empty row-uniqueness fact on an exact source
output. It is not a PRIMARY KEY, an authored UNIQUE occurrence, or an evidence
occurrence.

```text
candidate key != primary key != authored UNIQUE occurrence
candidate-key fact != row-uniqueness evidence occurrence
```

Candidate identities retain exact output owner, determinant field set in
source-output order, and `STRICT`/`LAX` strength. They are built only from
actual trusted concrete evidence; no field subset is enumerated.

Dominance is exactly:

```text
A dominates B
iff A.fields is a subset of B.fields
and A.strength is at least B.strength

STRICT > LAX
```

The complete non-dominated antichain is retained. No primary, shortest, first,
or lexicographic winner is selected. Multiple incomparable keys remain. Every
evidence occurrence supporting the same determinant/strength fact remains in
exact authority order.

```text
candidate-key set = antichain, not winner
```

## No FD Or Later-owner Inference

Candidate minimization uses direct uniqueness dominance only:

```text
Slice-4 key frontier = uniqueness-based frontier only
```

Slice 4 adds no value FD, closure, key transfer, max-one-row inference, empty
key, grain, referential coverage, cardinality, relationship match guarantee,
fanout, path, JOIN, or Project IR behavior.

```text
row uniqueness evidence != Value FD != intrinsic grain
row-key authority != FD authority
key evidence != directional match guarantee
max-one-row != authored UNIQUE
empty key != GLOBAL grain
```

Slice 5 owns strict/lax value-FD basis and targeted closure. Slice 7 owns
operator transfer. Slice 8 owns directional match guarantees/cardinality.

## Compatibility And Production Delta

The only production addition is the standalone private
`src/pietto/_project/project_row_keys.py` owner with empty `__all__`.

There is no change to:

```text
grammar / AST / generated parser
existing Shape structural diagnostics or ordering
public SemanticModel
script ShapeUniqueIR / RelationIR / ScriptIR
PostgreSQL / MySQL SQL
ProjectSemanticResult fields
relationship condition semantics
Project IR eight-operator algebra
CLI / JSON / Project Explain
package / dependency / workflow / version
```

Current UNIQUE source bytes remain compatible. Language documentation records
the Pietto `NULLS_DISTINCT` model-contract default without claiming physical
enforcement.

## Focused Assurance

Focused tests prove:

```text
current UNIQUE syntax unchanged
Pietto authored UNIQUE default = NULLS_DISTINCT
one exact UNIQUE declaration occurrence
one Shape reused by two Sources -> two distinct evidence applications
local and imported Shape applications
exact source-output field identities and provenance
NON_NULL determinants -> STRICT
NULLABLE/UNKNOWN determinant -> LAX
loose/checked/strict modes retain trusted authored model evidence
composite authored determinant order
same-field UNIQUE declarations remain distinct evidence
invalid missing/repeated/colliding UNIQUE produces no evidence
unresolved/ambiguous/non-concrete source terminals
failed application does not erase independent evidence
STRICT/LAX direct dominance
complete incomparable candidate frontier
same derived candidate retains every support occurrence
no empty key or hidden shortest/lexicographic winner
no table/query key propagation
no FD/grain/cardinality/fanout/JOIN authority
cwd/environment independence and detached-root rejection
non-concrete state/reason/payload consistency
```

Focused closure also retains existing Shape semantics, source-shape resolution,
source field attribution, Slice-3 scope, script IR/SQL, lifecycle, and reader
tests. Tests remain serial, xdist, order, cwd/environment, and Python 3.12/3.13
compatible.

## Slice 5 Handoff

Slice 4 leaves Slice 5 exact private readiness for:

```text
exact scoped source-row outputs
exact determinant field identities
trusted authored UNIQUE evidence
strict/lax row-uniqueness strength
complete candidate-key frontier
exact nullability premises
exact evidence provenance
```

The only next owner after successful publication is **Phase 62 Slice 5 —
Strict/Lax Value-FD Basis, Compact Indexes, And Targeted Closure**. Slice 5 may
derive value-FD facts but must not replace or mutate Slice-4 evidence.

## Review And Repair Accounting

Prior Slice repair accounting is terminal and is not reused. Slice 4 allows at
most one bounded repair batch after the complete finding set is frozen, only
for the same root, owner, and nine-path closure.

```text
Slice 4 repair batches allowed: 1
Slice 4 repair batches used after complete review: 1
```

The single repair root is:

```text
SLICE4_APPLICATION_LEDGER_SPLITS_NON_CONCRETE_CAUSAL_VALIDATION_FROM_CANONICAL_APPLICATION_ORDER
```

A second path set, authored grammar, public schema, FD, operator transfer,
cardinality, route change, or second repair is
`ARCHITECTURE_DECISION_REQUIRED`. Recurrence after repair is
`REVIEW_RECURRENCE`.

## Gate Lifecycle And Publication

The publication candidate state is:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slice 2 = COMPLETED / PUBLISHED
Slice 3 = COMPLETED / PUBLISHED
Slice 4 = CURRENT / PUBLICATION CANDIDATE
Slices 5-16 = NOT STARTED
```

After focused closure and fresh rereview, start exactly one authoritative
validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Gate 3 requires the exact reviewed seal, one ordinary commit, one fast-forward
push, and one natural exact-head `push/main` CI attempt without dispatch,
rerun, or cancellation. Python 3.12/3.13 plus generated, golden, and package
smoke must succeed.

The commit subject is:

```text
Add Phase 62 row uniqueness and candidate keys
```

The PASS title is:

```text
PASS — PHASE62_SLICE4_UNIQUE_NULL_POLICY_EVIDENCE_TRUST_STRICT_LAX_ROW_UNIQUENESS_CANDIDATE_KEYS_END_TO_END
```

Successful natural exact-head CI establishes without a status-only commit:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slice 2 = COMPLETED / PUBLISHED
Slice 3 = COMPLETED / PUBLISHED
Slice 4 = COMPLETED / PUBLISHED
Slices 5-16 = NOT STARTED

Phase 62 Slice 5
= NEXT / NOT IMPLEMENTED
```
