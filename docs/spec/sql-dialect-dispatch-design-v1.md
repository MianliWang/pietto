# SQL Dialect Dispatch Design v1

## Status

**Phase 10 Slice 3 is complete.**

**This design is specification-only and is not implemented.**

It defines Pietto's future internal closed SQL dialect selection and dispatch
boundary. It does not add a dispatcher, MySQL backend, source connector, CLI
dialect, public API, JSON behavior, or production code.

The only implemented SQL path remains:

```text
postgres -> emit_postgres_sql
```

The future Phase 10 mapping is:

```text
postgres -> emit_postgres_sql
mysql    -> emit_mysql_sql
```

`mysql` remains disabled until Phase 10 Slice 8. Slice 4 subsequently added a
private fail-closed `emit_mysql_sql` skeleton, but this design still adds no
dispatcher. `mysql.table` and `--dialect mysql` remain unimplemented.

## Goals

This design defines:

- the private closed mapping from CLI dialect names to dedicated emitters;
- the separation between an implemented backend and a CLI-enabled dialect;
- the exact stage at which dialect selection occurs;
- the data allowed to cross the CLI/backend boundary;
- unknown-dialect and backend-capability failure semantics;
- text and JSON v1 presentation ownership;
- output-file ownership;
- source-header and connector non-inference rules;
- public API, compatibility, and security boundaries.

The design preserves the handwritten PostgreSQL backend as the byte-exact
reference and the Slice 2 decision to use a small handwritten MySQL renderer.

## Decision Summary

1. CLI dialect selection is explicit, private, static, and closed.
2. The eventual mapping contains only `postgres` and `mysql`.
3. Every dialect maps to one dedicated `ScriptIR -> SqlResult` emitter.
4. `emit_postgres_sql(ScriptIR) -> SqlResult` remains unchanged.
5. The future MySQL entry point remains
   `emit_mysql_sql(ScriptIR) -> SqlResult`.
6. No generic public `emit_sql(...)` API is added.
7. Backend implementation and CLI enablement are separate gates.
8. Until Slice 8, the only CLI-enabled dialect is `postgres`.
9. Unknown or disabled dialects are rejected before source reading or parsing.
10. Unknown dialects remain CLI errors with exit code `2`.
11. JSON v1 preserves the supplied value and uses
    `cli_errors[].kind = "unsupported_dialect"`.
12. A selected backend capability failure remains a `PIE-B1000` diagnostic
    and exit code `1`.
13. The selected emitter receives exactly one `ScriptIR` argument.
14. Backends receive no dialect string, CLI namespace, path, output option,
    presentation mode, or JSON object.
15. CLI orchestration owns parsing, semantic analysis, IR construction,
    backend selection, presentation, exit codes, and output files.
16. Connector names and source headers never select or override the backend.
17. Dispatch uses no plugins, dynamic imports, entry points, environment
    variables, project configuration, or network discovery.
18. SQLGlot remains absent from the Phase 10 MVP.

## Current Baseline

The current text CLI declares:

```python
choices=("postgres",)
```

Argparse rejects `--dialect mysql` before source parsing and exits `2`.

The JSON command path intentionally accepts the raw dialect string long enough
to serialize a structured error. A non-`postgres` value:

- is preserved in the top-level `dialect` field;
- produces `unsupported_dialect`;
- stops before source parsing;
- exits `2`;
- writes no requested output file.

Both successful text and JSON PostgreSQL paths currently call
`emit_postgres_sql` only after parser, semantic, and IR stages succeed.

The current public `pietto.sql` exports remain:

```text
SqlArtifact
SqlArtifactKind
SqlResult
emit_postgres_sql
```

## Closed Dispatch Model

The future CLI implementation should use one private callable shape:

```python
type _SqlEmitter = Callable[[ScriptIR], SqlResult]
```

The selector is conceptually:

```python
def _select_sql_emitter(dialect: str) -> _SqlEmitter | None:
    if dialect == "postgres":
        return sql_api.emit_postgres_sql
    if dialect == "mysql":
        return mysql_backend.emit_mysql_sql
    return None
```

This is a design sketch, not production code added by Slice 3.

The implementation may use an equivalent private exhaustive branch. It should
not use a mutable registry or expose a mapping as public API.

The selector should resolve emitter attributes when called rather than capture
function objects in a module-import-time dictionary. This preserves focused
monkeypatching, avoids stale references in tests, and keeps dispatch behavior
observable at the existing module boundary.

The selector:

- accepts one normalized exact dialect name;
- performs no case folding or alias expansion;
- returns one dedicated emitter or `None`;
- performs no source parsing, connector inspection, or IO;
- does not invoke the emitter;
- does not catch backend diagnostics;
- does not construct a generic backend object.

