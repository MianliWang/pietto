# Phase 54 Slice 5 — Module-qualified Nominal Declaration Identity And Per-module Catalogs v1

## Status And Authority

Phase 54 is `ACTIVE`; Slices 1 through 4 are `COMPLETED`. The trusted Slice 5
base is `0f3c955c5a5fbd8046ef611ad1bef0b636c8be01`, with tree
`3a6144b018cbf9d4b1ce62089975000071db6c37`. During Gate 2, Slice 5 remains
incomplete. It becomes `COMPLETED` only after exact reviewed-tree publication,
natural exact-head pull-request CI attempt 1, squash-tree equality, natural
exact-head `main` CI attempt 1, ff-only reconciliation, branch cleanup, and
immutable Gate 3 evidence. Slice 6 then becomes the next separately gated
work.

The active roadmap v2, the Phase 54 plan, Slices 1 through 4 contracts and
immutable evidence, live source, and the Slice 5 Gate 0 / Gate 1 authority
control this contract. Historical descriptions do not expand it.

## Exact Scope

Slice 5 adds a private, immutable inventory of local declarations for
schema-v2 explicit-module projects. Its prospective Gate 2 changed set is
exactly `A3_M53_D0`: three additions, four direct modifications, and 49
executing mechanical readers. The focused module contains exactly 30
undecorated, non-parametrized top-level tests; projected clean collection is
10916; the one write-mode Ruff manifest contains 52 literal handwritten
Python paths.

This slice adds no source-visible syntax, name resolution, visibility,
binding, graph, diagnostic, IR, SQL, serializer, public API, dependency,
workflow, package-version, fixture, golden, example, release, or native-build
behavior.

## Four-component Nominal Identity

`ProjectNominalDeclarationIdentity` is a private frozen, slotted, keyword-only
value with exactly these fields, in this order:

1. `module_path: str`
2. `namespace: ProjectSymbolNamespace`
3. `declaration_kind: ProjectSymbolKind`
4. `declared_name: str`

Equality and hashing use exactly those four values. `module_path` follows the
existing exact normalized selected project-root-relative `.pietto` path
contract. Path and name case and Unicode spelling are retained literally.
There is no trimming, case folding, Unicode normalization, or rewriting.

AST object identity, source spans, ordinals, selected positions,
`ProjectLogicalModule` payload equality, physical or canonical paths,
device/inode facts, digests, trusted snapshots, parser contexts, process
identity, catalog order, and package identity do not participate.

## Declaration Occurrences

`ProjectDeclarationOccurrence` is a distinct private frozen, slotted,
keyword-only value containing:

1. `identity: ProjectNominalDeclarationIdentity`
2. `module_position: int`
3. `declaration_position: int`
4. `definition: Definition`

Positions are exact non-negative integers. The occurrence validates that the
definition's current name, namespace, and declaration kind match the nominal
identity. Its positional and AST payload does not change identity equality or
hashing. Repeated declarations may therefore share one identity while
remaining distinct source occurrences.

## Exact Definition Mapping

| AST definition | Namespace | Declaration kind |
| --- | --- | --- |
| `TypeDef` | `TYPE` | `TYPE_ALIAS` |
| `EnumDef` | `TYPE` | `ENUM` |
| `ShapeDef` | `TYPE` | `SHAPE` |
| `SourceDef` | `RELATION` | `SOURCE` |
| `TableDef` | `RELATION` | `TABLE` |
| `QueryDef` | `RELATION` | `QUERY` |
| `ConstraintDef` | `CALLABLE` | `CONSTRAINT` |
| `DeriveDef` | `CALLABLE` | `DERIVE` |

All eight mappings reuse the existing `ProjectSymbolNamespace`,
`ProjectSymbolKind`, and `_classify_project_definition` ontology. No second
enum family is introduced, and no enum-owner extraction is necessary because
the focused owner and function-local integration form no runtime import cycle.

`RelationshipMetadata` is not a `Definition` and is excluded. Slice 4
`ImportStatement` and `ExportStatement` values remain separate module
statements and are excluded. Constraint and derive declarations are inventoried
but are not made importable or exportable.

## Per-module Catalog

`ProjectModuleCatalog` retains one exact parsed `ProjectLogicalModule` and a
tuple of every `ProjectDeclarationOccurrence` in definition source order. Its
`module_path` property returns the owner's exact logical path. Construction is
valid only for `EXPLICIT_MODULES`, requires a parsed input, and rejects omitted,
reordered, or mismatched occurrences. Duplicate identities are valid.

`find_namespace_name(namespace, declared_name)` returns an immutable tuple of
all exact matches in source order. No match returns `()`, one match returns a
one-element tuple, and ambiguity returns the complete tuple.

