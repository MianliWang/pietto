# Phase 62 Slice 10 Authored JOIN And Traversal Semantic Uses v1

## Starting Authority

Slice 10 starts from published commit
`dc74cee6a0f6a67e396f12b4583a0d88d79ad130`, tree
`c32444755f191a45f68c7d9207979976ffc275dd`, and natural exact-head
`push/main` CI `33505927423`, attempt 1, success. Slices 1–9 are completed and
published. Slice 10 is the sole current publication candidate.

## Architecture Decision

The approved order is:

```text
parse
-> base FROM/module relation resolution
-> JOIN-aware row-availability barrier
-> module semantic facts and attribution
-> non-concrete single-relation Project IR terminal
-> Slice-7/8/9 concrete endpoint authority
-> authored relationship JOIN-use resolution
```

The barrier is determined only by authored JOIN occurrence presence. It never
depends on whether later relationship-use resolution succeeds.

```text
concrete JOIN semantic use != concrete combined relation-row schema
concrete JOIN semantic use != concrete single-relation Project IR fragment
semantic JOIN use != future binary JOIN occurrence
```

## Authored Syntax And AST

Tables and queries accept zero or more JOIN clauses immediately after `from`:

```pietto
query result:
    from orders

    inner join customers as customer:
        from orders

    left join regions as region:
        from customer
        via customer_region: customer -> region

    select:
        id
```

`INNER` and `LEFT` are the only JOIN kinds. Zero VIA steps request direct
shorthand; one or more VIA steps author one exact ordered path. `INNER`,
`LEFT`, `JOIN`, and `VIA` remain usable as ordinary identifier/name parts.
There is no JOIN-local `on` refinement.

`AuthoredJoinKind`, `JoinClause`, and `JoinTraversalStep` are immutable,
source-located AST carriers. `TableDef.join_clauses` and
`QueryDef.join_clauses` retain complete source order and default to `()`.

```text
JoinClause occurrence
!= relationship declaration
!= relationship direction
!= ProjectRelationshipPathStep
!= ProjectRelationshipPath
!= semantic JOIN use
!= future Project IR JOIN occurrence
```

## Project Semantic Barrier

`ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED` has exact value
`authored_join_deferred`. The same value exists in
`ProjectRowDependencyGraphReason` and `ProjectRowLineageReason`, and the
portable relation/row-fact domains admit
`("deferred", "authored_join_deferred")`.

When a JOIN-bearing relation's earlier base authority would otherwise be
concrete, its row fact is `DEFERRED / AUTHORED_JOIN_DEFERRED / schema=None`.
Earlier UNKNOWN, DEFERRED, BLOCKED, cycle, or upstream causes remain operative.
A downstream base FROM receives `UPSTREAM_DEFERRED`.

Module semantic facts retain the owner, base FROM resolution, row-fact root,
and authored clause ledgers, but publish no concrete input, base-result, final,
select, aggregate, grouped, window, key, FD, or output-field authority for the
combined relation. A forged concrete JOIN-bearing semantic fact is rejected.

## Single-Relation Project IR Boundary

A JOIN-deferred semantic fact produces one
`ProjectIRNonConcreteSingleRelationFragment` with construction state
`DEFERRED`, zero allocation, empty nodes/outputs/slots/uses/operators/property
products, and no root output. Direct single-fragment, project-plan, and
pipeline entry paths preserve this terminal. Mixed plans keep unrelated
join-free relations concrete, and the verifier may report `VERIFIED` only as
structural integrity—not JOIN lowering.

The legacy Script `RelationIR` builder emits `PIE-I1000` for the missing binary
JOIN-lowering prerequisite. PostgreSQL and MySQL therefore cannot silently
omit authored JOINs. Join-free IR, SQL, diagnostics, and goldens are unchanged.

## Query-Local Bindings And Uses

`project_relationship_uses.py` is private and has `__all__ = ()`. A binding
identity is the exact owning declaration occurrence plus binding position.
Position 0 is base FROM; positions 1..N are JOIN targets in source order.
Names are lookup surfaces, not identity.

Duplicate names, forward references, unavailable bindings, failed-binding
dependencies, unresolved or unavailable target relations, and ambiguous
candidates remain typed non-concrete outcomes. A failed JOIN still owns its
target binding. Later JOINs cannot reconnect around it.

`ProjectJoinUseIdentity` is owner occurrence plus JOIN position.
`ProjectTraversalStepUseIdentity` is JOIN-use identity plus authored VIA
position. The complete ledger is selected-module/declaration/JOIN ordered and
retains `CONCRETE`, `UNKNOWN`, `BLOCKED`, and `AMBIGUOUS` with causal objects.

## Direct And Explicit Paths

Direct shorthand calls the exact Slice-9 direct-candidate index. Only one
retained candidate succeeds; ABSENT and AMBIGUOUS keep their exact outcomes
and every candidate.

Every VIA step resolves the exact same-module relationship declaration,
source endpoint role, target endpoint role, and retained Slice-8 direction.
The ordered direction tuple is passed through
`build_explicit_relationship_path(...)` and
`analyze_relationship_path(...)`. Exact source/path-start and
target/path-end identity are required. Intermediate relations do not become
bindings.

INNER retains Slice-9 fanout and INNER-survival readiness. LEFT retains
Slice-9 fanout and LEFT null-potential readiness while distinguishing its
preserved source from its potential null-generating target. No analysis is
recomputed.

## Frozen Boundaries

Slice 10 adds no RIGHT/FULL/SEMI/ANTI/MARK/SINGLE JOIN, automatic BFS/DFS or
shortest-path search, joined scalar namespace, JOIN-local refinement, binary
Project IR, actual null extension, optional grain factor, SQL JOIN lowering,
relationship import/export, multi-fact/chasm analysis, public schema,
CLI/JSON, package, workflow, dependency, or version behavior.

## Reader Closure And Assurance

The fixed complete changed-path closure is `A3/M26/D0`, 29 paths. It contains
the 19 authorized production/generated paths, four documentation paths, four
core tests, and the two exact historical reason-vocabulary readers:

```text
tests/test_phase48_schema_availability_state_carrier.py
tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py
```

Assurance covers parser/AST occurrence order and spans; forbidden kinds;
join-free compatibility; barrier cause precedence; downstream propagation;
mixed concrete/non-concrete Project IR; direct plan/pipeline bypasses;
direct/explicit path resolution; bindings and failed-binding poisoning; exact
INNER/LEFT readiness; legacy IR fail-closed behavior; generated
reproducibility; and absence of Slice-11/12 behavior.

One coherent repair batch is allowed after the complete finding set is frozen.
The complete review froze and repaired the single root
`JOIN_USE_CARRIERS_DO_NOT_CLOSE_EXACT_BINDING_PATH_AND_STEP_EVIDENCE` in repair
batch 1/1. Concrete and non-concrete carriers now independently close exact
binding position, target output, authored VIA direction, Slice-9 index, path,
analysis, and ledger roots.

The authoritative validator is:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication uses one ordinary commit, one fast-forward push, and unique
natural exact-head CI with Python 3.12/3.13 success.

```text
Add Phase 62 authored relationship join uses
PASS — PHASE62_SLICE10_AUTHORED_JOIN_TRAVERSAL_SYNTAX_SEMANTIC_USES_END_TO_END
```

After PASS, `Phase 62 Slice 11 = NEXT / NOT IMPLEMENTED`. Do not begin Slice
11.
