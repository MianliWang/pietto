# Phase 10: MySQL SQL Generation MVP

## Status

**Phase 10 MySQL SQL Generation MVP is the current phase.**

**Slice 1: Phase 10 Master Plan And Readiness Audit is complete.**

**Slice 2: SQLGlot Evaluation And Isolated Adapter Spike is complete.**

**Slice 3: Dialect Dispatch Design is complete.**

**Slice 4: MySQL Backend Skeleton is complete.**

**Slice 5: MySQL Connector Semantic Surface is complete.**

**Slice 6: MySQL Expression And Relation Rendering MVP is complete.**

Phase 10 is the first implementation phase after the Phase 9 SQL backend
architecture work. Slices 1 through 3 are documentation and static audit only.
Slice 2 selects a small handwritten MySQL renderer for the Phase 10 MVP and
rejects SQLGlot for this MVP. Slice 3 defines closed internal dispatch without
implementing it. Slice 4 adds only a private, fail-closed MySQL backend
skeleton. Slice 5 adds static semantic recognition and IR preservation for
`mysql.table(Text)`. Slice 6 implements the closed handwritten MySQL
expression and relation renderer. MySQL remains private and is not publicly
exported or CLI-enabled.

Every later slice requires a separate explicit implementation request. A
planned capability is not an implemented or approved public interface merely
because it appears in this document.

## Goal

Add the smallest safe Oracle MySQL 8.0+ SQL-generation path while preserving
Pietto as a local, generation-only compiler and CLI developer tool.

The eventual Phase 10 pipeline may become:

```text
Pietto source
    -> parse
    -> analyze
    -> build IR
    -> explicitly selected PostgreSQL or MySQL SQL backend
    -> CLI text or JSON v1 output
```

The phase must preserve:

- `emit_postgres_sql(ScriptIR) -> SqlResult`;
- the handwritten PostgreSQL backend as the byte-exact reference;
- all reviewed PostgreSQL golden output;
- existing compiler-stage isolation;
- immutable `SqlArtifact` and `SqlResult` models;
- the current single-file CLI and JSON v1 contracts;
- generation-only behavior with no execution or database access;
- production and test Pyright cleanliness;
- targeted isolation of generated ANTLR diagnostics.

## Baseline After Phase 9.6

The repository currently provides:

- a single-file parser, semantic checker, Semantic IR builder, and handwritten
  PostgreSQL emitter;
- `pietto check file.pietto`;
- `pietto emit-sql file.pietto --dialect postgres`;
- CLI text output and the normative single-file JSON schema version 1;
- five reviewed byte-exact PostgreSQL SQL fixtures;
- production Pyright at zero errors and warnings;
- test Pyright at zero errors and warnings through
  `pyrightconfig.tests.json`;
- targeted Pyright and Pylance isolation for `src/pietto/generated`;
- a private fail-closed MySQL backend and closed handwritten renderer;
- static `mysql.table(Text)` semantic validation and `ConnectorIR`
  preservation;
- only `antlr4-python3-runtime` in the production dependency list.

The following remain unimplemented:

- `--dialect mysql`;
- an internal backend abstraction or dialect dispatcher;
- SQLGlot or another SQL-generation dependency;
- JSON v2 or project/multi-file behavior;
- SQL execution, database connections, connector runtime, and schema
  introspection.

## Planning Authorities

Phase 10 implementation must conform to:

- `docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md`;
- `docs/plan/phase-9-sqlglot-evaluation.md`;
- `docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md`;
- `docs/spec/sql-dialect-source-contract-v1.md`;
- `docs/spec/sql-backend-abstraction-contract-v1.md`;
- `docs/spec/sql-dialect-dispatch-design-v1.md`;
- `docs/spec/mysql-sql-generation-mvp-v1.md`;
- `docs/spec/cli-json-v1.md`.

If this master plan and a focused contract conflict, the narrower accepted
contract controls unless a later slice explicitly amends it.

## Phase Boundary

