# Phase 61 Slice 4 Current Project IR Operator Algebra v1

## Answer And Exact Owner

Slice 4 implements exactly:

```text
current target-independent logical operator algebra
+ operator attachment to existing plan-node occurrences
+ exact current stage order
+ conservative exact property-transfer proofs
+ narrow exact row-shape requirement compatibility
+ unchanged effect/estimate boundaries
```

The new private owner is:

```text
src/pietto/_project/project_ir_operators.py
```

It composes with one published `ProjectIRPropertyStage` and its unchanged
`ProjectIRStructuralStage` snapshot. It creates no node/ref allocator and no
semantic-facts builder.

Two causal refinements remain in the existing private property owner:

```text
operator-node outputs may reuse the same concrete relation-subject authority
ungrouped exact relation order/static limit may use retained authored authority
```

Neither refinement changes Slice 2 identity, topology, row-shape evidence, or
public behavior.

| Surface | Slice 4 result |
| --- | --- |
| Private logical operator layer | `ADDED` |
| Exact transfer/compatibility layer | `ADDED` |
| Existing structural topology mutation | `0` |
| Node/ref allocation or canonical builder | `0` |
| Aggregate/window evaluation-context construction | `0` |
| Optimizer/verifier/pass manager/estimator | `0` |
| JOIN/grain comparison/fanout/nesting/correlation/recursion | `0` |
| Parser/AST/SQL/CLI/public schema/Project Explain | `0` |
| Version | `0.1.0` |

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `be984f7ae9c0821cfa14229da99bf9c8da97a048` |
| Tree | `c0d4bc91aa1883065427244d5572ba3e2d424b67` |
| Parent | `a9725d46b1c4c79d5e1c78d79a0e042522e1edd3` |
| Subject | `Add Phase 61 Project IR property model` |
| Natural exact-head CI | `33308020119`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |
| Tag/signature/Release | no HEAD tag, unsigned commit, no GitHub Release |

The unique successful natural CI on that exact Slice 3 publication establishes:

```text
Phase 61 = ACTIVE
Slices 1-3 = COMPLETED
Slice 4 = NEXT / NOT IMPLEMENTED
```

Mutable lifecycle prose is advanced without a status-only predecessor commit.

## Frozen Reader And Changed-path Closure

Fixed-point closure covered the two private production owners, immutable Slice 4
contract, existing Slice 3 product reader, new Phase 61 product glob member,
mutable lifecycle owner, changed-path inventories, exact Python source/test count
reader, package discovery, and readers of those readers. The frozen allowlist is:

```text
docs/roadmap.md
docs/spec/phase61-slice4-project-ir-current-logical-operator-algebra-exact-property-transfer-v1.md
docs/status.md
src/pietto/_project/project_ir_operators.py
src/pietto/_project/project_ir_properties.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice4_project_ir_current_logical_operator_algebra_exact_property_transfer.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M5/D0`. Existing Phase 61 workflow/read-acquisition tests discover
the new product test through `test_phase61_slice*.py`; private package modules
remain dynamically discovered. `tests/test_active_phase_lifecycle.py` remains
the sole direct reader of mutable `docs/status.md` and `docs/roadmap.md`. A ninth
path is `READER_CLOSURE_DRIFT`.

The clean pre-write focused baseline was `72 passed`.

## Live Current Semantic Authority Audit

| Current stage | Exact retained evidence | Slice 4 use |
| --- | --- | --- |
| Relation Input | exact source declaration or derived `ProjectResolvedModuleRelationReference` | one target-independent `RELATION_INPUT`; no physical scan/access choice |
| Row Filter | exact owner `WhereClause`, typed predicate analysis, and concrete relation semantic facts | one `ROW_FILTER`; row membership only |
| Group/Aggregate | concrete `ProjectAggregateGroupedClauseReadiness`, complete group-key and aggregate-result facts | one combined `GROUP_AGGREGATE` |
| Result Filter | exact `SatisfyingClause` plus complete concrete `SATISFYING` candidate facts | one post-group `RESULT_FILTER` |
| Window Evaluation | complete concrete `ProjectModuleWindowOutputFact` and retained `WindowResultProjectFact` | one `WINDOW_EVALUATION`; window-local order remains local |
| Final Projection | complete source-ordered `ProjectModuleSelectFact` collection | one `FINAL_PROJECTION` |
| Relation Ordering | exact owner `OrderByClause`; grouped forms additionally retain complete concrete `GROUPED_ORDER` facts | one `RELATION_ORDERING` and exact provided ordering |
| Limit | exact static integer `LimitClause` under the existing semantic range | one `LIMIT` and exact upper bound |

