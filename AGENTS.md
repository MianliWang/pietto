# AGENTS.md

## Project

Pietto is a gradual, semantic SQL authoring DSL.

It is designed to make SQL easier to write, read, check, document, and compile. Pietto is not a database, not a runtime language, not a job scheduler, and not a concurrency framework.

Primary compiler pipeline:

```text
Pietto source
    -> parse
    -> analyze
    -> build IR
    -> emit explicitly selected PostgreSQL or MySQL SQL
    -> CLI text or JSON output
```

## Communication

- Communicate with the user in Chinese by default.
- Keep code, identifiers, file names, CLI commands, error codes, and commit messages in English.
- Technical terms may include English when clearer.

## Primary Goal

Build Pietto as a readable, safe, modular SQL authoring language.

Focus on:

- parser;
- AST;
- diagnostics;
- semantic checking;
- SQL generation;
- validation SQL;
- documentation;
- tests.

## Non-goals

Do not implement unless explicitly requested:

- multiprocessing;
- async runtime;
- goroutine-like concurrency;
- job scheduler;
- distributed execution;
- transaction manager;
- database optimizer replacement;
- web UI;
- DML execution;
- arbitrary Python evaluation inside Pietto;
- network/file IO from Pietto programs.

The database backend is responsible for SQL execution, transactions, locks, query planning, and physical concurrency.

## Language Style

Pietto uses Python-style indentation blocks.

Preferred:

```pietto
type Age = Int:
    ensure self between 0 and 130
```

Not preferred:

```pietto
type Age = Int {
    ensure self between 0 and 130
}
```

Rules:

- Use colon + indentation for blocks.
- Do not introduce braces as block delimiters.
- Use spaces for indentation.
- Do not mix tabs and spaces.
- Keep syntax readable and minimal.
- Avoid adding new keywords unless clearly necessary.

## Current Phase

Current phase status: Phase 14 is complete. Slice 1 is the final broad
readiness planning slice. Slice 2 selected the Relationship and endpoint
metadata syntax foundation and deferred the Ambiguity and name-ownership
foundation. Phase 14 Slice 3 implements only the exact parse-only and AST-only
metadata syntax in
`docs/spec/relationship-endpoint-metadata-syntax-v1.md`, regenerated ANTLR
artifacts, immutable relationship endpoint metadata AST nodes, and an
empty-by-default `Script.relationships` tuple. Relationship metadata remains
outside semantic definitions. Semantic analysis, Semantic IR, SQL, CLI, JSON
v1, runtime, database behavior, public APIs, dependencies, version, CI,
fixtures, and goldens remain unchanged. Slice 4 adds only backend
compatibility and completion audit coverage plus status documentation. It
adds no runtime or database behavior. Historical Phase 14 checkpoint:
Phase 15 has not started and remains unauthorized.

Phase 15 Slice 1 Relationship Metadata Semantic Validation is complete. It
adds only semantic validation that endpoint relation references exist,
relationship metadata names are unique among relationships, and endpoint
local names are unique within one relationship. Relationship metadata remains
outside semantic definitions and Semantic IR. Grammar, generated ANTLR, AST,
parser API, SQL, CLI formatting, JSON v1, runtime, database behavior, public
APIs, dependencies, version, CI, fixtures, and goldens remain unchanged.

Phase 15 Slice 2 Relationship Semantic Model Storage is complete. It adds only
immutable, source-ordered `SemanticModel.relationships` facts for validated
metadata. Each endpoint stores its local name, referenced relation name, and
resolved existing source/table/query definition. Relationship metadata still
does not enter type, callable, or relation namespaces, Semantic IR, SQL,
CLI/JSON formats, runtime, or database behavior.

Phase 15 Slice 3 Relationship Name Ownership And Ambiguity Contract is
complete as contract and audit work only. The contract at
`docs/spec/relationship-name-ownership-contract-v1.md` records the separate
relationship metadata namespace, relationship-local endpoint names, and
unchanged relation-only `from` lookup. It adds no runtime resolver, relation
composition, JOIN, SQL lowering, endpoint-qualified field lookup, multi-input
query semantics, or ambiguity diagnostics. Future implementation requires
separate authorization.

Phase 15 Slice 4 Relationship Metadata Semantics Completion Audit is complete.
It adds only `tests/test_phase15_completion_audit.py` and status
documentation. Phase 15 is complete as a semantic-only relationship metadata
phase. The final audit locks Slices 1 through 3 and confirms that no runtime
resolver, relation composition, JOIN, SQL lowering, endpoint-qualified field
lookup, multi-input query semantics, ambiguity diagnostics, runtime security,
database behavior, or new public API was added.

Phase 16 Slice 1 Language Direction and Syntax Philosophy is complete as
design, specification, and audit work only. It adds
`docs/spec/language-direction-v1.md`,
`docs/plan/phase-16-language-direction-safety-mode.md`, focused static audit
coverage, and minimal status documentation.

Phase 16 Slice 2 Safety Surface Deferral and SQL Portability Contract is
complete as design, specification, and audit work only. It adds
`docs/spec/safety-deferral-and-sql-portability-v1.md` and focused static audit
coverage. It prioritizes explicit dialect contracts, deterministic lossless
lowering within supported subsets, and fail-closed unsupported behavior while
deferring speculative safety and policy syntax.

Phase 16 Slice 3 Current Syntax Surface Audit is complete as syntax-surface
audit only. It adds `docs/spec/current-syntax-surface-audit-v1.md`, focused
static audit coverage, and minimal status documentation. It records the
unchanged accepted grammar/parser surface, existing `mode strict` checking
vocabulary, current `source ... is ...` form, and deferred speculative forms.