Phase 10 may eventually add:

- one dedicated MySQL 8.0+ generation backend;
- the static semantic connector `mysql.table(Text)`;
- a dedicated `emit_mysql_sql(ScriptIR) -> SqlResult` entry point;
- explicit internal CLI dispatch for `postgres` and `mysql`;
- manually reviewed MySQL byte-exact golden fixtures;
- a small handwritten MySQL renderer under the closed MVP contract.

Phase 10 does not add:

- SQL execution or validation against a live server;
- database drivers, connections, credentials, destinations, or network IO;
- connector execution or schema introspection;
- a PostgreSQL rewrite or SQLGlot-backed PostgreSQL path;
- PostgreSQL-to-MySQL transpilation;
- a generic public `emit_sql(...)` API;
- JSON v2, project mode, configuration loading, or multi-file compilation;
- richer SQL syntax or language features.

## Slice Sequence

1. **Phase 10 Master Plan And Readiness Audit**: complete. Create this master
   plan, mark Phase 10 as current, record the baseline and gates, and add
   static planning audits. No production implementation.
2. **SQLGlot Evaluation And Isolated Adapter Spike**: complete. Re-review an
   exact SQLGlot release, compare a direct `ScriptIR`-to-SQLGlot-AST MySQL
   adapter with a small handwritten renderer, measure resource and failure
   behavior, and select the handwritten renderer for the Phase 10 MVP.
3. **Dialect Dispatch Design**: complete. Define the exact internal closed
   routing contract for dedicated PostgreSQL and MySQL emitters without
   enabling `--dialect mysql`.
4. **MySQL Backend Skeleton**: complete. Implement the private, fail-closed
   `ScriptIR -> SqlResult` MySQL backend boundary and capability declaration,
   initially without CLI enablement.
5. **MySQL Connector Semantic Surface**: complete. Add the static
   `mysql.table(Text)` semantic signature and preserve it through IR lowering,
   with no connector execution or database behavior.
6. **MySQL Expression And Relation Rendering MVP**: complete. Implement the
   closed approved MySQL expression, literal, identifier, source, relation,
   artifact, and diagnostic surface.
7. **MySQL Golden Corpus And PostgreSQL Regression Lock**: planned. Add
   manually reviewed byte-exact MySQL fixtures and prove every PostgreSQL
   fixture remains unchanged.
8. **CLI Enablement For `--dialect mysql`**: planned. Enable explicit MySQL
   CLI text and JSON v1 dispatch only after every backend and compatibility
   gate passes.
9. **Completion Audit**: planned. Verify the complete MySQL generation MVP,
   PostgreSQL compatibility, dependency decision, typing gates, security
   boundaries, and deferred capabilities.

The order is fixed. In particular, CLI enablement is not an integration
shortcut for testing an incomplete backend.

## Slice 1: Phase 10 Master Plan And Readiness Audit

Slice 1:

- creates this master plan;
- records Phase 9, Phase 9.5, and Phase 9.6 as complete;
- marks Phase 10 as current without claiming MySQL implementation;
- records the nine-slice sequence and ordering gates;
- adds static audit coverage for planning boundaries;
- preserves all production, dependency, grammar, generated-file, CLI, JSON,
  PostgreSQL, semantic, and IR behavior.

Slice 1 does not add SQLGlot, `emit_mysql_sql`, `mysql.table`,
`--dialect mysql`, MySQL fixtures, or production source.

## Slice 2: SQLGlot Evaluation And Isolated Adapter Spike

**Slice 2 is complete.**

Slice 2 made a fresh evidence-based choice between:

```text
Option A: small handwritten MySQL renderer
Option B: isolated ScriptIR-to-SQLGlot-AST MySQL adapter
```

The isolated spike was limited to MySQL generation. It:

