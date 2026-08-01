# Phase 54 Slice 9 Cross-module Type Alias, Enum, Shape, And Source Resolution v1

Status: Gate 2 contract

## Scope

Slice 9 adds one private schema-v2 semantic sidecar for deterministic
cross-module type and source resolution. It consumes the already retained
logical modules, module catalogs, export facades, named-import binding
environments, module graph, and module diagnostic facts. It does not reopen
source files or reinterpret import target text.

The implementation surface is intentionally narrow:

- `TypeDef.base` is resolved directly and canonically;
- every `ShapeDef.fields[].type_expr` is resolved in field order;
- `SourceDef.shape_name` resolves only a direct shape;
- local and imported type aliases, enums, shapes, and sources retain nominal
  identity;
- module errors suppress same-root semantic cascades.

Constraint and derive signatures remain deferred because callable module-asset
ownership and complete signature propagation are later contracts. Table,
query, general relation, relationship endpoint, row-schema, field, IR, and SQL
resolution remain outside Slice 9.

## Trusted inputs

The resolver consumes only:

1. `tuple[ProjectLogicalModule, ...]`;
2. `ProjectModuleCatalogSet`;
3. `ProjectModuleExportSurfaceSet`;
4. `ProjectModuleBindingEnvironmentSet`;
5. `ProjectModuleGraph`;
6. `ProjectModuleDiagnosticSet`.

It performs no discovery, source reading, target normalization, basename or
suffix lookup, path-case folding, package lookup, registry access, network IO,
callback execution, or heuristic import reconstruction.

## Namespace contract

`TypeDef`, `EnumDef`, and `ShapeDef` share the existing
`ProjectSymbolNamespace.TYPE` namespace. `SourceDef` retains its existing
`ProjectSymbolNamespace.RELATION` / `ProjectSymbolKind.SOURCE` nominal
identity, but Slice 9 exposes only an exact source-kind lookup. A table or
query is never a source fallback.

Builtin type names retain current precedence. Otherwise a type reference sees
only local type declarations and explicit local imported bindings. A source
shape reference sees only that same type namespace and succeeds only when the
direct declaration kind is `SHAPE`. An alias whose canonical terminal is a
shape is not a direct source shape.

There is no local-over-import or import-over-local winner. Slice 7 collisions
block the affected namespace/local name. Local duplicate type or source
buckets also choose no winner. A failed intended-namespace lookup never
searches another namespace.

## Identity contract

`ProjectResolvedNominalSymbol` retains all of:

- the using module path;
- the local lookup name;
- the target four-component nominal declaration identity;
- the exact target catalog occurrence;
- either the local occurrence or the resolved imported binding.

Exactly one of the local occurrence and imported binding is present. For an
import alias, the local name remains distinct from the target declared name.
For an explicit re-export, the resolved binding's original target identity is
preserved; the intermediate facade module never becomes the declaration
owner.

Semantic identity is never replaced by an AST object's identity, a filesystem
path outside logical module identity, or display text.

## Dependency-first order

The resolver uses a deterministic Kahn traversal over the noncyclic induced
Slice 8 graph. Graph edges point from importer to dependency, so a vertex is
ready only after all of its noncyclic dependency targets have been emitted.
The lowest selected-input position is the only ready-set tie-breaker.

Every noncyclic vertex is emitted at most once. Dictionary iteration does not
control meaning, and no fixed point is used.

Cyclic SCC members do not receive resolution environments. An acyclic module
that imports a cyclic target remains eligible for independent local checking,
but that imported local binding is blocked by the existing `PIE-S2703` root.
An unresolved external import similarly blocks only its affected local binding
while unrelated local errors remain visible.

## Private carriers

`src/pietto/_project/module_resolution.py` is private and has `__all__ = ()`.
Its carriers are frozen, slotted, keyword-only dataclasses with tuple-backed
ordered collections and copied `MappingProxyType` lookups:

- `ProjectResolvedNominalSymbol`;
- `ProjectModuleTypeReference`;
- `ProjectResolvedModuleTypeReference`;
- `ProjectModuleSourceShapeReference`;
- `ProjectResolvedModuleSourceShapeReference`;
- `ProjectTypeSourceResolutionIssue`;
- `ProjectModuleTypeSourceResolutionEnvironment`;
- `ProjectTypeSourceResolutionSet`.

Lookups return complete tuples and never an arbitrary element. The project
result stores the sidecar only in the trailing private optional field
`ProjectSemanticResult.module_type_source_resolutions`.

## Direct and canonical type facts

Direct resolution uses the existing `ProjectResolvedTypeKind` vocabulary:

- `BUILTIN` for current builtin names;
- `TYPE_ALIAS` for a nominal alias declaration;
- `ENUM` for a nominal enum declaration;
- `SHAPE` for a nominal shape declaration;
- `UNKNOWN` for an absent or blocked target.

A direct alias retains its target alias identity. Its `alias_chain` is the
ordered unique tuple of alias identities traversed from that direct target.
Canonical expansion terminates at a builtin, enum, shape, or `UNKNOWN`; it
never terminates at `TYPE_ALIAS`.

