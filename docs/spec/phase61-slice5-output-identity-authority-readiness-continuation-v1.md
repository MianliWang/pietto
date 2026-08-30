# Phase 61 Slice 5 Output Identity Authority Readiness Continuation v1

## Answer And Exact Owner

This unnumbered continuation resolves the Slice 5 prerequisite blocker:

```text
RELATION_OUTPUT_IDENTITY_COUPLED_TO_DIRECT_LINEAGE_AVAILABILITY
```

It extends the existing private module-attribution authority with complete
semantic relation-output field attribution. It does not implement any Project
IR builder and does not complete Slice 5.

The exact production owner remains:

```text
src/pietto/_project/module_attribution.py
```

`ProjectModuleRowFieldIdentity` remains the single canonical row-field identity
domain. The new carrier is `ProjectModuleRelationOutputFieldAttribution`.

| Surface | Continuation result |
| --- | --- |
| Complete table/query semantic output attribution | `ADDED` |
| Existing direct/renamed identity objects | `REUSED` |
| Legacy row-lineage status/path semantics | `UNCHANGED` |
| New row-field identity domain | `0` |
| Project IR builder/allocation | `0` |
| Phase 61 route change | `0` |
| SQL/CLI/public schema/Project Explain | `0` |
| Version | `0.1.0` |

## Starting Authority And Observed Blocker

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `6359867c7e9c51d9b59bd23642d7bd2492b24862` |
| Tree | `ba3d57d0b7217cbf4ec47c2ec6b4fae40c8a3d02` |
| Parent | `be984f7ae9c0821cfa14229da99bf9c8da97a048` |
| Subject | `Add Phase 61 Project IR operator algebra` |
| Natural exact-head CI | `33317947197`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |
| Tag/signature/Release | no HEAD tag, unsigned commit, no GitHub Release |

The live read-only reproduction used real parsed/analyzed Project facts:

| Relation family | Final semantic row | Legacy attribution lineage |
| --- | --- | --- |
| direct projection | `CONCRETE`, 3 fields | `CONCRETE`, 3 field identities |
| grouped output | `CONCRETE`, 2 fields | `DEFERRED_PHASE48_BEHAVIOR`, 0 field identities |
| grouped/window output | `CONCRETE`, 3 fields | `DEFERRED_PHASE48_BEHAVIOR`, 0 field identities |

The previous stop was therefore correct: Slice 5 could not expose canonical
grouped/window scalar outputs without synthesizing field identity outside its
authority.

Successful Slice 4 CI establishes:

```text
Phase 61 = ACTIVE
Slices 1-4 = COMPLETED
Slice 5 = NEXT / UNSTARTED
```

## Frozen Reader And Changed-path Closure

