# Phase 9: SQL Backend Architecture & Dialect Strategy

## Status

**Phase 9 is the current architecture and compatibility-planning phase.**

Slices 1 through 3 are complete. Readiness And Compatibility Frame establishes
the post-Phase-8 baseline and phase boundary. PostgreSQL Compatibility Corpus
adds reviewed byte-exact pipeline fixtures. Dialect Capability And Source
Contract defines connector naming, stage ownership, required backend
capabilities, physical-name compatibility, fail-closed diagnostics, and the
future MySQL `matches` boundary.

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
- `pietto check file.pie` and
  `pietto emit-sql file.pie --dialect postgres`;
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
4. **SQLGlot Evaluation**: compare the handwritten backend with an isolated
   IR-to-SQLGlot-AST approach and record a go/no-go decision.
5. **Backend Abstraction Contract**: specify an internal backend interface,
   dispatch ownership, diagnostics, capability declaration, and dependency
   isolation without implementing it.
6. **MySQL MVP Contract**: define the exact MySQL 8.0+ generation surface,
   connector semantics, output policy, diagnostics, and Phase 10 acceptance
   criteria.
7. **Completion Audit**: verify that all decisions are documented, the
   compatibility corpus is complete, and no production dialect, dependency,
   CLI, grammar, JSON, runtime, or database behavior was added.

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

SQLGlot should be evaluated in Phase 9 but must not be installed or imported
by production code during the phase.

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

Official evaluation references:

- <https://github.com/tobymao/sqlglot#readme>
- <https://github.com/tobymao/sqlglot/blob/main/sqlglot/dialects/__init__.py>
- <https://github.com/tobymao/sqlglot/blob/main/pyproject.toml>

The evaluation must verify, for a specifically reviewed release:

- license and package provenance;
- supported Python versions and base dependencies;
- PostgreSQL and MySQL generator coverage;
- documented versioning and upgrade compatibility;
- public AST-construction API stability;
- strict unsupported-feature behavior;
- identifier and literal rendering control;
- pretty-printing and byte-exact compatibility limits;
- import time, package size, and representative generation cost;
- absence of required optimizer, executor, native-extension, or IO use.

SQLGlot's default or best-effort behavior must never silently approximate a
Pietto construct. Any future integration must configure or wrap unsupported
cases so they become deterministic Pietto diagnostics.

## SQLGlot Decision Matrix

Slice 4 must record evidence for each criterion:

| Criterion | Required result |
|---|---|
| IR mapping | Every Phase 10 MVP node maps without parsing SQL text |
| Isolation | SQLGlot types remain behind an internal adapter |
| PostgreSQL compatibility | Existing output remains byte-exact or handwritten backend remains authoritative |
| MySQL correctness | Reviewed MySQL output matches the accepted contract |
| Unsupported behavior | Unsupported constructs fail closed and deterministically |
| Diagnostics | Failures retain Pietto definition spans and ordering |
| Dependency review | License, provenance, lockfile, audit, and upgrade policy accepted |
| Security boundary | No optimizer, executor, database, connector, network, or introspection path |
| Maintenance | Adapter cost is lower than maintaining equivalent dialect renderers |

A failed mandatory criterion means SQLGlot is not adopted for Phase 10.
Approval for MySQL does not imply replacing the handwritten PostgreSQL
backend.

## Backend Abstraction Direction

Slice 5 should specify an internal backend contract with these properties:

- input is `ScriptIR`;
- output is the existing `SqlResult`;
- each backend owns source, identifier, literal, expression, relation, and
  unsupported-feature policies;
- capability declarations are explicit and testable;
- diagnostics remain ordered and source-located;
- compiler stages are not rerun;
- SQLGlot types, if later approved, do not cross the adapter boundary.

Phase 9 must preserve the public `emit_postgres_sql()` entry point. A future
`emit_mysql_sql()` may be added in Phase 10. A generic public `emit_sql()` API
is not required for the first multi-dialect MVP and must not be introduced
speculatively.

CLI dispatch remains outside the SQL backend. Phase 10 may add internal
dialect dispatch while preserving the existing PostgreSQL invocation and JSON
v1 fields.

## MySQL MVP Direction

Phase 10 should target MySQL 8.0+ SQL generation only. Its smallest candidate
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

`len` should map to `CHAR_LENGTH`, not byte-oriented `LENGTH`, unless a later
accepted type contract establishes different semantics.

`matches` is excluded from the initial MySQL MVP until regex function,
collation, case sensitivity, Unicode behavior, and escaping are specified.
The future backend must diagnose it rather than silently select an
approximation.

Slice 6 must also define:

- accepted MySQL SQL modes and string-literal assumptions;
- identifier case and quoting expectations;
- Boolean literal policy;
- reserved-word handling;
- diagnostic messages and codes;
- JSON v1 and CLI compatibility requirements;
- golden fixture review procedure.

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

## Completion Criteria

Phase 9 is complete only when:

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

## Deferred Decisions

The following questions must be resolved by later Phase 9 slices:

- SQLGlot adoption or rejection against the decision matrix;
- exact MySQL string and SQL-mode contract;
- future structured qualified source-name representation;
- final MySQL regex policy;
- whether PostgreSQL should ever migrate from the handwritten renderer.

These are not blockers for Slice 1 and do not authorize implementation.
