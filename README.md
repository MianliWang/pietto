# Pietto

Pietto is a gradual, semantic SQL authoring DSL.

The current implementation status is:

- Phase 1 Parser/frontend MVP: complete;
- Phase 2 Semantic Checker MVP: complete;
- Phase 3 Semantic IR MVP: complete;
- Phase 4 PostgreSQL SQL MVP: complete;
- Phase 5 CLI MVP: complete;
- Phase 5.5 Security / Robustness Hardening: complete;
- Phase 6 JSON / machine-readable CLI output: complete;
- **Phase 7 Developer Workflow & Stability Foundation: complete**;
- **Phase 8 Project Model & Configuration Planning: complete**;
- **Phase 9 SQL Backend Architecture & Dialect Strategy: complete**;
- **Phase 9.5 Static Typing And Source Extension Hardening: complete**;
- **Phase 9.6 Test Typing Hygiene: complete**;
- **Phase 10 MySQL SQL Generation MVP: complete**;
- **Phase 11 Release Readiness & Reproducible Validation: complete**;
- **Phase 12 SQL Feature Expansion I: complete**;
- **Phase 13 Relation Composition And Relationship Planning: complete as
  planning, contract, and audit work only**;
- **Phase 14: complete; Slices 1 through 4 cover readiness, candidate
  decision, parse-only relationship metadata AST implementation, and backend
  compatibility/completion audit**;
- **Phase 15 Slice 1 Relationship Metadata Semantic Validation: complete**.
- **Phase 15 Slice 2 Relationship Semantic Model Storage: complete**.

The current compiler pipeline parses one Pietto file, performs semantic
analysis, builds immutable Semantic IR, emits explicitly selected PostgreSQL
or MySQL SQL, and presents the result through CLI text or JSON output. The
public PostgreSQL backend consumes `ScriptIR` through
`emit_postgres_sql(script_ir)`; the MySQL emitter remains private to CLI
dispatch.

The backend emits minimal `SELECT` SQL for `RelationIR` definitions, including
projections, optional `WHERE`, optional source-ordered `ORDER BY`, and an
optional validated static `LIMIT`. Inputs may reference a static
`postgres.table(Text)` source or another relation by quoted name. Type, enum,
shape, source, constraint, and derive IR definitions are non-emitting metadata;
unsupported or invalid relation emission receives structured `PIE-B1000`
diagnostics. CTE expansion, inlining, nested subqueries, joins, grouping,
projection-alias/output-schema/ordinal ordering, offsets, metadata DDL,
SQLGlot integration, database or connector execution, and schema introspection
are not implemented.

The supported single-file CLI commands and forms include:

```bash
pietto --help
pietto --version
pietto check file.pietto
pietto check file.pietto --format json
pietto check file.pietto --format=json
pietto emit-sql file.pietto --dialect postgres
pietto emit-sql file.pietto --dialect postgres --output out.sql
pietto emit-sql file.pietto --dialect postgres --format json
pietto emit-sql file.pietto --dialect postgres --format=json
pietto emit-sql file.pietto --dialect postgres --format json --output out.sql
pietto emit-sql file.pietto --dialect mysql
pietto emit-sql file.pietto --dialect mysql --format json
pietto emit-sql file.pietto --dialect mysql --output out.sql
```

`check` performs parser and semantic validation only. `emit-sql` explicitly
runs parse, semantic, IR, and the explicitly selected PostgreSQL or MySQL
backend. SQL defaults to stdout; `--output` atomically replaces a safe regular
output file after successful rendering. Text diagnostics remain on stderr.
Recognized JSON requests produce one versioned machine-readable document on
stdout.

The CLI remains single-file developer tooling. It does not execute SQL,
connect to databases or connectors, introspect schemas, or provide project
configuration, multi-file support, watch mode, LSP/editor integration, or
compiler convenience wrappers. There is no `compile_to_ir()` or
`compile_to_sql()`.

Phase 5.5 Security / Robustness Hardening is complete. PSEC-001 through
PSEC-007 are fixed or documented at their intended boundaries, the Common
Vulnerability Category Checklist is complete, and no current vulnerability
blocked Phase 6. The completed work covers compiler exception containment,
PostgreSQL rendering safety, CLI output-path and terminal-text safety, and a
minimized production dependency set.

