# Phase 54 Slice 11 Module Attribution, Dependency, Origin, Provenance, And Lineage v1

Status: Gate 2 candidate. Completion still requires exact reviewed-tree Gate 3
publication.

## Scope

Slice 11 adds one private schema-v2 sidecar that attributes retained module
declarations, imports, facades, and concrete reference occurrences; records
direct module and semantic dependencies; reconstructs exact local, imported,
and explicitly re-exported origin paths; and preserves minimal direct or
renamed row lineage through the concrete Slice 10 row subset.

The implementation consumes only the complete preloaded Slice 5 through Slice
10 carriers. It performs no file or network I/O, no path discovery, no source
reopening, no parsing, and no independent symbol resolution. Schema v1 builds
no Slice 11 sidecar. Schema v2 continues to return `model=None`, builds no
Project IR or SQL, and serializes no private Slice 11 value.

## Occurrence-safe Identity

Nominal identity remains the Slice 5 tuple of module path, namespace,
declaration kind, and declared name. Slice 11 never rewrites that tuple with
an import alias or exposed facade name. The new sidecar separately retains:

- selected-module and declaration positions for a declaration occurrence;
- owning module, local binding name, target module, exported name, import
  statement position, and item position for an import occurrence;
- owning module, namespace, kind, exposed name, export statement position, and
  item position for a facade occurrence;
- owner occurrence, closed reference role, and member position for a reference
  occurrence;
- owner occurrence, row-field domain, field position, and field name for a row
  field occurrence.

Retained AST values are evidence only and are excluded from semantic equality
and hashing. Spans, diagnostics, display strings, filesystem identities,
dictionary iteration order, and Python object identity are not semantic
identities.

## Private Product

`src/pietto/_project/module_attribution.py` defines frozen, slotted,
keyword-only private carriers for declaration, import, facade, and raw
reference attribution; access and origin paths; reference provenance;
module-import and semantic dependency facts; source-field origin; row-lineage
hops, paths, fields, and relation states; and one project-wide fact set.

`ProjectSemanticResult.module_attribution_facts` is the only integration
field. It is `None` for schema v1. Ordered collections are tuples. Lookup
indexes copy complete buckets into `MappingProxyType` values and return tuples.
No public export or serializer exposes these private carriers.

## Attribution And Origin

Every selected declaration of the eight retained nominal kinds receives one
source-ordered declaration attribution. Every retained import request and
resolved export entry receives one exact occurrence attribution. Type-alias
bases, shape-field types, source-shape references, relation `from` references,
and direct eligible row-field selections receive raw reference attribution
even when resolution is unknown, ambiguous, cycle-blocked, or otherwise
blocked.

A local declaration has a zero-access-hop self origin. An imported binding has
one access hop for each exact import and direct facade occurrence. An explicit
re-export follows only its retained `resolved_from` candidate and matching
binding evidence until a local-declaration facade is reached. Every hop keeps
the original nominal target identity. There is no wildcard lookup, heuristic
span join, shortest path, first candidate, implicit transitive export, or
owner-name fallback.

Distinct aliases and distinct import occurrences that reach one nominal target
remain distinct origin paths. Only complete semantic equality may remove an
exact duplicate. Target lookup returns every retained route in deterministic
local-declaration order followed by resolved-import selected/source order.

## Dependency And Provenance

Module dependencies retain every Slice 8 import evidence edge, including
parallel occurrences in diamonds and cycle members. Canonical graph edges and
cycle witnesses are validation inputs, not lossy substitutes for evidence.

Concrete reference provenance preserves each immediate reference occurrence,
nominal target occurrence, exact origin path, and type-alias hop. A builtin
terminal retains the exact final reference occurrence and creates no nominal
dependency. Type/source/relation
semantic dependencies are direct hop facts; row-field dependencies target the
immediate upstream row-field occurrence. Alias chains do not collapse to only
their canonical terminal.

Unknown, ambiguous, and blocked references keep raw attribution but publish no
concrete provenance or semantic dependency. Existing Slice 7 through Slice 10
issue carriers remain the authoritative blocker-root evidence; Slice 11 does
not duplicate or reconstruct those roots from diagnostic text. Cyclic modules keep raw
declaration/import/reference attribution and module-import dependency evidence
but are absent from dependency-ordered concrete resolution environments.

## Minimal Row Origin And Lineage

A concrete shaped source publishes one source-field identity per shape field,
in shape order, with its exact shape-field identity and complete source-shape
provenance path. Its source fields are zero-hop lineage roots.

A concrete table or query in the Slice 10 direct subset publishes one
relation-output identity per selected item. Bare direct fields, exact
immediate-upstream-qualified fields, and direct renames preserve select order.
Each lineage hop records the exact selection reference, direct/renamed posture,
output occurrence, immediate upstream field occurrence, and relation origin
path. Multi-hop local, imported, and explicit re-export chains prepend every
immediate projection hop and retain every complete path to the original source
field.

Unknown, deferred, and blocked Slice 10 row states publish one empty lineage
state with the exact existing status and reason. Local relation cycles publish
an empty state for every blocked member. Unknown upstream, duplicate output,
computed projection, `let`, grouped, aggregate, and window rows remain outside
concrete Slice 11 lineage. Slice 11 does not infer partial roots for them.

## Determinism And Fail-closed Rules

Selected module order and declaration/member source order are the only
presentation-order evidence. Resolver environments remain in the exact Slice
9/10 dependency order. Fixed-point row propagation scans every pending fact in
each round and fails if a purported concrete acyclic set cannot progress.

The builder rejects incomplete, misaligned, reordered, or mixed carrier sets;
incomplete module graph evidence; incomplete canonical-edge evidence buckets;
incomplete component internal edges; dependency-order disagreement; missing
row facts; ambiguous facade/binding joins; and discontinuous paths. A complete
bucket never chooses a first or last winner.

## Compatibility And Retained Owners

Slice 11 changes no grammar, generated parser, AST, diagnostic code, public
Python export, Project JSON v2 key or key order, CLI JSON v1, Semantic Metadata
Artifact v1, IR, PostgreSQL/MySQL SQL, dependency, lockfile, workflow, package
version, fixture, golden, release, signing, attestation, or Rust behavior.

Slice 12 retains ownership of computed and `let` lineage, aggregate, grouped,
window, generic/type-argument, full-nullability, result-role, and capability
preservation. Project IR remains Phase 61 ownership. Relationship, JOIN, grain,
and fanout remain Phase 62 ownership. Project emit-SQL and multi-relation SQL
remain Phase 63 ownership. Public module inspection and serialization remain a
later explicitly authorized slice.
