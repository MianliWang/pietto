# Phase 54 Slice 11 Module Attribution, Dependency, Origin, Provenance, And Lineage v1

Status: Gate 2 candidate. Completion still requires exact reviewed-tree Gate 3
publication.

## Scope

Slice 11 adds one private schema-v2 sidecar that attributes retained module
declarations, imports, facades, and concrete reference occurrences; records
direct module and semantic dependencies; reconstructs exact local, imported,
and explicitly re-exported origin paths; and preserves minimal direct or
renamed row lineage through the concrete Slice 10 row subset.

The implementation consumes only the factory-produced
`ProjectParseCheckResult`, the complete preloaded Slice 5 through Slice 10
carriers, the exact selected-input index, and trusted-source snapshots.
It performs no file or network I/O, no path discovery, no source reopening, and
no parsing. Validation first re-derives the canonical Slice 8 diagnostics from
the exact graph, exports, and bindings, then re-derives the canonical Slice 9
and Slice 10 products through their existing pure private builders. It derives
the expected type and source product from the expected diagnostics and derives
the expected relation product from that expected type product. This adds no
independent resolution policy. Schema v1 builds no Slice 11 sidecar. Schema v2
continues to return `model=None`, builds no Project IR or SQL, and serializes no
private Slice 11 value.

The Slice 8 diagnostic set privately retains the exact graph, export-surface,
and binding-environment roots of its canonical builder. Slice 11 requires
those three objects to be the current roots even when the canonical diagnostic
projection is empty; value-equal diagnostics from another project therefore
cannot pass through the empty-product case.

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

The project-wide fact set retains the exact Slice 7
`ProjectModuleBindingEnvironmentSet` as a private validation-only
`binding_authority` root excluded from representation, semantic equality, and
hashing. It also retains one private frozen/slotted/keyword-only authority
carrier, likewise excluded from representation, equality, and hashing. That
carrier keeps the exact factory-produced parse result, selected-input index,
complete ordered trusted-source snapshot tuple, logical modules, and complete
Slice 5 through Slice 10 roots, including the Slice 8 diagnostic set. Its ten
top-level Slice 11 fact-tuple fields are private derived `init=False` products:
`__post_init__` derives them only through
`_derive_project_module_attribution_fact_collections` and assigns them with
`object.__setattr__`. The builder therefore constructs the authority from roots
only, and constructs the outer fact set from the authority's exact derived
tuple objects. `dataclasses.replace(authority)` accepts only roots and
coherently rebuilds every product; it cannot accept or graft an `origins`,
provenance, dependency, or lineage product. The fact set rejects any mixing of
old and rebuilt authority products, as well as every incomplete, reordered, or
foreign product. This creates no registry, global product state, I/O,
serialization, or public API surface; independently building the same complete
roots remains valid.

The parse result is the eleventh private validation root. It has exact
`ProjectParseCheckResult` type, is a successful explicit-module compiler
factory output with non-null root and config path, and retains the identical
logical-module tuple, selected-input index, trusted-source snapshot tuple, and
pinned root supplied to the attribution builder. Each logical module retains
the exact `ProjectInput` and `ProjectParsedInput` at the same parse-result
position. The selected-index entry's `ProjectInput` is not required to be that
same object because selection and successful parsing intentionally retain
different status carriers. The parse root is excluded from representation,
semantic equality, and hashing. No token, seal, digest, source reopening, or
reparse is introduced.

This root proves atomicity across trusted compiler-factory result object
graphs. It is not factory-origin attestation: the contract does not claim to
prove the historical origin of an arbitrary private dataclass created through
a direct constructor or `dataclasses.replace` with internally coordinated
foreign fields. Such a claim would require a token, seal, or reparse and is
explicitly outside Slice 11.