There are no aliases such as `postgresql`, `pg`, `mysql8`, or `mariadb`.
Adding another dialect or alias requires an explicit compatibility change.

## Backend Availability And CLI Enablement

Backend availability does not imply CLI enablement.

During Slices 4 through 7, a private `emit_mysql_sql` may be implemented and
tested directly while `mysql` remains absent from the CLI-enabled dialect set.
The CLI must continue rejecting it before parsing.

Conceptually, CLI admission uses one private immutable value:

```python
_ENABLED_SQL_DIALECTS = ("postgres",)
```

Slice 8 may atomically change it to:

```python
_ENABLED_SQL_DIALECTS = ("postgres", "mysql")
```

only after every MySQL backend, connector, golden, compatibility, typing, and
security gate passes.

Text argparse choices and JSON dialect admission must derive from the same
enabled set. Tests must prove that every enabled dialect selects exactly one
emitter and that no implemented-but-disabled backend is accepted.

The dispatch selector's future `mysql` branch and CLI enablement must be added
together in Slice 8. Earlier backend slices use direct backend tests and must
not add a dormant user-facing route.

## Selection And Compilation Flow

The future single-file flow is:

```text
parse command arguments
    -> validate explicit dialect against the enabled set
    -> select exactly one dedicated emitter
    -> validate output path, if requested
    -> read and parse one Pietto file
    -> run semantic analysis
    -> build ScriptIR
    -> call selected_emitter(script_ir)
    -> inspect SqlResult diagnostics
    -> present text or JSON v1
    -> atomically write output only when allowed
```

Dialect validation and emitter selection occur before source reading and
parsing. This preserves the existing unsupported-dialect short circuit and
prevents malformed or missing source files from masking a command usage error.

Parser, semantic, and IR failures stop before backend invocation. The selected
emitter is called once and only after a non-`None` `ScriptIR` exists.

The emitter call is exactly:

```python
sql_result = selected_emitter(script_ir)
```

The backend is not passed:

- the dialect name;
- source text, parser AST, or semantic model;
- input or output paths;
- text or JSON format;
- stdout or stderr handles;
- an argparse namespace;
- a connector-selected backend;
- database, schema, execution, or runtime state.

## Text And JSON Orchestration

The text and JSON paths may retain separate presentation functions, but they
must use the same enabled dialect policy and selected emitter contract.

The selected dialect string remains CLI-owned:

- text mode does not need to pass it into the backend;
- JSON v1 echoes it in the existing top-level `dialect` field;
- `SqlResult` does not gain a dialect field;
- `SqlArtifact` does not gain a dialect field.

Backend artifact SQL is presented without rewriting:

- text joins artifacts with the existing blank-line policy;
- JSON serializes the existing artifact fields;
- output files receive existing raw artifact text;
- backends never print, serialize JSON, or write files.

No backend receives an output path or decides whether an output write is
allowed.

## Error Classification

The dispatch boundary preserves these distinct outcomes:

| Condition | Owner | Representation | Exit |
|---|---|---|---|
| Missing `--dialect` | CLI argument handling | usage error | `2` |
| Unknown or disabled text dialect | argparse/CLI | invalid choice | `2` |
| Unknown or disabled JSON dialect | CLI | `unsupported_dialect` | `2` |
| Input or output path failure | CLI | existing CLI error | `2` |
| Parser, semantic, or IR error | compiler stage | structured diagnostic | `1` |
| Selected backend capability failure | selected backend | `PIE-B1000` | `1` |
| Successful or warning-only generation | CLI/backend | artifacts and diagnostics | `0` |

An unknown or disabled dialect is not a compiler diagnostic and must not use a
`PIE-*` code.

A backend capability failure is not `unsupported_dialect`. Examples include:

- a future MySQL backend receiving a demanded `postgres.table` source;
- a future PostgreSQL backend receiving a demanded `mysql.table` source;
- MySQL receiving `matches/2`;
- a selected backend receiving an unsupported expression or literal.

These cases have already selected an enabled backend. They return
`SqlResult.diagnostics`, use the narrowest IR span, produce no partial artifact
for the failed definition, and lead to exit `1`.

JSON v1 continues preserving successful artifacts returned alongside backend
diagnostics. A requested output file remains unwritten when backend errors are
present.

## Dialect, Header, And Connector Independence

The explicit CLI dialect is authoritative for backend selection.

The selector must not inspect:

- `dialect postgres` or `dialect mysql` source headers;
- `postgres.table` or `mysql.table` connector names;
- relation names or physical table strings;
- file suffixes;
- environment variables;
- future project configuration.

