# Phase 46 Project Semantic Continuation Scope Lock v1

## Status

Phase 46 Slice 1 locks the scope for:

**Candidate/scope lock + private relation dependency graph scaffold + very narrow relation cycle detection MVP**

Slice 1 is docs/spec/static-audit only. It adds no source behavior, no
dependency graph implementation, no relation cycle detection implementation, no
row schema implementation, no CLI behavior, no Project JSON v2 behavior, no IR,
no SQL, no project `emit-sql`, no project `explain`, and no release behavior.

Package version remains `0.1.0`.

## Selected Candidate

Phase 46 selects:

```text
Candidate/scope lock
    + private relation dependency graph scaffold
    + very narrow relation cycle detection MVP
```

The equivalent selected option is:

```text
C. Candidate/scope lock + dependency graph scaffold
   + narrow A. Cycle detection MVP
```

This selection continues the private project semantic model built in Phase 45.
It does not redefine Phase 45 as per-file aggregation and does not add project
SQL, project IR, project explain, or public project semantic APIs.

## Private Relation Dependency Graph Vocabulary

Phase 46 uses this private vocabulary:

- A relation node is a stable project relation definition.
- A relation edge is a private dependency from one project relation definition
  to another project relation definition.
- A dependency source is the syntax site that produces a relation edge.
- A cycle candidate is a deterministic relation-node path being considered for
  relation cycle diagnostics.
- A cycle diagnostic is a project semantic diagnostic produced for a confirmed
  relation dependency cycle.

The private relation dependency graph remains private project semantic state.
It is not a public API and must not be serialized as private graph facts.

## Graph Node Identity

Phase 46 graph nodes are stable project relation definitions.

For Phase 46, graph node identity is limited to table/query relation symbols.
Source definitions remain existing relation namespace members, but Phase 46
does not use source definitions as cycle-emitting graph nodes unless a later
Gate 1 revision explicitly authorizes that expansion.

Node ordering must be deterministic and based on stable project relation
definition identity, including project-relative path and source position where
needed.

## Relation Edge Boundary

Phase 46 relation edges are limited to existing table/query `from` relation
dependencies.

The edge boundary excludes:

- no JOIN edges;
- no relationship metadata edges;
- no inferred/schema edges;
- no row-schema propagation edges;
- no projection/body field-reference edges;
- no computed alias edges;
- no `let` schema edges;
- no aggregate output schema edges;
- no runtime/database edges.

The relation edge boundary does not authorize CTE expansion, SQL inlining,
nested query materialization, database execution, project IR, or project SQL.

## Deterministic Ordering Requirements

Phase 46 dependency graph and diagnostics must preserve deterministic behavior.

Required ordering rules:

- selected project input order remains stable and project-relative;
- relation symbol ordering remains stable;
- relation edge ordering remains stable;
- cycle candidate ordering remains stable;
- diagnostic ordering remains deterministic;
- diagnostic locations remain project-relative.

Determinism must not depend on filesystem timing, hash iteration ordering,
wall-clock time, database behavior, or runtime execution.

## Narrow Cycle Diagnostic MVP Boundary

The later Phase 46 cycle diagnostic MVP is limited to detecting relation cycles
among table/query `from` dependencies.

The cycle diagnostic MVP may block later row schema propagation, but Phase 46
does not compute row schemas. Row schema propagation is deferred to Phase 47.

Slice 1 does not choose a diagnostic code, does not implement cycle detection,
does not build graph carriers, and does not change diagnostic inventory source.
Cycle diagnostic code selection belongs to a later implementation slice.

## Project JSON v2 Rule

Phase 46 must not change Project JSON v2 shape.

Project semantic diagnostics may flow only through the existing top-level
`diagnostics[]` field. Private graph state, private relation nodes, private
relation edges, dependency sources, cycle candidates, and private semantic
facts must not be serialized into Project JSON v2.

Project JSON v2 input statuses and counters remain governed by the existing
project check behavior unless a later approved slice explicitly changes them.

## Private Fact Rule

The private relation dependency graph is internal project semantic state.

Phase 46 adds no public project semantic API. It does not expose graph nodes,
graph edges, dependency sources, cycle candidates, row schema facts, or private
semantic facts through CLI JSON, Project JSON v2, Semantic Metadata Artifact
v1, public Python APIs, fixtures, goldens, or generated artifacts.

## Explicit Deferrals

The following work is out of scope for Phase 46 Slice 1 and deferred:

- row schema propagation deferred to Phase 47;
- projection/body validation deferred;
- query-to-query row schema propagation deferred;
- computed aliases deferred;
- `let` schema deferred;
- aggregate output schema deferred;
- project IR deferred;
- project SQL deferred;
- project `emit-sql` deferred;
- project `explain` deferred;
- project explain/metadata deferred;
- JOIN behavior deferred;
- relationship-driven query behavior deferred;
- runtime/database execution deferred;
- parser/grammar/generated changes forbidden.

## Forbidden Surfaces

Slice 1 changes no production source, generated parser artifacts, grammar,
CLI behavior, Project JSON v2 serializer behavior, CLI JSON v1 behavior,
Semantic Metadata Artifact v1 behavior, fixtures, goldens, scripts, workflows,
dependency files, package metadata, package version, tag, release, publish,
upload, signing, or attestation behavior.

Slice 1 does not add or change:

- `src/**`
- `grammar/**`
- generated parser files
- `fixtures/**`
- `goldens/**`
- `scripts/**`
- `.github/**`
- `pyproject.toml`
- `uv.lock`
- `README*`
- `AGENTS*`
- `src/pietto/cli.py`
- `src/pietto/_project/json_v2.py`
- `src/pietto/_project/model.py`
- `src/pietto/_project/check.py`

## Tentative Phase 46 Slice Roadmap

The tentative Phase 46 route is:

1. Candidate decision and scope lock
2. Private relation dependency graph scaffold
3. Relation edge collection from existing table/query `from` dependencies
4. Deterministic cycle detection MVP
5. Text-mode project semantic diagnostics
6. JSON v2 diagnostics through existing `diagnostics[]`
7. Compatibility hardening
8. Completion audit/status lock

Any change to this route requires a later Gate 1 revision.