Phase 6 JSON / machine-readable CLI output is complete. It includes the
versioned JSON schema, serialization helpers, audited JSON output for `check`,
and `emit-sql --format json` with final output-file interaction. Both commands
use command-local
`--format {text,json}` with text as the unchanged default. JSON results use a
versioned schema, structured diagnostics and CLI errors, and one complete
stdout document. `emit-sql --format json --output out.sql` writes raw SQL
atomically to the file while retaining artifacts and output metadata in JSON
stdout. Text-mode `emit-sql --output` remains supported and unchanged. The
Phase 6 completion audit covers schema stability, exit codes, stage isolation,
security regressions, examples, text compatibility, and capability boundaries.

Phase 7 Developer Workflow & Stability Foundation is complete. It aligned
post-Phase-6 documentation, stabilized the normative JSON v1 contract, added
focused example-based golden SQL and JSON outputs, designed resource/depth
budgets, implemented fixed 1 MiB UTF-8 source and 200,000 raw non-EOF token
limits, documented future project-workflow prerequisites, and completed a
cross-slice stability audit.

Phase 8 Project Model & Configuration Planning is complete. It defines future
configuration, project-root and path, multi-file, CLI/JSON, and project
resource-model semantics without implementation. Phase 8 added no
`pietto.toml`, project discovery, multi-file behavior, JSON v2, SQLGlot,
another SQL dialect, richer SQL features, or runtime/database capabilities.

Phase 9 SQL Backend Architecture & Dialect Strategy is complete. It defines
PostgreSQL byte-exact compatibility, dialect-sensitive source and rendering
contracts, SQLGlot adoption criteria, an internal backend abstraction
contract, and a conservative future MySQL MVP. All seven slices are complete:
the phase frame, PostgreSQL compatibility corpus, dialect/source
responsibility contract, SQLGlot evaluation, backend abstraction contract,
MySQL MVP contract, and completion audit are documented. Phase 9 approved
SQLGlot only for a future isolated Phase 10 MySQL-generation spike, not as a
production dependency or PostgreSQL replacement. The internal backend
contract preserves
`ScriptIR -> SqlResult`, dedicated emitters, closed capabilities, explicit CLI
dispatch, and SQLGlot isolation without implementation. These slices add no
SQLGlot dependency, MySQL behavior, backend implementation, CLI or JSON
change, richer SQL feature, SQL execution, or database connection. The MySQL
MVP contract now fixes the future connector, closed SQL surface,
`len -> CHAR_LENGTH`, SQL-mode and escaping assumptions, diagnostics, golden
corpus, and CLI enablement gates.

Phase 9.5 Static Typing And Source Extension Hardening is complete. It
establishes a zero-error Pyright gate for handwritten
production source, isolates generated ANTLR typing noise, and makes `.pietto`
the only official Pietto source extension. The CLI remains path-based and does
not reject other suffixes.

Phase 9.6 Test Typing Hygiene is complete. It removes test-suite Pyright
diagnostics through precise test-only narrowing and helper typing. The
mandatory production Pyright gate remains unchanged; the clean test
configuration remains an explicit non-blocking command.

Phase 10 MySQL SQL Generation MVP is complete. Slice 1 defines the nine-slice
implementation path and readiness gates. Slice 2 reviews SQLGlot `30.10.0`,
runs an isolated uncommitted adapter spike, and selects a small handwritten
MySQL renderer for the Phase 10 MVP. SQLGlot is not adopted. Slice 3 defines
the future private closed `postgres -> emit_postgres_sql` and
`mysql -> emit_mysql_sql` dispatch contract while keeping CLI enablement
separate. Slice 4 adds a private MySQL backend skeleton that consumes
`ScriptIR`, skips current metadata definitions, and fails closed with ordered
`PIE-B1000` diagnostics for relations or unknown future definitions. It emits
no SQL artifacts and is not exported from `pietto.sql` or wired into the CLI.
Slice 5 adds static semantic recognition for `mysql.table(Text)`, including
exact name, arity, `Text`, non-empty compile-time literal validation, and
preservation of the opaque argument and connector span in `ConnectorIR`.
Slice 6 implements the private handwritten MySQL expression and relation
renderer: backtick identifiers, the accepted MySQL literal policy, minimal
`SELECT`/`FROM`/optional `WHERE`, approved operators and functions, relation
references, ordered artifacts, and fail-closed `PIE-B1000` diagnostics.
Slice 7 adds three manually reviewed byte-exact MySQL golden groups covering
literals/identifiers, expressions, and ordering/metadata, plus explicit locks
for every existing PostgreSQL SQL golden and public backend module.
Slice 8 enables the private closed CLI dispatch for explicit
`--dialect mysql` in text and JSON v1 modes, including the existing atomic
output-file contract. PostgreSQL remains the handwritten byte-exact reference.
The MySQL emitter remains absent from public `pietto.sql` exports, and no
generic public emitter is added. JSON v1 remains the only runtime CLI JSON
schema; `"dialect": "mysql"` is an allowed value within that unchanged schema.
Slice 9 completes the cross-slice behavioral and static audit, including both
typing gates, PostgreSQL and MySQL golden equality, dependency and generated
code locks, output safety, and deferred capability boundaries.

