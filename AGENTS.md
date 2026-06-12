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

Current phase status: Phase 11 Release Readiness & Reproducible Validation is
in progress. Slice 1 Master Plan And Baseline Audit and Slice 2 Authoritative
Validation Entry Point are complete. Slices 3 through 7 are planned only and
require separate explicit implementation requests. Slice 2 adds only
`scripts/validate.py`, focused tests, and scope-aware documentation. The
authoritative non-mutating command is
`uv run python scripts/validate.py`; direct
`python scripts/validate.py` is also supported. It adds no CI, ANTLR checksum
file, generated-file guard, golden policy implementation, packaging smoke
implementation, or Makefile integration.

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
`requires-python = ">=3.12"`. The future CI slice must validate Python 3.12
and Python 3.13; Slice 1 does not create a workflow.

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
and 2 are complete; Slices 3 through 7 remain planned and unimplemented.

Current strict boundaries remain:

- SQL is generated only and is never executed;
- no database connection, connector execution, or schema introspection;
- no runtime server or Web UI;
- no project configuration or multi-file implementation;
- no watch mode or LSP/editor implementation;
- no `compile_to_ir()` or `compile_to_sql()`.

Do not implement after the completed phase unless explicitly requested:

- joins, grouping, ordering, limits, windows, or unions;
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
10 MVP. Phase 11 Slices 1 and 2 are complete, while Slices 3 through 7 remain
planned only.
The private MySQL backend, static `mysql.table(Text)` semantic/IR surface, and
closed renderer are the MySQL compiler boundaries. Explicit private CLI
dispatch and JSON v1 presentation are enabled. Public emitter export, a
generic backend abstraction, richer SQL, execution, and database behavior
remain prohibited.

Compiler stages must remain isolated: IR construction must not mutate parser
or semantic inputs, and SQL backends must consume `ScriptIR` without rerunning
earlier stages or introducing grammar syntax.

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
