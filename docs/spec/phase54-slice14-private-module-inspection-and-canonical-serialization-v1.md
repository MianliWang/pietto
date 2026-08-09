# Phase 54 Slice 14 Private Module Inspection And Canonical Serialization v1

## Status And Authority

This document is the Gate 2 candidate contract for Phase 54 Slice 14. Phase 54
is `ACTIVE`; Slices 1 through 13 and the unnumbered post-Slice-12 workflow
hardening interlude are `COMPLETED`; Slice 14 remains incomplete until exact
reviewed-tree publication, natural exact-head pull-request continuous
integration, review closure, squash-tree equality, natural exact-head `main`
continuous integration, reconciliation, cleanup, and immutable Gate 3 evidence
all succeed.

Slice 14 owns a private module-inspection product and its canonical private
serialization. It exposes no public compiler, command-line, JSON, package, or
runtime product. Slice 15 retains Rust-ready pure boundaries, differential
vectors, Python reference behavior, and end-to-end hardening. Phase 58 retains
every public explain, portability, and package inspection artifact.

## Authority Roots And The Shared-root Predicate

`src/pietto/_project/module_inspection.py` owns one private schema-v2
inspection sidecar. Its `__all__` remains empty.

The private authority carrier retains exactly ten roots and nothing else. Every
root is consumed by at least one frozen inspection section; no root is retained
in case it is needed later.

| Root | Owner | Consumed by |
| --- | ---: | --- |
| ordered `ProjectLogicalModule` tuple | 2 | module identity and selected order |
| `ProjectModuleCatalogSet` | 5 | declaration order and occurrence alignment |
| `ProjectModuleExportSurfaceSet` | 6 | export section |
| `ProjectModuleBindingEnvironmentSet` | 7 | import and alias section |
| `ProjectModuleGraph` | 8 | component, dependency, evidence, and graph issues |
| `ProjectTypeSourceResolutionSet` | 9 | type and source-shape resolution sections |
| `ProjectModuleRelationResolutionSet` | 10 | relation resolution and relation issues |
| `ProjectModuleAttributionFactSet` | 11 | origin, dependency, and row-lineage sections |
| `ProjectModuleSemanticFactSet` | 12 | preserved semantic-fact section |
| `ProjectModulePackageNeutralIdentityFactSet` | 13 | owner, digest, readiness, availability |

The selected-input index and the trusted-source snapshots are deliberately not
roots. Their only Slice 14-relevant projection is the source digest, and that
digest is reached through the exact Slice 13 module asset which already anchors
both of them.

The **shared exact-authority-root predicate** admits the inspection only when
every root belongs to one identical settled root set. It is validated as a whole
and by object identity:

1. the Slice 13 authority retains the exact supplied module tuple, catalog set,
   Slice 11 fact set, and Slice 12 fact set;
2. the Slice 11 private authority retains the exact supplied module tuple,
   catalog set, export surfaces, graph, type/source resolutions, relation
   resolutions, and binding environments, and the Slice 11 fact set retains that
   exact binding authority;
3. the Slice 12 authority retains the exact supplied module tuple, catalog set,
   and relation resolutions;
4. the Slice 8 graph retains the exact supplied binding authority;
5. the Slice 12 dependency order and issue tuple are the exact Slice 10 tuples,
   and every Slice 12 environment retains its exact Slice 10 environment in
   order;
6. modules, catalogs, export surfaces, binding environments, and graph vertices
   align position by position, each retaining the exact logical module, and each
   graph vertex position equals its index;
7. the Slice 13 module assets are one per module in selected order, each
   retaining the exact module identity and position;
8. the Slice 13 declaration assets are the complete ordered projection of every
   catalog occurrence, each retaining the exact occurrence object;
9. the Slice 9 and Slice 10 environments follow their own dependency orders path
   by path.

A foreign, value-equal, partial, reordered, or coordinated mixed-root set
therefore fails closed even when every field compares equal, because the whole
root set is anchored together rather than child by child.

As in Slice 11 and Slice 13, a bare private dataclass constructed in isolation
is not factory-origin attestation, and Slice 14 claims no stronger guarantee.
`ProjectSemanticResult` requires the inspection authority's ten roots to be its
own exact objects, and that is where the whole root and product set is anchored.

## Canonical Root-derived Projection

