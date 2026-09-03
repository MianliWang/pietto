# Pietto Layering And Coupling Laws v1

These laws are the current durable dependency contract. They assign ownership
without claiming that future lowering, execution, interchange, adapter,
optimizer, or physical layers are implemented.

## Primary semantic / compilation / result flow

```text
AST
-> Semantic Authority
-> Project IR / Query Block IR
-> ProjectSQLPlan
-> Dialect SQL AST
-> optional Execution Plane
-> ResultContract / Arrow
-> Ecosystem Adapter Plane
```

Dependencies flow forward within this primary structure. Downstream layers may
consume upstream authority, but may not silently re-decide upstream semantic
facts. A downstream representation retains typed provenance to the fact it
projects instead of substituting names, positions, bytes, handles, or
observations for that fact. Result interchange and ecosystem adapters remain
downstream consumers, not normative planning inputs.

## Optimizer / physical planning side-plane

Logical optimizer and rewrite search consume already-established
semantic/logical authority. They may derive alternative semantically equivalent
logical or planning candidates and feed later planning/lowering only after the
required legality and verification. They never become name, path, identity, or
semantic-resolution authority.

Physical strategy selection consumes selected logical/planning authority. It
may influence later lowering or execution strategy and therefore occurs before
the execution/result boundary it affects. ResultContract / Arrow and ecosystem
adapters are not normative optimizer or physical-planning authority.

Accordingly:

- optimizer/physical plane is downstream of semantic authority;
- optimizer/physical plane is upstream of, or a planning side-plane to,
  lowering and execution;
- optimizer/physical plane is not downstream of ResultContract / Arrow;
- optimizer/physical plane is not downstream of ecosystem adapters.

Phases 88–89 own the exact future internal optimizer/physical IR topology. This
document does not implement those phases or define an optimizer IR, physical
IR, memo shape, cost model, optimizer API, or physical-plan representation.

## Coupling distinctions

- normative fact != compiled index;
- interface != capability;
- semantic requirement != optimization hint;
- semantic state != runtime resource state;
- cache != authority;
- inspection != resolver;
- optimizer != path resolver;
- optimizer != name resolver;
- verification != semantic authority;
- serialization != semantic authority;
- canonical bytes != semantic authority.

Compiled indexes accelerate an already-defined query. Interfaces describe a
surface, while capability evidence says what a selected provider supports.
Verification independently checks authority; it neither creates nor repairs
semantic facts. Inspection and serialization expose existing results without
becoming construction paths.

## Explicit boundaries

- Legality boundaries are explicit and unsupported shapes fail closed.
- Target requirements and provider capabilities are matched explicitly; one
  does not imply the other.
- Invalidation follows changed semantic roots through their derived facts.
- Verification is independently rerun wherever its contract requires fresh
  evidence.
- Snapshot-local derived analyses do not become persistent authority by
  observation alone.
- Compiler core has no ambient network, database, credential, or transaction
  authority.
- Plugins and adapters are explicit dependencies rather than ambient lookup or
  fallback mechanisms.

SQL planning/lowering, dialect lowering, optimizer search, physical strategy,
execution, result interchange, and ecosystem adapters remain separate
architectural owners. A later phase may implement one only through a fresh
[Product/Phase Initiation Gate v1](phase-initiation-gate-v1.md) and the
phase-level ownership in the [roadmap](../roadmap.md). This extraction
implements none of them.

Identity and candidate completeness remain governed by [Identity And Authority
Laws v1](identity-and-authority-laws-v1.md); the complete layer map is in
[Pietto Product Architecture v1](product-architecture-v1.md).
