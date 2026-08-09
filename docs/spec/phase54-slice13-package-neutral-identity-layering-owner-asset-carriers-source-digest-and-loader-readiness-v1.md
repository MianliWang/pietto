# Phase 54 Slice 13 Package-neutral Identity Layering, Owner / Asset-compatible Carriers, Source Digest, And Loader Readiness v1

## Status And Authority

This document is the Gate 2 candidate contract for Phase 54 Slice 13. Phase 54
is `ACTIVE`; Slices 1 through 12 and the unnumbered post-Slice-12 workflow
hardening interlude are `COMPLETED`; Slice 13 remains incomplete until exact
reviewed-tree publication, natural exact-head pull-request continuous
integration, review closure, squash-tree equality, natural exact-head `main`
continuous integration, reconciliation, cleanup, and immutable Gate 3 evidence
all succeed.

Slice 13 is the first authorized join of the Slice 11 attribution product and
the Slice 12 preservation product. Neither input is authority for the other,
and the join is a separate product with its own identity predicate. Slice 3
remains the sole authority for module identity, the selected-input index, the
trusted local loader, and the opened-byte source digest. Slice 14 retains
private module inspection and canonical serialization.

## Package-neutral Vocabulary

Slice 13 introduces new private Phase 54 vocabulary. It does not reuse, rename,
or re-activate the historical Phase 50 package-readiness names, which the Slice
1 route lock demotes to evidence.

- `ProjectLayeredOwnerKind` is exactly `LOCAL_PROJECT_ROOT` and `LOCAL_MODULE`.
- `ProjectLayeredAssetKind` is exactly `MODULE_SOURCE` and
  `NOMINAL_DECLARATION`.
- `ProjectLayeredAvailability` is exactly `CONCRETE`, `UNKNOWN`, `DEFERRED`,
  `BLOCKED`, `ABSENT`, and `AMBIGUOUS`.
- `ProjectLayeredLoaderReadiness` is exactly `READY` and `BLOCKED`.
- `ProjectLayeredLoaderReadinessReason` is exactly
  `TRUSTED_LOCAL_SOURCE_RESOLVED` and `MODULE_CYCLE_BLOCKED`.
- `ProjectLayeredDigestAlgorithm` is exactly `SHA256_OPENED_BYTES`, which names
  the existing Slice 3 digest authority and creates no second algorithm.

An owner identity carries a kind, a namespace, and a name. The namespace is the
reserved empty local namespace in every Phase 54 owner identity; a non-empty
namespace fails closed. This shape is deliberately extension-compatible and
carries no catalog content. The `LOCAL_PROJECT_ROOT` owner is unnamed, because
naming it would be a package identity that no Phase 54 authority may create.
The `LOCAL_MODULE` owner is named by the exact normalized project-relative
module path that Slice 3 already established as semantic module identity.

## Authority Roots And The Shared-root Predicate

`src/pietto/_project/module_package_neutral_identity.py` owns one private
schema-v2 layered sidecar. Its `__all__` remains empty.

The private authority carrier retains exactly six roots and nothing else:

| Root | Owner | Identity predicate |
| --- | --- | --- |
| `ProjectSelectedInputIndex` | Slice 3 | exact type and the exact object the Slice 11 authority already retains |
| ordered `ProjectTrustedSourceSnapshot` tuple | Slice 3 | exact type and the exact tuple object the Slice 11 authority already retains |
| ordered `ProjectLogicalModule` tuple | Slice 2 | the exact tuple object both sidecar authorities already retain |
| `ProjectModuleCatalogSet` | Slice 5 | the exact object both sidecar authorities already retain |
| `ProjectModuleAttributionFactSet` | Slice 11 | exact type plus its own private authority carrier |
| `ProjectModuleSemanticFactSet` | Slice 12 | exact type plus its own private authority carrier |

The **shared exact-authority-root predicate** admits the join only when both
independently rooted carriers are anchored to one identical root set. It is
validated as a whole and by object identity:

1. the Slice 11 authority's selected-input index, trusted-snapshot tuple,
   module tuple, and catalog set are the exact supplied objects;
2. the Slice 12 authority's module tuple and catalog set are those same exact
   objects;
3. both authorities retain the exact same `ProjectModuleRelationResolutionSet`;
4. the Slice 12 product's dependency order and issue tuple are that relation
   set's own exact tuples, and every Slice 12 environment retains the exact
   corresponding Slice 10 environment in order;
5. the module tuple, selected entries, trusted snapshots, and catalogs align
   position by position, each snapshot retaining its exact selected entry and
   each catalog retaining its exact logical module;
6. the Slice 11 declaration attributions are the complete ordered projection of
   every catalog occurrence, each retaining the exact occurrence object.

A value-equal foreign fact set therefore fails closed even when every field
compares equal, and a coordinated replacement that rebuilds both carriers over
one consistent foreign project also fails closed, because the whole root set is
anchored together rather than child by child.

## Digest And Loader Reach-through

The digest and loader roots reach a layered carrier only through the exact
retained objects. For the module at selected position `n`, the digest is read
from `trusted_source_snapshots[n]`, whose `selected_input` must be the exact
`selected_input_index.entries[n]`, whose identity must be the exact module
identity, and whose position must be `n`. A layered digest identity is accepted
only when its algorithm is `SHA256_OPENED_BYTES` and its hexadecimal digest and
byte count equal that exact snapshot's values.

No path is discovered, no file is reopened, no byte is re-hashed, no filesystem
state is re-examined, and no loader is implemented. Slice 13 performs no
filesystem, network, registry, or ambient resolution of any kind.

A layered source digest identity is deliberately a content identity. Two
distinct modules with byte-identical sources carry equal digest identities and
remain two identity-distinct module assets; the digest lookup returns the
complete two-element bucket.

## Canonical Root-derived Projection

There is one canonical projection: the ordered owner identity, module-asset
tuple, and declaration-asset tuple derived from the six roots inside the private
authority carrier's `__post_init__` and assigned with `object.__setattr__`.
Those three products are `init=False`, so `dataclasses.replace` on the authority
accepts roots only and coherently rebuilds every product; it can neither accept
nor graft a supplied owner, module asset, or declaration asset.

The complete identity bucket of every nominal identity is part of that
projection: it is built once in one pass over the catalog roots, and every
occurrence of one identity retains the exact same bucket object rather than a
freshly rescanned equal tuple. Each declaration asset retains that derived
mapping as a private validation-only root and admits only the exact bucket
object it holds for its own identity, so a supplied tuple carrying a foreign
value-equal occurrence cannot downgrade a unique declaration to `AMBIGUOUS`.

As in Slice 11, a carrier-level check is not factory-origin attestation: a
coordinated replacement that substitutes every root and every derived product
of one carrier at once is closed by the fact set, which requires the exact
objects the authority derived, not by the carrier alone.

The public fact set requires its `owner`, `module_assets`, and
`declaration_assets` to be the exact objects that authority derived. The three
lookup indexes are computed from those tuples at construction, copy complete
buckets into `MappingProxyType` values, and return tuples. They are derived
conveniences and never independent authorities.

Module assets follow exact selected-input order. Declaration assets follow
catalog order and then source declaration order. Every lookup returns the
complete matching bucket and selects no winner.

## Loader Readiness And Fail-closed States

Loader readiness is a module fact, and every declaration asset of a module
retains that exact same readiness object.

- `READY` with reason `TRUSTED_LOCAL_SOURCE_RESOLVED` and an empty blocking
  tuple, for a module that appears in the shared Slice 10 dependency order.
- `BLOCKED` with reason `MODULE_CYCLE_BLOCKED` and a non-empty blocking tuple of
  retained `MODULE_GRAPH_CYCLE_BLOCKED` issue roots, for a module that is absent
  from the dependency order.