- select and re-review one exact candidate SQLGlot release;
- use direct AST construction rather than parsing or transpiling SQL text;
- map only the closed MySQL MVP IR surface;
- explicitly select the MySQL generator;
- force strict unsupported behavior and treat warnings as failures;
- keep SQLGlot types and exceptions private to the adapter;
- compare reviewed output with a handwritten reference;
- measure import surface, package size, CPU, memory, depth, output size,
  warning, exception, and partial-output behavior;
- review license, provenance, maintainers, artifacts, release policy, hashes,
  and lockfile impact;
- prohibit extras, native acceleration, optimizer, executor, lineage,
  database, and schema modules;
- prove all PostgreSQL golden fixtures remain byte-exact.

The spike used SQLGlot `30.10.0` in a temporary isolated environment. It found
that direct MySQL AST construction and strict unsupported errors are feasible,
but exact Pietto formatting, ASCII 26 literal escaping, deterministic
parentheses, capability validation, diagnostics, and recursive resource
containment would remain Pietto responsibilities. SQLGlot therefore did not
demonstrate lower expected maintenance cost for the closed MVP.

**Decision: Phase 10 will implement a small handwritten MySQL renderer.
SQLGlot is rejected for this MVP and remains absent from production
dependencies.** The evidence, measurements, supply-chain review, comparison,
and future reevaluation conditions are documented in
`docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md`.

This decision does not weaken the MySQL contract. SQLGlot may be reevaluated
only in a later phase if a substantially richer SQL or multi-dialect surface
changes the maintenance tradeoff.

SQLGlot must never become:

- the Pietto parser or semantic analyzer;
- a PostgreSQL-to-MySQL transpiler;
- a PostgreSQL backend replacement;
- an optimizer or executor;
- a database, connector, or schema integration layer;
- a type exposed through Semantic IR, public APIs, diagnostics, CLI, or JSON.

## Slice 3: Dialect Dispatch Design

**Slice 3 is complete.**

Slice 3 defines the future internal closed mapping:

```text
postgres -> emit_postgres_sql
mysql    -> emit_mysql_sql
```

The design must:

- keep dedicated emitter entry points;
- preserve the existing PostgreSQL direct path and behavior;
- avoid a generic public `emit_sql(...)` API;
- distinguish an unknown CLI dialect from a selected backend capability
  failure;
- preserve unsupported-dialect exit `2` and JSON v1 `unsupported_dialect`;
- preserve backend-diagnostic exit `1`;
- pass only `ScriptIR` to the selected backend;
- keep output files, stdout/stderr, and JSON presentation outside backends;
- avoid inferring the backend from source headers or connector names.

The design fixes one private, static, exhaustive selector with dedicated
emitters and a separate immutable CLI-enabled dialect set. The selector
resolves emitter attributes at call time, receives only the explicit dialect
name, and later invokes the selected emitter with only `ScriptIR`. Text and
JSON admission share the enabled set, while presentation, exit codes, and
output files remain CLI-owned.

Backend availability does not imply CLI enablement. Slices 4 through 7 may
test a private MySQL emitter directly, but Slice 8 alone may atomically add the
`mysql` selector branch and enable `mysql` for text and JSON CLI paths.

Unknown or disabled dialects stop before source parsing and retain exit `2`;
JSON v1 preserves the supplied value and `unsupported_dialect`. Capability
failures from an already selected backend remain `PIE-B1000` diagnostics and
exit `1`.

The complete design is documented in
`docs/spec/sql-dialect-dispatch-design-v1.md`.

Slice 3 does not add a dispatcher, `mysql` to CLI choices, a public emitter,
or production code.

## Slice 4: MySQL Backend Skeleton

**Slice 4 is complete.**

Slice 4 implements the private dedicated boundary:

```python
emit_mysql_sql(script_ir: ScriptIR) -> SqlResult
```

The skeleton:

- consume `ScriptIR` directly;
- return existing immutable SQL result models;
- classify `RelationIR` as emitting and all current metadata definitions as
  non-emitting;
- diagnose unknown future definition kinds as unsupported;
- fail closed with deterministic `PIE-B1000` diagnostics;
- emit no partial artifact for a failed relation;
- preserve source definition order for diagnostics;
- avoid parser, semantic, IR-lowering, CLI, JSON, IO, or runtime imports;
- contain no SQLGlot dependency or types.

