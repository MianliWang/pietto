# Phase 9: SQL Backend Architecture & Dialect Strategy

## Status

**Phase 9 SQL Backend Architecture & Dialect Strategy is complete.**

All seven slices are complete. Readiness And Compatibility Frame establishes
the post-Phase-8 baseline and phase boundary. PostgreSQL Compatibility Corpus
adds reviewed byte-exact pipeline fixtures. Dialect Capability And Source
Contract defines connector naming, stage ownership, required backend
capabilities, physical-name compatibility, fail-closed diagnostics, and the
future MySQL `matches` boundary. SQLGlot Evaluation records an evidence-based
decision that permits only a future isolated Phase 10 MySQL-generation spike,
not a Phase 9 implementation, production dependency, or PostgreSQL migration.
Backend Abstraction Contract defines the internal `ScriptIR -> SqlResult`
boundary, closed capability declarations, explicit CLI dispatch, result and
diagnostic semantics, and SQLGlot isolation without implementation. MySQL MVP
Contract defines the exact MySQL 8.0+ generation surface, connector, SQL mode,
escaping, capability, golden, and CLI-enablement requirements. Completion
Audit verifies the contracts, compatibility corpus, production boundaries,
dependencies, grammar, generated files, and deferred threat model.

Phase 9 does not authorize production SQL backend implementation. Its allowed
deliverables are documentation, specifications, compatibility tests, and
manually reviewed golden fixtures that preserve existing behavior.

## Goal

Define a dialect-aware SQL backend architecture before adding SQLGlot, MySQL,
or richer SQL language features. Phase 9 must produce:

- a byte-exact PostgreSQL compatibility contract;
- an internal dialect-backend contract that consumes `ScriptIR`;
- a decision framework for adopting or rejecting SQLGlot;
- a conservative MySQL 8.0+ MVP contract for Phase 10;
- explicit dependency, security, and runtime boundaries.

The phase must preserve:

```python
emit_postgres_sql(script_ir: ScriptIR) -> SqlResult
```

It must also preserve current PostgreSQL artifact text, JSON v1, CLI behavior,
compiler-stage isolation, diagnostic ordering, and generation-only behavior.

## Baseline After Phase 8

Phase 8 completed project-model and configuration planning without runtime
implementation. The current repository provides:

- a single-file parser, semantic checker, Semantic IR builder, and PostgreSQL
  SQL emitter;
- `pietto check file.pietto` and
  `pietto emit-sql file.pietto --dialect postgres`;
- text output and the normative single-file JSON schema version 1;
- immutable `SqlArtifact` and `SqlResult` models;
- reviewed example-based SQL and JSON golden fixtures;
- only `antlr4-python3-runtime` as a production dependency.

The current SQL backend emits minimal ordered relation artifacts from
`ScriptIR`. It supports:

- scalar literals, fields, and qualified fields;
- `lower`, `trim`, `len`, and `matches`;
- comparisons, `IS NULL`, `BETWEEN`, unary operators, arithmetic operators,
  and Boolean operators;
- ordered projections, aliases, `FROM`, and optional `WHERE`;
- source-backed and relation-to-relation inputs;
- non-emitting metadata definitions;
- ordered `PIE-B1000` diagnostics for unsupported backend targets.

The public SQL API contains no generic dialect emitter. The CLI directly calls
`emit_postgres_sql()`.

## Phase Boundary

Phase 9 is architecture, specification, and compatibility-foundation work. It
may add:

- planning and specification documents;
- compatibility matrices and adoption criteria;
- manually reviewed PostgreSQL golden fixtures;
- tests that lock existing behavior;
- static completion audits.

Phase 9 must not add:

- production SQLGlot imports or dependencies;
- a MySQL backend or `--dialect mysql`;
- a generic public SQL emitter;
- PostgreSQL renderer replacement or output changes;
- new Pietto grammar or SQL language features;
- SQL execution, database access, or schema introspection.

An isolated SQLGlot feasibility experiment is allowed only if document review
cannot answer a specific architecture question. Such an experiment must be
temporary, uncommitted, outside the production dependency set, and must not
modify `pyproject.toml`, `uv.lock`, source files, tests, or generated files.