Cycle membership is decided only by the retained cycle component of each issue,
never by the issue's owning module. An acyclic, dependency-ordered module that
merely references a cycle-blocked target also owns a
`MODULE_GRAPH_CYCLE_BLOCKED` issue, and it remains `READY`. A module's blocking
evidence is exactly the retained issues whose cycle component lists that module
as a member.

Status, reason, and blocking evidence form one atomic tuple. `READY` with
blocking evidence, `BLOCKED` without it, a mismatched reason, and a blocking
issue of any other status each fail closed. A dependency-ordered module that is
still a retained cycle member, and an unordered module that is not, both fail
closed during derivation.

Blocking evidence is owned by the module it names, and ownership is decided by
object identity rather than by value. Every module asset and every declaration
asset retains the authority's derived per-module readiness mapping as a private
validation-only root and admits only the exact readiness object that mapping
holds for its own module. A second, disjoint module cycle's evidence is
rejected, and so is a value-equal readiness produced by another project with
the same module paths and the same cycle shape.

## Availability Algebra

Declaration-asset availability is reduced only after the complete identity
bucket and the complete semantic-fact bucket exist.

1. A loader-`BLOCKED` module publishes `BLOCKED` for every declaration asset,
   with no semantic facts and no relation state.
2. A nominal identity with more than one retained occurrence publishes
   `AMBIGUOUS` for every occurrence of that identity, retains the complete
   occurrence bucket, and publishes no relation state and no winner.
3. A unique non-relation-namespace declaration publishes `ABSENT`, meaning no
   syntactic or applicable relation fact exists. `ABSENT` is not `UNKNOWN`.
4. A unique relation-namespace declaration requires exactly one Slice 12
   semantic fact, retains that fact's exact `ProjectRelationRowSchemaState`
   object, and maps its status one-to-one onto `CONCRETE`, `UNKNOWN`,
   `DEFERRED`, or `BLOCKED`. No status is upgraded, downgraded, inferred from
   children, or collapsed into another family.

Every other combination fails closed. `AMBIGUOUS` without a repeated identity,
a published relation state under `AMBIGUOUS` or `BLOCKED`, a semantic fact under
`ABSENT`, an availability that disagrees with its retained state, and a state
object that is not the exact Slice 12 object each raise.

## Identity, Ordering, And Multiplicity

Nominal identity remains the exact Slice 5 tuple of module path, namespace,
declaration kind, and declared name. Slice 13 never rewrites it with an owner
name, an alias, a facade name, or a digest. Same-spelling declarations in
different modules never merge, because the module path is part of the identity
and the owner identity is separate from it.

Cardinalities zero, one, two, three, and every larger identity-distinct
occurrence survive. A declaration asset retains its own declaration position,
its exact occurrence object, its exact Slice 11 attribution object, and its
exact Slice 12 fact bucket. Retained occurrences, attributions, semantic facts,
selected entries, and snapshots are evidence: they are excluded from
representation, semantic equality, and hashing.

No first match, early return, shortest path, best score, or set-default
insertion selects a canonical fact. No name-keyed map, rendered message, or
display string is a deduplication key.

## Construction And Termination

Construction validates the whole shared root set before deriving any product,
then derives module assets in selected-input order and declaration assets in
catalog and source order. The procedure is a single finite pass over the finite
module tuple and the finite catalog occurrence tuples; it contains no fixed
point of its own and therefore terminates immediately.

The composed fixed point converges because both inputs converge independently
before the join: Slice 11 has already reached its fixed point over the Slice
5-10 roots, Slice 12 has already reached its own over the Slice 10 roots, and
the join adds no iteration, no propagation round, and no mutual recursion. It
only reads two settled products anchored to one shared root set. Missing,
foreign, partial, duplicated, reordered, or mixed-root authority fails closed
rather than iterating.

## Integration And All-or-none Boundary

