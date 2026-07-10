# Phase 50 Slice 1 Roadmap Reconciliation And Strategic Scope Lock v1

## Purpose And Slice Identity

Phase 50 Slice 1 is **Roadmap Reconciliation And Strategic Scope Lock**. It is
the docs/spec/static-audit-only entry scope lock for the broader eleven-slice
Phase 50 Post-v0.2 Semantic Readiness Consolidation route.

Pietto remains a typed SQL authoring DSL and semantic compiler. Slice 1 defines
roadmap, vocabulary, ordering, safety, and non-goal boundaries only.
Slice 1 implements no compiler or runtime behavior. It adds no package-manager,
database, dialect, extension, parser, AST, semantic, IR, SQL, CLI, JSON,
diagnostic, backend, or public-surface behavior.

## Post-maintenance Baseline

The trusted post-maintenance baseline is:

- Maintenance Phase 4 final commit
  `6d898559aaa244f3e4643488c111480e6933761b`;
- subject `Complete Maintenance Phase 4 worker benchmark audit`;
- natural CI run `29059542913`;
- workflow/event `CI / push`;
- status/conclusion `completed / success`;
- CI `headSha` exactly matched
  `6d898559aaa244f3e4643488c111480e6933761b`;
- package version remains `0.1.0`; and
- no tag at HEAD and no exact-match tag.

## Roadmap Reconciliation

The old Phase 45-60 table is historical. Its old Phase 50 row,
`Import / Module / Export Readiness`, remains preserved as a
Maintenance Phase 2 snapshot. Phase 47 through Phase 49 later planning treated
that old roadmap table as historical/superseded for active sequencing.

Current Phase 50 is **Post-v0.2 Semantic Readiness Consolidation**. It is an
eleven-slice readiness route. Current Slice 1 is only its roadmap reconciliation
and strategic entry scope lock.

This reconciliation reassigns and implements no behavior. The old labels
remain planning history rather than implementation authorization.

## Relation To The Phase 50 Plan

The authoritative Phase 50 route plan is
`docs/plan/phase-50-semantic-readiness-consolidation.md`.

The plan locks exactly eleven docs/spec/static-audit-only readiness slices.
Slice 1 is the only current documentation slice. Slices 2 through 11 remain
pending and separately authorized. No listed slice automatically authorizes
later implementation, and the tentative Phase 51-60 route remains subject to
Slice 2 deferred-inventory reconciliation.

## Slice 1 Boundary

Slice 1 owns only:

- append-only reconciliation of the historical roadmap with current active
  planning;
- the eleven-slice Phase 50 route lock;
- static semantic package, dialect, capability profile, and extension profile
  vocabulary;
- fail-closed missing-capability and no-approximation boundaries;
- Phase 49 private-carrier privacy; and
- explicit no-install, no-introspection, no-network, no-registry, and
  no-executable-code boundaries.

Slice 1 adds no package manifest, resolver, dependency solver, package graph,
catalog, signature schema, lowering, diagnostic, public schema, CLI surface,
JSON surface, or runtime behavior.

## Later Phase 50 Readiness Slices

Later Phase 50 work remains planning-only and separately authorized:

- Slice 2 owns the post-v0.2 deferred inventory and Phase 50-60 replan.
- Slice 3 owns Aggregate / Grouped Project Output-Schema Readiness.
- Slice 4 owns Type-System Gap And Capability Readiness.
- Slice 5 owns Window-Function Readiness.
- Slice 6 owns Import / Module / Export Readiness.
- Slice 7 owns Semantic Package Model Readiness.
- Slice 8 owns PostgreSQL Extension Capability Readiness.
- Slice 9 owns Multi-dialect Capability Ecosystem Readiness.
- Slice 10 owns the Explain / Public Metadata / Package Integration Boundary.
- Slice 11 owns the Completion Audit And Status Lock.

Historical import/module/export behavior remains deferred to Slice 6 readiness
and tentative Phase 54 planning. Aggregate/grouped project output-schema work
remains deferred to Slice 3 readiness and tentative Phase 51 foundation work.
project explain/public metadata, public lineage/export, project IR/SQL,
JOIN/relationship/grain/fanout, and runtime/database work remain deferred.

## Core Vocabulary

### Dialect

A dialect is a SQL syntax/lowering family. It identifies a language and
backend lowering context; it does not prove that any particular target server
has every optional semantic ability.

### Capability Profile

A capability profile is a static declaration of the semantic abilities of a
compilation target. Declared capability is only a prerequisite for later
validation under a separately approved contract. An absent or undeclared
capability is unsupported and must fail closed.

### Extension Profile

An extension profile is a static declared overlay on a base capability
profile. In particular, a PostgreSQL extension capability profile is static
declared metadata layered over a PostgreSQL base capability profile.

An extension profile is not server discovery, installation state, a database
connection, or proof that an extension exists on a running server.

### Semantic Package

