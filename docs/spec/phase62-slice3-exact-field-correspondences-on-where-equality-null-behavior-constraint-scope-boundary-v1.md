# Phase 62 Slice 3 Exact Field Correspondences, ON/WHERE Separation, Equality/Null Behavior, And Constraint-Scope Boundary v1

## Answer And Exact Owner

Slice 3 adds the smallest authored/private field-correspondence foundation:

```text
relationship declaration
-> optional authored base-match clause
-> ordered exact endpoint-field equality correspondences
-> exact Project field/output authority
-> standard equality and conservative NULL behavior
-> separate condition and constraint scopes
```

It adds no key, FD, grain, cardinality, path, fanout, JOIN occurrence, Project
IR JOIN, SQL strategy, or public condition schema.

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD / `main` / `origin/main` | `18baeb56b3c27488a4fc4791ff274213386c43f9` |
| Tree | `f96c34da8b4b7345babe0a8567433f88fec92971` |
| Parent | `998eaa5655bbe64d4ae13b8ac03f413ce84343ff` |
| Subject | `Add Phase 62 relationship identity foundation` |
| Natural exact-head CI | `33466301585`, `push`, `main`, attempt `1`, successful |
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
Slice 3 = NEXT / NOT IMPLEMENTED
```

## Frozen Reader And Changed-path Closure

The fixed-point changed-path set is exactly:

```text
docs/language.md
docs/roadmap.md
docs/spec/phase62-slice3-exact-field-correspondences-on-where-equality-null-behavior-constraint-scope-boundary-v1.md
docs/status.md
grammar/Pietto.g4
src/pietto/_project/project_relationship_conditions.py
src/pietto/ast_builder.py
src/pietto/ast_nodes.py
src/pietto/generated/Pietto.interp
src/pietto/generated/PiettoParser.py
src/pietto/generated/PiettoVisitor.py
tests/test_active_phase_lifecycle.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_phase62_slice3_exact_field_correspondences_on_where_equality_null_behavior_constraint_scope_boundary.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M12/D0`. `tests/test_active_phase_lifecycle.py` remains the sole
direct mutable roadmap/status reader. The Slice-1 live-source assurance accepts
the now-delivered optional condition surface without rewriting its immutable
historical contract. Validator inventory accounts for one production and one
test file. Only `Pietto.interp`, `PiettoParser.py`, and `PiettoVisitor.py`
change under canonical regeneration because the token vocabulary is unchanged.
A sixteenth path is `READER_CLOSURE_DRIFT`.

## Authored Base-match Syntax And AST

Existing endpoint-only declarations remain valid and retain:

```text
base_match = None
```

One optional clause may follow the two endpoints:

```pietto
relationship order_customer:
    endpoint order: Orders
    endpoint customer: Customers
    on order.customer_id == customer.id