Before deriving Slice 11 products, the builder requires canonical value
equality with freshly re-derived pure Slice 8 through Slice 10 outcomes. It then
requires every resolver environment module, declaration occurrence, AST
reference leaf, resolved symbol, imported binding, graph cycle, diagnostic
root, relation row owner, type/source issue root, and relation select item to
retain the exact object from the supplied current roots. The selected-input
index must cover the same complete module order, and each trusted snapshot must
retain the exact selected entry at that position. Thus value-equal foreign
resolvers, including foreign resolver environments rebound only to current
modules, fail closed. A coordinated graft that combines the modules and
semantic roots from one valid factory result with the selected-input index or
snapshots from another valid factory result also fails closed against the exact
parse-result root.

Relation row validation pairs every actual environment, row fact, and ordered
field with the freshly re-derived canonical counterpart. Fresh schema,
row-field, resolved-type, symbol, and provenance wrappers remain valid, but
each retained `field_def`, nominal resolved-type `symbol.definition`, and any
provenance `symbol.definition` must be the exact canonical AST leaf. This
rejects a value-equal foreign nominal-definition graft without making wrapper
object identity part of semantic equality.

The fact set requires the identical binding root and authority carrier, then
requires every supplied top-level tuple to have the canonical complete order
and every supplied wrapper object to be the original canonical object. Its
import attributions must be the complete ordered projection of every retained
request, including unresolved and colliding requests. Its module-import
dependencies must be the complete ordered projection of exactly those requests
whose target path names a selected module, including parallel, diamond, and
cyclic occurrences. Validation never fills, sorts, or normalizes supplied
facts.

`ProjectSemanticResult.module_attribution_facts` is the only integration
field. It is `None` for schema v1. Ordered collections are tuples. Lookup
indexes copy complete buckets into `MappingProxyType` values and return tuples.
The compilation mode must have exact `ProjectCompilationMode` type before any
mode branch or preliminary-state return. Legacy-flat results forbid every
module sidecar. Explicit-module preliminary results permit all module sidecars
to be absent, but once any Slice 5 through Slice 11 sidecar exists, catalogs,
exports, bindings, graph, diagnostics, type/source resolutions, relation
resolutions, and attribution facts must all exist and `model` must remain
`None`. The attribution value must have exact
`ProjectModuleAttributionFactSet` type. `ProjectSemanticResult` requires all ten
existing Slice 5 through Slice 10 and input authority roots plus the eleventh
parse-result root to be the exact objects held by that semantic result,
including the parse result's root, config path, modules, pinned root, selected
inputs, snapshots, diagnostics, and binding root;
its pinned root must be the selected-input index's exact pinned root. A foreign
otherwise-valid sidecar, a coordinated module-root graft retaining the old
input authority, a surrogate attribution object, or deletion of one sidecar
therefore fails closed. No public export or serializer exposes these private
carriers. Completed semantic results additionally require the Slice 8
diagnostic set's private graph, export, and binding authority roots to be the
same objects as their retained sidecars, and require their diagnostic tuple to
be the exact ordered concatenation of module, type/source, and relation
diagnostics without deduplication.
`ProjectSemanticResult` adds no direct parse-authority field: it reads the
private parse root only from the exact attribution authority carrier and
rechecks that root against its existing fields.

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
not duplicate or reconstruct those roots from diagnostic text. A retained
Slice 10 imported relation blocker selects roots only through the exact nominal
target identity, its exact declaration occurrence, and structured issue
evidence. It preserves target-environment issue order and existing root-object
order, removes only repeated references to the same root object, and cannot
adopt an unrelated same-spelling field diagnostic such as an `Other`
`PIE-S2102`. Value-equal but identity-distinct imported blocker roots remain
separate, and blocker components overlap only when they share the same root
object. Public relation diagnostics retain their existing codes, messages,
locations, and order. Cyclic modules keep raw declaration/import/reference
attribution and module-import dependency evidence but are absent from
dependency-ordered concrete resolution environments.

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
bucket never chooses a first or last winner. The graph and Slice 11 fact set
must retain the same exact binding-authority object. Fact-set construction
rejects dropped, injected, reordered, foreign value-equal, wrapper-cloned, or
coordinated rewrites of any top-level fact tuple, including import attribution,
module-import dependency, concrete provenance, source-field origin, row
lineage, and row dependency facts.

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