Phase 16 Slice 4 Phase 16 Completion Audit is complete as final audit and
status work only. It adds only `tests/test_phase16_completion_audit.py` and
completion status documentation. Phase 16 is complete as design,
specification, and audit work only. It introduced no accepted syntax,
public API, dependency, or output-format behavior. Phase 16 introduced no
compiler, runtime, or database behavior changes. Future work requires
separate explicit authorization.

Phase 17 Slice 1 Single-Input Qualified Field Binding is complete as a narrow
compiler slice. It adds only semantic, Semantic IR, and PostgreSQL/MySQL SQL
handling for already-parsed two-part dotted field references in existing
single-input relation `where`, `select`, and input-scope `order by` contexts.
Phase 17 Slice 2 Core Scalar Expression Semantics is complete as a narrow
semantic typing slice for already-parsed unary, binary, and `between`
expressions. It adds only `PIE-S2105` for invalid known operator operands,
keeps `/` semantically deferred, and uses pre-existing `%` SQL renderer
support. Phase 17 Slice 3 Computed Projection Schema Propagation is complete
as a narrow semantic row-schema propagation slice for named computed
projection aliases with known expression value types. It keeps unknown or
invalid computed aliases unknown, keeps projection aliases out of
same-relation `where` and input-scope `order by`, and adds no diagnostic code.
Phase 17 Slice 4 Relation-to-Relation Schema Hardening and Completion Audit
is complete as audit and status work only. It locks mixed relation schema
chains, semantic/IR row-schema consistency, diagnostic stability, SQL byte
stability, cycle fail-closed behavior, and the relationship metadata read-only
boundary. Phase 17 is complete. These slices keep relationship metadata
outside lookup and add no grammar,
generated ANTLR, parser, AST, relation alias syntax, JOIN, relation
composition, endpoint-qualified lookup, relationship-aware querying, runtime
security, database behavior, JSON v2, new public SQL API, dependency, package,
version, or CI change.

Phase 22 Min/Max Aggregate MVP is complete. Slices 1 through 6 cover candidate
decision and contract, semantic validation, IR lowering, PostgreSQL/MySQL SQL
lowering and goldens, CLI/JSON/output hardening, and completion audit/status
lock. The completed scope is exactly `min(field)` / `max(field)` as direct
aliased aggregate projections in no-GROUP and grouped contexts, with direct
field or supported single-input qualified field arguments. Supported argument
types are Int, Float, Date, and Timestamp, and each aggregate has a nullable
same-type result. Min/max remain aggregate names rather than scalar builtins.
Phase 22 adds no runtime/database execution, no JSON schema change, no CLI
option change, and no relationship/JOIN behavior.

Phase 23 Count(Field) Aggregate MVP is complete. Slices 1 through 6 cover
candidate decision and contract, semantic validation, IR lowering,
PostgreSQL/MySQL SQL rendering and goldens, CLI/JSON/output hardening, and
completion audit/status lock. The completed scope preserves `count()` as SQL
`COUNT(*)` and adds `count(field)` / `count(source.field)` as direct aliased
aggregate projections in no-GROUP and grouped contexts, with direct field or
supported single-input qualified field arguments. `count(field)` counts
non-null field values and returns `Int not null`; all concrete bound field
types are accepted except `Any`, and `Unknown` or unresolved fields remain
rejected through existing diagnostics. Count remains an aggregate name rather
than a scalar builtin. Phase 23 adds no runtime/database execution, no JSON
schema change, no CLI option change, and no relationship/JOIN behavior.

Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation is
complete. Slices 1 through 9 cover the aggregate expression argument contract,
numeric scalar semantics audit, `Decimal + Decimal` / `Decimal - Decimal`
scalar semantics, semantic acceptance for field-only `sum` / `avg` numeric
expression arguments, semantic acceptance for `count_distinct` lower/trim Text
transform chains, IR lowering to existing `AggregateCallIR.arguments`,
PostgreSQL/private MySQL SQL lowering, CLI/JSON/output and `satisfying`
hardening, and completion audit/status lock. The completed source scope
includes `sum(amount + tax)`, `avg(score * weight)`, and
`count_distinct(lower(trim(status)))` as direct aliased aggregate projections,
plus grouped `satisfying:` alias normalization to underlying aggregate
expressions. Phase 26 adds no runtime/database execution, no JSON schema
change, no CLI option change, no fixture/golden inventory change, no public
MySQL API expansion, and no relationship/JOIN behavior.

Phase 27 Grouped Result Ordering MVP Slice 1 is complete as candidate
decision, exact contract, and static audit work only. Phase 27 implementation
behavior has not started. The planned target is grouped result-scope
`ORDER BY` over bare select output names, with future SQL rendering through
underlying selected expressions rather than SELECT aliases. Slice 1 adds no
grammar, generated ANTLR, AST, Semantic IR, SQL backend, CLI, JSON schema,
fixture, golden, public API, runtime/database, project/multi-file, public
MySQL API, or relationship/JOIN behavior change.