## Slice Sequence

1. **Readiness And Compatibility Frame**: complete. Establish the current
   backend inventory, phase boundary, compatibility requirements, SQLGlot
   evaluation frame, future MySQL boundary, and slice sequence.
2. **PostgreSQL Compatibility Corpus**: complete. Added manually reviewed
   byte-exact fixtures and focused compatibility tests for the high-risk
   implemented SQL surface without changing production output.
3. **Dialect Capability And Source Contract**: complete. Defined the
   dialect-sensitive capability matrix, connector policy, table-name model,
   unsupported-feature behavior, and source compatibility rules.
4. **SQLGlot Evaluation**: complete. Compared the handwritten backend with an
   isolated IR-to-SQLGlot-AST approach and approved only a future Phase 10
   MySQL-generation spike, subject to strict adoption gates.
5. **Backend Abstraction Contract**: complete. Defined the conceptual internal
   `ScriptIR -> SqlResult` contract, closed capabilities, explicit dispatch,
   partial-result semantics, diagnostics, and dependency isolation.
6. **MySQL MVP Contract**: complete. Defined the exact MySQL 8.0+ generation
   surface, connector semantics, output policy, diagnostics, golden corpus,
   and Phase 10 acceptance gates.
7. **Completion Audit**: complete. Verified that all decisions are documented,
   the compatibility corpus is complete, and no production dialect,
   dependency, CLI, grammar, JSON, runtime, or database behavior was added.

## Slice 1: Readiness And Compatibility Frame

Slice 1 creates this master plan and aligns current project-status
documentation. It records Phase 8 as complete and Phase 9 as the current
architecture and compatibility-planning phase.

Slice 1 changes no public API, CLI command, CLI flag, exit code, JSON field,
diagnostic, grammar rule, generated parser file, compiler stage, SQL artifact,
golden fixture, dependency, or lockfile entry.

## Slice 2: PostgreSQL Compatibility Corpus

Slice 2 adds three manually reviewed source and SQL fixture pairs:

- `compatibility_literals_identifiers` covers quote and backslash escaping,
  Boolean, integer, float, identifier spelling, aliases, dotted source-name
  treatment, and stable relation formatting;
- `compatibility_expressions` covers all currently supported PostgreSQL
  functions, predicates, comparisons, unary and binary operators, nested
  precedence, parentheses, and one complex filter;
- `compatibility_ordering_metadata` covers type, enum, constraint, derive,
  shape, and source metadata remaining non-emitting while two relation
  artifacts retain definition order and one-blank-line CLI separation.

The fixtures run through the existing CLI parse, semantic, IR, PostgreSQL, and
text presentation pipeline. Tests compare stdout bytes directly with reviewed
`.sql` files and require empty stderr.

Backend-only unsupported cases remain covered by focused unit tests. A valid
Pietto source cannot naturally produce the deliberately malformed or future
IR nodes used by those tests, so Slice 2 does not manufacture a second
test-only CLI path for `PIE-B1000`.

Slice 2 adds no fixture generator, snapshot library, automatic rewrite
command, production source change, CLI behavior, JSON behavior, grammar,
generated parser, dependency, or lockfile change.

## Slice 3: Dialect Capability And Source Contract

Slice 3 publishes `docs/spec/sql-dialect-source-contract-v1.md`. It defines:

- dialect-specific initial physical connectors, preserving
  `postgres.table(Text)` and reserving `mysql.table(Text)` as a future
  candidate only;
- no generic `table(...)` connector for the initial multi-dialect model;
- semantic ownership of connector catalog names, static signatures, argument
  typing, and static-value requirements;
- backend ownership of connector compatibility, expression/function/operator
  support, identifier and literal policy, physical-name interpretation, and
  SQL rendering;
- CLI ownership of implemented dialect selection and usage errors;
- required backend capability declaration categories without implementing an
  interface;
- deterministic `PIE-S2306`, `PIE-I1000`, and `PIE-B1000` stage ownership;
- fail-closed rejection with no fallback or best-effort SQL generation;
- preservation of the current opaque dotted PostgreSQL table-name behavior;
- explicit MySQL rejection of `matches` until regex and collation semantics
  are accepted.

