# Phase 54 Slice 8 Module Graph, Cycles, Diagnostics, And Deterministic Ordering v1

## Status And Authority

This document is the narrow Phase 54 Slice 8 production contract. Phase 54 is
`ACTIVE`; Slices 1 through 7 are `COMPLETED`. Slice 8 becomes `COMPLETED` only
after exact reviewed-tree publication, natural exact-head PR CI, squash-tree
equality, natural exact-head `main` CI, ff-only reconciliation, cleanup, and
immutable Gate 3 evidence. Slices 9 through 16 remain `UNSTARTED`; the
successful successor is `PHASE54_SLICE9_GATE0_GATE1`.

Authority remains live source and tests, `AGENTS.md`, active roadmap v2,
permanent phase-start governance, Slice 1 scope authority, the Phase 54 master
plan, Slices 2 through 7 contracts, this contract, status documents, and
immutable external evidence. Historical readiness grants no broader behavior.

## Scope

Slice 8 adds only:

- a distinct private schema-v2 logical-module dependency graph;
- repeated per-request evidence edges and deduplicated canonical dependencies;
- deterministic strongly connected components and canonical cycle witnesses;
- private graph issues and deterministic module diagnostic facts;
- one-way public `Diagnostic` adaptation for `PIE-S2701` through `PIE-S2707`;
- trailing-default `ProjectSemanticResult` graph and diagnostic-fact fields;
- existing project text and Project JSON v2 diagnostic rendering;
- the diagnostics registry rows and focused compatibility/privacy coverage.

It adds no cross-module type or relation resolution, semantic model, IR, SQL,
execution, inspection schema, package/remote/wildcard import, public Python
API, dependency, workflow, version, fixture, golden, generated, release,
signing, attestation, or Rust/native behavior.

## Construction Boundary

`src/pietto/_project/module_graph.py` owns the private carriers and keeps
`__all__ = ()`. Construction consumes only the trusted selected-input index,
the selected-order logical-module tuple, Slice 7 binding environments, and
Slice 6 export surfaces. An edge target is accepted only through exact
`ProjectModuleBindingEnvironmentSet.find_module_path(...)` lookup. The
completed graph retains the exact Slice 7
`ProjectModuleBindingEnvironmentSet` as a private validation-only authority
root; this root is excluded from representation,
semantic equality, and hashing.

The builder never walks the filesystem, reopens source, examines excluded
files, guesses a path, searches a suffix or basename, folds case, consults a
package or network registry, invokes a callback, or reuses the relation
dependency graph.

## Vertices And Edges

One `ProjectModuleGraphVertex` exists for each selected parsed schema-v2
logical module. Its logical identity is the exact `ProjectModuleIdentity.path`
and its position is the selected-input position.

Every exact `ProjectModuleImportRequest` whose target is selected creates one
`ProjectModuleImportEvidenceEdge`. Repeated items and repeated statements stay
distinct. Every unique origin-target pair creates one
`ProjectModuleDependencyEdge` retaining all corresponding evidence in source
statement/item order.

Canonical dependency edges are ordered by origin selected position and target
selected position. Outgoing adjacency is target-selected ordered. Textual
import order remains evidence; it never chooses an endpoint, binding, SCC,
cycle, or winner. Reordering evidence cannot change the canonical graph.

Unselected or invalid targets create no edge. They retain one grouped graph
issue per owning module, import statement, and exact raw target, including all
item requests and their existing Slice 7 issue facts.

## Private Carrier Model

All carriers are frozen, slotted, keyword-only dataclasses; ordered collections
are tuples and lookup mappings are copied `MappingProxyType` values.

The exact carriers are:

- `ProjectModuleGraphVertex(identity, position, module)`;
- `ProjectModuleImportEvidenceEdge(origin, target, request)`;
- `ProjectModuleDependencyEdge(origin, target, evidence_edges)`;
- `ProjectModuleStronglyConnectedComponent(members, internal_edges)`;
- `ProjectModuleCycleWitness(vertices, edges)`;
- `ProjectModuleCycle(component, witness)`;
- `ProjectModuleGraphIssue(status, owning_vertex, requests, cycle,
  conflicting_vertices, binding_issues)`;
- `ProjectModuleGraph(binding_authority, _canonical_authority, vertices,
  evidence_edges, edges, components, cycles, issues)` plus private copied
  lookups. `_canonical_authority` is a private frozen root-derived projection
  carrier. Its only init field is the exact binding-authority root; its vertex,
  evidence-edge, edge, component, cycle, and issue fields are non-init private
  products reconstructed in `__post_init__` from that root;
- `ProjectModuleDiagnosticFact(origin, diagnostic, module_position,
  module_statement_position, item_position, related_locations, graph_issues,
  export_issues, binding_issues)`;