Phase 13 Relation Composition And Relationship Planning is complete as
planning, contract, and audit work only. Slices 1 through 6 are complete.
Slice 1 Master Plan And Baseline Audit, Slice 2 Relationship /
Relation Role Contract, Slice 3 Composition Scope And Name Resolution
Contract, Slice 4 Join / Composition SQL Shape Contract, and Slice 5 Security
Boundary And Diagnostics Contract are complete.
Slice 2 adds only
`docs/spec/relationship-relation-role-contract-v1.md`, focused static audit
coverage, and scope-aware documentation. Slice 3 adds only
`docs/spec/composition-scope-name-resolution-contract-v1.md`, focused static
audit coverage, and scope-aware documentation. Slice 4 adds only
`docs/spec/composition-sql-shape-contract-v1.md`, focused static audit
coverage, and scope-aware documentation. Slice 5 adds only
`docs/spec/composition-security-diagnostics-contract-v1.md`, focused static
audit coverage, and scope-aware documentation. Slice 6 adds only
`tests/test_phase13_completion_audit.py` and final scope-aware documentation.
The Slice 2 baseline described
Slices 3 through 6 as planned only. The Slice 3 baseline described Slices 4
through 6 as planned only. The Slice 4 baseline described Slices 5 through 6
as planned only. The historical Slice 5 checkpoint statement, "Slice 6 remains
planned only", is retained for audit compatibility. Phase 13 Slices 1 through
6 change no grammar, generated
ANTLR, production compiler, SQL output, CLI, JSON v1, public API, dependency,
package metadata, version, CI, or golden fixture. Relation composition, JOIN,
SQL shape implementation, CTEs, subqueries, relationship syntax, relation-role
syntax, permission gates, runtime security, threat model, diagnostic code,
database connection, SQL execution, schema introspection, JSON v2, project
mode, LSP, Web UI, playground, SQLGlot, release, publish, signing, upload, and
attestation behavior are not implemented. The Phase 13 terms are conceptual
planning vocabulary, not keywords, reserved words, or accepted Pietto syntax.
Future implementation work requires a new explicit phase and authorization.
The Phase 14 Slice 1 readiness gate changes no grammar, generated ANTLR,
production compiler, SQL output, CLI, JSON v1, public API, dependency, package
metadata, version, CI, or golden fixture. It does not implement relation
composition, JOIN, SQL shape implementation, CTEs, subqueries, relationship
syntax, relation-role syntax, permission gates, runtime security, threat
model, diagnostic code, database connection, SQL execution, schema
introspection, JSON v2, project mode, LSP, Web UI, playground, SQLGlot,
release, publish, signing, upload, or attestation behavior.
Phase 14 Slice 2 adds only
`docs/plan/phase-14-first-implementation-candidate-decision.md`, focused
static audit coverage, readiness-plan updates, and scope-aware status
documentation. It changes no production code, grammar, generated ANTLR,
parser, AST, semantic analysis, IR, SQL backend, CLI, JSON v1, public API,
dependency, package metadata, version, CI, fixture, or golden. It implements
no relationship syntax, relation composition, JOIN, SQL shape, relation-role
semantics, permission gate, runtime security, threat model, diagnostic code,
database connection, SQL execution, schema introspection, JSON v2, project
mode, LSP, Web UI, playground, SQLGlot, release, publish, signing, upload, or
attestation behavior.

Phase 12 SQL Feature Expansion I is complete. Slices 1 through 6 are complete.
Slice 1 adds only the master plan,
a focused planning audit, and scope-aware status documentation. Slice 2 adds
only `docs/spec/order-limit-contract-v1.md`, focused static contract tests,
and scope-aware documentation. Slice 3 implements only static `LIMIT` through
grammar, regenerated ANTLR, AST, semantic validation, Semantic IR, and both
SQL backends. Slice 4 implements only input-scope `ORDER BY` through those
same compiler stages and both SQL backends. Slice 5 adds only reviewed
PostgreSQL/MySQL composition inputs and goldens, golden inventory ownership,
and focused coverage of the unchanged CLI text, atomic output-file, and JSON
v1 paths. Projection aliases, output-schema lookup, ordinal ordering, null
ordering, and collation remain unimplemented. CLI options, JSON v1 schema,
public Python APIs, dependencies, package metadata, version, and all
historical golden bytes remain unchanged.
Slice 6 adds only `tests/test_phase12_completion_audit.py` and final
scope-aware documentation. It locks the language, compiler, dual-backend,
golden, CLI/JSON v1, API, dependency, package, and Phase 11 workflow
boundaries without production changes. Future implementation work requires
separate explicit authorization.
Phase 11 Release Readiness & Reproducible Validation is complete. All seven
slices are complete, including Slice 7 Completion Audit And Documentation.
Historical Phase 11 status text: "Current phase status: Phase 11 Release
Readiness & Reproducible Validation is complete."
Slice 2 adds only `scripts/validate.py`, focused tests, and scope-aware
documentation. Its authoritative non-mutating command is
`uv run python scripts/validate.py`; direct
`python scripts/validate.py` is also supported. Slice 3 adds only the reviewed
ANTLR jar checksum, the independent
`uv run python scripts/check_generated.py` guard, focused tests, and
scope-aware documentation. It does not modify `scripts/validate.py`, grammar,
or generated files. Slice 4 adds only
`docs/spec/golden-fixture-policy-v1.md`, the independent
`uv run python scripts/check_goldens.py` audit, focused tests, and scope-aware
documentation. It changes no existing golden content and invokes no compiler.
Slice 5 adds only `.github/workflows/ci.yml`, focused static tests, and
scope-aware documentation. CI uses Python 3.12/3.13, Java 21, uv `0.11.19`,
minimal read-only permissions, and reviewed full action SHAs to invoke the
independent local commands. Slice 6 adds only the independent
`uv run python scripts/package_smoke.py` command, focused tests, one CI
invocation, and scope-aware documentation. It builds and installs only in
temporary directories, runs the installed console script outside the
repository, and performs no publication, upload, signing, deployment, package
metadata change, or Makefile integration.
Slice 7 adds only `tests/test_phase11_completion_audit.py` and scope-aware
completion documentation. It locks the four independent commands, CI,
compiler, package, golden, API, and deferred-capability boundaries without
adding production behavior.

