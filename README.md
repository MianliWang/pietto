# Pietto

[![CI](https://github.com/MianliWang/pietto/actions/workflows/ci.yml/badge.svg)](https://github.com/MianliWang/pietto/actions/workflows/ci.yml)
![Python 3.12 and 3.13](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![Package version 0.1.0](https://img.shields.io/badge/package-0.1.0-6f42c1)

**Readable, typed SQL authoring with deterministic compilation.**

Pietto is a gradual, semantic SQL authoring DSL and compiler. It combines
Python-style indentation, readable declarations, compile-time validation, and
deterministic SQL generation so that a data model can grow without turning its
SQL boundary into an untyped string-building layer.

Pietto currently compiles explicitly selected PostgreSQL or MySQL SQL. It does
not connect to a database or execute the generated statements. PostgreSQL is
the public Python SQL backend; MySQL lowering is available through explicit CLI
selection while its emitter remains a private implementation surface.

The project is under active development. Package and CLI version `0.1.0`
describe the current repository package, not a published stability promise.
Start with the [Quick Start](#quick-start), then use the status and roadmap
sections to distinguish available behavior from active foundations.

## Why Pietto

SQL is an excellent execution language, but large SQL-authoring surfaces often
lose useful structure before a database ever sees them. Pietto keeps that
structure explicit during compilation.

- Describe shapes, sources, tables, and queries with compact declarations.
- Catch unknown names, incompatible types, invalid aggregates, and unsupported
  lowering before SQL execution.
- Preserve deterministic ordering, diagnostics, metadata, provenance, and
  lineage facts.
- Generate reviewable SQL for a deliberately bounded language surface.
- Grow from one source file toward project, module, and semantic-package
  workflows without introducing runtime evaluation.

The language is intentionally gradual. A small file can begin with a shape and
a query, while richer semantic facts remain available to the compiler as the
project grows. Unsupported behavior fails closed instead of silently emitting
an approximate query.

## Current Status

Pietto is a working compiler with an active project/module foundation. The
current repository facts are recorded in the [package metadata](pyproject.toml)
and the [Phase 54 plan](docs/plan/phase-54-local-import-module-export-foundation.md).

| Area | Current state |
| --- | --- |
| Package and CLI | `0.1.0` |
| Python | Requires `>=3.12`; CI checks 3.12 and 3.13 |
| PostgreSQL | Available SQL generation and public Python emitter |
| MySQL | Explicit CLI lowering; private emitter/API surface |
| Single-file mode | Check, explain, and emit SQL |
| Project schema v1 | Available legacy-flat project checking |
| Project schema v2 | Explicit modules, trusted loading, private catalogs/facades/bindings, module graph/diagnostics, resolution, attribution, provenance, minimal direct lineage, package-neutral identity, and private inspection facts |
| Runtime | Compiler only; no database connection or SQL execution |

Phase 54 is **COMPLETED**. Slices 1 through 16 are **COMPLETED** after exact
reviewed-tree publication, as is the unnumbered post-Slice-12 workflow
hardening interlude. Slice 15 published one portable, deterministic, total pure
boundary over the Slice 14 canonical serialization, one private
differential-vector corpus, and one Python reference harness; it added no
production Rust, no foreign function interface, and no public artifact format.
Slice 16 published the Phase 54 completion audit, status lock, and Phase 55
handoff recorded in
[the completion audit](docs/spec/phase54-slice16-completion-audit-status-lock-and-phase55-handoff-v1.md).
Phases 55 through 70 remain **UNSTARTED**, and the next lifecycle state is
`PHASE55_GATE0_GATE1`.

That final sentence is the published Phase 54 handoff checkpoint. Phase 55
Slice 1 Gate 0/Gate 1 has since passed, and the exact Gate 2 authority candidate
is now **IMPLEMENTED_UNPUBLISHED**. Phase 55 remains **UNSTARTED**; the sole
next lifecycle state is `PHASE55_SLICE1_GATE3`. Only exact reviewed-tree Gate 3
publication activates Phase 55 and completes Slice 1. This candidate freezes
the Phase 55 package decisions, three ledgers, `11 / 9 / 8 / 17 / 2`
classification totals, and selected twelve-slice route. It adds no schema-v3
parsing, package manifest/carrier/identity/assets/dependencies/loading,
diagnostic, public artifact, dependency, workflow, version, or release behavior.

Slice 3 provides stable project-relative module identity, an immutable
selected-input index, pinned-root path checks, and trusted source loading.
Slice 4 adds contextual top-level import/export source syntax and immutable,
source-located parser AST. It is a parser/AST foundation only: successful
parsing or checking does not validate import/export bindings, visibility,
target or declaration existence, module graphs, catalogs, or cross-module
resolution. Slice 5 adds private module-qualified nominal declaration identity
and one immutable local-declaration catalog per parsed module. These catalogs
do not consume import/export metadata and select no duplicate winner. Slice 6
adds private-by-default local visibility, exact six-kind local export matching,
a narrow caller-supplied explicit named re-export seam, and one immutable
private export facade per parsed module. Slice 7 resolves exact named-import
targets only through the selected-input index and direct facades, preserves
import-side aliases and nominal target identities, retains immutable binding
environments and private no-winner collision facts, and supplies real
candidates to the Slice 6 seam. Slice 8 adds the distinct selected-module
dependency graph, canonical SCC/cycle facts, and deterministic public
`PIE-S2701` through `PIE-S2707` diagnostics. Slice 9 adds dependency-first
private resolution for type aliases, enums, shapes, sources, shape field type
references, and source shape references while preserving import-local and
nominal target identities. Slice 10 adds private dependency-first source,
table, and query resolution plus minimal four-state row facts, preserving
import aliases, nominal kinds, field order, and immediate-upstream
qualification. Slice 11 adds private occurrence-safe declaration, import,
facade, and reference attribution; exact dependency and origin paths; complete
type/source/relation provenance; and minimal direct or renamed row lineage.
Slice 12 preserves existing advanced semantic facts in a separate private
sidecar without changing any public compiler or output contract. Slice 13
layers package-neutral owner and asset identities, one source digest identity,
and fail-closed loader-readiness facts over the exact Slice 3, Slice 11, and
Slice 12 roots, without a package manager, registry, manifest, solver, or
loader. Slice 14 derives one private canonical inspection projection over those
settled facts and serializes it to deterministic private bytes, without a
public inspection artifact, deserializer, or cache. Slice 15 turns that
serialization into one portable pure boundary with a normalized rejection
algebra, backs it with a frozen private differential-vector corpus and a
deterministic Python reference harness, and hardens the whole private schema-v2
path end to end. Slice 16 closes the phase with its completion audit, status
lock, and Phase 55 handoff, and adds no product behavior. Schema v2 therefore
remains a foundation rather than a completed module system. The runnable Quick
Start remains schema v1.

## Quick Start

These instructions use the repository checkout and its locked uv environment.
Pietto does not currently claim an authorized public PyPI installation route.

### Install

From the repository root, install the locked development environment and
inspect the CLI:

```bash
uv sync --locked
uv run pietto --help
uv run pietto --version
```

### Check a Pietto file

Save the following program as
`demo-project/models/active_users.pietto`:

```pietto
pietto 0.9
mode checked
dialect postgres
encoding utf8

shape User:
    id: UUID not null
    email: Text nullable
    email_norm: Text nullable
    deleted_at: Timestamp nullable

source users: User is postgres.table("public.users")

table active_users:
    from users
    where deleted_at is null
    select:
        id
        email
        email_norm = lower(trim(email))
```

Check it in text mode or request the versioned JSON result:

```bash
uv run pietto check demo-project/models/active_users.pietto
uv run pietto check demo-project/models/active_users.pietto --format json
```

`check` parses the file and performs semantic validation. It does not generate
or execute SQL. Diagnostics are deterministic and carry stable codes and source
locations where the current stage can provide them.

### Generate SQL

Select PostgreSQL explicitly when lowering the same file:

```bash
uv run pietto emit-sql demo-project/models/active_users.pietto --dialect postgres
```

The generated SQL is:

```sql
SELECT
    "id" AS "id",
    "email" AS "email",
    lower(trim("email")) AS "email_norm"
FROM "public.users"
WHERE "deleted_at" IS NULL
```

SQL is written to stdout by default. The CLI can also return a versioned JSON
document or atomically replace an explicitly selected regular output file.
Generation stops on parser, semantic, IR, or backend errors.

### Work with a project

Use this minimal project layout:

```text
demo-project/
├── pietto.toml
└── models/
    └── active_users.pietto
```

For the currently available legacy-flat project semantics, create
`demo-project/pietto.toml` with schema version 1:

```toml
schema_version = 1

[sources]
include = ["models/*.pietto"]
```

Then check every selected source as one project compilation unit:

```bash
uv run pietto check --project demo-project
```

Project checking discovers the explicit root, validates the configuration,
selects inputs deterministically, parses each selected file, and builds the
current project semantic facts. Project mode does not emit project SQL.

## Language Tour

A Pietto file begins with a language version and may declare checking mode,
dialect, and encoding. Blocks use a colon followed by spaces-only indentation;
braces are not block delimiters.

The Quick Start program demonstrates the central vocabulary:

- `shape User` declares a typed row shape. `not null` and `nullable` are
  semantic nullability facts.
- `source users` binds that shape to an opaque PostgreSQL table name. The
  compiler preserves the physical name but never opens a connection.
- `table active_users` describes a relation over that source.
- `where deleted_at is null` is checked as a predicate and lowers to SQL null
  syntax.
- `email_norm = lower(trim(email))` creates a named computed output with row
  schema, dependency, origin, and lineage facts.

The implemented expression surface includes typed unary and binary operators,
comparisons, `between`, selected scalar transforms, and bounded numeric rules.
Aggregate queries support count-family operations, sum/average, min/max,
grouping, result predicates, grouped result ordering, and bounded window
families. Unsupported operand combinations and unsupported SQL shapes fail
closed with diagnostics.

Pietto source remains more constrained than arbitrary SQL. That constraint is
deliberate: accepted forms must have defined semantic behavior and
deterministic lowering for the selected backend.

## What Works Today

The labels in this table distinguish public behavior from private compiler
facts and forward-compatible foundations.

| Surface | Status | Current boundary |
| --- | --- | --- |
| Parser and immutable AST | Available | Indentation-based source and structured diagnostics |
| Semantic type checking and diagnostics | Available | Known types, nullability, names, expressions, and relations |
| Relations, computed fields, `let`, aggregates, grouping, and bounded windows | Available | Bounded, explicitly tested SQL-authoring surface |
| Single-file `check`, `explain`, and `emit-sql` | Available | Text and applicable JSON output |
| Schema-v1 legacy-flat project checking | Available | Deterministic selected-file project semantics |
| PostgreSQL generation and public Python emitter | Available | Handwritten deterministic SQL lowering |
| MySQL CLI lowering/private emitter | Private | Explicit CLI dialect; no public emitter export |
| CLI JSON v1, project JSON v2 envelope, and metadata artifact v1 | Available | Separately versioned output contracts |
| Project provenance, lineage, capability, and module carriers | Private | Compiler facts, not public API promises |
| Schema-v2 module identity, selected-input index, and trusted loader | Foundation | Active Phase 54 module-loading boundary |
| Import/export syntax and private export facades | Foundation | Slice 4 AST and Slice 6 private visibility/facade facts |
| Named-import aliases and binding environments | Private | Slice 7 exact direct-facade facts |
| Module graph, cycles, and module diagnostics | Private compiler facts plus public diagnostics | Slice 8 deterministic fail-closed boundary |
| Cross-module type/source resolution | Private | Slice 9 identity-safe type aliases, enums, shapes, and sources |
| Cross-module relation and row-fact resolution | Private | Slice 10 direct relation resolution and minimal row facts |
| Module attribution, dependency, origin, provenance, and lineage | Private | Slice 11 occurrence-safe exact paths and minimal concrete direct/renamed lineage |
| Module semantic-fact preservation | Private | Slice 12 lossless generic, nullability, aggregate, grouped, window, result-role, and capability facts |
| Package-neutral identity layering | Private | Slice 13 owner/asset identities, source digest identity, and fail-closed loader readiness |
| Module inspection and canonical serialization | Private | Slice 14 one canonical inspection projection and deterministic private bytes |
| Rust-ready pure boundary and differential vectors | Private | Slice 15 one portable total boundary, normalized rejections, and a frozen internal vector corpus |

Existing project facts include deterministic source ordering, flat namespace
resolution for schema v1, row-schema propagation, relation dependency graphs,
aggregate and window facts, origin, dependency, provenance, lineage, and
capability readiness. Private facts may evolve until an independently
versioned public artifact adopts them.

## Project And Module Modes

Project mode always uses an explicit root containing `pietto.toml`. Source
patterns are configuration data, not executable Python, and selected files are
ordered and bounded before compilation.

### Schema version 1: legacy-flat projects

Schema version 1 is the available production project mode. All selected files
participate in one legacy-flat catalog. Project checking can resolve the
current type, source, table, query, relation, row-schema, aggregate, window,
origin, dependency, provenance, and lineage facts across that selected set.

Use schema version 1 for the Quick Start workflow. Duplicate declarations,
unknown references, relation cycles, invalid types, and unsupported expression
shapes report deterministic diagnostics. This mode remains compatible while
Phase 54 builds the explicit-module path.

### Schema version 2: explicit-module foundation

Schema version 2 activates the explicit-module compilation mode:

```toml
schema_version = 2

[sources]
include = ["models/*.pietto"]
```

The explicit-module identity, trusted-loading, import/export AST, local
catalog, private export-facade, named-import binding environment, distinct
module graph, public fail-closed module-diagnostic foundation, and private
cross-module type/source and relation resolution sidecars with minimal row
facts, plus private occurrence-safe attribution, dependency, origin,
provenance, and minimal direct/renamed lineage facts exist. Public inspection
and serialization of these private carriers, advanced row preservation,
Project IR, and project SQL remain future boundaries.

After Slice 3, each selected path has a stable logical module identity and an
immutable index entry. Project roots and source targets are pinned and checked
across discovery and reading; trusted snapshots preserve the exact bytes given
to the parser. Slice 4 retains contextual import/export AST, Slice 5 builds one
complete local declaration catalog per parsed module, Slice 6 derives one
private-by-default export facade per catalog, Slice 7 builds one immutable
named-import environment per parsed module and integrates exact candidates back
into those facades, Slice 8 builds canonical module dependency, SCC, cycle,
and diagnostic facts, Slice 9 resolves the authorized type/source surfaces,
and Slice 10 resolves source/table/query references and minimal row facts in
dependency-first order without collapsing imported-binding and nominal target
identity. Slice 11 retains occurrence-safe attribution, exact import/re-export
origins, direct semantic dependencies, complete supported provenance, and
minimal concrete row lineage. Private carriers are not serialized into the
current public project JSON envelope. Slice 12 independently preserves the
existing advanced semantic facts from the exact Slice 10 authority roots and
does not consume Slice 11 attribution.

Schema-v2 semantic completion intentionally fails closed. Module graph and
binding/export failures render deterministic `PIE-S2701` through `PIE-S2707`
diagnostics; independent Slice 9 type/source failures reuse `PIE-S2001`,
`PIE-S2002`, `PIE-S2003`, and `PIE-S2303`. Slice 10 relation failures reuse
`PIE-S2001`, `PIE-S2102`, `PIE-S2301`, and `PIE-S2302` while suppressing
derived cascades behind existing module/type/source roots.

The activation carrier is specified in the
[schema-v2 carrier contract](docs/spec/phase54-slice2-schema-v2-explicit-module-activation-and-immutable-carrier-v1.md).
The loader and identity boundary is specified in the
[Slice 3 trusted-loader contract](docs/spec/phase54-slice3-module-identity-selected-input-index-trusted-local-loader-path-symlink-boundary-v1.md).
The private visibility and facade boundary is specified in the
[Slice 6 export-facade contract](docs/spec/phase54-slice6-local-export-eligibility-visibility-explicit-named-reexport-and-facade-semantics-v1.md).
The private named-import binding boundary is specified in the
[Slice 7 binding-environment contract](docs/spec/phase54-slice7-named-imports-aliases-binding-environments-and-collision-rules-v1.md).
The graph, cycle, ordering, and diagnostic boundary is specified in the
[Slice 8 module-graph contract](docs/spec/phase54-slice8-module-graph-cycles-diagnostics-and-deterministic-ordering-v1.md).
The private type/source resolution boundary is specified in the
[Slice 9 resolution contract](docs/spec/phase54-slice9-cross-module-type-alias-enum-shape-and-source-resolution-v1.md).
The private relation and minimal row-fact boundary is specified in the
[Slice 10 resolution contract](docs/spec/phase54-slice10-cross-module-table-query-relation-resolution-row-facts-and-legacy-compatibility-v1.md).
The private attribution, dependency, origin, provenance, and lineage boundary
is specified in the
[Slice 11 attribution contract](docs/spec/phase54-slice11-module-attribution-dependency-origin-provenance-and-lineage-v1.md).
The private semantic-fact preservation boundary is specified in the
[Slice 12 preservation contract](docs/spec/phase54-slice12-semantic-fact-preservation-v1.md).
The exact Slice 13 boundary is the
[Slice 13 package-neutral identity contract](docs/spec/phase54-slice13-package-neutral-identity-layering-owner-asset-carriers-source-digest-and-loader-readiness-v1.md).

## Compiler Architecture

Pietto keeps compilation stages explicit. Public single-file SQL generation
and private project/module work share parsing primitives without pretending
that project SQL already exists.

```mermaid
flowchart LR
    S[Pietto source] --> P[Parser and AST]
    P --> A[Semantic analysis]
    A --> I[Immutable Semantic IR]
    I --> G[PostgreSQL SQL]
    C[pietto.toml] --> D[Project discovery and selection]
    D --> L[Trusted source loading]
    L --> F[Per-file parsing and private project/module facts]
```

The main SQL path above shows the current public PostgreSQL posture. Explicit
MySQL CLI lowering consumes the same immutable Semantic IR, but its emitter is
not exported as a public Python backend. Backend selection never executes a
connector.

The project path discovers and safely loads selected files. Schema v1 can
continue into the current flat project semantic model. Schema v2 currently
continues through per-file parsing, private identity/loading facts, local
declaration catalogs, export facades, import bindings, module graph/diagnostics,
and private type/source and relation resolution with minimal row facts plus
occurrence-safe attribution, dependency, origin, provenance, and direct or
renamed lineage. It does not yet produce Project IR or project SQL.

## Roadmap

The roadmap is organized by product boundary rather than dates or completion
percentages. The complete route is maintained in the
[active Phase 53–70 roadmap](docs/spec/pietto-active-roadmap-phase53-70-v2.md).

| Route | Product milestone | Status or boundary |
| --- | --- | --- |
| Phase 54 | Local module, import, export, binding, graph, and hardening foundation | Completed through Slice 16 |
| Phases 55–59 | Package assets, capability profiles, extension catalog, public inspection, and local package graph | Planned |
| Phase 60 | Advanced windows and ecosystem/release-readiness checkpoint | Planned; no tag or publication |
| Phases 61–63 | Project IR, relationships, JOIN semantics, multi-relation SQL, and `QUALIFY` | Planned |
| Phases 64–66 | Advanced types, aggregation, and advanced module/package assets | Planned |
| Phases 67–70 | Remote packages, solver/lockfile, Rust, dialect expansion, and ecosystem readiness | Planned |

Phase 68 is the preferred first production Rust kernel. Earlier phases may
shape pure, immutable, differential-testable boundaries, but they do not imply
a native rewrite.

Phase 60 does not tag or publish. Release 0.1.0 is separately authorized and
uses its own release workflow. Phase 70 targets v0.2 ecosystem-beta readiness,
not automatic publication or v1.0.

Roadmap phases identify ownership, not automatic implementation authority,
dates, or release promises. Each active slice retains its own scope,
validation, publication, and compatibility gates.

## Development

Run contributor commands from the repository root. The authoritative
validation entrypoint checks the lockfile, formatting, lint, production and
test typing, and the full test suite. Independent checks protect generated
ANTLR files, reviewed SQL/JSON goldens, and installed package behavior.

```bash
uv run python scripts/validate.py
uv run pytest tests/test_cli_golden_outputs.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
```

The focused pytest command is useful while changing CLI golden presentation;
the authoritative validation command remains the local completion gate. The
three independent audit scripts are also run by CI and do not rewrite their
protected inputs.

For the rationale and exact validation boundaries, see the
[release-readiness and reproducible-validation plan](docs/plan/phase-11-release-readiness-reproducible-validation.md).

## Documentation

The README is a landing page, not a second lifecycle ledger. These documents
own detailed contracts:

- [Language specification](docs/spec/pietto-v0.9.md) — accepted language and
  compiler semantics.
- [Project configuration schema contract](docs/spec/phase44-project-config-schema-contract-v1.md) — current strict project configuration.
- [CLI JSON schema v1](docs/spec/cli-json-v1.md) — single-file machine-readable
  output.
- [Golden fixture policy](docs/spec/golden-fixture-policy-v1.md) — reviewed SQL
  and structural JSON fixture rules.
- [Diagnostics specification](docs/spec/diagnostics.md) — stable diagnostic
  families and messages.

Detailed historical plans remain in `docs/plan/`, while current and durable
contracts live in `docs/spec/`. The active roadmap and the current Phase 54
plan remain authoritative when a historical checkpoint describes an older
state.

## Project Boundaries

Pietto is a compiler and authoring language. Its boundaries are deliberate:

- It generates SQL but never executes it.
- It does not connect to a database, inspect schemas, or manage transactions.
- It is not an ORM, database optimizer replacement, arbitrary-SQL replacement,
  job scheduler, distributed runtime, or PostgreSQL extension manager.
- It provides no web UI, server runtime, deployment service, or policy engine.
- Compiler checks do not create access-control, privacy, authorization,
  row-level-security, masking, or safe-sharing guarantees.
- Private emitters and project facts are not public API commitments.
- Foundation and planned labels do not imply production module, package, JOIN,
  registry, remote-I/O, or Rust behavior.
- Package version `0.1.0` does not imply a tag, registry publication, signature,
  attestation, or release promise.

Database execution, locking, transactions, query planning, and physical
concurrency remain responsibilities of the selected database backend and the
application that submits generated SQL.

## License

This repository does not currently include a license file. Licensing is not
implied by the package version or roadmap.

## Phase 55 Slice 2 Current Gate Status

The preceding Phase 54 and Phase 55 Slice 1 paragraphs are retained as
historical checkpoints. This current-state entry supersedes their Phase 55
status only. Phase 54 is **COMPLETED**, Phase 55 is **ACTIVE**, Slice 1 is
**COMPLETED**, and Slice 2, **Explicit Package Activation, Compatibility, And
Immutable Package Carrier**, is **IMPLEMENTED_UNPUBLISHED** in Gate 2. The
sole next token is `PHASE55_SLICE2_GATE3`.

Slice 2 adds the private schema-v3 activation boundary: exactly one
`[package]` table with five authored root fields creates a private immutable
root-package carrier. Schema v1 remains legacy-flat and package-absent schema
v2 remains the existing explicit-module behavior. Package mode deliberately
does not select project sources, read a manifest, construct modules, or enter
the module semantic pipeline. Manifest normalization, package identity,
SemVer, digest, assets, dependencies, loading, inspection, public output, and
release behavior remain later work. Package and installed CLI version remain
`0.1.0`.

## Phase 55 Slice 3 Current Gate Status

The Slice 2 status above is retained as a historical checkpoint. At baseline
`019f7355c1556d918f180209736fec2b75a9e964`, tree
`ba285171d8d9b4a1cf34556990fff0b7b6181a69`, natural `push` CI attempt 1 run
`32078392127` succeeded. Phase 54 is **COMPLETED**, Phase 55 is **ACTIVE**,
Slices 1 and 2 are **COMPLETED**, and Slice 3, **Package Manifest Input Schema
And Canonical Normalization**, is **IMPLEMENTED_UNPUBLISHED**. Slices 4 through
12 are **UNSTARTED**; the sole next token is `PHASE55_SLICE3_GATE3`.

Slice 3 adds only private `pietto-package.toml` v1 schema validation and
canonical manifest normalization. Schema v1, package-absent schema v2, and
Slice 2's schema-v3 activation carrier remain exact. It adds no package
identity, digest, asset catalog, locator, loading, dependency, public, or
release behavior. Package and installed CLI version remain `0.1.0`.