Slice 3 adds no connector, dialect, backend abstraction, SQLGlot dependency,
production code, grammar, generated parser, JSON, dependency, lockfile, or
runtime behavior.

## Slice 4: SQLGlot Evaluation

Slice 4 publishes `docs/plan/phase-9-sqlglot-evaluation.md`. It reviews
SQLGlot 30.9.0 using official documentation, repository metadata, tag history,
and PyPI package metadata without installing or executing the package.

The decision is:

**SQLGlot is approved only for a future isolated Phase 10 MySQL-generation
spike. It is not approved as a production dependency, PostgreSQL replacement,
or Phase 9 implementation.**

The evaluation records:

- feasibility of direct Semantic IR to SQLGlot AST construction;
- official PostgreSQL and MySQL dialect-generator availability;
- incompatibility between default best-effort behavior and Pietto's
  fail-closed contract;
- mandatory Pietto capability prevalidation and strict unsupported handling;
- SQLGlot type isolation behind an internal adapter;
- rejection of PostgreSQL-to-MySQL transpilation;
- rejection of parser, semantic, optimizer, executor, database, connector,
  and schema roles;
- failure of the current PostgreSQL byte-exact migration criterion;
- exact-version pinning and upgrade review requirements;
- license, provenance, release-cadence, dependency, native-extra, resource,
  and failure-mode risks;
- a Phase 10 spike contract comparing SQLGlot with a handwritten MySQL
  renderer.

Slice 4 adds no SQLGlot dependency, adapter, backend implementation, MySQL
behavior, CLI or JSON change, PostgreSQL output change, grammar, generated
file, runtime feature, or lockfile change.

## Slice 5: Backend Abstraction Contract

Slice 5 publishes `docs/spec/sql-backend-abstraction-contract-v1.md`. It
defines a behavioral internal contract without requiring a Python protocol,
base class, registry, or production refactor.

The accepted decisions are:

- the internal backend boundary remains `ScriptIR -> SqlResult`;
- each backend has one immutable, closed, reviewable capability declaration;
- declarations cover dialect identity, connectors, definitions, expressions,
  functions, operators and predicates, identifier and literal policy,
  relation and artifact policy, and diagnostics;
- a definition fully validates before its artifact is accepted;
- one failed definition produces no partial artifact for that definition;
- processing may continue in source order so successful artifacts and ordered
  diagnostics can coexist;
- the handwritten PostgreSQL backend and
  `emit_postgres_sql(ScriptIR) -> SqlResult` remain authoritative;
- a future approved MySQL backend should use a dedicated
  `emit_mysql_sql(ScriptIR) -> SqlResult` entry point;
- public export of that MySQL entry point is a separate Phase 10 decision;
- CLI dispatch remains an explicit closed mapping to dedicated emitters;
- no generic public `emit_sql(...)` API is approved;
- SQLGlot types remain private to a future adapter and never enter Semantic
  IR, public exports, result models, diagnostics, CLI, or JSON;
- `PIE-B1000` remains the default selected-backend unsupported or invalid
  emission code, with new `PIE-Bxxxx` codes requiring distinct semantics and
  explicit specification.

Slice 5 adds no backend abstraction implementation, capability object,
registry, dispatcher, SQLGlot dependency, MySQL behavior, public API, CLI or
JSON change, PostgreSQL output change, grammar, generated file, runtime
feature, or lockfile change.

## Slice 6: MySQL MVP Contract

Slice 6 publishes `docs/spec/mysql-sql-generation-mvp-v1.md`. It defines the
smallest safe Phase 10 generation-only target without adding MySQL behavior.

The accepted MySQL MVP is:

- Oracle MySQL 8.0 or later, with no MariaDB compatibility promise;
- dedicated `emit_mysql_sql(ScriptIR) -> SqlResult`;
- future static `mysql.table(Text)` with one non-empty compile-time literal;
- one opaque physical table identifier with no dotted-name decomposition;
- `RelationIR` emission and current metadata definition no-op behavior;
- minimal `SELECT`, projection, aliases, `FROM`, and optional `WHERE`;
- relation-name references without CTEs, inlining, or materialization;
- literal, field, qualified-field, comparison, null, between, unary,
  arithmetic, and Boolean expression support;