- `ProjectModuleDiagnosticSet(_canonical_authority, facts, diagnostics)`, where
  `_canonical_authority` is a private frozen root-only carrier with the exact
  graph, export-surface, and binding-environment roots as its only init inputs.
  It derives the fact and public-diagnostic tuples in `__post_init__`; the
  outer set retains that exact authority and every product object by identity.

Vertex equality and hash use path identity plus selected position; the
validated retained module object is excluded. Evidence and complete graph
values remain source-evidence sensitive. SCC and cycle computation consult
only canonical endpoints.

Graph construction and replacement validate, without overwriting or
normalizing supplied outer graph values, the complete ordered projection
rederived from the retained binding-authority root: selected vertices and exact
module objects; every selected request evidence edge; every complete canonical
edge bucket; exact SCC members and internal edges; canonical cycle witnesses;
every grouped unresolved issue; and one issue for every cycle. Each supplied
top-level graph tuple must retain every object by identity from the private
root-derived authority projection for that same binding root. Replacing the
authority root independently rebuilds all six private products; replacing a
non-init product through `dataclasses.replace` is rejected. Any omission,
injection, reordering, foreign value-equal evidence object, noncanonical
witness, or authority/product mismatch is a fail-closed `ValueError`.
Adapter-only issue statuses remain independently validated issue carriers and
are not invented as graph facts. The authority carrier is private, uses no
registry or global mutable state, performs no I/O, and adds no public API.

Diagnostic construction follows the same private-root rule. The canonical
diagnostic authority accepts only mutually aligned exact graph,
export-surface, and binding-environment roots, then derives both facts and
diagnostics as non-init products. `ProjectModuleDiagnosticSet` retains the
authority privately and requires every supplied fact and diagnostic to be the
same object as its authority product. The authority and all roots are excluded
from representation, equality, and hashing, but remain available for private
downstream identity validation: even an empty diagnostic tuple from a foreign
project has a distinct authority root and cannot be grafted into the current
project sidecar. No authority is public, serialized, or exported.

## Strongly Connected Components

The implementation uses deterministic iterative Kosaraju traversal. The first
pass starts vertices in selected order and follows target-selected adjacency.
The reverse pass uses origin-selected reverse adjacency. Component members are
selected ordered; components are ordered by their lowest-selected member.

A component is cyclic when it contains more than one member or its singleton
member has a canonical self-edge. A self-import is therefore a cycle. A DAG
diamond is not. Every cyclic component produces exactly one
`ProjectModuleCycle`; no winner or silently removed edge exists.

## Canonical Witness

The witness begins at the cyclic component's lowest-selected member. For each
target-selected outgoing first edge, deterministic breadth-first search finds
the shortest return path to the start. The selected witness minimizes edge
count, then the tuple of selected target positions. A self-edge is a one-edge
witness.

Witness vertices omit the repeated closing start. Rendering appends it.
Witness edges include the closing edge. The first source evidence request on
the closing edge supplies the public diagnostic's primary target span.

## Graph Issue Statuses

The exact graph issue statuses are:

- `UNRESOLVED_TARGET_MODULE`;
- `DUPLICATE_OR_CONFLICTING_MODULE_IDENTITY`;
- `MODULE_IMPORT_CYCLE`;
- `UNSUPPORTED_EXPLICIT_MODULE_REFERENCE`.

Only unresolved targets and cycles have integrated producers in the current
validated architecture. Selected-input, logical-module, catalog, and binding
constructors already reject duplicate/conflicting identities. The current AST
admits no advanced form. The latter statuses retain fail-closed adapter
branches without inventing fake source behavior.

## Diagnostic Mapping

All Slice 8 module diagnostics have severity `error`, no suggestion, and exact
source-relative paths. Public Project JSON v2 `related_locations` remains an
empty list because the current public `Diagnostic` has one location; complete
ordered related evidence remains private on `ProjectModuleDiagnosticFact`.

The one-way structured mapping is:

