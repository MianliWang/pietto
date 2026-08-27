# Phase 59 Slice 8 Semantic And Field-Lineage Integration v1

## Scope

Phase 59 Slice 8 projects Pietto's existing private semantic field and lineage
authorities into `src/pietto/_project/package_graph.py`. It adds no semantic
resolution, inference, catalog, visibility, SQL, IR, CLI, or public artifact
behavior.

The only accepted combined input is one exact
`ProjectModulePackageNeutralIdentityFactSet` per successful package occurrence.
That existing fact set already binds the exact Slice 11 module attribution
authority to the exact Slice 12 semantic preservation authority. Slice 8 does
not rebuild either side and never reconstructs facts from Project Explain v1.

## Authority Join

One supplied semantic authority slot must match one inspection package slot.
The join validates:

1. package-local module count and order;
2. exact module logical path, local position, and trusted opened bytes;
3. complete module/declaration occurrence coverage;
4. exactly one semantic fact for each relation declaration occurrence; and
5. exact retained attribution and semantic witness membership.

Missing, foreign, ambiguous, or impossible joins fail closed with no snapshot.
A package dependency does not select a semantic authority and grants no
cross-package semantic visibility. Each package remains an independent semantic
island even when paths, names, fields, or source bytes are equal.

## Field And Let Occurrences

`PackageGraphFieldRef` is snapshot-scoped and
package/module/declaration-qualified. Its local position is the authoritative
shape/source field position or selected-output ordinal. The field name, alias,
type, provenance, expression text, location, and content digest remain facts,
not occurrence identity.

`PackageGraphLetRef` retains the additional declaration-local owner segment
required by existing let semantics. Let names likewise do not define
occurrence identity.

The graph retains exact existing field and let witnesses. Equal names across
declarations or packages remain distinct. A renamed output and its upstream
field remain separate occurrences connected by lineage.

## Direct Lineage Authorities

Positive lineage remains four closed typed relationship families rather than a
generic graph edge:

| Family | Exact existing evidence |
| --- | --- |
| source | `ProjectModuleSourceFieldOrigin` |
| direct / renamed | `ProjectModuleRowLineageHop` plus exact `ProjectModuleProjectionKind` |
| computed / let / aggregate | ordered `ProjectModuleExpressionReferenceFact` occurrences and their exact select/let/aggregate owners |
| current-window | `ProjectModuleWindowOutputFact` plus duplicate-preserving `WindowDependencyOccurrence` |

Computed, let, and aggregate inputs retain `container_ordinal` and
`dependency_ordinal`. Current-window inputs retain role, `global_ordinal`, and
`role_ordinal`. Therefore n-ary input order and repeated use of one upstream
field remain visible exactly where the existing authority distinguishes them.
No name equality, expression text, AST resemblance, module path, type, or
package dependency creates a lineage relationship.

## Non-Concrete Lineage

Slice 8 retains separate typed non-concrete carriers for:

- relation row status and `ProjectRelationRowSchemaReason`;
- let status, including exact `ABSENT`, and `ProjectLetScopeFactsReason`;
- aggregate/grouped readiness status and reason;
- unresolved expression candidate status without inventing a reason the
  upstream authority does not provide; and
- current-window output status and exact existing reason.

Non-concrete authority creates no partial positive lineage. Absence of a
positive relationship implies no synthetic unknown, blocked, unsupported,
absent, ambiguous, or not-applicable reason.

## Provenance

Package, module, declaration, field, and let ownership relationships, followed
by the four typed lineage families, participate in the existing Slice 6 direct
provenance model. Direct links remain authority. Transitive paths remain
on-demand derived results that preserve every direct occurrence, order, and
multiplicity. The snapshot stores no eager closure, path cache, reverse index,
shortest path, preferred path, or winner.

## Current-Window And Later Boundary

Only existing current-window dependency occurrences are integrated. Slice 8
adds no new window function semantics, partition/order semantics, frames,
frame identity, or frame lowering. Phase 60 may attach advanced frame facts
without changing any Phase 59 package, module, declaration, field, or let
occurrence identity.

## Privacy And Compatibility

All new carriers remain private, frozen, slotted, and absent from
`pietto.__init__` and `pietto._project.__init__`. There is no serializer,
canonical graph format, public lineage artifact, Project Explain v1 field,
CLI delta, dependency, Rust code, IR change, SQL change, or Slice 9 behavior.

Project Explain v1 and all current CLI behavior remain zero-delta sibling
consumers of their existing authorities.

## Lifecycle

The candidate records Phase 59 active, Slices 1–7 completed, Slice 8 current,
and Slice 9 next/unstarted. Live Git plus successful natural exact-head CI own
completion; no status-only follow-up commit is required.

The only ordinary commit subject is:

```text
Add Phase 59 semantic field lineage
```