- `LOWER`, `TRIM`, and mandatory `len -> CHAR_LENGTH`;
- explicit rejection of `matches`, `LIKE`, and all undeclared capabilities;
- backtick identifiers with context-specific MySQL length limits;
- single-quoted literals under the default MySQL 8.0 SQL-mode reference, with
  `NO_BACKSLASH_ESCAPES` disabled;
- `utf8mb4` as the text reference environment without emitted session setup;
- source-ordered artifacts and `PIE-B1000` diagnostics;
- three manually reviewed byte-exact MySQL SQL fixture groups and one
  structural JSON v1 fixture;
- CLI `--dialect mysql` enablement only after semantic, IR, backend, golden,
  compatibility, dependency, and security gates pass.

The contract keeps source header metadata and connector names from selecting
the backend. It preserves explicit CLI dispatch and all PostgreSQL public API
and byte-exact compatibility.

Slice 6 adds no `mysql.table` runtime support, emitter, CLI dialect, SQLGlot,
backend abstraction, semantic or IR change, public export, JSON change,
grammar, generated file, production dependency, runtime feature, or lockfile
change.

## Slice 7: Completion Audit

Slice 7 adds `tests/test_phase9_completion_audit.py` as a focused static and
compatibility audit. It verifies:

- all seven slices and all four focused Phase 9 planning/specification
  documents;
- consistency of the dialect/source, SQLGlot, backend abstraction, and MySQL
  MVP decisions;
- the five manually reviewed PostgreSQL SQL golden fixtures and three
  structural JSON fixtures;
- the stable `emit_postgres_sql(ScriptIR) -> SqlResult` public API, explicit
  PostgreSQL-only CLI dispatch, JSON v1 schema, artifact ordering, diagnostics,
  metadata no-op behavior, and opaque dotted table-name compatibility;
- absence of SQLGlot, MySQL, `mysql.table`, `emit_mysql_sql`, a generic public
  emitter, a backend registry, project behavior, execution, database access,
  connector execution, schema introspection, watch mode, LSP, and Web UI;
- the minimal production dependency surface;
- unchanged `uv.lock`, grammar, and generated ANTLR content against the
  established pre-Phase-9 baseline;
- canonical full diagnostic codes and the separate runtime/database threat
  model requirement.

The Phase 7 and Slice 6 audit tests receive narrow status-assertion updates so
they verify their completed scopes without permanently requiring Phase 9 to
remain in progress.

Slice 7 adds no production source, runtime fixture, compiler behavior, CLI
behavior, JSON schema, diagnostic, dependency, grammar, generated parser,
golden output, or lockfile change.

## PostgreSQL Compatibility Contract

The handwritten PostgreSQL backend remains the compatibility baseline.
Phase 9 and later backend work must preserve:

- the public `emit_postgres_sql(ScriptIR) -> SqlResult` signature;
- public SQL exports and immutable tuple-backed result models;
- artifact kind, name, source order, and diagnostic order;
- four-space projection indentation and current multiline formatting;
- explicit aliases for named projections;
- no trailing newline inside an artifact;
- one blank line between artifacts in CLI text and file output;
- always-quoted PostgreSQL identifiers and current escaping behavior;
- current PostgreSQL literal spelling and rejection behavior;
- current expression precedence and parenthesization;
- metadata no-op behavior;
- relation-name references without CTE expansion or inlining;
- `PIE-B1000` ownership for current unsupported backend cases.

The existing behavior of
`postgres.table("public.users")` is compatibility-sensitive:
`public.users` is rendered as the single quoted identifier `"public.users"`,
not as `"public"."users"`. Phase 9 may document a future qualified-name model
but must not reinterpret or correct existing output.

## Compatibility Corpus Direction

The golden corpus now contains five byte-exact SQL fixtures, two structural
`check` JSON fixtures, and one structural `emit-sql` JSON fixture. The broader
SQL unit suite continues to lock invalid and backend-internal behavior that is
not naturally reachable through valid CLI input.

The reviewed PostgreSQL fixtures cover:

- identifier spelling, quoting, reserved words, aliases, and dotted source
  names;