`src/pietto/sql/mysql.py` owns the boundary. Its `emit_mysql_sql` entry point
remains intentionally importable only from the internal module:

- it is absent from `pietto.sql.__all__`;
- the CLI does not import or dispatch to it;
- Slice 6 adds rendering without changing that private API boundary.

Public export of `emit_mysql_sql` remains a separate compatibility decision.

## Slice 5: MySQL Connector Semantic Surface

**Slice 5 is complete.**

Slice 5 adds:

```text
mysql.table(Text)
```

as a static connector parallel to `postgres.table(Text)`.

Semantic analysis now enforces:

- exact connector recognition;
- one-argument arity;
- `Text` typing;
- compile-time literal enforcement;
- source-shape and row-schema validation;
- deterministic `PIE-S2306` failures.

IR lowering preserves the exact connector name, ordered static argument, and
source span in `ConnectorIR`. It adds no runtime handles, dialect objects,
credentials, endpoints, schemas, or connections.

The connector argument remains one non-empty opaque physical table
identifier. It is not split on `.`. Structured qualification remains deferred.

This slice does not change legacy `postgres.table(Text)` behavior. It does not
select a SQL backend from the connector name.

## Slice 6: MySQL Expression And Relation Rendering MVP

**Slice 6 is complete.**

Slice 6 implements only the closed surface accepted by
`mysql-sql-generation-mvp-v1.md`.

### Relation Surface

- `SELECT`;
- ordered projections and explicit aliases;
- `FROM`;
- optional `WHERE`;
- `mysql.table(Text)` source inputs;
- quoted relation-name inputs;
- stable artifact ordering;
- metadata non-emission.

### Expression Surface

- identifiers and separately quoted qualified field components;
- scalar literals;
- field references;
- comparisons `==`, `!=`, `<`, `<=`, `>`, and `>=`;
- Boolean `and` and `or`;
- unary `+` and `-`;
- arithmetic `+`, `-`, `*`, `/`, and `%`;
- `BETWEEN`;
- `IS NULL` and `IS NOT NULL`;
- `lower/1 -> LOWER`;
- `trim/1 -> TRIM`;
- `len/1 -> CHAR_LENGTH`.

MySQL identifiers use backticks and the accepted context-specific length
limits. Physical source names remain opaque. Literals follow the accepted
MySQL 8.0 SQL-mode and `utf8mb4` reference contract.

The backend must reject, without approximation:

- `matches/2`;
- `LIKE`;
- unknown expressions, functions, operators, predicates, definitions,
  connectors, identifiers, or literal values;
- any SQLGlot warning or best-effort rewrite.

No failed relation receives a partial artifact.

The handwritten implementation is isolated in private modules:

- `pietto.sql.mysql_render` owns MySQL identifier and literal policies;
- `pietto.sql.mysql_expressions` owns the closed expression capability;
- `pietto.sql.mysql_relations` owns source resolution and relation formatting;
- `pietto.sql.mysql` owns definition ordering, artifacts, and diagnostics.

The implementation preserves opaque dotted physical names, quotes qualified
field components separately, uses uppercase MySQL functions, and rejects
unsupported functions, operators, nodes, connectors, identifiers, and
literals with one ordered `PIE-B1000` per failed relation.

Expected fail-closed rejections use the private `MySqlRenderError` boundary.
Only that error is converted to `PIE-B1000`; unexpected programming errors
remain visible.

Slice 6 does not add reviewed golden fixtures, CLI dispatch, JSON MySQL
success behavior, or a public SQL API. Those remain later gates.

## Slice 7: MySQL Golden Corpus And PostgreSQL Regression Lock

Slice 7 adds manually reviewed fixtures only. It must not add snapshot
libraries, generated expected output, or automatic update commands.

The minimum MySQL corpus is:

1. **Literals And Identifiers**: backticks, escaping, reserved names, scalar
   literals, Unicode, qualified fields, and one dotted opaque physical name.
2. **Expressions**: all approved functions, comparisons, predicates, unary,
   arithmetic, Boolean operators, precedence, and parentheses.
3. **Ordering And Metadata**: non-emitting metadata, two ordered relation
   artifacts, relation-name input, and stable CLI artifact separation.
4. **Structural JSON v1**: successful `emit-sql` output with
   `"dialect": "mysql"`.

Focused negative tests must cover connector mismatch, `matches`, `LIKE`,
unknown nodes and operators, identifier limits, invalid literals, NUL,
failure ordering, no partial artifact, and SQLGlot failure containment if
used.

All five PostgreSQL byte-exact SQL fixtures and existing PostgreSQL unit tests
must pass unchanged.

## Slice 8: CLI Enablement For `--dialect mysql`

Slice 8 is the only slice that may enable:

```bash
pietto emit-sql file.pietto --dialect mysql
```

Enablement requires:

- the selected implementation technology decision is complete;
- `mysql.table(Text)` semantic and IR support is stable;
- the full closed MySQL backend surface is implemented;
- positive, negative, golden, resource, and isolation tests pass;
- PostgreSQL output and API remain unchanged;
- text and JSON v1 behavior, exit codes, artifact ordering, diagnostics, and
  output-file safety pass for both dialects;
- dependency and supply-chain review passes if SQLGlot is adopted;
- no execution, database, connector runtime, or schema path exists.

The CLI remains explicit. Connector names and source headers do not choose the
backend.

## Slice 9: Completion Audit

The completion audit must verify:

- every Phase 10 slice and acceptance gate;
- the MySQL capability declaration and fail-closed behavior;
- `emit_mysql_sql(ScriptIR) -> SqlResult`;
- `mysql.table(Text)` static semantics;
- MySQL text and JSON v1 CLI behavior;
- reviewed MySQL byte-exact fixtures;
- unchanged PostgreSQL API, output, fixtures, diagnostics, and artifact order;
- the final SQLGlot adoption or rejection record;
- production and test Pyright gates;
- targeted generated ANTLR isolation;
- dependency, lockfile, grammar, and generated-file boundaries;
- absence of JSON v2, project mode, execution, database, connector runtime,
  schema introspection, watch, LSP, and Web UI.

## JSON Compatibility Boundary

JSON schema version 1 remains the only runtime CLI JSON schema in Phase 10.
The existing top-level fields, diagnostics, artifacts, output metadata, exit
codes, and stdout/stderr rules remain unchanged.

A successful future MySQL result may set:

```json
{
  "schema_version": 1,
  "command": "emit-sql",
  "dialect": "mysql"
}
```

This is a value within the existing schema, not JSON v2.

JSON schema version 2 remains reserved for future explicit project and
multi-file mode. Phase 10 must not implement its serializer, CLI invocation,
root/path behavior, resource model, or project result aggregation.

## Typing And Generated-Code Gates

Every Phase 10 slice must run:

```bash
uvx pyright
uvx pyright --project pyrightconfig.tests.json
```

The first command remains the blocking standard-mode gate for handwritten
production source. The second preserves the clean test-suite baseline and is
part of Phase 10 validation.

Generated ANTLR files remain targeted-isolated through `pyrightconfig.json`
and `.vscode/settings.json`. They must not be hand-edited. Parser generation
runs only after a separately approved grammar change; Phase 10 does not
require a grammar change.

## PostgreSQL Compatibility Gate

The handwritten PostgreSQL backend remains the byte-exact reference
implementation throughout Phase 10.

Phase 10 must not:

- route PostgreSQL through SQLGlot;
- replace or wrap `emit_postgres_sql`;
- reinterpret `"public.users"` as a qualified name;
- change public SQL result models;
- change PostgreSQL identifiers, literals, expressions, formatting,
  diagnostics, artifact order, metadata behavior, or relation references.