```

Pietto's existing standard-equality spelling is `==`. Accepting SQL-style `=`
would either broaden the shared expression grammar or require a second Boolean
grammar, so it is not added. Composite correspondence uses the existing `and`
expression surface:

```pietto
on left.tenant_id == right.tenant_id and left.id == right.left_id
```

`RelationshipMatchClause` retains the exact authored clause span and existing
`Expression` AST. `RelationshipMetadata.base_match` is optional. Existing
`RelationshipSemanticInfo` and `RelationshipSemanticEndpointInfo` remain
unchanged and continue to own endpoint admission only.

```text
missing base match
!= invalid base match
!= unknown field match
```

## Private Carriers And Identity Laws

The dedicated owner is
`src/pietto/_project/project_relationship_conditions.py` with empty `__all__`.

| Carrier | Exact responsibility |
| --- | --- |
| `ProjectRelationshipBaseMatchIdentity` | one condition occurrence subordinate to one exact declaration identity |
| `ProjectRelationshipCorrespondenceIdentity` | one exact authored conjunct position |
| `ProjectRelationshipEndpointFieldReferenceIdentity` | one exact lhs/rhs operand occurrence |
| `ProjectExactRowOutputConstraintScope` | one exact unconditional semantic row output |
| `ProjectRelationshipEndpointFieldReferenceOccurrence` | exact authored reference, endpoint, target semantic fact, field identity, field evidence, and attribution |
| `ProjectRelationshipEqualityCorrespondence` | authored lhs/rhs plus normalized endpoint-0/endpoint-1 pairing |
| `ProjectRelationshipConditionIssue` | one exact conjunct/operand failure identity and retained resolved references |
| `ProjectConcreteRelationshipCondition` | complete non-empty ordered correspondence tuple |
| `ProjectNonConcreteRelationshipCondition` | ABSENT without a fabricated condition identity, or one complete failed condition without partial facts |
| `ProjectRelationshipConditionSet` | every concrete Slice-2 relationship in selected-module/source order |

Identity remains occurrence-safe:

```text
relationship declaration occurrence
!= base-match condition occurrence
!= equality-correspondence occurrence
!= endpoint-field reference occurrence
```

Correspondence identity is exactly condition identity plus authored conjunct
position. Field names, field pairs, hashes, canonical bytes, equality classes,
and operand normalization are not identity. Repeated or reversed equalities are
not deduplicated.

## Exact Field Resolution Authority

Each proof-capable operand is exactly a two-part authored dotted name:

```text
endpoint_role.field_name
```

Resolution follows only:

```text
exact Project relationship endpoint occurrence
-> exact ProjectResolvedModuleRelationSymbol target
-> exact ProjectModuleRelationSemanticFacts final row state
-> exact ProjectModuleRowFieldIdentity
-> exact ProjectRowField
-> exact source-origin or relation-output attribution
```

Sources retain `ProjectModuleSourceFieldOrigin`; tables and queries retain
`ProjectModuleRelationOutputFieldAttribution` directly, independently of
source-lineage availability. Imported endpoints use the already-resolved
target occurrence. There is no all-module search, same-name inference,
alternate compiler, SQL-name lookup, or schema reconstruction.

Self-relationship references remain distinct endpoint-field occurrences even
when their exact relation target and field identity are equal.

## Accepted Shape And Exact Compatibility

A concrete condition is exactly an ordered non-empty conjunction of
`ComparisonExpr(operator="==")` nodes. Every conjunct resolves one field from
endpoint 0 and one from endpoint 1. Authored lhs/rhs order is retained
separately from normalized endpoint order.

Known types are compatible only when their exact current logical identities
match. There is no numeric promotion, implicit cast, backend coercion, or
name-only compatibility. Unknown types, shapes, and currently deferred
`Any`/`Bytes`/`Decimal`/`Json` equality authority remain conservative
`UNKNOWN` rather than becoming proof-capable. Decimal precision/scale equality
compatibility remains with Phase 64.

Known distinct exact types are `BLOCKED`. Slice 3 adds no public or general
comparison compatibility matrix; this rule applies only to private
relationship proof authority.

## Unsupported Conditions And No Partial Extraction

The following never publish proof-capable correspondences:

```text
OR / NOT
non-equality comparisons
LIKE / BETWEEN / IS NULL
calls / arithmetic / literals
same-endpoint equality
three-or-more-part paths
implicit same-name fields
arbitrary residual predicates
```

Top-level `and` is flattened only to retain exact source-ordered conjunct
occurrences. If any conjunct is unsupported, unresolved, ambiguous, or
incompatible, the whole condition is non-concrete and publishes zero
correspondences. All independently discovered issues remain in authored order;
an earlier/later valid candidate is not partially extracted.

## Standard Equality And NULL Laws

The sole concrete semantic tag is:

```text
STANDARD_EQUALITY_TRUE_ONLY_NULL_REJECTING
```

It freezes:

```text
TRUE     -> match
FALSE    -> no match
UNKNOWN  -> no match
NULL on either operand prevents TRUE
```

This is ordinary standard equality, not `IS NOT DISTINCT FROM`, GROUP BY NULL
equality, collation/NaN/coercive equality, or a proof that either field is
globally non-null.

```text
predicate rejects NULL
!= field is globally NOT NULL
```

The exact current `ProjectRowFieldNullability` remains attached to each field
reference independently of null rejection.

## Condition And Constraint Scope Boundaries

The condition scope vocabulary is:

```text
RELATIONSHIP_BASE_MATCH
JOIN_LOCAL_ON_REFINEMENT
POST_JOIN_FILTER
```

Only `RELATIONSHIP_BASE_MATCH` is constructible. No JOIN occurrence or JOIN
syntax is added. Current relation `where` remains a separate row-filter owner.

Constraint scope is a distinct type:

```text
UNCONDITIONAL_ON_EXACT_ROW_OUTPUT
UNDER_PREDICATE
UNDER_POLICY
UNDER_MATCH_CONTEXT
```

Only `UNCONDITIONAL_ON_EXACT_ROW_OUTPUT` has a constructible carrier, bound to
one exact concrete `ProjectModuleRelationSemanticFacts` output. Conditional
forms are vocabulary readiness only.

```text
condition evaluation scope != constraint evidence scope
base-table fact != automatically valid fact on every filtered row output
```

No key, FD, coverage, or cardinality evidence is created.

## Condition States Completeness And Ordering

Condition construction is independent of Slice-2 declaration construction:

```text
ABSENT
CONCRETE
UNKNOWN
BLOCKED
AMBIGUOUS
```

An endpoint-only concrete declaration produces `ABSENT`. Unknown roles,
fields, or unavailable types produce `UNKNOWN`. Unsupported shapes,
same-endpoint equality, and known incompatible types produce `BLOCKED`.
`AMBIGUOUS` is retained as an exact state but no artificial reachable example
is fabricated when existing concrete Slice-2 endpoint/field authorities are
winner-free.

`ABSENT` carries no `ProjectRelationshipBaseMatchIdentity`; no authored
condition occurrence exists. Failed field resolution retains the exact lhs/rhs
operand identity, so two missing operands remain two ordered evidence
occurrences rather than indistinguishable duplicates.

Every concrete Slice-2 relationship has exactly one condition result in exact
selected-module and source order. A failed condition never changes its
relationship declaration into a non-concrete declaration and never removes an
independent condition.

## Compatibility And Later-owner Boundaries

The only grammar/AST change is optional relationship declaration `on`. Exact
canonical generated artifacts are regenerated, never hand-edited. Existing
endpoint-only source remains accepted.

There is zero delta to:

```text
public RelationshipSemanticInfo / RelationshipSemanticEndpointInfo
SemanticModel relationship representation
existing endpoint admission diagnostics and order
script RelationIR / ScriptIR
PostgreSQL and MySQL SQL
ProjectSemanticResult fields
Project IR eight-operator algebra
CLI / JSON / Project Explain
package / dependency / workflow / version
```

Slice 4 owns UNIQUE null policy, evidence trust, strict/lax row uniqueness, and
candidate keys. Slices 5-12 retain FD/grain/coverage/cardinality/path/fanout/
JOIN/Project-IR/multi-fact ownership. Phase 63 owns SQL lowering and further
JOIN forms; Phase 64 owns null-safe/collation/NaN/coercive and advanced-type
comparison; Phase 66 owns relationship import/export; Phase 70 owns public
condition exposure.

```text
field correspondence != key evidence != cardinality evidence
relationship declaration on != authored JOIN use
```

## Focused Assurance

Focused tests prove:

```text
legacy endpoint-only acceptance and ABSENT condition
single and composite equality correspondence
exact authored conjunct and operand order
reversed/repeated equality without identity collapse
self-relationship occurrence-safe fields
local table-output and imported source-field authority
exact final semantic field/output provenance
aggregate/final output identity independent of source-lineage availability
known incompatible and unknown/deferred type conservatism
distinct ordered operand identities for multiple unresolved fields
unknown field/role and same-endpoint rejection
OR, residual, path, literal, and general predicate rejection
no partial extraction from a failed condition
TRUE-only and NULL-rejecting standard equality metadata
nullable field evidence remains nullable
condition-scope and constraint-scope separation
failed condition does not erase an independent concrete condition
cwd/environment independence
public semantic, script IR, and PostgreSQL/MySQL SQL zero delta
no key/FD/grain/cardinality/fanout/JOIN/path authority
generated artifact reproducibility
```

Tests remain serial, xdist, order, cwd/environment, and Python 3.12/3.13
compatible.

## Slice 4 Handoff

Slice 3 leaves Slice 4 exact private readiness for:

```text
exact relationship and condition identities
ordered equality-correspondence identities
exact endpoint-field occurrences and row-output scopes
exact Project field types/nullability
standard equality NULL rejection
complete condition states and issues
```

The only next owner after successful publication is **Phase 62 Slice 4 —
UNIQUE Null Policy, Evidence Trust, Strict/Lax Row Uniqueness, And Candidate
Keys**. Slice 4 is not implemented here.

## Review And Repair Accounting

Slice-1 and Slice-2 repair accounting is terminal and is not reused. Slice 3
allows at most one bounded repair batch after the complete finding set is
frozen, only for the same root, owner, and 15-path closure.

```text
Slice 3 repair batches allowed: 1
Slice 3 repair batches used after complete review: 1
```

The single repair root is:

```text
SLICE3_PROOF_MODEL_USES_CONVENIENT_RESULT_SHAPES_INSTEAD_OF_EXACT_OPTIONAL_OCCURRENCE_AND_FINAL_OUTPUT_AUTHORITY
```

A second path set, public semantic expansion, later owner, route change, or
second repair is `ARCHITECTURE_DECISION_REQUIRED`. Recurrence after repair is
`REVIEW_RECURRENCE`.

## Gate Lifecycle And Publication

The publication candidate state is:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slice 2 = COMPLETED / PUBLISHED
Slice 3 = CURRENT / PUBLICATION CANDIDATE
Slices 4-16 = NOT STARTED
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
Add Phase 62 relationship field correspondences
```

The PASS title is:

```text
PASS — PHASE62_SLICE3_EXACT_FIELD_CORRESPONDENCES_ON_WHERE_EQUALITY_NULL_BEHAVIOR_CONSTRAINT_SCOPE_BOUNDARY_END_TO_END
```

Successful natural exact-head CI establishes without a status-only commit:

```text
Phase 61 = COMPLETED

Phase 62 = ACTIVE
Slice 1 = COMPLETED / PUBLISHED
Slice 2 = COMPLETED / PUBLISHED
Slice 3 = COMPLETED / PUBLISHED
Slices 4-16 = NOT STARTED

Phase 62 Slice 4
= NEXT / NOT IMPLEMENTED
```
