# Phase 54 Slice 6 — Local Export Eligibility, Visibility, Explicit Named Re-export, And Facade Semantics v1

## Status And Authority

This document is the narrow Phase 54 Slice 6 production contract. Phase 54 is
`ACTIVE`; Slices 1 through 5 are `COMPLETED`. Slice 6 becomes `COMPLETED` only
after exact reviewed-tree publication, natural exact-head PR CI, squash-tree
equality, natural exact-head `main` CI, ff-only reconciliation, cleanup, and
immutable Gate 3 evidence. Slices 7 through 16 remain `UNSTARTED` and the
successful successor is `PHASE54_SLICE7_GATE0_GATE1`.

The authority order remains live source and tests, `AGENTS.md`, the active
roadmap v2, permanent phase-start governance, the Slice 1 scope authority,
Slices 2 through 5 contracts, this contract, status documents, and immutable
external evidence. Historical readiness never grants broader authority.

## Scope

Slice 6 implements only:

- private-by-default schema-v2 local declaration visibility;
- the exact six eligible source export kinds;
- exact same-module local export resolution;
- source-ordered immutable export request facts;
- a narrow caller-supplied explicit named imported-binding candidate seam;
- one-hop explicit named re-export entries;
- private immutable module facades and a selected-input-ordered facade set;
- private issue facts without public diagnostic adaptation;
- trailing-default private `ProjectSemanticResult` integration;
- focused behavioral, compatibility, privacy, topology, and reader tests.

It does not implement import target resolution, aliases, binding environments,
module graphs, cycles, cross-module semantic resolution, public diagnostics,
IR, SQL, execution, or serialization.

## Private-by-default Visibility

Every local schema-v2 declaration is private unless one exact source `export`
item successfully resolves it. A module without an export block still receives
one empty private facade. Its local catalog remains complete and unchanged.

Visibility never changes nominal declaration identity, occurrence order,
catalog membership, AST values, or existing semantic facts. Private
declarations are not deleted from a catalog and visibility is not encoded into
identity.

## Exact Eligibility Map

The only eligible kinds are:

| Source kind | Namespace | Declaration kind |
| --- | --- | --- |
| `type` | `TYPE` | `TYPE_ALIAS` |
| `enum` | `TYPE` | `ENUM` |
| `shape` | `TYPE` | `SHAPE` |
| `source` | `RELATION` | `SOURCE` |
| `table` | `RELATION` | `TABLE` |
| `query` | `RELATION` | `QUERY` |

`constraint`, `derive`, relationship metadata, future callable assets,
wildcards, dotted or source-qualified names, package assets, and implicit
exports remain ineligible. Slice 4 already excludes unsupported syntax; Slice
6 changes no grammar, generated parser, AST, builder, span, or parser API.

## Exact Local Resolution

A local request is matched only against the same module's Slice 5 catalog with
the exact key:

```text
(module path, namespace, declaration kind, local name)
```

Cardinality is fail closed:

- zero exact local occurrences produces `UNRESOLVED_EXPORT_BINDING` unless one
  exact imported candidate resolves the request;
- one exact local occurrence produces a `LOCAL_DECLARATION` entry when no
  imported candidate competes;
- more than one exact local occurrence produces
  `AMBIGUOUS_LOCAL_DECLARATION` and no entry;
- one local occurrence plus an imported candidate produces
  `AMBIGUOUS_CANDIDATE_SET` and no entry.

No first, last, source-order, or arbitrary winner exists. Another namespace,
declaration kind, module path, case spelling, or Unicode spelling does not
satisfy the request. Source order is deterministic evidence only.

## Requests And Duplicate Source Items

The builder traverses `Script.module_statements` in order, selects only exact
`ExportStatement` values, and traverses each statement's `items` tuple in
order. Every item becomes one immutable `ProjectModuleExportRequest` retaining
the owning logical path, exact namespace and kind, local name, complete module
statement position, item position, and source `ExportItem`.

Repeated requests remain distinct. Each may resolve to an entry with the same
target identity. A later repeated request also retains a non-blocking
`DUPLICATE_SOURCE_REQUEST` fact referring to all prior exact requests. No
deduplication, precedence, or implicit visibility is introduced.

## Narrow Explicit Named-import Candidate

`ProjectImportedExportCandidate` is a frozen, slotted, keyword-only private
carrier with exactly:

- `owning_module_path`;
- eligible `namespace` and `declaration_kind`;
- `local_binding_name`;
- caller-resolved `target_identity`;
- `ProjectImportedBindingCandidateProof.EXPLICIT_NAMED_IMPORT`;
- module statement and item positions;
- source span.