There is exactly one canonical projection: `ProjectModuleInspection`, derived
inside `_ProjectModuleInspectionAuthority.__post_init__` and assigned with
`object.__setattr__`. The canonical serialized payload is derived from that
projection in the same construction. Both are `init=False`, so
`dataclasses.replace` on the authority accepts roots only and can neither accept
nor graft a supplied projection or payload.

The public fact set requires `inspection` to be the exact derived projection
object and `canonical_bytes` to be the exact derived payload object. A forged
payload is therefore rejected by object identity rather than by value, because a
value-equal payload can be produced from any equal-valued projection.

Every reusable bucket and index is built once in one pass over the roots:
component by member path, outgoing edges and import evidence by origin, export
entries and export issues by exact request object, resolved bindings and binding
issues by exact request object, Slice 13 declaration assets by module path,
Slice 11 origins, dependencies, and row lineages by owning module path, and
graph, type/source, and relation issues by owning module path. No section
performs a repeated full-catalog or full-project scan.

The two derived lookup indexes — inspected module by module path and inspected
declaration by nominal identity — are computed from the canonical projection at
construction, copy complete buckets into `MappingProxyType` values, return
tuples, and are never independent authorities. Every lookup returns the complete
matching bucket and selects no winner.

## Private Inspection Sections

The project level carries exactly the private format marker, the exact Slice 13
`LOCAL_PROJECT_ROOT` owner identity, and the ordered module records.

Each module record carries, in this exact order: the project-relative module
identity and its selected position; the exact Slice 13 source digest identity;
the loader-readiness status, reason, and the complete ordered blocking cycles;
the graph component members, cyclicity, canonical dependency targets, and
ordered import evidence; the import requests with their local alias, namespace,
declaration kind, target module path, exported name, source positions, resolved
nominal target or absence, and the complete ordered bucket of binding issue
statuses; the export requests with their local name, source positions, resolved
exposed name, entry origin, nominal target or absence, and the complete ordered
bucket of export issue statuses; the declarations in exact source order with
their owner identity, nominal identity, declaration position, availability,
complete identity-bucket size, occurrence index inside that bucket, relation
row-schema status and reason or absence, and ordered concrete row fields; the
Slice 11 origins with local or imported binding and their exact access hops; the
Slice 11 dependencies with either a nominal declaration target or a nominal row
field target, never both; the Slice 11 row lineage with every identity-distinct
path and every ordered hop; the Slice 9 type and source-shape resolutions; the
Slice 10 relation resolutions with their local lookup name and nominal target;
the Slice 12 preserved semantic facts with their ordinals, output names, and
bucket statuses; and the complete ordered issue union in graph, type/source, and
relation family order.

The local lookup alias and the nominal declaration identity are always separate
fields. An alias never rewrites the identity of its nominal target, and two
aliases to one target remain two route facts.

The following are deliberately excluded, and the omission is a recorded scope
decision rather than an oversight:

- Slice 11 reference provenance paths, because they are a strict refinement of
  the dependency and origin facts already projected and add no independent
  identity, order, multiplicity, or availability dimension;
- Slice 11 module dependency facts, because the graph import-evidence section
  already projects the same origin, target, statement, and item identities from
  the same Slice 8 authority;
- Slice 11 source field origins, because the row-lineage roots already project
  the same field identities;
- diagnostic codes, messages, severities, and source locations, because Slice 14
  projects structural state rather than rendered text, and because coupling a
  private projection to public diagnostic text would create a compatibility
  surface no Phase 54 authority owns;
- raw source bytes and decoded source text, because no Slice 14 authority
  requires them and the digest identity is the authorized content projection.

## Canonical Serialization

The serialization is private, internal, and deterministic. It establishes no
public package, manifest, command-line, or JSON format, and no deserializer is
added.

The payload is UTF-8 without a byte order mark. It is a sequence of records;
every record is one line terminated by exactly one line feed, including the
last, so the payload always ends with exactly one newline and is never empty.
A record is a fixed lowercase ASCII kind followed by zero or more tab-separated
`key=token` pairs whose keys are fixed lowercase ASCII identifiers declared by
this contract and never derived from data.