Historical Phase 10 status text: "Current phase status: Phase 10 MySQL SQL Generation MVP is complete."
Phases 8 and 9 are complete. Phase 9.5 improved handwritten type safety,
isolated generated ANTLR typing noise, and migrated official source paths to
`.pietto`. Phase 9.6 removed test-suite Pyright diagnostics through precise
test-only typing cleanup. Phase 10 Slice 1 adds the master plan and readiness
audit. Slice 2 reviews SQLGlot `30.10.0` in an isolated uncommitted spike and
selects a small handwritten MySQL renderer for the Phase 10 MVP. SQLGlot is not
adopted. Slice 3 defines a private closed dialect-dispatch contract without
implementing it. Slice 4 adds a private MySQL backend skeleton that consumes
`ScriptIR`, treats current metadata as non-emitting, and fails closed with
ordered `PIE-B1000` diagnostics for relations and unknown future definitions.
Slice 5 adds static `mysql.table(Text)` recognition with exact name, arity,
`Text`, non-empty compile-time literal validation, plus exact connector name,
argument, and span preservation in `ConnectorIR`. Slice 6 adds the private
handwritten MySQL expression and relation renderer under the closed MVP
contract. Slice 7 adds three manually reviewed byte-exact MySQL golden groups
and locks every existing PostgreSQL SQL golden and public backend module.
Slice 8 enables explicit private CLI dispatch for `--dialect mysql` in text
and JSON v1 modes while preserving output-file safety. The MySQL emitter
remains absent from public `pietto.sql` exports.
Slice 9 completes the cross-slice behavioral and static audit, including
PostgreSQL and MySQL golden equality, CLI and JSON v1 behavior, typing gates,
dependency and generated-code locks, and all deferred capability boundaries.
Phase 10 completion does not itself authorize later compiler expansion.

Phase 11 is release-readiness work around the unchanged post-Phase-10
compiler. Its planned seven slices cover the master plan and baseline audit,
an authoritative non-mutating validation entry point, ANTLR provenance and
generated-file verification, golden-fixture policy and audit, minimal
GitHub Actions CI, packaging and installed-CLI smoke tests, and a completion
audit. `pyproject.toml` remains authoritative with
`requires-python = ">=3.12"`. The implemented CI validates Python 3.12 and
Python 3.13; Slice 1 itself did not create a workflow.

Phase 1 parser/frontend, Phase 2 Semantic Checker, Phase 3 Semantic IR, Phase 4
PostgreSQL SQL, Phase 5 CLI, Phase 5.5 Security / Robustness Hardening, and
Phase 6 JSON / machine-readable CLI output are complete. Phase 7 Developer
Workflow & Stability Foundation is also complete. The Phase 4 public
`emit_postgres_sql(script_ir)` API consumes `ScriptIR` directly and currently
emits minimal `SELECT`, projection, `FROM`, and optional `WHERE` SQL for
`RelationIR` definitions backed by static `postgres.table(Text)` sources or
another relation referenced by quoted name. Type, enum, shape, source,
constraint, and derive definitions are non-emitting metadata. Unsupported or
invalid relation emission and unknown future backend targets receive ordered
`PIE-B1000` diagnostics. Empty IR returns an empty successful result.

The Phase 4 backend itself does not include DDL, CTE expansion, SQL inlining,
nested subqueries, joins, grouping, ordering, limits, windows, unions,
database or connector execution, or CLI orchestration.

The SQL backend must not parse source, run semantic analysis, call `build_ir()`,
import SQLGlot, connect to databases, or execute connectors. There is no
`compile_to_ir()` wrapper.

The completed MVP provides:

- immutable PostgreSQL SQL artifacts and results;
- conservative source-backed and relation-name SQL generation;
- explicit non-emitting metadata handling without DDL;
- deterministic backend diagnostics;
- backend isolation from parser, semantic, and IR construction stages;
- focused SQL backend tests and planning.

The current CLI provides `pietto --help`, `pietto --version`, and
`pietto check file.pietto`. The check command performs parser and semantic
analysis only; it does not build IR or emit SQL. The CLI also provides
`pietto emit-sql file.pietto --dialect postgres` and
`pietto emit-sql file.pietto --dialect mysql`, which explicitly orchestrate
parser, semantic, IR, and one closed selected SQL backend. They emit SQL text
but never execute SQL or connect to a database or connector. SQL defaults to
stdout;
`--output path` atomically replaces one regular file after successful
rendering, rejects the input file and symbolic-link outputs, and leaves
diagnostics on stderr. CLI diagnostics use
`path:line:column CODE severity: message`, preserve compiler order, and are
written to stderr with C0 control characters and DEL rendered as visible
escapes.

Both `check` and `emit-sql` support command-local `--format {text,json}`, with
text as the default. JSON v1 uses standard-library serialization, structured
diagnostics and CLI errors, and one complete stdout document. JSON
`emit-sql --output` retains artifacts in stdout while writing raw SQL
atomically to the requested file.

Phase 5.5 Security / Robustness Hardening is complete and documented in
`docs/plan/phase-5-5-security-hardening.md`. PSEC-001 through PSEC-007 are
fixed or documented at their intended boundaries, the Common Vulnerability
Category Checklist and focused completion audit are complete, and no
vulnerability blocked Phase 6. The current production dependency surface
contains only the ANTLR Python runtime; planned technologies are not installed
until an implemented compiler slice requires them.

The completed Phase 6 JSON output uses a standard encoder, versioned schema,
strict stdout/stderr separation, and malicious-text tests. Full global
resource/depth budgets and recursive algorithm rewrites remain future
hardening. SQL execution, database connections, connector execution, schema
introspection, Web UI, runtime, project or multi-file support, and LSP/editor
integration remain out of scope. Database or runtime integration requires a
separate threat model before implementation.