`ProjectSemanticResult.module_package_identity_facts` is the only integration
field and the tenth module sidecar. The all-or-none invariant now covers ten
sidecars: catalogs, exports, bindings, graph, diagnostics, type/source
resolutions, relation resolutions, semantic facts, attribution facts, and
package-neutral identity facts. Legacy-flat results forbid all ten.
Explicit-module preliminary results permit all ten to be absent, but once any
one exists all ten must exist and `model` must remain `None`.

The semantic result additionally requires the layered authority's attribution
root to be its own exact attribution sidecar, its semantic root to be its own
exact semantic sidecar, and its selected-input index, trusted-snapshot tuple,
module tuple, and catalog set to be its own exact objects. A foreign otherwise
valid layered sidecar, a surrogate layered object, and deletion of any one
sidecar therefore fail closed.

## Privacy And Compatibility Boundary

Schema v1 has no Slice 13 sidecar and remains byte-exact. Schema v2 continues to
use `model=None`.

Slice 13 adds no public export, CLI option, CLI text or JSON v1 field, Project
JSON v2 key or key order, Semantic Metadata Artifact v1 key, diagnostic code,
diagnostic message, grammar, generated artifact, abstract syntax tree node,
intermediate representation node, PostgreSQL or MySQL SQL behavior, fixture,
golden, example, package dependency, lockfile, workflow, package version,
release, signing, attestation, runtime behavior, or database behavior.

## Negative Boundary

Slice 13 implements none of the following, and each remains owned elsewhere:

- a package manager, package registry, remote discovery, fetch, install, cache,
  trust boundary, or signing (Phase 67);
- dependency ranges, a version solver, or a canonical lockfile (Phase 68);
- a final package manifest, typed package asset schema, package identity,
  manifest key, asset schema field, package dependency fact, or package loading
  (Phase 55);
- a package-level local graph or package provenance (Phase 59);
- a capability-profile language or declared checking (Phase 56);
- extension catalog content (Phase 57);
- a public explain, portability, or package inspection artifact (Phase 58);
- private module inspection or canonical serialization (Slice 14);
- Rust-ready pure boundaries and differential vectors (Slice 15);
- Project IR (Phase 61); relationship, JOIN, grain, and fanout semantics (Phase
  62); project emit-SQL (Phase 63).

A material unresolved owner, asset, digest, or loader product decision is a
substantive stop rather than an invitation to invent package semantics.

## Validation Lock

The focused property matrix covers the package-neutral owner and asset
vocabulary; the shared-root predicate against value-equal, misaligned,
partial, and coordinated foreign root sets; digest reach-through, byte-equal
digest multiplicity, and digest lookup completeness; loader readiness `READY`
and `BLOCKED` with their atomicity failures; availability `CONCRETE`,
`UNKNOWN`, `DEFERRED`, `BLOCKED`, `ABSENT`, and `AMBIGUOUS`; nominal-identity
collision with a complete no-winner bucket; cardinalities zero through three;
selected-input, catalog, and source ordering; cross-module same-spelling
separation; the foreign value-equal graft and derived-product graft rejections;
Slice 11 and Slice 12 independence and their unchanged behavior; the tenth
all-or-none sidecar boundary; schema-v1 absence and byte exactness; and builder
purity with no input or output operation. Dimensions are covered without a
Cartesian product.

Gate 2 additionally requires the corrected exact 60-reader zero-addition and
zero-delta fixed point, check-only Ruff over the exact 64 Python paths,
production and test Pyright, focused and compatibility suites, the seven
publication-topology projections, generated count 8, golden count 37, package
smoke, lock check, authoritative offline validation, an independent full pytest
run, exact `A3_M65_D0`, an empty Git index, a reviewed tree, and immutable
evidence.
Gate 3 alone may make Slice 13 `COMPLETED`; the next valid resume point is then
`PHASE54_SLICE14_GATE0_GATE1`.
