# Phase 54 Slice 4 — Import / Export Contextual Grammar, Generated Parser, And Immutable AST v1

## Status And Authority

Phase 54 is `ACTIVE`. Slices 1 through 3 are `COMPLETED`. During Slice 4
Gate 2, Slice 4 remains incomplete and Slices 5-16 remain `UNSTARTED`. The
exact trusted base is `15bae172ee151e370fe59d3bf909d735aee6aa90`, with tree
`12e9f69d80c9a5059166cf99a2eb1a94e30e416c`.

This contract implements only contextual top-level import/export parsing,
deterministically regenerated ANTLR artifacts, and immutable parser-owned AST
facts. The Supplemental Pre-authorization Addendum authorizes the AST-only
pipeline posture: semantic analysis ignores module statements. Successful
parsing or checking therefore does not validate import/export binding,
visibility, target existence, declaration existence, graph edges, catalogs, or
cross-module resolution.

Gate 2 keeps the Git index empty and is fully offline. Gate 3 alone owns
publication. Only successful exact-tree publication, natural exact-head PR and
`main` CI, squash-tree equality, ff-only reconciliation, cleanup, and immutable
Gate 3 evidence complete Slice 4. The resulting next lifecycle is
`PHASE54_SLICE5_GATE0_GATE1`.

## Contextual Syntax

The exact import form is:

```pietto
import "models/customer.pietto":
    shape Customer
    query orders as imported_orders
```

The target is exactly one Pietto string literal. Its value is decoded by the
existing string-literal policy and retained without path normalization,
filesystem lookup, selected-input lookup, containment checking, URL/package
classification, or module resolution. An import body contains at least one
item. Each item contains exactly one declaration kind and one simple exported
name, followed optionally by `as` and one simple local name. Alias direction
is `exported_name as local_name`.

The exact export form is:

```pietto
export:
    type UserId
    enum Status
    shape Customer
    source customers
    table staged_customers
    query active_customers
```

An export body contains at least one item. Each item contains exactly one
declaration kind and one simple local name. Export aliases and export targets
are not accepted.

The closed declaration-kind domain is exactly:

| Source spelling | AST value |
| --- | --- |
| `type` | `ModuleDeclarationKind.TYPE` |
| `enum` | `ModuleDeclarationKind.ENUM` |
| `shape` | `ModuleDeclarationKind.SHAPE` |
| `source` | `ModuleDeclarationKind.SOURCE` |
| `table` | `ModuleDeclarationKind.TABLE` |
| `query` | `ModuleDeclarationKind.QUERY` |

`import`, `export`, and `as` are contextual tokens. They remain accepted
through the existing `identifier` rule in every previously valid identifier
position. They introduce module syntax only through the exact top-level block
rules. Import/export blocks may interleave with definitions and relationship
metadata. Their own source order is preserved. They are never accepted inside
another indentation block.

Comments and blank lines use the existing indentation grammar policy. Duplicate
blocks, duplicate items, repeated names, collisions, and unknown names are
retained structurally; Slice 4 neither deduplicates nor validates them.

## Exact Grammar Boundary

The script rule admits `moduleStatement` beside `definition` and
`relationshipDefinition`. The module grammar is:

```antlr
moduleStatement
    : importStatement
    | exportStatement
    ;

importStatement
    : IMPORT importTarget COLON NEWLINE NEWLINE* INDENT importBody DEDENT
    ;

importTarget
    : STRING
    ;

importBody
    : NEWLINE* importItem (importItem | NEWLINE)*
    ;

importItem
    : moduleDeclarationKind identifier (AS identifier)? NEWLINE
    ;

exportStatement
    : EXPORT COLON NEWLINE NEWLINE* INDENT exportBody DEDENT
    ;

exportBody
    : NEWLINE* exportItem (exportItem | NEWLINE)*
    ;

exportItem
    : moduleDeclarationKind identifier NEWLINE
    ;
```

The authoritative implementation is `grammar/Pietto.g4`. This summary does
not create a second grammar.

## Explicitly Rejected Syntax

Slice 4 does not accept wildcard, bare side-effect, brace, comma-list, dotted
name, `from`, `import ... from ...`, `export from`, package-target,
remote-target, module-declaration, export-alias, or implicit-transitive forms.
Callable, constraint, derive, and relationship are not eligible item kinds.
Import and export bodies may not be empty. Existing parser diagnostics and
source-location policy report malformed forms; no module semantic diagnostic is
introduced.

## Immutable AST

`ModuleDeclarationKind` is a closed `StrEnum`. The new values are frozen,
slotted, keyword-only dataclasses and tuple-backed:

1. `ImportItem(declaration_kind, exported_name, local_name,`
   `declaration_kind_span, exported_name_span, local_name_span)`;
2. `ImportStatement(target, target_span, items)`;
3. `ExportItem(declaration_kind, local_name, declaration_kind_span,`
   `local_name_span)`;
4. `ExportStatement(items)`;
5. `ModuleStatement = ImportStatement | ExportStatement`.