Phase 11 Release Readiness & Reproducible Validation is complete. Slice 1
adds the master plan and post-Phase-10 baseline audit. Slice 2 adds the
authoritative non-mutating local validation command:

```bash
uv run python scripts/validate.py
```

The standard-library script runs lock validation, Ruff format checking,
linting, production and test Pyright, and the full pytest suite in fail-fast
order from the repository root. It can also run directly with
`python scripts/validate.py`.

Slice 3 adds the reviewed ANTLR 4.13.2 jar checksum and an independent,
non-mutating generated-file reproducibility guard:

```bash
uv run python scripts/check_generated.py
```

The guard verifies the local jar, regenerates into a temporary directory, and
compares the complete tracked generated inventory and bytes. It does not
download tools, update generated files, or join `scripts/validate.py`.

Slice 4 defines the reviewed SQL byte-exact and JSON structural golden policy
and adds an independent, non-mutating inventory and orphan audit:

```bash
uv run python scripts/check_goldens.py
```

The audit validates fixture classification, test references, paired Pietto
inputs, and JSON decoding without invoking the compiler or changing fixtures.
The policy is documented in
[Golden Fixture Policy v1](docs/spec/golden-fixture-policy-v1.md).

Slice 5 adds minimal-permission GitHub Actions CI for pull requests and pushes
to `main`. The Python 3.12/3.13 matrix uses Java 21 and pinned action SHAs,
installs uv `0.11.19`, and invokes the accepted local commands without
duplicating their logic:

```bash
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
```

The workflow has only `contents: read`, disables persisted checkout
credentials and uv cache upload, and performs no publishing, deployment,
artifact upload, or release creation.

Slice 6 adds an independent standard-library package smoke command:

```bash
uv run python scripts/package_smoke.py
```

It builds sdist and wheel artifacts only in a temporary directory, checks
runtime and generated ANTLR inventory plus metadata and the console entry
point, installs the wheel into a clean temporary virtual environment, and
runs the installed `pietto` executable from outside the repository. The smoke
checks `--version`, `--help`, one successful `check`, PostgreSQL byte-exact
text, and MySQL JSON v1 structural compatibility. It does not publish, upload,
sign, change package metadata or version, or join the other three validation
scripts.

Slice 7 adds the final static completion audit and closes Phase 11. It proves
that the four independent commands, minimal-permission CI, package metadata,
compiler stages, reviewed SQL and JSON outputs, and deferred capability
boundaries remain intact. Slices 1 through 7 change no production compiler
behavior, dependency, grammar, generated file, existing golden content, SQL
backend, CLI behavior, JSON schema, public Python API, package metadata,
version, or Makefile.
`pyproject.toml` continues to declare Python `>=3.12`; the current CI matrix
covers Python 3.12 and 3.13 without changing that compatibility floor.

Phase 11 is release-readiness and reproducible-validation hardening, not an
actual package release. Package publication, PyPI or other registry
credentials, release signing, provenance attestations, and automated
versioning remain unimplemented.

Phase 12 SQL Feature Expansion I is complete. Slices 1 through 6 are complete.
Slice 2 defines the normative
[ORDER BY / LIMIT Contract v1](docs/spec/order-limit-contract-v1.md), including
static limit bounds, ordering scope, diagnostics, IR expectations, and dual
backend formatting. Slice 3 implements only static `LIMIT` for PostgreSQL and
MySQL. Slice 4 implements input-scope `ORDER BY` for both backends, with
source-ordered expressions and normalized explicit directions. Projection
aliases are not available to ordering. CLI options, JSON v1, public Python
APIs, dependencies, package metadata, version, and all existing golden
fixtures remain unchanged. Slice 5 adds reviewed PostgreSQL and MySQL
composition goldens plus coverage of the unchanged CLI text, atomic
output-file, and JSON v1 paths. Slice 6 completes the cross-slice audit and
documentation without production changes. JSON schema version 1 remains
unchanged.