It is a pure one-hop input fact. It is not the Slice 7 binding environment, an
import target resolver, a graph, a registry, a callback, a collision winner,
or a public API. Current integrated schema-v2 construction supplies no
candidates; focused tests may construct exact candidates directly.

## Explicit Named Re-export

One `EXPLICIT_REEXPORT` entry is created only when exactly one candidate:

1. belongs to the current module;
2. has the same local binding name as the request;
3. has the same eligible namespace and declaration kind;
4. carries the exact explicit named-import proof;
5. retains a target identity whose namespace and declaration kind agree;
6. has no local or imported competitor.

The exposed facade name is the current local binding name because Slice 4 has
no export alias form. The entry retains the original target nominal identity.
The builder treats that identity as caller-resolved evidence and does not
require it to occur in the current catalog set.

Wrong-owner candidates cannot resolve another module's request. Same-owner and
same-name candidates with inconsistent namespace, kind, or target identity
produce `INELIGIBLE_OR_INCONSISTENT_CANDIDATE`. Multiple exact imported
candidates, or local plus imported competition, produce
`AMBIGUOUS_CANDIDATE_SET`. No entry is chosen.

For one request, fail-closed resolution classification has the exact precedence
`AMBIGUOUS_LOCAL_DECLARATION`,
`INELIGIBLE_OR_INCONSISTENT_CANDIDATE`,
`AMBIGUOUS_CANDIDATE_SET`, then `UNRESOLVED_EXPORT_BINDING`. A duplicate-source
fact is retained separately before that request's resolution fact. Every issue
retains the complete applicable evidence; no precedence selects an entry.

Every hop requires an explicit export request. The builder never consults
another facade, infers a transitive export, follows a target identity, or
supports wildcard, `export from`, dotted, source-qualified, package, callable,
constraint, derive, relationship, or implicit facade behavior.

## Private Carrier Model

`src/pietto/_project/module_exports.py` owns the private model and keeps
`__all__ = ()`.

The exact frozen, slotted, keyword-only carriers are:

- `ProjectModuleExportRequest`;
- `ProjectImportedExportCandidate`;
- `ProjectModuleExportEntry`;
- `ProjectModuleExportIssue`;
- `ProjectModuleExportSurface`;
- `ProjectModuleExportSurfaceSet`.

Entry origins are exactly `LOCAL_DECLARATION` and `EXPLICIT_REEXPORT`.

One surface retains the exact owning logical module, all requests in source
order, resolved entries in request order, and issues in deterministic request
order. Its `export_statements` property exposes the exact retained statement
tuple from the parsed module without duplicating AST ownership.

The surface provides only complete deterministic operations:

- `find_namespace_kind_name(...)` returns every exact entry as a tuple;
- `find_target_identity(...)` returns every matching entry as a tuple;
- `is_local_declaration_visible(...)` distinguishes resolved local exports
  from re-exports and private identities;
- `.entries` and `.issues` remain immutable source-ordered tuples.

The facade set retains one surface per catalog in selected-input order. It
provides zero-or-one tuple lookup by exact module path and complete target
identity lookup across surfaces. No lookup returns an arbitrary single item.

Facade value equality and hashing depend on immutable logical values, not
Python object identity, physical paths, digests, source snapshot objects,
filesystem state, or mapping insertion accidents.

## Private Issue Facts

The exact private statuses are:

- `UNRESOLVED_EXPORT_BINDING`;
- `AMBIGUOUS_LOCAL_DECLARATION`;
- `AMBIGUOUS_CANDIDATE_SET`;
- `INELIGIBLE_OR_INCONSISTENT_CANDIDATE`;
- `DUPLICATE_SOURCE_REQUEST`.

They retain source requests and exact local, imported, or prior-request
evidence as applicable. They are not `Diagnostic` values. Slice 6 does not
add, register, emit, or serialize `PIE-S2701` through `PIE-S2707`, and does not
repurpose `PIE-S2001`, `PIE-S2002`, `PIE-S2301`, or `PIE-S2302`.

Slice 8 owns diagnostic adaptation and deterministic public diagnostic order.

## Pure Construction Boundary

`_build_project_module_export_surface_set(...)` derives its result only from:

- the Slice 5 `ProjectModuleCatalogSet`;
- retained Slice 4 export statements and items reachable from each catalog's
  parsed logical module;
- an optional exact tuple of caller-supplied imported candidates.

