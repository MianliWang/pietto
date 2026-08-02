# Phase 54 Slice 10 Cross-module Table / Query / Relation Resolution, Row Facts, And Legacy Compatibility v1

Status: Gate 2 candidate. Completion still requires exact reviewed-tree Gate 3
publication.

## Scope

Slice 10 adds one private schema-v2 sidecar for relation-name resolution and
the minimal row facts directly obtainable from it. `SourceDef`, `TableDef`,
and `QueryDef` are the complete relation-producing declaration set. Only
`TableDef.from_clause` and `QueryDef.from_clause` are compiler relation lookup
sites; relationship endpoint metadata remains Phase 62 work.

Schema v1 continues to use the byte-exact legacy-flat resolver and constructs
no Slice 10 sidecar. Schema v2 continues to return `model=None`, builds no
Project IR or SQL, and serializes no private Slice 10 value.

## Inputs And Identity

The resolver consumes only retained parsed modules, Slice 5 catalogs, Slice 6
facades, Slice 7 binding environments, Slice 8 graph/diagnostic facts, and
Slice 9 type/source facts. It does not reopen sources, rediscover paths, probe
excluded files, consult packages or registries, or invoke callbacks.

Relation lookup uses exactly `ProjectSymbolNamespace.RELATION`. Source, table,
and query nominal kinds remain distinct. A local import alias changes only the
importing-module lookup name. The target identity remains the exact tuple of
target module path, relation namespace, declaration kind, and declared name.
An explicit re-export retains the direct facade path in its binding and the
original nominal target identity. There is no cross-namespace fallback,
implicit import, wildcard, qualified module lookup, or implicit transitive
export.

## Private Product

`src/pietto/_project/module_relation_resolution.py` defines frozen, slotted,
keyword-only private carriers for:

- one resolved local/imported relation symbol;
- one retained relation reference and its exact resolution;
- one relation-producing declaration row fact;
- typed emitted or root-suppressed issues;
- one dependency-ordered per-module environment;
- one project-wide resolution set.

Ordered values are tuples. Lookup indexes are copied `MappingProxyType`
values and return complete tuples. A bucket with more than one candidate never
selects a winner. `ProjectSemanticResult.module_relation_resolutions` is the
only integration field and remains `None` for schema v1.

## Deterministic Resolution

Slice 10 reuses the exact Slice 9 dependency order: target modules precede
importers, module-cycle vertices are excluded, and selected-module position is
the stable tie-break among independent vertices. Each acyclic module performs
one collect-before-resolve relation pass. Local table/query edges then use one
finite declaration-ordered topological pass. A local cycle is canonicalized at
its lowest declaration position. No cross-module fixed point is required:
explicit import edges already order every valid nominal target before its
importer.

The direct facade is checked for a module cycle before the nominal target.
Local/import collisions, import/import collisions, ambiguous facades,
unresolved/private imports, and complete local source/table/query name buckets
remain blocked without a first, last, kind-based, or source-order winner.

## Minimal Row Facts

Slice 10 reuses `ProjectRelationRowSchemaState`,
`ProjectRelationRowSchemaStatus`, `ProjectRelationRowSchemaReason`,
`ProjectRowSchema`, and `ProjectRowField`.

- A shaped source with known Slice 9 field types is concrete. Shape field
  order, the exact `FieldDef`, canonical type, and directly parsed nullability
  are retained.
- A missing, untyped, or type-invalid source schema is unknown.
- An unresolved relation or local cycle is blocked.
- Unknown, deferred, and blocked upstream states propagate as
  `UPSTREAM_UNKNOWN`, `UPSTREAM_DEFERRED`, and `UPSTREAM_BLOCKED`.
- Direct bare fields, exact two-part immediate-upstream-qualified fields, and
  direct renames preserve select order and copy the upstream field definition,
  type, and nullability.
- An imported alias is the immediate-upstream qualifier. An original target or
  source name is not a downstream qualification path.
- An unknown field makes the row fact unknown. A duplicate output retains the
  existing private unknown `DUPLICATE_OUTPUT_NAME` behavior.
- Computed, let, grouped, aggregate, or window output propagation is deferred
  with the existing row-state vocabulary. Slice 12 owns full preservation of
  those facts.

Slice 10 deliberately leaves provenance and result-role fields at their
minimal defaults. Slice 11 owns module attribution, dependency, origin,
provenance, and lineage. Slice 12 owns full generic, nullability, aggregate,
grouped, window, result-role, and capability preservation.

## Diagnostics And Suppression

Private issues adapt in one direction to existing diagnostics:

| Condition | Public diagnostic |
| --- | --- |
| Unblocked duplicate local relation name | `PIE-S2001` |
| Unknown local relation reference | `PIE-S2301` |
| Local relation dependency cycle | `PIE-S2302` |
| Unknown or invalid direct field | `PIE-S2102` |

Existing `PIE-S2701` through `PIE-S2707` roots suppress derived module,
facade, export, and binding cascades. Existing Slice 9 `PIE-S2001`,
`PIE-S2002`, `PIE-S2003`, and `PIE-S2303` roots suppress dependent source-row
cascades. Repeated consumers of one failed import do not duplicate its root;
independent local unknown relations and cycles remain visible. No diagnostic
code is added.

Diagnostic projection order remains Slice 8 module roots, then Slice 9
type/source roots, then Slice 10 issues in dependency-module and source-span
order.

## Compatibility And Retained Owners

Slice 10 changes no grammar, generated parser, AST, public Python export,
Project JSON v2 key or key order, CLI JSON v1, Semantic Metadata Artifact v1,
IR, PostgreSQL/MySQL SQL, dependency, lockfile, workflow, package version,
fixture, golden, release, signing, attestation, or Rust behavior.

Project IR remains Phase 61 ownership. Relationship, JOIN, grain, and fanout
remain Phase 62 ownership. Project emit-SQL, multi-relation SQL, and `QUALIFY`
remain Phase 63 ownership. Public module inspection/serialization remains a
later Phase 54 slice.