- plain strings, quotes, backslashes, Boolean values, `NULL`, integers, and
  finite floats;
- all supported functions, predicates, comparisons, and operators;
- nested expression parentheses;
- filtered and unfiltered relations;
- relation-to-relation inputs and ordered multiple artifacts;
- metadata no-op behavior and ordered supported artifacts.

Embedded quotes in source-language identifiers are not grammar-reachable and
remain covered by renderer unit tests. Deliberately unsupported connectors,
IR nodes, calls, and operators remain covered by backend unit tests.

JSON fixtures remain structural through `json.loads()`. SQL fixtures remain
byte-exact. Phase 9 must not add snapshot dependencies, fixture rewrite
commands, or generated expected output.

## Dialect-Sensitive Inventory

The following implemented behavior requires an explicit per-dialect decision:

| Area | PostgreSQL baseline | Future MySQL concern |
|---|---|---|
| Identifier quoting | Double quotes | Backticks and case behavior |
| Source connector | `postgres.table(Text)` | Separate connector contract |
| Table-name interpretation | One opaque identifier | Qualification policy |
| String escaping | Standard strings or `E'...'` | SQL mode and backslashes |
| Boolean literals | `TRUE` / `FALSE` | Accepted spelling and semantics |
| Regex | `left ~ pattern` | Function/operator and collation semantics |
| Length | `length(value)` | Character length versus byte length |
| `lower` / `trim` | PostgreSQL functions | Collation and text semantics |
| Modulo | `%` | Operator support and numeric semantics |
| Reserved words | Always quoted | Dialect-specific reserved words |
| Case folding | Quoted spelling preserved | Filesystem/server differences |
| Qualified fields | Each component quoted | Backtick-delimited components |
| Diagnostics | PostgreSQL-specific messages | Dialect-specific capability errors |

`NULL`, comparisons, and basic operators are syntactically similar across the
candidate dialects, but their type coercion and three-valued logic assumptions
must still be documented. Similar syntax is not proof of identical semantics.

## Source And Connector Contract

The accepted dialect and source contract is documented in
`docs/spec/sql-dialect-source-contract-v1.md`.

Initial physical connectors are dialect-specific. Semantic analysis owns the
recognized static connector signature catalog; selected backends own
connector compatibility and rendering capability. The first MySQL candidate
uses `mysql.table(Text)` rather than treating `postgres.table(Text)` as
portable. This direction is specification-only and is not implemented.

No connector performs IO or connects to a database. Existing dotted
PostgreSQL strings remain one opaque identifier. Structured qualification
requires a future explicit, versioned connector representation and must not
split current strings.

## SQLGlot Evaluation

The completed evaluation is documented in
`docs/plan/phase-9-sqlglot-evaluation.md`.

SQLGlot 30.9.0 was reviewed through official documentation and package
metadata without installation or execution. SQLGlot remains absent from
production code and dependencies.

The only candidate role is:

```text
Semantic IR
    -> isolated Pietto adapter
    -> SQLGlot AST
    -> selected dialect generator
    -> SQL text
```

The following roles are rejected:

- transpiling current PostgreSQL output into MySQL;
- parsing Pietto or replacing Pietto semantic analysis;
- exposing SQLGlot AST nodes through Semantic IR or public APIs;
- query optimization or semantic rewriting;
- SQL execution or in-memory execution;
- database, connector, or schema-introspection integration.

Transpiling generated PostgreSQL text is not an acceptable architecture. It
would make PostgreSQL syntax the intermediate representation, obscure
Pietto source and IR attribution, and encourage best-effort translations.

The Phase 9 decision approves only a future isolated Phase 10
MySQL-generation spike. It does not approve a production dependency or
PostgreSQL migration. SQLGlot's default best-effort behavior remains
incompatible with Pietto; a future adapter must combine closed Pietto
capability validation with strict generator failure handling.

## SQLGlot Decision Matrix

Slice 4 records the full evidence matrix in the focused evaluation document.
The resulting adoption state is:

| Criterion | Slice 4 result |
|---|---|
| IR mapping | Feasible in principle; direct mapping remains a Phase 10 spike gate |
| Isolation | Accepted only behind one internal adapter |
| PostgreSQL compatibility | Migration not approved; handwritten backend remains authoritative |
| MySQL correctness | Requires reviewed Phase 10 MySQL output |
| Unsupported behavior | Default best effort rejected; layered fail-closed handling required |
| Diagnostics | Must remain Pietto-owned and source-located |
| Dependency review | Conditional; exact release, lockfile, provenance, and audit remain future gates |
| Security boundary | Generation-only role accepted; optimizer, executor, IO, and database paths rejected |
| Maintenance | Open until compared with a handwritten MySQL renderer |

Failure of any mandatory Phase 10 spike gate means SQLGlot is not adopted.
Approval to run that spike does not imply replacing the handwritten
PostgreSQL backend.

## Backend Abstraction Direction

The accepted internal contract is documented in
`docs/spec/sql-backend-abstraction-contract-v1.md`.

It preserves `ScriptIR -> SqlResult`, requires closed and testable capability
declarations, validates each definition before artifact acceptance, preserves
ordered partial results, and keeps implementation-library types private.

Phase 9 must preserve the public `emit_postgres_sql()` entry point. A future
`emit_mysql_sql()` may be added in Phase 10 through a separately approved
implementation. Exporting it publicly is a separate compatibility decision. A
generic public `emit_sql()` API is not approved.

CLI dispatch remains outside the SQL backend and explicit by dialect. Phase 10
may add a closed internal branch or mapping while preserving the existing
PostgreSQL invocation and JSON v1 fields.

## MySQL MVP Direction

The accepted planning contract is documented in
`docs/spec/mysql-sql-generation-mvp-v1.md`.

Phase 10 may target MySQL 8.0+ SQL generation only. Its closed candidate
surface is:

- static `mysql.table(Text)` source metadata;
- one non-empty opaque table identifier;
- identifiers, literals, fields, and qualified fields;
- `lower`, `trim`, and `len` rendered with character-length semantics;
- comparisons, `IS NULL`, `BETWEEN`, unary operators, arithmetic operators,
  and Boolean operators;
- minimal `SELECT`, projection, alias, `FROM`, and optional `WHERE`;
- relation-to-relation name references;
- stable artifact and diagnostic ordering;
- metadata non-emitting behavior;
- `--dialect mysql` and reviewed MySQL golden fixtures.

`len` maps to `CHAR_LENGTH`, not byte-oriented `LENGTH`.

`matches` is excluded from the initial MySQL MVP until regex function,
collation, case sensitivity, Unicode behavior, and escaping are specified.
The future backend must diagnose it rather than silently select an
approximation.

The contract fixes backtick identifier quoting, default MySQL 8.0 SQL mode as
the semantic reference, disabled `NO_BACKSLASH_ESCAPES`, single-quoted and
canonically escaped text, `utf8mb4` reference text handling, uppercase Boolean
literals, source-ordered `PIE-B1000`, unchanged JSON v1, and reviewed golden
fixture requirements.

## Richer SQL Roadmap

Richer SQL features remain deferred until the backend contract is complete.
The recommended order for later separately approved work is:

1. `ORDER BY` and `LIMIT`;
2. joins;
3. `GROUP BY` and aggregates;
4. CTEs, subqueries, and materialization;
5. window functions and unions;
6. DDL only under a much later explicit plan.

Phase 9 and the first Phase 10 MVP must not use richer SQL features to justify
or test an abstraction.

## Dependency And Security Review

Before SQLGlot can enter production dependencies, a later implementation
slice must:

- approve an exact compatible version range and upgrade policy;
- review license, provenance, maintainers, release history, and package
  distribution;
- review all `pyproject.toml` and `uv.lock` changes;
- prohibit optional native extensions initially;
- run the locked dependency audit;
- test strict unsupported-feature handling;
- audit AST API stability and resource behavior;
- ensure optimizer and executor modules are neither imported nor invoked;
- require PostgreSQL compatibility and reviewed MySQL output;
- preserve a handwritten backend or fallback strategy.

The current minimal production dependency surface remains the baseline.
Phase 9 adds no dependency and does not modify `uv.lock`.

## Runtime And Database Threat Boundary

SQL execution, database connections, connector execution, schema
introspection, credentials, network access, migrations, and runtime services
remain outside Phase 9 and Phase 10.

