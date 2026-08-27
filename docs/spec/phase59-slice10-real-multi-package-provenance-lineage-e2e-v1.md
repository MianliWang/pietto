# Phase 59 Slice 10 Real Multi-Package Provenance And Lineage E2E v1

## Scope

Phase 59 Slice 10 proves the private package graph from real authored
project/package/module inputs through production discovery, loading,
inspection, capability, semantic, graph, integrity, inspection, and query
entry points. It adds no production semantics or new graph carrier.

The principal proof is
`tests/test_phase59_slice10_real_multi_package_provenance_lineage_e2e.py`.
It writes only repository-native temporary authored files and never hand-builds
the final graph.

## Real Authored Topology

Each E2E construction writes:

- one schema-v4 project `pietto.toml` with a real root-package activation and
  project capability environment;
- one root `pietto-package.toml` with an authored dependency declaration;
- one dependency `pietto-package.toml` with schema-v3 capability requirements
  and an extension-signature selector;
- one real `main.pietto` module in each package; and
- one schema-v2 project config inside each package for existing production
  semantic compilation of that exact module source.

The root and dependency deliberately use the same module path, declaration
names, field names, and source bytes. Their loaded package occurrences,
package-qualified modules, declarations, and fields must nevertheless remain
distinct.

## Production Entry Points

The proof follows this exact production chain:

```text
load_project_config
-> _locate_root_package
-> _load_root_package
-> _build_package_load_plan
-> _build_package_inspection_fact_set
-> _build_project_capability_environment
-> _package_contexts
-> build_package_capability_checking_matrix
-> build_capability_inspection
-> check_project_parse_only
-> build_empty_project_semantic_result
-> _build_package_graph
-> _validate_package_graph_integrity
-> _inspect_package_graph
-> private direct/all-path/why-not queries
```

No final `PackageGraphSnapshot` is hand-built. Tests inspect the production
result only after construction and do not author capability checks, semantic
lineage facts, or final graph sections.

In plain terms, no final PackageGraphSnapshot is hand-built.

## Package And Capability Provenance

The dependency package declares two real requirements in source order:

1. one extension-signature requirement with a typed selector and existing
   selected catalog/provider evidence; and
2. one logical-type requirement that reaches an existing checked non-success
   result under the authored target environment.

The extension path proves package → requirement → selector → capability →
catalog/provider evidence. The logical path provides a real typed why-not
terminal. The satisfied extension result produces no why-not. Missing edges
remain absence only and never become synthetic negative evidence.

No new capability checking, catalog selection, or provider behavior is added.

## Reachable Semantic Lineage

The authored module uses separate real declarations so each currently
reachable authority remains valid:

- source fields;
- direct and renamed projection in a projection-only query;
- computed and let lineage in a calculation query;
- an aggregate with repeated ordered input occurrences; and
- one current-window navigation result with argument, default, partition, and
  order dependencies.

Thus source, direct, renamed, computed, let, aggregate, and current-window
lineage are exercised without combining syntax families that current earlier
authorities intentionally keep non-concrete. Unreachable negative states stay
owned by their existing lower-level tests.

Every semantic lineage link remains package-local. A package dependency grants
no semantic visibility and creates no cross-package field graft.

## Integrity, Query, And Determinism

The real graph passes Slice 9 integrity unchanged. Direct and transitive query
results preserve direct-link order, n-ary/repeated input multiplicity, and all
authoritative occurrence paths. Real why-not query output retains its exact
terminal evidence.

Two independent authored project trees with equivalent contents create fresh,
unequal runtime scopes and equal private canonical inspections. Runtime scope,
object identity, and address text do not enter canonical data.

## Compatibility And Deferrals

The same authored project remains successful through the existing Project
Explain runtime. Project Explain v1 and CLI remain zero-delta.

Slice 10 adds no loader/resolver semantics, version solver, lockfile,
cross-package imports, capability or lineage kind, JOIN/grain, window frame,
generic graph framework, public graph artifact, persistent ID, Project IR, SQL
lowering, Rust, or Slice 11 differential-assurance behavior.

## Lifecycle

The candidate records Phase 59 active, Slices 1–9 completed, Slice 10 current,
and Slice 11 next/unstarted. Live Git plus successful natural exact-head CI own
completion; no status-only follow-up commit is required.

The only ordinary commit subject is:

```text
Add Phase 59 real multi-package E2E
```