The completed Phase 6 design is documented in
`docs/plan/phase-6-json-output.md`. The normative JSON v1 interface is
documented in `docs/spec/cli-json-v1.md`. The completed Phase 7 direction,
slice sequence, and completion audit are documented in
`docs/plan/phase-7-developer-workflow-stability.md`. Phase 7 also provides
focused golden outputs, fixed source/token parser budgets, resource/depth
design, and future workflow design only. Those designs do not implement
project configuration, multi-file behavior, watch mode, or editor tooling.
The completed Phase 8 direction, planning-only slice sequence, and audit are
documented in `docs/plan/phase-8-project-model-configuration-planning.md`.
Phase 8 does not authorize project, CLI, JSON, SQL, dependency, or runtime
implementation.
The completed Phase 9 direction, PostgreSQL compatibility boundary, SQLGlot
evaluation criteria, backend abstraction direction, MySQL MVP boundary, slice
sequence, and completion audit are documented in
`docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md`.
The completed Phase 9.5 typing and source-extension boundary is documented in
`docs/plan/phase-9-5-static-typing-source-extension-hardening.md`. `.pietto` is
the only official source extension, but the CLI remains path-based and does
not validate suffixes.
The completed planning-only SQLGlot evaluation is documented in
`docs/plan/phase-9-sqlglot-evaluation.md`. It approves only a future isolated
Phase 10 MySQL-generation spike. It does not approve a production dependency,
PostgreSQL migration, transpilation, optimizer, executor, database, connector,
or runtime use.
The completed Phase 10 spike and final MVP implementation-technology decision
are documented in
`docs/plan/phase-10-sqlglot-evaluation-adapter-spike.md`. SQLGlot `30.10.0`
was evaluated only in an isolated temporary environment. Phase 10 selects a
small handwritten MySQL renderer and adds no SQLGlot dependency or adapter.
The completed Phase 10 dialect dispatch design is documented in
`docs/spec/sql-dialect-dispatch-design-v1.md`. It defines a future private
closed selector, separate CLI-enabled dialect gate, dedicated emitters,
unknown-dialect exit `2`, backend-diagnostic exit `1`, and CLI ownership of
presentation and output files. Slice 8 implements that private selector and
enables only the explicit `postgres` and `mysql` dialect values.
The planning-only internal backend contract is documented in
`docs/spec/sql-backend-abstraction-contract-v1.md`. It preserves
`ScriptIR -> SqlResult`, the public `emit_postgres_sql` entry point, explicit
CLI dispatch, closed capability declarations, ordered partial results,
`PIE-B1000`, and private SQLGlot isolation. No backend protocol, registry,
dispatcher, or generic public emitter is implemented. The Slice 4 MySQL entry
point remains private to `pietto.sql.mysql`.
The MySQL MVP contract is documented in
`docs/spec/mysql-sql-generation-mvp-v1.md`. It defines
`mysql.table(Text)`, `emit_mysql_sql(ScriptIR) -> SqlResult`, the closed
MySQL 8.0+ SQL surface, `len -> CHAR_LENGTH`, `matches` rejection, identifier
and literal policy, SQL-mode assumptions, golden fixtures, and CLI enablement
gates. The private fail-closed backend, closed handwritten renderer, and static
`mysql.table(Text)` semantic/IR surface are implemented without runtime
connector behavior. The reviewed MySQL golden corpus is implemented without
public emitter export; Slice 8 enables text and JSON v1 CLI generation.
The planned dialect-specific connector names, semantic/backend responsibility
boundary, required capability declaration, physical-name model, and
unsupported-case policy are documented in
`docs/spec/sql-dialect-source-contract-v1.md`. The contract is
the authority for the implemented `mysql.table(Text)` semantic and IR subset;
the private closed CLI dispatch is implemented, while a generic dialect
abstraction remains unimplemented.
The handwritten PostgreSQL backend and
`emit_postgres_sql(ScriptIR) -> SqlResult` remain the compatibility baseline.
Phase 9 does not authorize a production dialect implementation or dependency.
The planned strict, non-executable future configuration contract is documented
in `docs/spec/pietto-config-v1.md`. It is a specification only; the current
repository does not contain or read `pietto.toml`.
The planned explicit project-root and path contract is documented in
`docs/spec/project-path-semantics-v1.md`. It is also specification-only; no
root discovery, path traversal, or glob expansion is implemented.
The planned project compile-unit and cross-file semantic contract is documented
in `docs/spec/project-multifile-semantics-v1.md`. It is specification-only; no
multi-file compiler, module, import, or dependency graph is implemented.
The planned explicit project invocation and JSON schema version 2 contract is
documented in `docs/spec/project-cli-json-v2.md`. It is specification-only; no
`--project` option, project CLI behavior, or JSON v2 serializer is implemented,
and JSON v1 remains unchanged.
The planned project-level resource ceilings, deterministic stage gates, and
failure classification are documented in
`docs/spec/project-resource-model-v1.md`. It is specification-only; the
current implemented limits remain only the per-file source/token parser
budgets, and no project budget or config override is implemented.
The current Phase 10 slice sequence, implementation gates, JSON boundary,
typing requirements, and generation-only MySQL scope are documented in
`docs/plan/phase-10-mysql-sql-generation-mvp.md`. Slices 1 through 3 are
documentation and static audit only. Slice 4 is the first production slice
and adds only the private MySQL backend skeleton. Slice 5 adds only static
MySQL connector semantics and IR preservation. Slice 6 adds only the private
closed MySQL expression and relation renderer. Slice 7 adds only reviewed
MySQL fixtures, private-backend golden tests, negative regressions, and
PostgreSQL compatibility locks. Slice 8 adds only explicit private CLI
dispatch, MySQL text/JSON v1 coverage, and output-file integration.
The current Phase 11 release-readiness baseline, fixed seven-slice sequence,
allowed workflow changes, compatibility gates, and hard non-goals are
documented in
`docs/plan/phase-11-release-readiness-reproducible-validation.md`. Slices 1
through 7 are complete.
The completed Phase 12 fixed six-slice sequence, compatibility gates, and hard
non-goals are documented in
`docs/plan/phase-12-sql-feature-expansion-i.md`. Slices 1 through 6 are
complete. The normative contract is
documented in
`docs/spec/order-limit-contract-v1.md`.
The completed Phase 13 planning-only relation-composition direction, fixed
six-slice sequence, completion audit, SQL-lowering invariant, and security
boundaries are documented in
`docs/plan/phase-13-relation-composition-planning.md`. Slices 1 through 6 are
complete as planning, contract, and audit work only. The Slice 2
conceptual terminology and compiler-versus-runtime boundary are documented in
`docs/spec/relationship-relation-role-contract-v1.md`. The Slice 3
input/output scope, name-resolution, qualification, ambiguity, projection
alias, and endpoint-naming boundaries are documented in
`docs/spec/composition-scope-name-resolution-contract-v1.md`. The Slice 4
selected-dialect shape, qualification preservation, dialect parity,
cardinality, fanout, deterministic artifact, and fail-closed backend
boundaries are documented in
`docs/spec/composition-sql-shape-contract-v1.md`. The Slice 5
compiler-versus-runtime boundary, current security non-claims, threat-model
prerequisites, diagnostic-family ownership, source-span, ordering, cascade,
and fail-closed planning are documented in
`docs/spec/composition-security-diagnostics-contract-v1.md`.
The Phase 14 final broad readiness gate, fixed four-slice transition, two
candidate directions, implementation gates, and mandatory concrete Slice 2
decision are documented in
`docs/plan/phase-14-relation-composition-implementation-readiness.md`. Slice 1
is complete as planning/readiness work only.
The Slice 2 chosen candidate, deferred candidate, exact implemented Slice 3
allowlist, compiler-stage impacts, gate outcome, and hard non-goals are
documented in
`docs/plan/phase-14-first-implementation-candidate-decision.md`. Slice 2 is
complete as a candidate decision only. Slice 3 is complete as parse-only and
AST-only relationship metadata. Slice 4 is complete as backend compatibility
and completion audit work only. Phase 14 is complete. Historical Phase 14
checkpoint: Phase 15 has not started and remains unauthorized. Phase 15 Slice
1 is complete as semantic validation only, as documented in
`docs/plan/phase-15-relationship-metadata-semantics.md` and
`docs/spec/relationship-metadata-semantic-validation-v1.md`. Phase 15 Slice 2
adds only read-only semantic model storage for validated relationship
metadata. Phase 15 Slice 3 adds only
`docs/spec/relationship-name-ownership-contract-v1.md` and static audit
coverage; it adds no runtime behavior. Phase 15 Slice 4 adds only the final
completion audit and status documentation. Phase 15 is complete. Phase 16
Slice 1 adds only the language-direction specification, four-slice
design/audit plan, static audit, and status documentation. Phase 16 Slice 2
adds only the safety-deferral and SQL-portability contract, static audit, and
status documentation. Phase 16 Slice 3 adds only the current syntax-surface
audit, static audit coverage, and status documentation. Phase 16 Slice 4 adds
only the final completion audit and status documentation. Phase 16 is complete
as design, specification, and audit work only. Phase 17 Slice 1 adds only
single-input qualified field binding for existing dotted expressions and the
corresponding narrow Semantic IR and SQL backend handling. Phase 17 Slice 2
adds only core scalar expression semantic typing and `PIE-S2105`; it changes
no grammar, generated ANTLR, SQL renderer, SQL golden, CLI, JSON, dependency,
package, version, or CI behavior. Phase 17 Slice 3 adds only computed
projection schema propagation for named aliases and changes no grammar,
generated ANTLR, SQL renderer, SQL golden, CLI, JSON, dependency, package,
version, or CI behavior. Phase 17 Slice 4 adds only relation-to-relation
schema hardening audit coverage and completion status documentation. Phase 17
is complete.

