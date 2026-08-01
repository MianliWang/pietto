# Phase 54 Slice 7 Named Imports, Aliases, Binding Environments, And Collision Rules v1

Status: Gate 2 implementation contract.

This specification implements the private schema-v2 Slice 7 boundary frozen by
the Phase 54 roadmap and Gate 0 / Gate 1 authority. It adds deterministic named
import binding facts and feeds the existing Slice 6 explicit named re-export
candidate seam. It adds no public success path, diagnostic, graph, semantic
resolution, IR, SQL, runtime, dependency, package, workflow, fixture, or golden
behavior.

## Accepted Source Boundary

Slice 7 consumes only the contextual AST admitted by Slice 4:

```pietto
import "models/customer.pietto":
    shape Customer
    query orders as imported_orders
```

The alias direction is exactly `exported_name as local_name`. An omitted alias
uses the exported name as the local binding name. The six eligible declaration
kinds remain `type`, `enum`, `shape`, `source`, `table`, and `query`. Slice 7
adds no wildcard, qualified, side-effect, package, remote, `export from`, or
alternate-alias form.

## Exact Target And Facade Resolution

An import target is resolved only by
`ProjectSelectedInputIndex.find_path(ImportStatement.target)`. The lookup uses
the normalized logical module path already retained by Slice 3. It performs no
filesystem access, source reopening, discovery, suffix or basename matching,
case folding, package search, remote lookup, or physical-path comparison.

Only an exact `ProjectModuleExportEntry` on the direct target module facade is
importable. A declaration present only in the Slice 5 catalog remains private
or unexported. A missing, inconsistent, or ambiguous facade match fails closed.
The resolved binding retains the facade entry's existing
`ProjectNominalDeclarationIdentity`; an alias never rewrites its module path,
namespace, declaration kind, or declared name.

## Private Carrier Model

`src/pietto/_project/module_bindings.py` owns the new private model and keeps
`__all__ = ()`. Every carrier is a frozen, slotted, keyword-only dataclass and
all ordered collections are tuples.

`ProjectImportedBindingIdentity` has exactly:

- `owning_module_path`;
- eligible `namespace`;
- eligible `declaration_kind`; and
- `local_binding_name`.

`ProjectModuleImportRequest` has exactly:

- `identity`;
- `target_module_path`;
- `exported_name`;
- complete module-statement and item positions;
- retained source `ImportStatement`; and
- retained source `ImportItem`.

`ProjectResolvedImportedBinding` has exactly:

- the importing-module-owned local `identity`;
- the direct `target_module_path`;
- the source-module-owned `target_identity`;
- the exact source `request`; and
- the direct `resolved_entry`.

`ProjectModuleBindingIssue` retains its exact status and request plus the
applicable complete tuples of target surfaces, target entries, target
declaration occurrences, local declaration occurrences, competing import
requests, and prior exact requests.

`ProjectModuleBindingEnvironment` retains one parsed logical module, every
source-ordered import request, every unambiguous binding in request order, and
all request-ordered issues. Its binding lookup is a copied immutable
`MappingProxyType` keyed by `ProjectImportedBindingIdentity` and returns tuples.

`ProjectModuleBindingEnvironmentSet` retains environments in selected-input
order, the exact source-ordered `ProjectImportedExportCandidate` tuple supplied
to Slice 6, and a copied immutable module-path lookup.

## Exact Private Issue Statuses

The private statuses are:

1. `UNRESOLVED_TARGET_MODULE`;
2. `UNKNOWN_EXPORTED_NAME`;
3. `PRIVATE_OR_UNEXPORTED_DECLARATION`;
4. `INCONSISTENT_TARGET_FACADE`;
5. `AMBIGUOUS_TARGET_FACADE`;
6. `LOCAL_DECLARATION_COLLISION`;
7. `IMPORT_BINDING_COLLISION`; and
8. `DUPLICATE_SOURCE_REQUEST`.

The first five are retained for future `PIE-S2705` or `PIE-S2707` adaptation.
The two collision statuses are retained for future `PIE-S2706` adaptation.
The duplicate request fact remains private input evidence for those future
adapters. Slice 7 neither registers nor emits any `PIE-S2701` through
`PIE-S2707` diagnostic.

## Collision And No-winner Semantics

Every exact import item remains a distinct request. A later byte-equivalent
request retains all earlier exact requests in a `DUPLICATE_SOURCE_REQUEST`
fact. All requests claiming the same local binding name collide, including
different exported names aliased to that name and namespace or kind
disagreements. A local declaration with the same local name also collides.

Collision evidence never establishes precedence. There is no first, last,
source-order, alias, local, import, export, or shadow winner. A request with any
blocking resolution or collision fact creates no resolved binding and supplies
no Slice 6 candidate. Reordering import statements or items can reorder source
evidence, but it cannot change whether a binding bucket is ambiguous.

An exact export request matching one unambiguous imported local binding remains
the intentional explicit named re-export path. Slice 6 independently validates
that request against the supplied candidate and continues to reject local,
imported, kind, namespace, or multiplicity competition.

## Direct Re-export And Single Backfill

The pure builder consumes the selected-input index, parsed logical modules, and
catalog set. It first constructs the Slice 6 local-facade snapshot, resolves
direct named imports, supplies those exact candidates to Slice 6 once, and then
resolves the retained environments against that backfilled direct-facade
snapshot.

When the direct target entry has origin `EXPLICIT_REEXPORT`, Slice 7 copies its
already-resolved `target_identity` into the importing binding. It does not
follow `resolved_from`, inspect the target identity's owning module, recurse,
traverse a module graph, or iterate facades to a fixed point. Every exposed hop
still requires a source `export` request. Deeper graph validation and cycle
behavior remain Slice 8 work.

## Slice 6 Integration

Each successful binding becomes exactly one
`ProjectImportedExportCandidate` with:

- the importing module path;
- local binding namespace and declaration kind;
- local binding name;
- unchanged target nominal identity;
- `EXPLICIT_NAMED_IMPORT` proof;
- original import statement and item positions; and
- the alias span when present, otherwise the exported-name span.

`build_empty_project_semantic_result` passes that tuple to
`_build_project_module_export_surface_set`. Slice 7 does not modify the Slice 6
candidate carrier, constructor validation, facade entry, or issue model.

## Schema And Public Posture

For a successfully parsed schema-v2 project, `ProjectSemanticResult` privately
retains the selected-input index, trusted source snapshots, module catalogs,
binding environments, and integrated module export surfaces. It still has
`model=None`, `.ok == false`, no public diagnostics, text exit status 1 with
empty output, and the exact existing nine-key Project JSON v2 envelope.

Schema v1 never constructs the Slice 7 environment. Its legacy flat catalog,
first-winner duplicate behavior, diagnostics and ordering, semantic model,
`.ok`, CLI text and JSON, check, explain, PostgreSQL, and private MySQL behavior
remain exact.

## Retained Boundaries

Slice 8 retains graph edges, cycles, strongly connected components,
topological behavior, public issue ordering, diagnostic adaptation, and
`PIE-S2701` through `PIE-S2707`. Later slices retain cross-module type and
relation resolution, semantic propagation, inspection and serialization,
Project IR, and project SQL. Phase 66 retains advanced import and package
forms.

Grammar, generated parser, AST layout, parser API, public exports, CLI and JSON
schemas, diagnostics registry, IR, SQL, runtime/database behavior,
dependencies, `uv.lock`, workflows, package version, fixtures, goldens,
examples, release operations, and Rust/native surfaces remain unchanged.