Any future proposal requires a separate threat model covering:

- trusted and untrusted input boundaries;
- credential storage, access, rotation, and redaction;
- network destinations, DNS, redirects, timeouts, and SSRF-like risks;
- SQL authority, parameterization, least privilege, and DML/DDL permissions;
- transactions, cancellation, retries, and partial failures;
- schema and data exposure;
- logging, diagnostics, telemetry, and sensitive-value redaction;
- driver, connector, and plugin supply-chain risk;
- audit trails and operator attribution.

SQLGlot evaluation must not become an indirect route to execution or
introspection features.

## Explicit Non-Goals

Phase 9 does not implement:

- SQLGlot integration or another SQL library;
- MySQL or another SQL dialect;
- `mysql.table` semantic or IR support;
- a generic public SQL emitter;
- PostgreSQL renderer replacement or output changes;
- new CLI commands, flags, dialects, or exit behavior;
- JSON v2 or any JSON v1 change;
- project configuration, project discovery, or multi-file behavior;
- joins, grouping, ordering, limits, windows, unions, DDL, CTEs, SQL inlining,
  nested subqueries, or materialization;
- SQL execution, database connections, connector execution, schema
  introspection, migrations, or DML execution;
- optimizer or executor use;
- runtime servers, network services, Web UI, watch mode, or LSP/editor
  integration;
- `compile_to_ir()` or `compile_to_sql()`;
- grammar, generated parser, production dependency, or lockfile changes.

## Risks And Scope Creep

- treating SQLGlot evaluation as approval to add it;
- replacing PostgreSQL rendering before compatibility is demonstrated;
- transpiling PostgreSQL text instead of lowering from Semantic IR;
- overlooking PostgreSQL-specific connector validation and IR lowering;
- changing dotted source names into qualified names;
- silently approximating regex, string, collation, or case semantics;
- adding richer SQL features to exercise a proposed abstraction;
- leaking SQLGlot AST types into Pietto IR or public APIs;
- accepting best-effort generation instead of deterministic diagnostics;
- changing CLI or JSON v1 while designing dialect dispatch;
- conflating SQL generation with execution or database access;
- expanding Phase 9 into project or multi-file implementation.

## Completion Audit Result

Phase 9 is complete because:

- all seven slices are complete;
- the full implemented PostgreSQL surface has reviewed compatibility coverage;
- dialect-sensitive behavior and source connector semantics are explicit;
- SQLGlot has a documented evidence-based go/no-go decision;
- the internal backend contract is decision-complete;
- the MySQL MVP contract is decision-complete;
- runtime and database threat boundaries remain explicit;
- no production SQL dialect, dependency, CLI, JSON, grammar, runtime, or
  database behavior has been added;
- formatting, linting, tests, lockfile checks, dependency audit, diagnostic
  scan, and changed-file boundary checks pass.

The final validation baseline requires:

- Ruff formatting and lint checks;
- the full pytest suite, including the focused Phase 9 completion audit;
- lockfile consistency and locked dependency vulnerability review;
- the repository-wide bare diagnostic-code scan;
- whitespace and changed-file boundary checks.

The Slice 7 completion run recorded:

- Ruff formatting and lint checks passed;
- `1,098` pytest tests passed;
- `uv lock --check` resolved 19 locked packages successfully;
- `uv audit --locked` found no known vulnerabilities or adverse project
  statuses in 18 packages;
- the bare diagnostic-code scan produced no output;
- `git diff --check` passed;
- only completion-audit tests and approved status/documentation files changed.

Phase 9.5 Static Typing And Source Extension Hardening follows Phase 9 as a
separate tooling and repository-convention phase. It does not alter any Phase
9 backend decision or authorize Phase 10 implementation.

## Deferred Beyond Phase 9

The following questions remain for later separately approved work:

- future structured qualified source-name representation;
- the Phase 10 SQLGlot production go/no-go after an isolated spike;
- any post-MVP MySQL regex and collation contract;
- whether a much later proposal should reconsider PostgreSQL migration.

Phase 9 completion does not authorize implementation. PostgreSQL migration is
not part of the Phase 10 spike.