Phase 12 completion is not an actual package release. Package publication,
registry upload, signing, attestations, automated versioning, and a version
bump remain unimplemented.

Phase 13 is complete as planning, contract, and audit work only. Slices 1
through 6 are complete. Slice 1 completes the master plan and baseline audit.
Slice 2 completes the planning-only
[Relationship And Relation Role Contract v1](docs/spec/relationship-relation-role-contract-v1.md).
Slice 3 completes the planning-only
[Composition Scope And Name Resolution Contract v1](docs/spec/composition-scope-name-resolution-contract-v1.md).
Slice 4 completes the planning-only
[Composition SQL Shape Contract v1](docs/spec/composition-sql-shape-contract-v1.md).
Slice 5 completes the planning-only
[Composition Security And Diagnostics Contract v1](docs/spec/composition-security-diagnostics-contract-v1.md).
The contracts define conceptual vocabulary and future semantic and backend
boundaries; they define no currently accepted Pietto syntax, SQL shape,
runtime security, threat model, or diagnostic code. The Slice 2 baseline
described Slices 3 through 6 as
planning-only. The Slice 3 baseline described Slices 4 through 6 as
planning-only. The Slice 4 baseline described Slices 5 through 6 as
planning-only. The historical Slice 5 checkpoint statement, "Slice 6 remains
planned only", is retained for audit compatibility. Slice 6 adds only
`tests/test_phase13_completion_audit.py` and final scope-aware documentation.
Relation composition, JOIN, SQL shape implementation, CTEs, subqueries,
relationship syntax, relation-role syntax, permission gates, runtime security,
threat model, diagnostic code, database connection, SQL execution, schema
introspection, JSON v2, project mode, LSP, Web UI, playground, SQLGlot,
release, publish, signing, upload, and attestation behavior are not
implemented. Pietto currently provides no access-control, privacy,
authorization, row-level security, masking, policy-isolation, or safe-sharing
guarantee.

Future implementation work requires a new explicit phase and authorization.
Changes outside that phase require separate explicit authorization.
Unrequested future work is not authorized.

Phase 14 Slice 1 is complete as the final broad transition and
planning/readiness work only. Slice 2 is complete as candidate decision work:
it selected the Relationship and endpoint metadata syntax foundation and
deferred the Ambiguity and name-ownership foundation.

Slice 1 changes no production code, grammar, generated ANTLR, parser, AST,
semantic analysis, IR, SQL backend, CLI, JSON v1, public API, dependency,
package metadata, version, CI, or golden fixture. Relation composition, JOIN,
SQL shape implementation, CTEs, subqueries, relationship syntax,
relation-role syntax, permission gates, runtime security, threat model,
diagnostic code, database connection, SQL execution, schema introspection,
JSON v2, project mode, LSP, Web UI, playground, SQLGlot, release, publish,
signing, upload, and attestation behavior remain not implemented.

Phase 14 Slice 2 is complete as a candidate decision only. It selected the
Relationship and endpoint metadata syntax foundation as the first real
implementation candidate and deferred the Ambiguity and name-ownership
foundation. The proposed Slice 3 boundary is parse-only and AST-only: a
separately reviewed exact syntax contract, minimal grammar and regenerated
ANTLR changes, immutable AST metadata, parser tests, necessary fixed-hash
updates, and scope-aware documentation.

Phase 14 Slice 3 is complete. It implements only the exact parse-only and
AST-only
relationship metadata syntax in
[Relationship Endpoint Metadata Syntax v1](docs/spec/relationship-endpoint-metadata-syntax-v1.md),
regenerated ANTLR artifacts, immutable `RelationshipMetadata` and
`RelationshipEndpoint` AST nodes, and the backward-compatible
`Script.relationships` tuple. Relationship metadata remains outside
`Script.definitions`; semantic analysis, Semantic IR, PostgreSQL and MySQL
SQL, CLI, JSON v1, public APIs, dependencies, package metadata, version, CI,
fixtures, and goldens remain unchanged.

Phase 14 Slice 4 is complete and adds only
`tests/test_phase14_completion_audit.py` plus status documentation. The
backend compatibility and completion audit locks the parse-only and AST-only
relationship metadata boundary; semantic analysis, Semantic IR, PostgreSQL
and MySQL SQL, CLI, JSON v1, runtime, database behavior, public APIs,
dependencies, package metadata, version, CI, examples, fixtures, and goldens
remain unchanged. Phase 14 is complete.

