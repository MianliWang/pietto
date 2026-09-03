# Pietto Layering And Coupling Laws v1

These laws are the current durable dependency contract. They assign ownership
without claiming that future lowering, execution, interchange, adapter,
optimizer, or physical layers are implemented.

## Forward authority sequence

```text
AST
-> Semantic Authority
-> Project IR / Query Block IR
-> ProjectSQLPlan
-> Dialect SQL AST
-> Execution Plane
-> ResultContract / Arrow
-> Ecosystem Adapter Plane
-> Optimizer / Physical Plane
```

Dependencies flow forward. Downstream layers may consume upstream authority,
but may not silently re-decide upstream semantic facts. A downstream
representation retains typed provenance to the fact it projects instead of
substituting names, positions, bytes, handles, or observations for that fact.

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

SQL planning/lowering, dialect lowering, execution, result interchange,
ecosystem adapters, optimizer search, and physical strategy remain separate
architectural owners. A later phase may implement one only through a fresh
[Product/Phase Initiation Gate v1](phase-initiation-gate-v1.md) and the
phase-level ownership in the [roadmap](../roadmap.md). This extraction
implements none of them.

Identity and candidate completeness remain governed by [Identity And Authority
Laws v1](identity-and-authority-laws-v1.md); the complete layer map is in
[Pietto Product Architecture v1](product-architecture-v1.md).