Current strict boundaries remain:

- SQL is generated only and is never executed;
- no database connection, connector execution, or schema introspection;
- no runtime server or Web UI;
- no project configuration or multi-file implementation;
- no watch mode or LSP/editor implementation;
- no `compile_to_ir()` or `compile_to_sql()`.

Do not implement after the completed phase unless explicitly requested:

- joins, grouping, projection-alias/output-schema/ordinal ordering, null
  ordering, collation, offsets, windows, or unions;
- metadata DDL such as `CREATE TABLE`, `CREATE VIEW`, constraints, or indexes;
- relation dependency CTE expansion, SQL inlining, or nested subqueries;
- SQLGlot integration;
- SQL execution;
- database connections or schema introspection;
- user-defined callable resolution or call graphs;
- purity checking;
- implicit conversions, overloads, or generics;
- DML;
- optimizer;
- CLI behavior beyond the current help/version, check, and emit-sql commands;
- project configuration or `pietto.toml` implementation;
- multi-file support;
- watch mode;
- LSP/editor integration;
- web API;
- visualization;
- concurrency/runtime features.

All seven Phase 9 slices, Phase 9.5, and Phase 9.6 are complete. Phase 10
is complete with all nine slices audited. SQLGlot is rejected for the Phase
10 MVP. Phase 11 is complete with all seven slices audited.
Phase 12 Slices 1 through 6 are complete. Slice 3 adds only the approved
static `LIMIT` vertical slice, Slice 4 adds only the approved input-scope
`ORDER BY` vertical slice, and Slice 5 adds only reviewed composition
fixtures, goldens, and unchanged CLI/JSON v1 coverage. Slice 6 adds only the
completion audit and final documentation.
Phase 13 is complete as planning, contract, and audit work only. Slices 1
through 6 added only planning contracts, static audits, and status
documentation. Phase 13 itself defined no accepted source syntax, SQL backend
behavior, runtime security, threat model, or diagnostic code and implemented
no relation composition, JOIN, SQL shapes, relation-role syntax, relation
gates, permission matching, runtime security, database connection, SQL
execution, schema introspection, or SQLGlot.
Phase 14 Slices 1 through 4 are complete. Slice 2 chose the Relationship and
endpoint metadata syntax foundation and deferred the Ambiguity and
name-ownership foundation. Slice 3 implements only parse-only and AST-only
relationship metadata. Slice 4 adds only backend compatibility and completion
audit coverage plus status documentation. Historical Phase 14 checkpoint:
Phase 15 has not started and remains unauthorized. Phase 15 Slice 1 validates
relationship metadata only; it adds no Semantic IR, SQL, CLI/JSON format,
runtime, or database behavior. Phase 15 Slice 2 stores validated metadata only
in the read-only semantic model and preserves those same boundaries. Phase 15
Slice 3 documents name ownership and future ambiguity boundaries only; it
implements no relation composition, endpoint-qualified lookup, multi-input
query semantics, or ambiguity diagnostic. Phase 15 Slice 4 completes the
semantic-only phase with a strict audit and no compiler or runtime behavior.
Phase 16 Slice 1 is complete as language-direction design, specification, and
audit work only. Phase 16 Slice 2 is complete as safety-deferral and
SQL-portability design, specification, and audit work only. Phase 16 Slice 3
is complete as syntax-surface audit only. Phase 16 Slice 4 completes the final
audit and status work only. Phase 16 is complete with no production
implementation authorization.
Phase 17 Slices 1 through 4 are complete. Slices 1 through 3 are narrow
implementation slices for single-input qualified field binding, core scalar
expression semantic typing, and computed projection schema propagation. Slice
4 is audit and status work only. They do not authorize grammar changes, JOIN,
relation composition, endpoint-qualified lookup, aggregate/grouping work,
runtime behavior, or public API expansion. Phase 17 completion does not
authorize Phase 18.
Phase 22 Slices 1 through 6 are complete. Slices 1 through 5 deliver the
bounded Min/Max Aggregate MVP for `min(field)` / `max(field)`, and Slice 6
adds only completion audit/status lock coverage plus narrow behavior-neutral
format cleanup. Supported min/max argument types are Int, Float, Date, and
Timestamp with a nullable same-type result. Phase 22 adds no runtime/database
execution, no JSON schema change, no CLI option change, and no
relationship/JOIN behavior.
The private MySQL backend, static `mysql.table(Text)` semantic/IR surface, and
closed renderer are the MySQL compiler boundaries. Explicit private CLI
dispatch and JSON v1 presentation are enabled. Public emitter export, a
generic backend abstraction, richer SQL, execution, and database behavior
remain prohibited.