`RelationIR`, semantic analysis, aggregate/window helpers, and SQL lowering
confirm the sequence and effects but are not stored as Project IR authority.
`ProjectModuleRelationSemanticFacts` retains the exact authored definition and
the Project-owned evidence consumed here.

The audit found no target-independent current effect catalog and no estimate
producer. PostgreSQL volatility remains backend-specific and unused.

## Frozen Current Operator Algebra

`ProjectIRLogicalOperatorKind` contains exactly:

```text
Relation Input
-> Row Filter
-> Group/Aggregate
-> Result Filter
-> Window Evaluation
-> Final Projection
-> Relation Ordering
-> Limit
```

Absent authored stages are omitted. Derived relations always retain Relation
Input and Final Projection; source declarations use one logical Relation Input
leaf. No placeholder/no-op operator exists.

Operator meanings are frozen:

- Relation Input retains exact relation/source resolution, never scan,
  materialization, CTE, index, or physical access strategy.
- Row Filter is only current `where` and differs from Result Filter.
- Group/Aggregate remains one combined current stage; Phase 65 algebra/state is
  absent.
- Result Filter is only grouped `satisfying`.
- Window Evaluation uses exact validated window outputs and preserves current
  row multiplicity.
- Final Projection uses the complete source-ordered selected outputs and remains
  BAG-preserving.
- Relation Ordering is the only current positive relation-result ordering
  establishment stage.
- Limit uses the exact validated static integer and establishes an upper bound;
  Limit alone establishes no ordering.

Freeze:

```text
window-local ordering != relation-result ordering
input row multiplicity == output row multiplicity
BAG != SET
```

`let:` and named-window declarations are not operators. Aggregate argument
ordering, window frames, `EXCLUDE`, null treatment, and `FROM FIRST/LAST` are
operator-local evidence, not row-stream stages.

An exactly empty `SATISFYING` dependency ledger for a literal predicate remains
complete evidence; empty is not treated as missing or unknown.

## Operator Occurrence And Stage-order Laws

`ProjectIRLogicalOperatorOccurrence` contains exactly:

```text
one existing ProjectIRPlanNodeOccurrence
+ one current ProjectIRLogicalOperatorKind
+ the exact matching concrete ProjectModuleRelationSemanticFacts
```

Freeze:

```text
operator kind != plan-node identity
```

No replacement node/ref identity is minted. The plan ref remains occurrence
authority.

`ProjectIRLogicalOperatorStage` validates caller-supplied operators rather than
constructing them. Its operator tuple must map object-for-object to every node
in the unchanged structural tuple. For each exact concrete relation subject it
requires the complete authored stage sequence, exact semantic evidence, and the
final operator node as the existing structural root.

It rejects foreign nodes/scopes, missing nodes, duplicate assignment, evidence
owned by another relation, absent-evidence operator kinds, hidden reorder, and
hidden deduplication. It performs no graph traversal, reachability, cycle,
optimizer, or analysis-invalidation work.

## Exact Property-transfer Matrix

Freeze:

```text
provided property != required property != effect evidence != estimate
```

`ProjectIRPreservedPropertyTransfer` proves one caller-supplied input/output
property pair. The slot must be preserved by the operator's exact matrix, both
properties must reuse the same exact relation semantic authority, their semantic
payloads must match, and the output must be owned by the receiving operator.
The logical stage additionally requires the input property to be owned by the
immediately preceding operator of that relation pipeline.

`ProjectIREstablishedPropertyTransfer` accepts only a positive property slot
that exact current operator evidence may establish. `ProjectIRUnavailablePropertyTransfer`
retains explicit unknown/not-applicable output without converting it into a
positive fact.