Historical Phase 14 checkpoint: Phase 15 has not started and remains
unauthorized.

Phase 15 Slice 1 is complete as relationship metadata semantic validation
only. Semantic analysis now requires endpoint references to name existing
relations, relationship declaration names to be unique among relationships,
and endpoint local names to be unique within one relationship. Relationship
metadata remains outside semantic definitions and Semantic IR, and produces
no SQL. JOIN, relation composition, SQL lowering, relation-role semantics,
additional endpoint-role enforcement, cardinality or fanout behavior,
permission gates, runtime security, threat models, database behavior, JSON
v2, project mode, SQLGlot, release, publish, signing, upload, and attestation
remain unimplemented.

Phase 15 Slice 2 is complete as read-only semantic model storage. Validated
relationships are preserved in source order in `SemanticModel.relationships`;
their endpoints preserve source order, local names, referenced relation names,
and resolved source/table/query definitions. This adds no semantic namespace,
Semantic IR, SQL, CLI/JSON format, runtime, or database behavior.

The implemented source/token limits are deterministic parser/frontend
containment, not complete denial-of-service protection. Pietto has not added
full structural depth, semantic graph, diagnostic/output, wall-clock, CPU, or
memory budgets, and it has not rewritten recursive compiler algorithms. SQL is
generated only and is never executed.
There is no database connection, connector execution, schema introspection,
runtime server, Web UI, project or multi-file support, watch mode, or
LSP/editor integration. Database or runtime integration remains deferred and
requires a separate threat model.