Compiler stages must remain isolated: IR construction must not mutate parser
or semantic inputs, and SQL backends must consume `ScriptIR` without rerunning
earlier stages or introducing grammar syntax.

Phase 11 completion is release-readiness and reproducible-validation
hardening, not an actual release. Package publication, registry credentials,
release signing, provenance attestations, and automated versioning remain
unimplemented. Phase 12 SQL Feature Expansion I has implemented only the
Slice 3 static `LIMIT`, Slice 4 input-scope `ORDER BY`, and Slice 5 reviewed
composition coverage. Slice 6 completes the audit without production changes.
Phase 12 completion is not an actual package release; publication, registry
upload, signing, attestations, automated versioning, and version bump remain
unimplemented.

## Required Repository Structure

```text
pietto/
    AGENTS.md
    README.md
    pyproject.toml
    uv.lock
    Makefile

    docs/
        spec/
            pietto-v0.9.md
        plan/
            phase-1-parser.md
        decisions/

    grammar/
        Pietto.g4

    examples/
        basic/
        constraints/

    src/
        pietto/
            __init__.py
            ast_nodes.py
            ast_builder.py
            parser_api.py
            errors.py
            generated/
            semantic/
            ir/
            sql/
            cli.py

    tests/
        test_parser_basic.py
        test_parser_types.py
        test_parser_shapes.py
        test_parser_tables.py
        test_diagnostics.py
```

## Environment

Use uv-first.

Recommended setup:

```bash
sudo apt update
sudo apt install -y git curl unzip default-jdk make

curl -LsSf https://astral.sh/uv/install.sh | sh

uv python install 3.12
uv python pin 3.12

uv init --package
uv add antlr4-python3-runtime
uv add --dev pytest pytest-cov ruff mypy pyright
```

ANTLR jar:

```bash
mkdir -p tools
curl -L -o tools/antlr-4.13.2-complete.jar https://www.antlr.org/download/antlr-4.13.2-complete.jar
```

## Commands

After changes, run:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

If grammar changed, regenerate parser:

```bash
make generate-parser
```

Do not edit generated parser files manually.

## Parser Rules

- Source grammar lives in `grammar/Pietto.g4`.
- Generated files live under `src/pietto/generated/`.
- Generated files must not be manually edited.
- AST builder must convert parse tree nodes into custom Pietto AST dataclasses.
- Public parser API should hide ANTLR internals.
- User-facing errors should be represented through `src/pietto/errors.py`.

## Core Syntax Decisions

### Header

Support:

```pietto
pietto 0.9
mode checked
dialect postgres
encoding utf8
```