## Immutable Project Catalog Set

`ProjectModuleCatalogSet` contains module catalogs in exact selected-input
order. It requires contiguous module positions and unique logical paths. The
exact empty carrier is valid, even though the current source-selection
contract makes a zero-selected-input project fail with `PROJECT_GLOB` before a
complete integrated catalog set can be built.

`find_identity(identity)` returns all matching occurrences in module then
definition order. `find_module_path(module_path)` returns a zero- or
one-element catalog tuple. Invalid paths fail closed to `()`.

The builder derives the complete set only from the schema-v2
`ProjectLogicalModule` tuple and each retained
`module.parsed_input.script.definitions`. It does not reopen source files,
walk the filesystem, consult import target strings, normalize paths again,
resolve names, inspect visibility or exports, build graph edges, call a
registry, or create IR or SQL.

## Duplicate And Collision Preservation

- The same spelling in different modules has distinct nominal identities.
- The same spelling in different namespaces has distinct namespace buckets.
- The same namespace/name across declaration kinds has distinct identities
  and one complete ambiguous namespace/name bucket.
- Repeating all four identity components yields one identity with multiple
  retained occurrences.
- Source order is deterministic evidence, not precedence.

There is no `first`, winner, fallback, shadowing, last-write-wins, or arbitrary
unique lookup. Schema-v2 catalogs do not emit `PIE-S2001` or `PIE-S2701`
through `PIE-S2707`. Existing schema-v1 first-winner `PIE-S2001` behavior is
unchanged.

## Project Result Integration

`ProjectSemanticResult` gains one trailing defaulted private field:

```python
module_catalogs: ProjectModuleCatalogSet | None = None
```

The type-only model import and function-local schema-v2 builder import avoid a
runtime cycle. Invalid parse/check results retain `None`. A valid schema-v2
result retains the complete catalog set while keeping `model=None`,
`diagnostics=()`, and `.ok == False`; it still returns before the legacy flat
catalog. `ProjectParseCheckResult`, `ProjectSemanticModel`, and the schema-v1
semantic path are unchanged.

## CLI, JSON, And Public Privacy

For a valid schema-v2 project, text check still exits 1 with empty stdout and
stderr. JSON check still exits 1 while preserving the current Project JSON v2
document, key order, and parse-owned `"ok": true` value. No identity, catalog,
namespace, kind, module path, collision bucket, or count is serialized.

The new owner has `__all__ = ()`. Pietto's top-level exports, parser API, CLI
options, CLI JSON v1, Project JSON v2, Semantic Metadata Artifact v1, public
Python emitters, diagnostics inventory, Semantic IR, and PostgreSQL/private
MySQL SQL remain unchanged.

## Import And Export Non-consumption

Catalog construction reads only `Script.definitions`. Imports do not add local
declarations; exports do not remove them; aliases do not rename them; targets
do not trigger lookup or loading. Module statements create no visibility,
binding, re-export, reachability, graph, diagnostic, or resolution facts in
Slice 5.

## Schema-v1 Compatibility

Schema v1 retains selected-input order, the flat project-global
TYPE/RELATION/CALLABLE maps, collect-before-resolve behavior, first-winner
duplicate handling, `PIE-S2001`, diagnostic ordering, semantic facts, CLI text,
Project JSON v2, and single-file `check`, `explain`, and `emit-sql` behavior.
PostgreSQL and private MySQL behavior remain byte-stable.

## Retained-later Ownership

Slice 6 retains local export eligibility, private-by-default visibility,
explicit named re-export, and facade semantics. Slice 7 retains named imports,
aliases, binding environments, and collision rules. Slice 8 retains the module
graph, cycles, deterministic issues, the diagnostic adapter, and `PIE-S2701`
through `PIE-S2707`.

Slice 9 retains cross-module type alias, enum, shape, and source resolution.
Slice 10 retains cross-module table/query/relation resolution and legacy
integration. Slices 11 and 12 retain identity-safe semantic fact propagation.
Slices 13 through 15 retain package-neutral identity layering, inspection,
serialization, pure boundaries, vectors, and hardening. Slice 16 remains under
the active roadmap. No retained-later behavior is pulled into Slice 5.

## Stop And Next State

Mechanical hash, manifest, inventory, formatter, topology, or evidence repair
inside the frozen `A3_M53_D0` reader closure is not a product decision. A
substantive identity, catalog, compatibility, privacy, or publication-boundary
change is a STOP. After exact Gate 3 success, stop at
`PHASE54_SLICE6_GATE0_GATE1`; do not begin Slice 6 in this slice.