Token tags are exactly `s:` text, `i:` integer, `b:` boolean, `e:` enumeration,
and `n:` absence. Text and enumeration payloads escape `\` as `\\`, tab as
`\t`, line feed as `\n`, carriage return as `\r`, and every other code point
below U+0020 plus U+007F as `\x` followed by exactly two lowercase hexadecimal
digits; every other code point is emitted literally as UTF-8. Integer payloads
are canonical non-negative decimal with no sign and no leading zero except the
single digit `0`; a negative integer is rejected. Boolean payloads are exactly
`true` or `false`. Enumeration payloads are the exact declared enumeration
value. `n:` is exactly two characters and is the only representation of absence.

Key order inside a record is the fixed declared order for that record kind.
Record order is the canonical projection order: the format header, the project
owner, then for each module in selected-input order every section in the fixed
section order above, and inside a section every item in its exact authority
order. Every module-scoped record carries `module` as its first key, and nested
records additionally carry their owning ordinals, so a same-value record in a
different position is a distinct line.

No dictionary, set, or frozen set iteration ever contributes to record or key
order: every iteration is over an ordered tuple of the canonical projection. No
floating point value, no representation string, no object address, no
process-local identifier, and no host path is ever encoded.

The payload is invariant under `PYTHONHASHSEED`, process, interpreter minor
version inside the supported matrix, and equivalent non-authoritative container
construction order. It changes whenever an authoritative identity, order,
multiplicity, availability, digest, readiness, or inspected fact changes.
Same-value but identity-distinct facts remain distinct records. Ambiguity,
duplicates, collisions, cycles, and blocked evidence are never normalized away.

Serialization performs no filesystem discovery, no source reopening, no network
access, no registry access, no package loading, and no database or runtime
execution.

The thirty-four record kinds are `inspection`, `owner`, `module`, `digest`,
`readiness`, `readiness_cycle`, `readiness_cycle_member`, `graph`,
`graph_component_member`, `graph_dependency_target`, `graph_import_evidence`,
`import`, `import_issue`, `export`, `export_issue`, `declaration`,
`declaration_row_field`, `origin`, `origin_hop`, `dependency`, `row_lineage`,
`row_lineage_field`, `row_lineage_path`, `row_lineage_hop`, `type_resolution`,
`type_resolution_alias`, `source_shape_resolution`, `relation_resolution`,
`semantic_facts`, `semantic_let_binding`, `semantic_select`,
`semantic_clause_dependency`, `semantic_window_output`, and `issue`.

## Identity, Ordering, Multiplicity, And State

Nominal identity remains the exact Slice 5 tuple of module path, namespace,
declaration kind, and declared name. Slice 14 never rewrites it with an alias, a
facade name, an owner name, or a digest. Project-relative module identity,
nominal declaration identity, and occurrence identity are preserved exactly.

Selected-input order, catalog order, source declaration order, dependency-first
resolution order, and every authority tuple order are preserved. Cardinalities
zero, one, two, three, and every larger identity-distinct occurrence survive,
and each occurrence carries its own bucket size and its own index inside that
bucket.

Collisions and ambiguity retain the complete bucket and publish no winner.
Cycles, blocked, unknown, deferred, absent, and concrete states are each
represented explicitly, and `ABSENT` is never confused with `UNKNOWN`. Digest
identities are preserved exactly without reopening or rehashing any source.
Loader readiness is preserved as a fact and no loader is implemented.

No first match, early return, shortest path, best score, or set-default
insertion selects a canonical fact. No name-keyed map, rendered message, or
display string is a deduplication key. Retained authority objects inside the
projection are evidence: they are excluded from representation, semantic
equality, and hashing, so inspection equality equals canonical-payload equality.

## Construction And Termination

Construction validates the whole shared root set before deriving any product,
then derives module records in selected-input order and each section in its own
authority order, and finally serializes the settled projection in one pass. The
procedure is a single finite walk over finite tuples; it contains no fixed point
of its own and terminates immediately.

The composed fixed point converges because every input has already converged
before the inspection: Slices 5 through 13 have each reached their own fixed
point over their own roots, and the inspection adds no iteration, no propagation
round, and no mutual recursion. It only reads settled products anchored to one
shared root set. Missing, foreign, partial, duplicated, reordered, or mixed-root
authority fails closed rather than iterating.

## Integration And All-or-none Boundary

`ProjectSemanticResult.module_inspection_facts` is the only integration field
and the eleventh module sidecar. The all-or-none invariant now covers eleven
sidecars: catalogs, exports, bindings, graph, diagnostics, type/source
resolutions, relation resolutions, semantic facts, attribution facts,
package-neutral identity facts, and inspection facts. Legacy-flat results forbid
all eleven. Explicit-module preliminary results permit all eleven to be absent,
but once any one exists all eleven must exist and `model` must remain `None`.

The semantic result additionally requires the inspection authority's ten roots
to be its own exact objects. A foreign otherwise valid inspection sidecar, a
surrogate inspection object, and deletion of any one sidecar therefore fail
closed.

## Privacy And Compatibility Boundary

Schema v1 has no Slice 14 sidecar and remains byte-exact. Schema v2 continues to
use `model=None`.

The inspection and its canonical payload expose no absolute host path, no
invocation path, no canonical real path, no symbolic link target, no device or
inode identity, no size or modification or change timestamp, no memory address,
no `id()` value, no Python representation string, no temporary path, no
credential, no mutable runtime state, and no raw or decoded source text.

Slice 14 adds no public export, command-line option, command-line text or JSON
v1 field, Project JSON v2 key or key order, Semantic Metadata Artifact v1 key,
diagnostic code, diagnostic message, grammar, generated artifact, abstract
syntax tree node, intermediate representation node, PostgreSQL or MySQL SQL
behavior, fixture, golden, example, package dependency, lockfile, workflow,
package version, release, signing, attestation, runtime behavior, or database
behavior.

## Negative Boundary

Slice 14 implements none of the following, and each remains owned elsewhere:

- public module inspection, public command-line inspection commands, and public
  JSON or serializer fields (Phase 58);
- a package manifest, package asset schema, package identity, or package graph
  expansion (Phase 55 and Phase 59);
- a registry, discovery, download, installation, cache, trust boundary,
  signing, or dependency solving (Phase 67 and Phase 68);
- module or source loading, deserialization, or persisted cache restoration;
- Project IR (Phase 61); relationship, JOIN, grain, and fanout semantics
  (Phase 62); project emit-SQL and QUALIFY (Phase 63);
- new grammar, abstract syntax tree, diagnostics, language semantics, type
  semantics, or runtime and database behavior;
- Rust-ready pure boundaries, differential vectors, Python reference behavior,
  and end-to-end hardening (Slice 15);
- release, publishing, signing, or attestation (a separate Release Gate).

A material unresolved public-format, external-compatibility, package-identity,
loader-behavior, or Slice 15 ownership question is a substantive stop rather
than an invitation to invent a public product.

## Validation Lock

The focused property matrix covers the inspection vocabulary and privacy; the
shared-root predicate against value-equal, partial, misaligned, reordered, and
coordinated mixed-slice foreign root sets; complete module and declaration
coverage in exact selected, catalog, and source order; digest reach-through,
byte-equal digest multiplicity, and complete digest lookup; loader readiness
with and without cycle evidence; availability `CONCRETE`, `UNKNOWN`, `DEFERRED`,
`BLOCKED`, `ABSENT`, and `AMBIGUOUS`; nominal-identity collision with a complete
no-winner bucket; cardinalities zero through three; local alias separation from
nominal ownership; graph, origin, dependency, lineage, resolution, semantic-fact,
and issue completeness; derived-index completeness; the canonical format marker,
final-newline rule, record grammar, escaping, and UTF-8 exactness; canonical
byte identity across repeated processes and varied `PYTHONHASHSEED`; canonical
byte stability under non-authoritative mapping construction order; canonical
byte sensitivity to identity, order, multiplicity, availability, digest, and
readiness changes; forged-payload and grafted-projection rejection; builder
purity with no input or output operation; the eleventh all-or-none sidecar
boundary; schema-v1 absence and byte exactness; and the unchanged public
surface. Dimensions are covered without a Cartesian product.

Gate 2 additionally requires the exact 58-reader zero-addition and zero-delta
fixed point, check-only Ruff over the exact 62 Python paths, production and test
Pyright, focused and compatibility suites, the applicable publication-topology
projections, generated count 8, golden count 37, package smoke, lock check,
authoritative offline validation, an independent full pytest run, the
exact `A3_M63_D0` allowlist, an empty Git index, a reviewed tree, and immutable
evidence.
Gate 3 alone may make Slice 14 `COMPLETED`; the next valid resume point is then
`PHASE54_SLICE15_GATE0_GATE1`.