The current positive matrix is:

| Operator | Proven preservation | Proven establishment |
| --- | --- | --- |
| Relation Input | none | output shape, BAG multiplicity, closed bindings |
| Row Filter | shape, upper bound, BAG, relation ordering, closed bindings | none |
| Group/Aggregate | closed bindings | grouped output shape, BAG, local group-key evidence |
| Result Filter | grouped shape, upper bound, BAG, ordering, local group evidence, closed bindings | none |
| Window Evaluation | upper bound, BAG, local group evidence, closed bindings | exact output shape, existing evaluation policy |
| Final Projection | upper bound, BAG, closed bindings | exact final output shape |
| Relation Ordering | shape, upper bound, BAG, closed bindings | exact relation-result ordering |
| Limit | shape, tighter/equal upper bound, BAG, ordering, local group evidence, closed bindings | exact static upper bound |

Preserving an upper bound requires an equal or tighter exact output bound.
Projection does not preserve shape/order/grain merely from names. Window-local
ordering never establishes relation ordering. No rule manufactures SET,
uniqueness, FD/key, fanout, effect purity, or an estimate.

The Slice 3 ordering carrier now accepts an exact ungrouped authored order
clause as well as the already-stricter grouped fact collection. The static-limit
carrier uses the exact current integer validation for grouped and ungrouped
relations alike. Both still require the output row shape's exact semantic-fact
object.

## Required Row-shape Compatibility

`ProjectIRRowShapeCompatibility` is a pure caller-supplied proof boundary over:

```text
one exact ProjectIRProvidedOutputShape
+ one exact consumer-side ProjectIRRequiredRowShape
```

`ProjectIRRowShapeCompatibilityStatus` is exactly `SATISFIED` or
`NOT_SATISFIED`. Positive satisfaction requires a relation-row output, the exact
required target relation, the same exact semantic-fact authority, and the full
typed ordered row shape. Equal names alone cannot satisfy it.

The boundary does not search for a provider, traverse a graph, choose an
upstream winner, or instantiate required ordering/grain. The logical stage only
checks that caller-supplied provided and required carriers are already retained
by its one property stage.

## Effect And Estimate Preservation

All four effect axes remain explicitly unknown. No operator or transfer may
upgrade them to deterministic, non-volatile, cannot-error, side-effect-free, or
evaluation-count-insensitive.

`ProjectIRLogicalOperatorStage.effects` returns the exact existing Slice 3
effect tuple; it creates no effect transfer object. Existing exact window frame
policy remains a provided evaluation-policy property and is not an effect
classification.

`ProjectIRLogicalOperatorStage.estimates` returns the exact existing empty
estimate boundary. Estimate statistics cannot enter a transfer, compatibility,
operator legality, equality, or ordering decision.

## Logical-stage Formation Laws

The logical stage contains only:

```text
one exact ProjectIRPropertyStage
+ exact ordered logical operator occurrences
+ exact ordered preserved/established/unavailable transfer proofs
+ exact caller-supplied row-shape compatibility results
```

The property stage retains the exact same structural object. Slice 4 refines
its output-owner check so an intermediate operator node may own an output only
when that output reuses the same unique concrete relation subject and exact
semantic-fact authority. It still cannot create or reorder topology.

Formation proves:

```text
operator -> exact retained node
operator evidence -> exact concrete relation subject
complete source-authored stage order
one operator per node
transfer output -> exact operator node
transfer identity -> operator + exact output occurrence + property slot
preserved input -> immediately preceding operator
all transfer properties -> retained property-stage objects
every retained provided property -> exactly one transfer proof
all compatibility carriers -> retained provided/required objects
every retained required row shape -> exactly one compatibility result
effect tuple and estimate boundary -> unchanged Slice 3 objects
```

Formation derives no canonical pipeline, ref allocation, graph reachability,
cycle result, property provider, optimizer alternative, or verifier analysis.

## Determinism Immutability And Privacy

All Slice 4 carriers are frozen, slotted, keyword-only dataclasses. Collections
are exact tuples. Caller order is validated and never silently sorted,
deduplicated, or winner-selected.

