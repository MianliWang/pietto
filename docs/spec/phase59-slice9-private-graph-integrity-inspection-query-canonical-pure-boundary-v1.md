# Phase 59 Slice 9 Private Graph Integrity, Inspection, Query, And Canonical Pure Boundary v1

## Scope

Phase 59 Slice 9 validates and projects the exact private graph produced by
Slices 2–8. The graph remains semantic authority. Slice 9 adds comprehensive
referential integrity, deterministic private inspection, on-demand private
queries, and one canonical pure evaluator boundary. It does not repair or
invent semantic facts.

The production owner is
`src/pietto/_project/package_graph_inspection.py`. It remains private and has
`__all__ = ()`.

## Comprehensive Integrity

Integrity re-instantiates the complete immutable `PackageGraphSnapshot` from
its exact fields. This re-runs every existing Slice 2–8 constructor invariant
without mutation, fallback, or repair. It then resolves both endpoints of every
typed direct provenance step.

Consequently, dangling and foreign-snapshot refs, wrong domains, invalid
package/module/declaration/field scope crossings, wrong selector attribution,
nonexistent lineage inputs, inconsistent ownership, and incomplete or grafted
semantic projections fail closed. Existing `PackageGraphProvenancePath` and
`PackageGraphWhyNot` constructors continue to own exact path contiguity and
terminal attachment.

Cycle validity is not reduced to a universal graph predicate. Package,
relation, module, and semantic cycle states retain their upstream
domain-specific authorities.

## Canonical Runtime Separation

Runtime references retain:

```text
runtime snapshot scope + typed local coordinate
```

Canonical inspection retains only:

```text
closed domain + typed local positions + authoritative facts
```

These are typed local coordinates. They preserve authoritative ordering and
multiplicity without becoming runtime or persistent identities.

The runtime snapshot scope, object identity/address, UUID, timestamp, global
counter, Python `repr`, pickle, and hash-derived occurrence IDs never enter
canonical data. Equal graphs constructed under independent scopes therefore
have unequal runtime refs and identical canonical inspection data.

Canonical data uses explicit length framing. Record, direct-link, and
negative-state tuples remain in upstream order. Canonicalization performs no
sorting or deduplication and preserves authoritative ordering and multiplicity,
parallel occurrences, roles, local positions, typed evidence distinctions,
and exact non-concrete status/reason facts.

## Private Inspection

The inspection has exactly four fields:

```text
records
links
states
canonical_bytes
```

Records distinguish every occurrence domain. Links contain only direct
positive topology derived from exact provenance witnesses. States separately
retain typed negative/non-concrete evidence. Inspection never relies on
`repr()` or a runtime owner token and is not a public or persistent schema.

## Query Boundary

The private query boundary provides:

- direct upstream;
- direct downstream;
- on-demand derived upstream/downstream paths;
- all authoritative why paths; and
- why-not paths with exact terminal records.

The one ordered direct-link tuple remains the source. Downstream queries scan
that tuple in reverse relation; no reverse index is stored. All-path queries
run DFS per request, preserve parallel occurrence-distinct routes, and store no
eager closure. There is no shortest, preferred, best, or canonical winner
behavior and no hidden deduplication.

## Pure Evaluator

The pure evaluator consumes only the explicit typed inspection. It validates:

- record/link/state ordinal and section order;
- field schemas;
- typed coordinate arity and uniqueness;
- parent ownership;
- link endpoint and witness domains;
- dangling refs and cross-package lineage grafts; and
- canonical-byte equality.

It uses no filesystem, cwd, environment, package loading, registry, network,
database, or mutable cache authority. Equivalent explicit inputs yield equal
inspection and query results.

Live architecture needs no private canonical parser or reconstruction, so
Slice 9 adds none. Malformed typed canonical input is evaluated fail closed;
there is no coercion, inferred owner, winner selection, or duplicate-looking
occurrence merge.

In short: no canonical parser or reconstruction is introduced.

## Deferrals And Compatibility

Slice 9 adds no public graph/schema/lineage artifact, persistence format,
persistent graph ID, Project Explain v2, graph CLI, graph database, loader or
resolver change, semantic change, cross-package visibility, IR, JOIN/grain,
SQL lowering, window frame, Rust, or Slice 10 E2E content. Phase 70 retains
public projection ownership.

Project Explain v1 and CLI remain zero-delta. Existing Slice 2–8 graph
construction and provenance behavior remain unchanged.

## Lifecycle

The candidate records Phase 59 active, Slices 1–8 completed, Slice 9 current,
and Slice 10 next/unstarted. Live Git plus successful natural exact-head CI own
completion; no status-only follow-up commit is required.

The only ordinary commit subject is:

```text
Add Phase 59 private graph inspection
```
