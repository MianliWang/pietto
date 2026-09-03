# Pietto Product Architecture v1

This document is the current repository entry point for durable, cross-phase
product boundaries and architecture. It projects already-published authority;
it does not add syntax, behavior, or a numbered Slice route.

## Product boundary

Pietto is a gradual semantic SQL authoring DSL and compiler. Its intended 1.0
core is a read/query/analytics semantic compiler with optional, explicit
execution. Pietto is not itself a:

- DBMS;
- transaction manager;
- job scheduler;
- general Python runtime;
- remote package registry or dependency solver;
- full optimizer or physical execution engine;
- DML, DDL, or migration runtime.

Compiler core has no ambient network, database, credential, transaction,
installation-discovery, or remote-loading authority. Any future execution or
adapter boundary must be explicit and separately authorized.

## Compilation authority flow

```text
.pietto
-> parser
-> AST
-> semantic authority
-> Project IR / Query Block IR
-> ProjectSQLPlan
-> dialect SQL AST
-> SQL
```

The semantic compiler establishes typed meaning and identity. Project IR and
Query Block IR carry target-independent logical/query authority.
`ProjectSQLPlan` owns target-neutral SQL planning and lowering requirements; a
dialect SQL AST owns selected-backend lowering. Optional execution consumes
compiled output but does not become semantic authority. Optimizer and physical
planning consume established semantic/logical authority: they are downstream
of semantic authority, but upstream of, or a planning side-plane to, the
lowering and execution they affect. They are not downstream of
PiettoResultContract / Arrow or ecosystem adapters and never become name, path,
identity, or semantic resolvers. Phases 88–89 own their exact future internal
topology; this document neither implements those phases nor defines an
optimizer IR, physical IR, memo shape, cost model, optimizer API, or
physical-plan representation.

This sequence is architectural ownership, not a claim that every downstream
layer is implemented today. Current phase ownership and implementation state
remain with the [roadmap](../roadmap.md), [status](../status.md), published
phase contracts, live Git, and natural exact-head CI.

## Result and interchange flow

```text
completed semantic/query authority
-> PiettoResultContract
-> Arrow interchange
-> Python/data-science ecosystem adapters
-> domain/device adapters
```

The result contract projects completed query authority into a stable result
boundary. Arrow is typed tabular and nested interchange. Python/data-science
and domain/device integrations are explicit adapters above that boundary; they
do not reach back into compiler semantics.

Arrow does not define Pietto semantic identity. Arrow does not define
`NestedRelation` semantics. Arrow does not define RDKit semantics or provide
arbitrary SciPy lowering or database execution. It is not the sole GPU/device
interchange mechanism. In particular:

- Arrow field name != Pietto field occurrence;
- Arrow `List<Struct>` != Pietto `NestedRelation` semantics;
- Arrow metadata != key, grain, or lineage authority.

## Layer ownership

| Concern | Durable owner |
| --- | --- |
| Source shape and locations | parser and AST |
| Meaning, identity, legality, and complete resolution evidence | semantic authority |
| Target-independent logical/query structure | Project IR / Query Block IR |
| Rewrite search, costing, and physical algorithms | optimizer / physical planning side-plane; downstream of semantic/logical authority and upstream/side-plane to lowering and execution |
| Target-neutral SQL requirements and lowering plan | ProjectSQLPlan |
| Selected backend SQL representation | dialect SQL AST |
| Connections, statements, streaming, and cancellation | optional execution plane |
| Completed-result shape and transport | PiettoResultContract / Arrow |
| pandas, Polars, NumPy, SciPy, plotting, domain, and device integration | explicit adapter planes |

Downstream layers may consume upstream authority but may not silently re-decide
it. The detailed dependency laws are in [Layering And Coupling Laws
v1](layering-and-coupling-laws-v1.md); identity rules are in [Identity And
Authority Laws v1](identity-and-authority-laws-v1.md).

## Documentation authority map

| Material | Authority |
| --- | --- |
| [`AGENTS.md`](../../AGENTS.md) | live repository working, safety, and publication rules |
| [`docs/architecture/`](./) | durable cross-phase product and architecture laws |
| [Product Design Lessons v1](../references/product-design-lessons-v1.md) | concise evidence synthesis; external products are not Pietto authority |
| [Roadmap](../roadmap.md) | phase-level future ownership and release milestones |
| [Published phase/slice contracts](../spec/) | exact phase-specific routes, decisions, and publication evidence |
| [Status](../status.md) | lifecycle summary subordinate to live Git and natural exact-head CI |
| [Historical plans](../plan/README.md) | historical planning evidence only |
| Source and tests | implemented behavior and executable contracts |
| Live Git and natural exact-head CI | publication and lifecycle authority |

Every phase must apply the [Product/Phase Initiation Gate
v1](phase-initiation-gate-v1.md) against fresh authority before substantive
work.