Unknown alias roots emit one `PIE-S2002`. Downstream aliases and consumers
retain canonical `UNKNOWN` without additional diagnostics. Alias traversal is
iterative and bounded by the number of valid alias identities.

## Alias cycles

Local alias cycles retain current single-file meaning. Each cycle emits one
`PIE-S2003` at the base `TypeExpr` of the earliest participating alias in
module/declaration order:

```text
Type alias cycle involving A
```

All cycle members and aliases leading into the cycle have canonical
`UNKNOWN`. A module graph cycle is excluded before alias traversal and remains
owned by `PIE-S2703`; it is never relabeled as a type-alias cycle.

## Enums

Imported enums retain exact nominal enum identity. Equal member lists do not
merge declarations. Enums are not converted to `Text` or another primitive,
and Slice 9 adds no coercion, comparison, storage, SQL, or serialization
semantics.

## Shapes

Imported shapes retain exact nominal shape identity. Each field's `TypeExpr`
produces one direct/canonical resolution fact in field order. Duplicate field
occurrences remain separate reference facts; current shape-local structural
diagnostics are not reimplemented.

No shape result becomes a relation row schema in Slice 9.

## Sources

Unambiguous local sources and explicit imported source bindings produce exact
source nominal symbols. Import aliases and explicit re-exports retain local
binding identity separately from the original source identity.

A source without `shape_name` creates no source-shape reference. A shaped
source resolves only a direct local or imported `SHAPE`. Missing and wrong-kind
references use the current `PIE-S2303` messages.

No source consumer, table/query input, relation dependency, row schema, field
lookup, relationship endpoint, IR, or SQL fact is built.

## Structured issues

The closed issue statuses are:

- `AMBIGUOUS_LOCAL_TYPE_NAME`;
- `AMBIGUOUS_LOCAL_SOURCE_NAME`;
- `UNKNOWN_TYPE_REFERENCE`;
- `TYPE_ALIAS_CYCLE`;
- `UNKNOWN_SOURCE_SHAPE_REFERENCE`;
- `INCOMPATIBLE_SOURCE_SHAPE_KIND`;
- `MODULE_GRAPH_CYCLE_BLOCKED`;
- `MODULE_DIAGNOSTIC_BLOCKED`.

Each issue retains exact typed evidence, primary location, private related
locations, and either one emitted diagnostic or the exact suppressing Slice 8
diagnostic values. Issue kind is never inferred from message text.

## Diagnostic mapping

No new diagnostic code is introduced:

| Issue | Code | Exact message form |
| --- | --- | --- |
| ambiguous local type | `PIE-S2001` | `Duplicate symbol name in type namespace: {name}` |
| ambiguous local source | `PIE-S2001` | `Duplicate symbol name in relation namespace: {name}` |
| unknown type | `PIE-S2002` | `Unknown type: {name}` |
| alias cycle | `PIE-S2003` | `Type alias cycle involving {anchor_name}` |
| unknown source shape | `PIE-S2303` | `Unknown source shape: {name}` |
| wrong source shape kind | `PIE-S2303` | `Source shape must refer to a shape: {name}` |

All emitted diagnostics have severity `ERROR` and no suggestion. Duplicate
diagnostics use the second occurrence as primary. Type diagnostics use the
exact `TypeExpr` span. Alias cycles use the anchor alias base span. Source
shape diagnostics use the complete `SourceDef` span, matching current project
behavior.

## Suppression and ordering

Existing module roots remain first and byte-stable:

- `PIE-S2701` owns unresolved selected targets;
- `PIE-S2703` owns module graph cycles;
- `PIE-S2704` owns target export failures;
- `PIE-S2705` owns private or non-exported imports;
- `PIE-S2706` owns local/import/alias collisions;
- `PIE-S2707` owns inconsistent facades and unsupported module forms.

One root blocker is retained per affected namespace/local-name bucket,
regardless of consumer count. It emits no derived type/source diagnostic.
Independent local semantic errors remain visible.

Slice 9 diagnostics follow dependency-first environment order. Within one
environment they follow source location and the closed issue-status order.
Cyclic-member block issues are private, selected-position ordered, and emit no
second public diagnostic.

## Compatibility and privacy

Schema v1 constructs no Slice 9 sidecar and continues through the existing
legacy-flat resolver byte-for-byte. Slice 9 changes no schema-v1 model,
diagnostic, text, JSON, CLI, IR, PostgreSQL, MySQL, or package behavior.

Schema v2 retains `model=None`, constructs no Project IR or project SQL, and
does not claim complete module semantics. The private sidecar is not added to
Project JSON v2, CLI JSON v1, Semantic Metadata Artifact v1, or public Python
exports. Only existing project diagnostic surfaces may expose the mapped
diagnostics, with unchanged document keys and ordering rules.

## Retained boundary

Slice 10 retains table/query/relation lookup, relation dependency resolution,
row-schema propagation, relation field lookup, relationship/JOIN/grain/fanout,
Project IR, and project SQL.

Slices 11 and 12 retain complete attribution, dependency, origin, provenance,
lineage, generic-signature, nullability, aggregate, grouped, window,
result-role, and capability propagation. Phase 66 retains callable,
constraint, derive, relationship, wildcard, qualified, and advanced
module/package assets.