A semantic package is a static, declarative, reviewable bundle of semantic
assets. It packages semantic authoring contracts rather than executable code.

A semantic package is not:

- a Python package;
- an executable import;
- a plugin;
- a lifecycle-hook bundle;
- a remote installer; or
- a runtime service.

It does not run arbitrary code by default.

## Static Semantic Package Candidate Assets

Candidate asset families for future contracts are:

- Pietto definitions and source shapes;
- domain aliases;
- relationship and grain metadata;
- metrics and query templates;
- dialect capability metadata;
- extension signatures and lowering contracts; and
- tests, goldens, and documentation.

These are vocabulary and categorization candidates only. Phase 50 defines no
manifest syntax, config key, resolver, loader, registry, public schema, or
execution behavior for them.

## Capability And Extension Boundaries

A PostgreSQL extension capability profile is static declared metadata only.
PostGIS, pgvector, pg_trgm, and TimescaleDB are future catalog examples only.
Phase 50 adds no concrete signatures, types, functions, operators, SQL
lowering, diagnostics, fixtures, or goldens for those extensions.

The boundary is explicit:

- no `CREATE EXTENSION`;
- no auto-install;
- no server guessing;
- no connector-name inference;
- no database connection;
- no extension discovery;
- no database introspection;
- no schema introspection;
- no credentials;
- no network access; and
- no SQL execution.

A missing or undeclared capability must fail closed. There is no best-effort
lowering, implicit fallback, syntax-similarity inference, or silent
approximation.

## Future Conceptual Pipeline

The future conceptual pipeline is:

`static metadata -> typed semantic signatures -> declared capability checking -> dialect lowering contract -> explain/diagnostics/portability reporting`

Every transition requires a separately approved contract and bounded
implementation. This conceptual ordering is not an API, data model, public
schema, or implementation commitment in Phase 50.

## Staging

The staged direction is:

1. Near-term: static vocabulary and schemas only.
2. Mid-term: semantic package asset schemas.
3. Later: PostgreSQL extension signatures.
4. Later still: multi-dialect capability profiles.

DuckDB, SQLite, MySQL, BigQuery, Snowflake, Trino, and other systems are
future examples only. Phase 50 adds no backend and no public dialect value.
Existing PostgreSQL and private MySQL behavior remains unchanged.

## Relation To Phase 49

Phase 49 private row schemas, origin/provenance, dependency graphs, and
multi-hop lineage are useful prerequisites for future work. They may later
support:

- semantic asset output descriptions;
- package attribution;
- deterministic ordering;
- dependency analysis;
- portability reporting; and
- extension-function lineage.

Phase 50 does not expose, serialize, rename, widen, or consume those private
carriers. Phase 50 changes neither Project JSON v2 nor public lineage. No
private row schema, origin/provenance, dependency graph, or lineage fact
becomes public.

Semantic packages remain distinct from current source files, project compile
units, future modules/imports, and Python distribution packages.

## Precedent And Distinctions

Existing Phase 9 closed backend capability declarations remain relevant
precedent. Backend IR-node support is not the same as target/server extension
capability. A backend can support an IR node without establishing that a
specific server extension capability is declared or available.

Current non-executable `pietto.toml` principles and deterministic
project graph principles remain preserved. Phase 50 adds no config key and no
package manifest syntax.

## Explicit Non-goals

Phase 50 includes:

- no runtime package installation;
- no dependency resolution;
- no registry access;
- no remote fetch;
- no lockfile semantics;
- no package CLI;
- no package cache;
- no package publishing;
- no arbitrary package code execution;
- no plugins;
- no entry points;
- no hooks;
- no dynamic imports;
- no Python evaluation;
- no external script execution;
- no `CREATE EXTENSION`;
- no auto-install;
- no database connection;
- no extension discovery;
- no server introspection;
- no database introspection;
- no schema introspection;
- no credentials;
- no network access;
- no SQL execution;
- no runtime/database behavior;
- no concrete PostGIS, pgvector, pg_trgm, or TimescaleDB functions, types,
  operators, signatures, lowering, diagnostics, fixtures, or goldens;
- no DuckDB, SQLite, BigQuery, Snowflake, or Trino backend behavior;
- no grammar, parser, AST, generated, semantic, private project model, IR,
  SQL, CLI, JSON, diagnostic, source, fixture, golden, example, or public API
  behavior change;
- no `pyproject.toml`, `uv.lock`, dependency, package
  metadata, version, workflow, validation-script, `README.md`,
  `AGENTS.md`, or whitepaper change;
- no aggregate/grouped output schema behavior;
- no import/module/export behavior;
- no project explain/public metadata behavior;
- no public lineage/export behavior;
- no project IR/SQL behavior;
- no JOIN/relationship/grain/fanout behavior; and
- no package version bump, tag, release, publish, upload, signing, or
  attestation.

Package version remains `0.1.0`. This phase performs no release
operation.