Every node also carries its inherited full `span`. Statement spans run from
the contextual introducer through the final significant item token. The target,
kind, exported-name, local-name, and alias spans use the existing one-based,
half-open source convention. A missing import alias has both
`local_name=None` and `local_name_span=None`.

No AST value contains an ANTLR node/token, physical path, inode, source digest,
selected-input entry, module graph, semantic declaration identity, binding
identity, package identity, catalog fact, or resolved target.

## Existing Script Compatibility

`Script.header`, `Script.definitions`, and `Script.relationships` retain
their existing meaning and order. One backward-compatible field is appended:

```python
module_statements: tuple[ModuleStatement, ...] = ()
```

Module statements never masquerade as definitions or relationships. Existing
source without module syntax retains an empty tuple and otherwise equal AST
behavior. Existing keyword-only `Script` constructors remain compatible.

## AST Builder And Generated Parser

`AstBuilder` visits the shared `moduleStatement` sequence so import and
export block order is preserved. It uses the existing string decoder and span
helpers, creates tuples, and performs no I/O, lookup, normalization, resolution,
visibility check, or semantic validation.

Generation uses the repository-pinned ANTLR 4.13.2 jar with SHA-256:

```text
eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76
```

The tracked inventory remains exactly eight files. The seven ANTLR outputs are
regenerated; `src/pietto/generated/__init__.py` remains empty. Generated files
are never hand edited.

## Parser-only Pipeline Posture

`parse_source` exposes the module AST through `Script.module_statements`.
The semantic analyzer continues to consume existing definitions and
relationship metadata only. It deliberately ignores module statements.
`SemanticModel`, Semantic IR, PostgreSQL SQL, private MySQL SQL, CLI text and
JSON, Project JSON v2, Semantic Metadata Artifact v1, and public Python exports
gain no module field or behavior.

For a syntactically valid module block, `pietto check` may succeed when all
existing definitions also pass their existing checks. That success means only
that parsing and existing semantic checks succeeded. It is not evidence that
the target exists, an exported name exists, an alias is collision-free, an
export is eligible or visible, or a binding/graph/catalog/resolution result
exists.

Existing unresolved definition references retain their existing diagnostics.
`PIE-S2001`, `PIE-S2002`, `PIE-S2301`, and `PIE-S2302` are not
repurposed. `PIE-S2701` through `PIE-S2707` remain absent and un-emitted.

## Project-mode Boundary

Schema v1 remains legacy-flat and ignores module statements when building its
existing catalog. Schema v2 trusted loading preserves each parsed `Script`
including module AST, then stops before the legacy flat catalog exactly as
established by Slice 2. Import targets do not drive source selection, discovery,
opening, walking, or trusted loading. Slice 3 root, symlink, physical identity,
digest, snapshot, and selected-input guarantees remain unchanged.

## Public And Packaging Boundary

No top-level `pietto` export, parser API signature, public serializer field,
JSON key, CLI option, CLI output section, semantic model field, IR node, SQL
node, fixture, golden, example, dependency, lockfile, workflow, package
metadata, version, Rust source, tag, release, publish, upload, signing, or
attestation is added.

## Retained-later Ownership

Slice 5 owns module-qualified nominal declaration identity and per-module
catalogs. Slice 6 owns local export eligibility, private visibility, explicit
named re-export, and facade semantics. Slice 7 owns named import bindings,
aliases, environments, and collision rules. Slice 8 owns module graphs, cycles,
diagnostics, and deterministic ordering. Slices 9-15 retain cross-module
resolution, fact preservation, package-neutral carriers, inspection,
serialization, pure boundaries, and hardening. Slice 16 retains completion
audit and Phase 55 handoff.

No later ownership is promoted by successful parsing.

## Verification Contract

The focused Slice 4 module contains exactly 30 undecorated, non-parametrized
top-level tests. They cover positive import/export forms, all six kinds,
aliases, ordering, exact spans, immutability, contextual compatibility, negative
grammar, parser-only pipeline privacy, schema-v1/v2 posture, generated
inventory, and publication-reader topology. The expected clean suite is exactly
`10886 passed`.

The frozen Gate 2 changed set is `A2_M138_D0`: two additions, 138
modifications, no deletions. It includes exactly seven generated paths and 125
mechanical reader tests. The single write-mode Ruff manifest contains exactly
128 literal handwritten Python paths.

Gate 2 must pass the focused and complete offline validation, generated
reproducibility, 37-golden audit, installed `pietto 0.1.0` package smoke,
reader fixed point, and exact synthetic PR/main publication projections before
publication is authorized.

## Non-goals

This slice adds no import/export semantics, path resolution, filesystem access,
selected-input lookup, binding environment, visibility, export eligibility,
named re-export validation, collision winner, graph, cycle detection,
cross-module semantic resolution, module diagnostics, project IR, project SQL,
public module inspection, package/remote behavior, runtime, database execution,
or release behavior.