See [the language specification](docs/spec/pietto-v0.9.md),
[the Phase 3 Semantic IR plan](docs/plan/phase-3-semantic-ir.md), and
[the Phase 4 PostgreSQL SQL plan](docs/plan/phase-4-postgres-sql.md), and
[the Phase 5 CLI tooling plan](docs/plan/phase-5-cli-tooling.md).
Security audit details and repeatable tooling commands are in
[the Phase 5.5 security hardening note](docs/plan/phase-5-5-security-hardening.md).
The normative machine-readable interface is documented in
[the CLI JSON schema version 1 specification](docs/spec/cli-json-v1.md).
The implementation history and original slice sequence are in
[the Phase 6 JSON output plan](docs/plan/phase-6-json-output.md).
The current stability direction and slice sequence are in
[the Phase 7 Developer Workflow & Stability plan](docs/plan/phase-7-developer-workflow-stability.md).
The completed planning direction, slice sequence, and audit are in
[the Phase 8 Project Model & Configuration Planning plan](docs/plan/phase-8-project-model-configuration-planning.md).
The completed SQL backend architecture direction, compatibility frame,
seven-slice sequence, and completion audit are in
[the Phase 9 SQL Backend Architecture & Dialect Strategy plan](docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md).
The completed typing and source-extension hardening work is documented in
[the Phase 9.5 Static Typing And Source Extension Hardening plan](docs/plan/phase-9-5-static-typing-source-extension-hardening.md).
The completed test-only typing cleanup and non-blocking test configuration are
documented in
[the Phase 9.6 Test Typing Hygiene plan](docs/plan/phase-9-6-test-typing-hygiene.md).
The completed generation-only MySQL implementation sequence and readiness gates
are documented in
[the Phase 10 MySQL SQL Generation MVP plan](docs/plan/phase-10-mysql-sql-generation-mvp.md).
The exact SQLGlot release evidence, isolated spike findings, handwritten
renderer decision, and reevaluation conditions are documented in
[the Phase 10 SQLGlot evaluation and adapter spike](docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md).
The current release-readiness baseline, seven-slice sequence, compatibility
gates, and deferred workflow implementations are documented in
[the Phase 11 Release Readiness & Reproducible Validation plan](docs/plan/phase-11-release-readiness-reproducible-validation.md).
The completed Phase 12 six-slice sequence, compatibility gates, and hard
non-goals are documented in
[the Phase 12 SQL Feature Expansion I plan](docs/plan/phase-12-sql-feature-expansion-i.md).
The completed planning-only relation-composition direction, six-slice
sequence, completion audit, SQL-lowering invariant, and security boundaries
are documented in
[the Phase 13 Relation Composition And Relationship Planning plan](docs/plan/phase-13-relation-composition-planning.md).
The completed broad readiness gate, two concrete candidate directions,
four-slice transition, and final compatibility audit are documented
in
[the Phase 14 Relation Composition Implementation Readiness plan](docs/plan/phase-14-relation-composition-implementation-readiness.md).
The selected first implementation candidate, deferred candidate, implemented
Slice 3 allowlist, stage impacts, readiness gates, and hard non-goals are
documented in
[the Phase 14 First Implementation Candidate Decision](docs/plan/phase-14-first-implementation-candidate-decision.md).
The implemented Phase 15 Slice 1 semantic boundary is documented in
[the Phase 15 Relationship Metadata Semantics plan](docs/plan/phase-15-relationship-metadata-semantics.md)
and
[the Relationship Metadata Semantic Validation v1 specification](docs/spec/relationship-metadata-semantic-validation-v1.md).
The conceptual relationship, endpoint-role, relation-role, cardinality,
authority, and compiler-versus-runtime boundary is documented in
[the Relationship And Relation Role Contract v1](docs/spec/relationship-relation-role-contract-v1.md).
The future composition input/output scope, clause visibility, qualification,
ambiguity, projection-alias, and endpoint-naming boundaries are documented in
[the Composition Scope And Name Resolution Contract v1](docs/spec/composition-scope-name-resolution-contract-v1.md).
The future selected-dialect composition shapes, qualification preservation,
dialect parity, cardinality, fanout, deterministic artifact, and fail-closed
backend boundaries are documented in
[the Composition SQL Shape Contract v1](docs/spec/composition-sql-shape-contract-v1.md).
The compiler-versus-runtime security boundary, current security non-claims,
threat-model prerequisites, diagnostic-family ownership, source-span,
ordering, cascade, and fail-closed planning are documented in
[the Composition Security And Diagnostics Contract v1](docs/spec/composition-security-diagnostics-contract-v1.md).
The future private closed selector, enabled-dialect gate, failure
classification, stage boundary, and presentation ownership are documented in
[the SQL dialect dispatch design](docs/spec/sql-dialect-dispatch-design-v1.md);
Slice 8 implements that private selector and explicit CLI enablement.
The evidence matrix, rejected roles, dependency and resource risks, and
conditional Phase 10 spike decision are in
[the Phase 9 SQLGlot evaluation](docs/plan/phase-9-sqlglot-evaluation.md);
SQLGlot remains uninstalled and unimplemented.
The planning-only internal backend boundary, capability, result, dispatch,
diagnostic, and SQLGlot-isolation rules are in
[the SQL backend abstraction contract](docs/spec/sql-backend-abstraction-contract-v1.md);
no abstraction layer or generic emitter is implemented.
The MySQL 8.0+ generation surface, connector, identifier, literal, SQL-mode,
diagnostic, golden, and CLI-gate rules are in
[the MySQL SQL generation MVP contract](docs/spec/mysql-sql-generation-mvp-v1.md);
the private fail-closed backend, static connector/IR surface, and closed
renderer are implemented, the reviewed MySQL golden corpus is locked, and
explicit MySQL CLI generation is enabled.
The planned connector naming, stage ownership, backend capability, physical
source-name, and fail-closed diagnostic rules are in
[the SQL dialect capability and source contract](docs/spec/sql-dialect-source-contract-v1.md);
the `mysql.table(Text)` semantic and IR subset is now implemented.
The planned strict, non-executable project configuration contract is in
[the Pietto project configuration schema version 1 specification](docs/spec/pietto-config-v1.md);
it is not implemented or read by the current CLI.
The planned explicit-root, containment, glob, file-identity, and deterministic
ordering contract is in
[the project root and path semantics version 1 specification](docs/spec/project-path-semantics-v1.md);
it is not implemented by the current CLI.
The planned project compile unit, flat namespaces, cross-file dependency,
stage-gating, diagnostic, and artifact-ordering contract is in
[the project multi-file semantics version 1 specification](docs/spec/project-multifile-semantics-v1.md);
multi-file compilation remains unimplemented.
The planned explicit project invocation and project JSON schema version 2
contract is in
[the project CLI and JSON schema version 2 design](docs/spec/project-cli-json-v2.md);
no project CLI or JSON v2 behavior is implemented.
The planned fixed project ceilings, deterministic resource stage gates, and
failure classification are in
[the project resource model version 1 specification](docs/spec/project-resource-model-v1.md);
no project-level budget is implemented.
Diagnostic codes are documented in
[the diagnostics specification](docs/spec/diagnostics.md).