Check mode can be declared in the file header. A later CLI phase may allow an
override such as:

```bash
pietto check app.pietto --mode strict
```

### Type

Support inline and block forms:

```pietto
type Age = Int ensure self between 0 and 130
```

```pietto
type Age = Int:
    ensure self between 0 and 130
```

Prefer block form for complex definitions.

### Text

Support explicit length and encoding:

```pietto
type Username = Text(max = 32, encoding = utf8):
    ensure len(self) >= 3
```

Distinguish:

- `Text(max = 32)` = type-level / physical length boundary;
- `ensure len(self) <= 32` = semantic validation rule.

### Constraint keywords

Preserve distinction:

| Keyword | Scope | Meaning |
|---|---|---|
| `where` | table/query | filters rows |
| `ensure` | type/field | guarantees value contract |
| `check` | shape | row-level invariant |
| `expect` | table/query | planned result validation; not parsed in Phase 1 |

Do not merge these concepts.

### Shape

Use `shape`, not `view`, for data contracts:

```pietto
shape User:
    id: UUID not null
    email: Text(max = 255, encoding = utf8) nullable
```

### Source

Bind sources to shapes when possible:

```pietto
source users: User is postgres.table("public.users")
```

### Table

Reusable logical relation:

```pietto
table adult_users:
    from users
    where age >= 18

    select:
        id
        age
```

### Query

Minimal parse-only output:

```pietto
query recent_adult_users:
    from adult_users
    select:
        id
        age
```

## Coding Conventions

- Use Python 3.12-compatible code.
- Use dataclasses for AST nodes.
- Prefer explicit small functions over large visitors.
- Keep AST independent from ANTLR classes.
- Avoid dynamic `eval`.
- Avoid global mutable compiler state.
- Use typed function signatures.
- Use `pathlib.Path`.
- Keep diagnostics structured.

## Documentation and Comments

- Use English docstrings and code comments.
- Add docstrings for public APIs, AST nodes, diagnostics, and non-trivial parser helpers.
- Comment design decisions and tricky logic, not obvious line-by-line behavior.
- Keep grammar comments concise and focused on language design choices.
- When adding new syntax, update `docs/spec` or `docs/plan` if relevant.
- Avoid noisy comments that merely restate code.

## Diagnostics

Diagnostics should include:

- error code;
- severity;
- message;
- file path if available;
- line and column if available;
- optional suggestion.

Use the canonical `PIE-<PHASE><NUMBER>` format documented in
`docs/spec/diagnostics.md`:

- `PIE-Pxxxx` for parser, lexer, and indentation diagnostics;
- `PIE-Sxxxx` for semantic diagnostics;
- `PIE-Ixxxx` for IR and SQL compilation diagnostics;
- `PIE-Bxxxx` for backend capability diagnostics;
- `PIE-Rxxxx` for runtime and execution diagnostics.

Severity remains a separate field and must not be encoded in the diagnostic
code.

Example:

```text
ERROR PIE-S2102 at examples/basic/users.pietto:12:9
Unknown field "emails" on shape "User".

Suggestion:
  Did you mean "email"?
```

## Testing Rules

For every grammar feature, add:

- one positive parse test;
- one negative parse test;
- one AST shape assertion;
- at least one example fixture if the syntax is user-facing.

Parser tests should not require a live database.

## Before Coding

For non-trivial changes:

1. Inspect existing files.
2. Write a short plan.
3. Implement the smallest useful slice.
4. Run formatting, linting, and tests.
5. Summarize changed files and remaining work.

## Historical Phase 1 Bootstrap

The following prompts are retained as Phase 1 project history and are not
current implementation instructions:

```text
Read AGENTS.md, docs/spec/pietto-v0.9.md, and docs/plan/phase-1-parser.md.

Do not code yet.

Create an implementation plan for Phase 1 parser and AST only.
List files to create, grammar rules to implement, test cases to add, and risks.
Do not implement SQL generation, database execution, DML, or web UI.
```

Then implement with:

```text
Implement Phase 1 parser skeleton.

Scope:
- project structure
- AST dataclasses
- grammar/Pietto.g4
- parser generation command
- parser_api.parse_source
- basic tests for type, shape, source, table, query

Run:
- uv run ruff format .
- uv run ruff check .
- uv run pytest

Stop after Phase 1 skeleton. Do not implement SQL generation.
```

## Codex Skills Strategy

Do not depend on external popular skills for Phase 1.

Use project-local guidance first:

```text
AGENTS.md
docs/spec/pietto-v0.9.md
docs/plan/phase-1-parser.md
```

Optional local skills can be added later:

```text
.codex/skills/
    pietto-parser/
        SKILL.md
    pietto-spec-review/
        SKILL.md
    pietto-test/
        SKILL.md
    pietto-doc/
        SKILL.md
```

### Local skill: pietto-parser

Use for grammar and parser tasks.

Rules:

- edit `grammar/Pietto.g4`;
- regenerate parser with `make generate-parser`;
- do not edit generated files manually;
- add parser tests.

### Local skill: pietto-spec-review

Use before changing syntax.

Rules:

- preserve Python-style blocks;
- avoid braces;
- avoid runtime/concurrency features;
- keep keyword set small;
- preserve `where/ensure/check/expect` distinction.

### Local skill: pietto-test

Use after implementation tasks.

Rules:

- add fixture;
- add positive test;
- add negative test;
- run `ruff` and `pytest`.

### Local skill: pietto-doc

Use when syntax changes.

Rules:

- update `docs/spec/pietto-v0.9.md`;
- add an example;
- update keyword list if needed.

External skills can be considered later for GitHub PRs, docs, database integration, security review, or web UI, but they are not needed for Phase 1.