It does not reopen files, walk the filesystem, inspect excluded files, parse or
resolve import target strings, access a global registry, invoke a callback,
create graph edges, resolve types or relations, or create IR or SQL.

## ProjectSemanticResult Integration

`ProjectSemanticResult` adds one trailing defaulted private field:

```python
module_exports: ProjectModuleExportSurfaceSet | None = None
```

Parse or read failure leaves catalogs and facades absent. A valid schema-v2
parse first builds catalogs once, then builds one facade per catalog. The
schema-v2 model remains `None`, diagnostics remain unchanged, and `.ok`
remains false. Schema-v1 leaves both module fields `None` and follows the
unchanged legacy-flat path. Manual constructors remain compatible.

`ProjectParseCheckResult` remains parse-owned and `ProjectSemanticModel`
remains unchanged. Facades are never flattened into the legacy catalog.

## Schema-v2 CLI And JSON Compatibility

For a valid schema-v2 project:

- text check exits 1 with empty stdout and stderr;
- JSON check exits 1;
- Project JSON v2 key order remains `schema_version`, `command`, `mode`, `ok`,
  `project`, `inputs`, `diagnostics`, `cli_errors`, `result`;
- JSON `ok` remains parse-owned;
- no facade, visibility, request, issue, module identity, target identity,
  origin, or count is serialized.

A valid private export does not make schema-v2 publicly successful.

## Schema-v1 Compatibility

Schema-v1 retains the exact flat global catalog, first-winner duplicate
behavior, `PIE-S2001`, diagnostics and order, semantic model and `.ok`, project
text and JSON, single-file check/explain/emit-sql, PostgreSQL, and private
MySQL behavior. It gains no module facade.

## Import, Graph, And Retained-later Ownership

Slice 7 retains import target resolution against the selected-input index,
named binding identity, aliases, binding environments, local/import/alias/export
collision rules, and integrated imported candidates.

Slice 8 retains the module graph, cycles, topological behavior, structured
issue ordering, public diagnostic adaptation, and `PIE-S2701` through
`PIE-S2707`.

Slices 9 and 10 retain cross-module type and relation resolution. Slices 11 and
12 retain identity-safe semantic propagation. Slices 13 through 15 retain
layering, inspection, serialization, pure differential boundaries, and
hardening. Slice 16 retains completion and status lock. Phase 66 retains
advanced module and semantic-package export assets.

## Reader-containment Migration

`tests/_phase54_active_gate2_manifest.py` is the one exact test-only active
Gate 2 authority. It recognizes only the frozen Slice 6 A/M/D manifest over
the exact base with an empty index, aligned `main` and `origin/main`, one
non-shallow worktree, and no active Git operation.

It rejects subset, superset, wrong base, stale Slice marker, staged state,
unrelated paths, wrong branch or refs, shallow state, extra worktrees, and
active Git operations. It cannot be activated by environment variables or
callbacks. Clean committed state returns false so historical assertions run.

The existing Slice 5 predicate remains only as a fixed compatibility wrapper.
Its 107 importers remain byte-identical. Thirty literal old-manifest source
readers and the Phase 47 direct allowlist reader migrate once to the stable
helper. Future Slice transitions change the focused active authority and exact
direct readers rather than rewriting 160 unrelated files.

## Privacy And No-change Locks

All new carriers remain private. Slice 6 adds no public export, CLI command or
option, JSON v1 key, Project JSON v2 key, Semantic Metadata Artifact v1 field,
public inspection API, IR, SQL, dependency, lockfile, workflow, package
version, fixture, golden, example, tag, release, publishing, signing,
attestation, or Rust/native-build behavior.

The following remain byte-locked outside the exact reader/status integration
allowlist: grammar, generated parser, AST, parser API, trusted loader and
selected-input index, module carrier, module catalog, public serializers, IR,
SQL, dependencies, `uv.lock`, CI workflow, package metadata, fixtures, and
goldens.

## Completion Boundary

Slice 6 is complete only when all focused and compatibility behavior, the
reader fixed point, offline validation, generated and golden inventories,
package smoke, synthetic publication topology, exact reviewed tree, ready PR,
natural exact-head PR CI, squash-tree equality, natural exact-head `main` CI,
ff-only reconciliation, cleanup, and immutable evidence pass.

The completion state is:

```text
Phase53=COMPLETED
Phase54=ACTIVE
Slices1_through_6=COMPLETED
Slices7_through_16=UNSTARTED
next=PHASE54_SLICE7_GATE0_GATE1
```