Any PostgreSQL golden diff blocks the relevant slice unless separately
approved as a PostgreSQL compatibility change outside this phase.

## Dependency Gate

Slices 1 and 2 change no dependency or lockfile. Slice 2 rejects SQLGlot for
the Phase 10 MVP, so later Phase 10 slices must not add it.

Any future phase that reopens SQLGlot adoption requires:

- an exact reviewed version;
- no extras, native extension, plugin dialect, optimizer, or executor;
- explicit `pyproject.toml` and `uv.lock` review;
- license, provenance, artifact, maintainer, release, and vulnerability
  review;
- strict failure handling and private adapter types;
- acceptable measured resource behavior;
- lower expected maintenance cost than the handwritten option.

SQLGlot support in upstream does not define Pietto capability.

## Security And Runtime Boundary

Phase 10 is SQL generation only. It adds no:

- SQL execution, query validation against a server, or result fetching;
- database driver, connection, DSN, host, port, credential, or secret;
- DNS resolution, network access, or destination selection;
- connector execution, schema introspection, or migration;
- transaction, retry, timeout, cancellation, or session management;
- dynamic backend or plugin discovery;
- optimizer or executor;
- filesystem behavior beyond the existing protected CLI output path;
- runtime server or Web UI.

Any future execution, connection, credential, connector, or introspection
proposal requires a separate threat model and phase.

## Explicit Non-Goals

Phase 10 does not implement:

- PostgreSQL migration or PostgreSQL SQL changes;
- PostgreSQL-to-MySQL transpilation;
- a generic public `emit_sql(...)`;
- regex or `matches` support for MySQL;
- collation selection or `COLLATE`;
- structured database/table qualification;
- alternate MySQL SQL-mode profiles;
- MariaDB or vendor-fork certification;
- joins, grouping, aggregates, ordering, limits, windows, unions, CTEs,
  subqueries, materialization, DDL, DML, or migrations;
- JSON v2;
- `pietto.toml`, project discovery, globbing, or multi-file compilation;
- SQL execution, database access, connector runtime, schema introspection,
  credentials, or network access;
- watch mode, LSP/editor integration, Web UI, or runtime server;
- `compile_to_ir()` or `compile_to_sql()`.

## Risks And Scope Control

- treating Slice 1 planning as MySQL implementation approval;
- treating the SQLGlot spike as automatic dependency adoption;
- using PostgreSQL output as a transpilation intermediate;
- changing PostgreSQL rendering to share code prematurely;
- enabling the CLI before backend and golden stability;
- inferring a dialect from `mysql.table` or a source header;
- splitting opaque dotted source names;
- silently approximating `matches`, `LIKE`, collation, or string behavior;
- exposing SQLGlot AST types outside one private adapter;
- adding richer SQL to justify backend abstraction;
- conflating generated SQL with executable or validated SQL;
- allowing JSON v2 or project-mode work into a single-file dialect phase.

## Phase 10 Completion Criteria

Phase 10 is complete only when:

- the SQLGlot go/no-go decision is evidence-based and final for the MVP;
- a dedicated MySQL backend implements the complete closed MVP;
- `mysql.table(Text)` is statically validated and preserved in IR;
- `--dialect mysql` is enabled only after all prior gates;
- reviewed MySQL byte-exact and JSON v1 fixtures pass;
- PostgreSQL remains byte-exact and API-compatible;
- unsupported MySQL cases fail closed with deterministic diagnostics;
- production and test Pyright gates report zero errors and warnings;
- dependency, security, resource, grammar, generated-file, and lockfile
  boundaries pass;
- JSON v2 and all runtime, database, project, watch, LSP, and Web capabilities
  remain unimplemented.

Slices 1 through 3 satisfy none of the MySQL implementation criteria. Slice 4
establishes the private fail-closed backend boundary, Slice 5 satisfies the
static connector and IR-preservation gate, and Slice 6 satisfies the closed
rendering gate. The golden-corpus, CLI, and completion criteria remain open.