The implementation introduces no registry, singleton, global counter, UUID,
random identity, cwd lookup, hash identity, ambient current project, cache,
fallback resolver, or persistent ID. Equivalent semantic pipelines remain
occurrence-distinct through their existing Slice 2 refs.

The same explicit logical stage has stable formation across hash seeds and
unrelated cwd values. The module exports nothing through `__all__` and is not
imported by public Pietto, CLI, script IR, SQL, or Project Explain.

## Focused Assurance Contract

Focused tests directly construct Slice 2-4 private carriers; they are not
authored Project IR E2E and invoke no canonical builder.

They prove:

```text
the exact eight-stage current algebra and order
absent clauses omit nodes
source input remains one logical non-physical leaf
let and named windows create no operators
where and satisfying remain distinct
an exact empty satisfying dependency ledger still forms Result Filter
group/aggregate remains one stage
row filter preserves only exact caller-supplied properties
one operator retains distinct relation/scalar output transfers without a winner
group establishes shape, BAG, and local group evidence without SET/order
window preserves multiplicity and never promotes local order
projection preserves BAG but does not preserve shape implicitly
ungrouped relation ordering establishes exact ordering
limit establishes an exact upper bound and preserves existing order
unknown effects remain unknown and estimates remain empty
provided and required domains remain separate
row-shape compatibility rejects names-only or rebuilt authority
operator kind leaves plan-node identity unchanged
foreign/missing/duplicate/reordered operator formation fails closed
logical composition preserves structural/property objects
hash seed and cwd do not affect formation
public, SQL, and script RelationIR behavior remain unchanged
```

All temporary paths are pytest-owned and subprocess environments are isolated;
the tests retain xdist/serial compatibility.

## Integration Boundary And Non-goals

The following remain unchanged authorities rather than logical-stage storage:

```text
parser/AST and semantic analyzer
src/pietto/ir/model.py::RelationIR
ProjectModuleRelationSemanticFacts and aggregate/group/window facts
Slice 2 refs/anchors/occurrences/construction states
Slice 3 row/output/effect/estimate domains
PostgreSQL and MySQL SQL lowering
```

No authored Project automatically constructs Slice 4 carriers. Slice 5 owns
the canonical single-relation builder and plan-node/ref allocation.

Slice 4 adds no cross-module composition, Project DAG builder, aggregate/window
evaluation context, verifier, pass manager, semantic rewrite, optimizer memo,
cost model, estimator, JOIN, grain comparison, fanout, nesting, correlation,
recursion, physical source access, materialization, CTE strategy, parser/AST,
grammar, diagnostics, SQL, CLI, JSON, public schema, Project Explain field,
persistent identity, backend behavior, Rust implementation, tag, Release,
signing, or attestation.

## Slice 5 Handoff

The only next owner is:

```text
Phase 61 Slice 5 — Canonical Single-Relation Construction From Existing Project Semantic Facts
```

Slice 5 may allocate the canonical current pipeline from exact semantic facts
using the frozen algebra and transfer laws. It must not change the eight-stage
sequence, invent omitted stages, or begin cross-module composition. Slice 5
remains next / unstarted and is not implemented here.

## Gate Lifecycle And Publication

Gate 2 uses focused tests, Ruff, and Pyright; performs one complete candidate
review; permits at most one same-root repair batch; performs a fresh rereview;
and runs exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Package smoke is locally required because a new private packaged module is
added. Generated and golden auxiliaries are not locally required because no
input surface changes; natural CI still runs them.

Gate 3 rebinds the predecessor, stages exactly the sealed tree, makes one
ordinary commit, performs one fast-forward push, and observes the unique
natural exact-head CI without dispatch or rerun.

The exact commit subject is:

```text
Add Phase 61 Project IR operator algebra
```

The published PASS title is:

```text
PASS — PHASE61_SLICE4_PROJECT_IR_CURRENT_LOGICAL_OPERATOR_ALGEBRA_EXACT_PROPERTY_TRANSFER_END_TO_END
```

Successful natural exact-head CI completes Slice 4 without a status-only
follow-up commit. Slice 5 remains next / unstarted.