| Code | Private producer | Exact message |
| --- | --- | --- |
| `PIE-S2701` | unresolved target graph issue | `Unresolved module import target: <quoted target>` |
| `PIE-S2702` | conflicting identity adapter boundary | `Duplicate or conflicting module identity: <path>` |
| `PIE-S2703` | cycle graph issue | `Module import cycle detected: <path> -> ... -> <start>` |
| `PIE-S2704` | duplicate export request | `Duplicate export request: <kind> <name>` |
| `PIE-S2704` | unresolved export binding | `Unknown export binding: <kind> <name>` |
| `PIE-S2704` | ambiguous local export declaration | `Ambiguous local export declaration: <kind> <name>` |
| `PIE-S2704` | inconsistent imported candidate | `Invalid imported export candidate: <kind> <name>` |
| `PIE-S2705` | unknown imported name | `Unknown imported declaration: <kind> <name> from <quoted target>` |
| `PIE-S2705` | private/non-exported declaration | `Imported declaration is private or not exported: <kind> <name> from <quoted target>` |
| `PIE-S2706` | local/import collision | `Import binding collides with a local declaration: <local name>` |
| `PIE-S2706` | import/import or alias collision | `Import binding name is ambiguous: <local name>` |
| `PIE-S2706` | ambiguous export candidate set | `Export binding name is ambiguous: <local name>` |
| `PIE-S2707` | inconsistent target facade | `Inconsistent explicit-module target facade: <quoted target>` |
| `PIE-S2707` | ambiguous target facade | `Ambiguous explicit-module target facade: <quoted target>` |
| `PIE-S2707` | unsupported-form adapter boundary | `Unsupported explicit-module reference: <quoted target>` |

Targets use deterministic double-quoted ASCII JSON rendering. Export primary
locations use `ExportItem.local_name_span`. Imported-name diagnostics use
`ImportItem.exported_name_span`. Collision diagnostics use the alias span when
present and otherwise the exported-name span. Target diagnostics use
`ImportStatement.target_span`. Identity-only adapter facts use logical path
`1:1`. Cycle diagnostics use the closing witness target span.

No adapter infers meaning from an arbitrary message. `PIE-S2001`,
`PIE-S2002`, `PIE-S2301`, and `PIE-S2302` are unchanged.

## Ordering And Suppression

Public facts sort by diagnostic code `PIE-S2701` through `PIE-S2707`, owning
selected-module position, source statement position, source item position,
logical path, then rendered message. Module-level facts sort before item facts.
This makes graph diagnostics precede export/import diagnostics by explicit
code policy while retaining source order within a category.

Cascade rules are exact:

- one unresolved import statement emits one `PIE-S2701`; its target lookup
  issues do not also emit `PIE-S2705` or `PIE-S2707`;
- one local binding-name collision bucket emits one canonical `PIE-S2706`;
  local-declaration wording takes precedence inside that bucket;
- duplicate import facts remain private and add no equivalent collision output;
- a duplicate export request emits only its duplicate `PIE-S2704` for that
  request;
- an export resolution failure caused by a same-name blocking import issue is
  suppressed in favor of the import root diagnostic;
- an import target-facade error caused by an already-emitted target export
  problem for the same exact namespace/kind/name is suppressed;
- cycles suppress later Slice 9/10 resolution cascades, which do not yet exist;
- cycles do not suppress independent current source export/import errors.

## ProjectSemanticResult Integration

`ProjectSemanticResult` appends trailing defaulted private fields:

```python
module_graph: ProjectModuleGraph | None = None
module_diagnostic_facts: ProjectModuleDiagnosticSet | None = None
```

Valid schema v2 builds catalogs, bindings, integrated exports, the graph, and
diagnostic facts exactly once from retained inputs. It exposes the diagnostic
projection through the existing `diagnostics` tuple. Its cross-module semantic
`model` remains `None` and `.ok` remains false. Parse/read failure leaves the
new fields absent. Manual constructors remain compatible.

## CLI And JSON Compatibility

Schema-v2 text check renders deterministic diagnostics to stderr, keeps stdout
empty, and exits 1. Project JSON v2 keeps the exact nine-key order
`schema_version`, `command`, `mode`, `ok`, `project`, `inputs`, `diagnostics`,
`cli_errors`, `result`; diagnostic objects retain their current shape and no
private carrier is serialized.

Schema v1 constructs no module graph and emits no `PIE-S2701` through
`PIE-S2707`. Its legacy catalog, diagnostics/order, semantic model, CLI/JSON,
single-file behavior, IR, PostgreSQL, and private MySQL outputs remain exact.

## Retained Boundaries

Slice 9 retains cross-module type alias, enum, shape, and source resolution.
Slice 10 retains table/query/relation resolution and row facts. Slices 11 and
12 retain identity-safe semantic propagation. Slices 13 through 15 retain
inspection, serialization, pure-boundary, and hardening work. Slice 16 retains
completion audit/status lock. Phase 66 retains advanced module/package forms.

## Completion Boundary

Slice 8 is complete only after focused and compatibility behavior, complete
reader fixed point, offline validation, generated/golden/package checks,
canonical reviewed-tree reconstruction, ready PR, natural exact-head PR CI,
squash-tree equality, natural exact-head `main` CI, ff-only reconciliation,
cleanup, and immutable Gate 3 evidence all pass.

The completion state is:

```text
Phase53=COMPLETED
Phase54=ACTIVE
Slices1_through_8=COMPLETED
Slices9_through_16=UNSTARTED
next=PHASE54_SLICE9_GATE0_GATE1
```
