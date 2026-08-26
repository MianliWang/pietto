# Phase 59 Slice 7 Package-To-Module Attribution Bridge v1

## Answer And Owner

Slice 7 attaches each successful Phase 59 package occurrence to the exact
trusted modules already retained by its loaded-package authority, then attaches
each module to its exact source-ordered AST definition occurrences.

```text
package occurrence
-> package-qualified module occurrence
-> package-qualified declaration occurrence
```

This is ownership and occurrence attribution only. It adds no semantic
visibility, resolution, import, field, lineage, SQL, Project Explain, or CLI
behavior.

## Existing Authority

| Authority | Existing owner | Slice 7 use |
| --- | --- | --- |
| Successful package order and loaded package entry | `PackageInspectionFactSet` | Exact package occurrence owner |
| Root package module | `PackageParsedModule` | Exact trusted module witness |
| Dependency package module | `_PackageModuleContent` | Exact trusted module witness |
| Module identity/order/source/script | loaded package `modules` tuple | Exact package-local module order |
| Declaration occurrence/order | `module.script.definitions` | Exact authored definition witnesses |

Package inspection already verifies that each loaded package retains every
typed module asset in manifest order and that every module position, asset,
identity path, source, and parsed script agrees. Slice 7 consumes that authority
without reading files, reparsing source, or constructing another semantic
model.

Package-root project semantics deliberately expose no `ProjectLogicalModule`,
`ProjectModuleCatalogSet`, or `ProjectModuleAttributionFactSet`. Slice 7 does
not graft explicit-module sidecars onto package-root mode and does not create
alternate nominal declaration identities. The exact AST definition is retained
only as the authored declaration witness.

## Package-Qualified Occurrence Identity

| Ref | Deterministic local coordinate |
| --- | --- |
| `PackageGraphModuleRef` | snapshot scope + exact package ref + package-local module position |
| `PackageGraphDeclarationRef` | snapshot scope + exact module ref + module-local declaration position |

`PackageGraphModule` retains its module ref, package ref, exact loaded package
authority, and exact loaded module witness. `PackageGraphDeclaration` retains
its declaration ref, module ref, and exact AST `Definition` witness.

Paths, names, declaration names, source text, source bytes, content digests,
display syntax, and semantic identity do not participate in graph occurrence
identity. The same `main.pietto` module and same declaration name under two
package occurrences therefore remain distinct.

All refs are snapshot-scoped and domain-typed. Foreign-snapshot, wrong-domain,
dangling, reordered, grafted, or package-authority-mismatched refs fail closed.

## Construction And Order

Canonical package-graph construction consumes only successful retained package
inspection authority. For each package in existing inspection order it:

1. retains the exact loaded package object;
2. creates one graph module per `package.modules` occurrence in existing order;
3. creates one graph declaration per `module.script.definitions` occurrence in
   existing order;
4. retains every exact module and definition witness;
5. validates package coordinate, content digest, role, module membership,
   package/module positions, and complete declaration coverage.

Snapshot storage order is package, then package-local module, then module-local
declaration. Construction performs no sorting, deduplication, path matching,
name matching, or winner selection.

## Compilation-Island Boundary

Package dependency topology and semantic visibility remain separate. A package
dependency does not expose, import, re-export, resolve, or bind the target
package's modules or declarations. Slice 7 stores only forward ownership
attribution.

The Slice 6 direct-step union and path/why-not derivations remain unchanged and
do not traverse module/declaration occurrences. Slice 8 owns semantic and field
lineage integration. Slice 9 owns general queries, reverse indexes, integrity,
inspection, and canonical pure representation.

## Non-Goals

Slice 7 adds no semantic catalog, module binding environment, import/export
surface, name resolution, visibility rule, field occurrence, field lineage,
computed/let/aggregate/window lineage, JOIN/grain semantics, traversal,
why algorithm, generalized query API, reverse index, serializer, public graph,
Project Explain field, CLI behavior, package loader/resolver change, semantic
behavior, Rust, Slice 8, or Slice 9 behavior.

Project Explain v1 and existing CLI remain zero-delta.

## Evidence And Lifecycle

Focused evidence covers one package/module, module and declaration order,
same-path modules in distinct packages, equal declaration names and source
bytes, exact package ownership, dependency/visibility separation,
foreign/wrong-domain rejection, inconsistent successful authority,
deterministic reconstruction, Slice 2–6 regression, privacy, and public
compatibility.

Phase 59 remains active. Slices 1–6 are completed, Slice 7 current, and Slice 8
next/unstarted. Natural exact-head CI owns published completion; no status-only
follow-up commit is required. This Slice does not authorize Slice 8.

The publication subject is:

```text
Add Phase 59 package-to-module attribution
```