Fixed-point closure covered semantic-fact construction, the attribution
authority/fact-set/products/lookups, `ProjectSemanticResult`, the two downstream
readers that bind attribution and semantic roots, historical static carrier
readers, lifecycle/readers of lifecycle, product-test glob readers, and exact
Python source/test count readers. The frozen allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice5-output-identity-authority-readiness-continuation-v1.md
docs/status.md
src/pietto/_project/model.py
src/pietto/_project/module_attribution.py
src/pietto/_project/module_inspection.py
src/pietto/_project/module_package_neutral_identity.py
tests/test_active_phase_lifecycle.py
tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py
tests/test_phase61_slice5_output_identity_authority_readiness_continuation.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M9/D0`. No production module is added. Existing Phase 61 workflow
and repository-reader tests discover the new product test dynamically.
`tests/test_active_phase_lifecycle.py` remains the sole direct reader of mutable
status/roadmap. A twelfth path is `READER_CLOSURE_DRIFT`.

The corrected clean pre-write focused baseline was `217 passed`.

## Identity And Lineage Architecture Decision

Freeze:

```text
output-field occurrence identity != row-lineage availability
```

The architecture decision is:

1. `ProjectModuleRowFieldIdentity` remains the single canonical row-field
   identity domain.
2. `ProjectModuleAttributionFactSet.relation_output_fields` owns every current
   concrete table/query final output identity.
3. Existing `ProjectModuleRelationLineage` independently retains its current
   `CONCRETE`, `UNKNOWN`, `DEFERRED`, or `BLOCKED` status and paths.
4. Concrete output attribution does not imply concrete lineage.
5. No aggregate/window/computed projection kind or fake source-root path is
   created.

`ProjectIRFieldAnchor` continues to wrap only
`ProjectModuleRowFieldIdentity`; no identity union is introduced.

## Complete Semantic Output Attribution

`ProjectModuleRelationOutputFieldAttribution` retains exactly:

```text
one canonical ProjectModuleRowFieldIdentity(RELATION_OUTPUT)
+ one exact ProjectModuleRelationSemanticFacts authority
+ the exact ProjectRowField object at that final semantic position
```

Its local validation requires a concrete `TABLE` or `QUERY` semantic result,
the exact owner occurrence, a dense in-range field position, matching name, and
the same semantic field object retained by the final schema.

Canonical construction iterates only the complete ordered semantic fact set:

```text
semantic dependency-order environments
-> source-ordered relation facts
-> exact final semantic row-field order
```

For every concrete table/query final row, it creates exactly one attribution
per field at positions `0..n-1`. Non-concrete final rows create none. Source
field origin/identity authority is unchanged.

Construction uses no caller subset, name lookup, sorting, deduplication, SQL,
AST reanalysis, content/path/hash identity, or winner selection.

## Legacy-lineage Reconciliation

When legacy row lineage is concrete, canonical output attribution reuses the
existing `ProjectModuleRowFieldLineage.field` identity objects one-for-one and
in exact order. Complete semantic field cardinality/name/position validation is
then performed by each attribution carrier.

When semantic output is concrete but legacy lineage is deferred, canonical
identities are formed from the complete exact semantic row authority while the
legacy lineage remains deferred with no fabricated paths.

Freeze:

```text
no AGGREGATE projection hop
no WINDOW projection hop
no COMPUTED direct-lineage hop
no fake source-root path
```

A concrete-lineage cardinality/order/identity mismatch is a hard invariant
failure. It is never repaired by choosing a matching name or position.

## Build Direction And Root Integrity

The live build order is retained and made explicit:

```text
relation resolution -> semantic facts -> attribution completion
```

`_build_project_module_attribution_fact_set` now requires the exact existing
`ProjectModuleSemanticFactSet`. `_ProjectModuleAttributionAuthority` retains
that object as an immutable private root and derives all output attributions
from it.

`ProjectSemanticResult` verifies that its attribution authority retains its
exact semantic-fact object. The package-neutral identity and module-inspection
readers first preserve their historical diagnostic ordering, then also verify
the coupled attribution/semantic root.

Semantic-fact construction does not import or depend on the new attribution
product. The dependency remains acyclic and no ambient/global lookup exists.

## Fact-set Integrity And Lookup

`ProjectModuleAttributionFactSet` retains one exact ordered
`relation_output_fields` tuple and immutable indexes:

```text
exact relation occurrence -> complete ordered output attributions
exact ProjectModuleRowFieldIdentity -> exact attribution tuple
```

`find_relation_output_fields` and `find_relation_output_field` return tuples
only. They select no first/latest/nearest/best result.

Fact-set formation proves:

```text
every concrete table/query semantic row -> complete ordered output collection
every output attribution -> exact owner + exact semantic field evidence
every non-concrete semantic row -> no output attribution
every concrete old lineage -> exact identity-object reconciliation
all supplied collections -> exact canonical authority objects and order
```

Duplicate identities, reordered canonical collections, grafted evidence, and
missing output attributions fail closed.

## Phase 61 Integration Boundary

This continuation changes no Slice 2-4 carrier or identity law. It constructs
no `ProjectIRStructuralStage`, `ProjectIRPropertyStage`, or
`ProjectIRLogicalOperatorStage` and performs no snapshot/ref allocation.

The new attribution is the sole downstream authority Slice 5 may later consume
for exposed final scalar outputs. Slice 5 still may not reconstruct identities.

Phase 61 route remains exactly 12 slices. This publication is an unnumbered
prerequisite, not a new Slice and not Slice 5 completion.

## Determinism Immutability And Privacy

The new carrier is frozen, slotted, and keyword-only. Collections are exact
tuples in existing semantic order. Lookup indexes are immutable mapping proxies
over complete tuple buckets.

Formation uses no registry, singleton, global counter, UUID, random value, cwd,
hash iteration, content identity, ambient current project, I/O, or fallback
resolver. Equal field names in different relation occurrences remain distinct
through their exact owner occurrence identities.

The same project produces the same canonical attribution coordinates across
hash seeds and unrelated cwd values.

## Focused Assurance Contract

Focused tests use real parsed/analyzed explicit-module Project facts. They prove:

```text
direct projection identities remain the exact existing lineage objects
renamed projection identities remain the exact existing lineage objects
grouped semantic outputs are complete while legacy lineage remains deferred
aggregate-only semantic outputs are complete while legacy lineage remains deferred
window semantic outputs are complete while legacy lineage remains deferred
mixed group/aggregate/window fields retain exact final order/types/evidence
non-concrete semantic relations create no output attributions
same names in different relations remain occurrence-distinct
lookups are tuple-backed, immutable, complete, and winner-free
semantic -> attribution -> downstream root identity is exact
there is no second identity type or fake lineage projection kind
hash seed and cwd do not affect formation
Project IR, package projection, SQL, CLI, and public surfaces remain unchanged
```

Existing Phase 54 attribution, package-neutral identity, module inspection, and
Phase 59 integration tests remain part of focused closure. Temporary paths are
pytest-owned and subprocesses are isolated for xdist/serial compatibility.

## Integration Non-goals

This continuation adds no Project IR builder, snapshot cursor, ref allocation,
canonical relation pipeline, upstream traversal, cross-relation use, Project
DAG, JOIN, grain/fanout, nested/correlated plan, optimizer, verifier,
inspection feature, serializer, estimator, cost model, physical planning,
parser/AST/grammar, diagnostic, SQL, CLI, JSON, public schema, Project Explain
field, package-graph behavior, persistent identity, backend behavior, Rust
implementation, tag, Release, signing, or attestation.

It does not change grouped/window lineage status, fabricate aggregate/window
lineage, broaden `ProjectModuleProjectionKind`, or add a second sidecar.

## Slice 5 Resume Handoff

After successful natural exact-head CI:

```text
Phase 61 route remains 12 slices
Slices 1-4 remain completed
output-identity continuation = COMPLETED
Slice 5 remains next / unstarted
```

The only next owner is again:

```text
Phase 61 Slice 5 — Canonical Single-Relation Construction From Existing Project Semantic Facts
```

Slice 5 may consume `find_relation_output_fields` but may not reconstruct those
identities. The builder is not begun here.

## Gate Lifecycle And Publication

Gate 2 uses focused tests, Ruff, and Pyright; performs one complete candidate
review; permits at most one same-root repair batch; performs a fresh rereview;
and runs exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Local package smoke is required because packaged production source changes.
Generated and golden auxiliaries are not locally required because no input
surface changes; natural CI still runs them.

Gate 3 rebinds the predecessor, stages exactly the sealed tree, makes one
ordinary commit, performs one fast-forward push, and observes the unique
natural exact-head CI without dispatch or rerun.

The exact commit subject is:

```text
Add complete Project relation output identities
```

The published PASS title is:

```text
PASS — PHASE61_SLICE5_OUTPUT_IDENTITY_AUTHORITY_READINESS_CONTINUATION_END_TO_END
```

Successful natural exact-head CI completes only this readiness continuation.
Slice 5 remains next / unstarted.