Source header dialect metadata remains descriptive under the Phase 10
contract. Header/CLI mismatch validation is deferred and must not be
implemented as implicit dispatch.

Connector identity is semantic and backend capability metadata. A connector
does not:

- enable a CLI dialect;
- select a backend;
- redirect generation to another backend;
- trigger connector execution;
- open a database or inspect a schema.

After both connectors exist, a connector/backend mismatch is diagnosed by the
already selected backend with `PIE-B1000`.

## Dedicated Emitters And Public API

Dedicated emitter entry points remain the compatibility model:

```python
emit_postgres_sql(script_ir: ScriptIR) -> SqlResult
emit_mysql_sql(script_ir: ScriptIR) -> SqlResult
```

This design does not decide when or whether `emit_mysql_sql` becomes part of
`pietto.sql.__all__`. The CLI may call an internal MySQL module entry point
without expanding public exports. Public export requires a separate explicit
compatibility decision after the MySQL golden and stability gates pass.

The following remain unapproved:

```python
emit_sql(script_ir, dialect)
compile_to_sql(...)
```

No public dialect enum, registry, backend object, capability negotiation API,
or plugin interface is introduced.

## PostgreSQL Compatibility

The future selector must return the existing
`emit_postgres_sql(ScriptIR) -> SqlResult` function for `postgres`.

It must not:

- wrap, replace, or rewrite the PostgreSQL emitter;
- route PostgreSQL through MySQL code or shared rendering code;
- change PostgreSQL SQL bytes, diagnostics, artifact ordering, or metadata
  behavior;
- change `"public.users"` opaque-name rendering;
- change `pietto.sql.__all__`;
- add a dialect argument to `emit_postgres_sql`;
- route PostgreSQL through SQLGlot.

All five reviewed PostgreSQL SQL golden files remain byte-exact gates.

## Security And Extensibility Boundary

Dispatch is a closed compile-time policy, not an extension mechanism.

The implementation must not use:

- `importlib` or user-controlled module names;
- package entry points or plugin discovery;
- `eval` or `exec`;
- environment-variable backend loading;
- filesystem or network discovery;
- project configuration to name executable code;
- fallback to a generic SQL dialect.

This prevents a user-supplied dialect string from becoming an import path or
execution primitive. New dialects require code review, tests, documentation,
and an explicit release.

Dispatch adds no SQL execution, database connection, connector runtime,
schema introspection, credentials, destination control, runtime server,
project mode, watch mode, LSP, or Web UI.

## Implementation Sequence

This design does not authorize dispatch implementation now.

1. Slice 4 implements and directly tests a private MySQL backend skeleton.
2. Slice 5 adds the static semantic `mysql.table(Text)` surface.
3. Slice 6 completes the closed handwritten MySQL rendering MVP.
4. Slice 7 locks reviewed MySQL output and PostgreSQL regression behavior.
5. Slice 8 adds the private selector branch and enables `mysql` in text and
   JSON CLI admission together.

Until Slice 8, current PostgreSQL dispatch remains direct and unchanged.

## Static Audit Requirements

Before Slice 8, repository audits must continue proving:

- text CLI choices contain only `postgres`;
- JSON rejects `mysql` as `unsupported_dialect` before parsing;
- `emit_mysql_sql` remains private until a separate public API decision;
- `mysql.table` is absent until its own slice;
- no generic `emit_sql(...)` exists;
- current public SQL exports are unchanged;
- SQLGlot is absent from production dependencies and source;
- PostgreSQL golden hashes are unchanged;
- grammar and generated ANTLR files are unchanged.

Slice 8 must add focused tests for:

- both enabled dialects selecting exactly one dedicated emitter;
- text and JSON paths using the same enabled set;
- unknown values stopping before parsing;
- the selected emitter receiving only `ScriptIR`;
- backend diagnostics retaining exit `1`;
- unknown dialects retaining exit `2`;
- output-file and presentation ownership remaining in the CLI;
- no header or connector inference.

## Explicit Non-Goals

Slice 3 does not implement:

- a dispatcher or backend registry;
- `emit_mysql_sql`;
- `mysql.table`;
- `--dialect mysql`;
- public SQL exports;
- a generic public emitter;
- CLI or JSON behavior changes;
- semantic or IR behavior changes;
- PostgreSQL changes;
- SQLGlot or another dependency;
- grammar or generated ANTLR changes;
- JSON v2 or project mode;
- SQL execution, database access, connector runtime, or schema introspection;
- watch mode, LSP/editor integration, Web UI, or runtime services.
