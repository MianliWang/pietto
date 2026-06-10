# Phase 7 Resource / Depth Budget Design

## Status

**Design complete; implementation deferred to Phase 7 Slice 5.**

This document defines Pietto's deterministic resource-budget direction. It
does not add limits, diagnostics, tests, configuration, or runtime behavior.

## Motivation

Phase 5.5 contained known Python recursion failures at the public parser and
semantic API boundaries. Excessively long numeric literals also produce
ordinary parser diagnostics instead of uncaught conversion exceptions.

Those protections prevent specific crashes, but they are not a general
resource model. Before Pietto grows project-level, runtime, database-facing,
watch, or editor surfaces, the single-file compiler needs deterministic and
testable limits that fail through its existing diagnostic contracts.

The first implementation should be deliberately small. Source-size and token
budgets can reject disproportionately expensive inputs early without changing
the language grammar, semantic model, IR, SQL backend, JSON schema, or CLI
surface.

## Current Baseline

Current protections include:

- numeric literals are limited to 4096 characters before Python numeric
  conversion;
- `parse_source()` catches `RecursionError` and returns a parser diagnostic;
- `analyze()` catches `RecursionError` and returns `PIE-S2006`;
- semantic alias, relation, and field-derive cycles receive diagnostics;
- CLI output paths reject same-file, hard-link, and symbolic-link targets;
- output writes are atomic and compiler errors do not write SQL files;
- JSON schema version 1 provides structured diagnostics, stable exit-code
  relationships, one-document stdout, and handled-error stream separation;
- there is no SQL, connector, database, schema, network, or runtime execution
  surface.

Current gaps include:

- no global UTF-8 source byte limit;
- no lexer token-count limit;
- no AST node-count limit;
- no expression-depth budget independent of Python recursion;
- no explicit type-alias expansion depth;
- no relation dependency traversal budget;
- no semantic graph size or traversal-work budget;
- no diagnostic-count cap;
- no SQL artifact-size limit;
- no JSON output-size limit;
- no wall-clock timeout policy;
- no CPU or memory sandbox.

The absence of these controls does not currently expose a remote service, but
it matters before accepting untrusted batch inputs or adding broader
integration surfaces.

## Budget Categories

### Source UTF-8 Bytes

This budget limits the UTF-8 encoded size of one source file or one
`parse_source()` input. It should be checked before constructing the ANTLR
`InputStream` where practical.

The same byte unit must apply to the public string and file APIs:

- `parse_source()` measures the input string's UTF-8 encoded byte length;
- `parse_file()` reads at most the limit plus one byte in binary mode, rejects
  an over-limit file before decoding, and decodes UTF-8 only after it is known
  to fit.

This avoids using Unicode code-point count for one API and encoded byte count
for another. Ordinary file `OSError` and in-budget UTF-8 decoding failures
remain file-read failures rather than resource diagnostics.

### Lexer Tokens

This budget counts every raw non-EOF token emitted by the Pietto lexer,
regardless of token channel. EOF is excluded. Synthetic `INDENT` and `DEDENT`
tokens are not counted because the limit is enforced before indentation
injection.

Token collection must stop as soon as the first token beyond the limit is
emitted. Pietto must not materialize the remainder of the token stream and then
check its length.

### AST Nodes

A future AST budget could bound the number of nodes constructed by
`AstBuilder`. It requires an agreed node-count definition covering
definitions, type expressions, relation clauses, projections, and expression
nodes. It is not part of Slice 5.

### Expression Depth

A future structural expression-depth budget should count language nesting
rather than depend on Python's interpreter recursion limit. Unary chains,
binary trees, call nesting, and grouped expressions require explicit and
consistent depth rules. Slice 5 retains existing recursion containment and
does not add this budget.

### Type Alias Expansion

Cycle detection already rejects alias cycles, but a long acyclic alias chain
can still consume traversal depth. A future budget should distinguish:

- graph size;
- maximum acyclic expansion depth;
- repeated expansion work.

No alias-depth implementation is included in Slice 5.

### Relation Dependency Traversal

Relation cycles are diagnosed, but large acyclic dependency graphs can still
require substantial traversal. A future budget should cover graph vertices,
edges, maximum dependency depth, and repeated schema-propagation work.

### Semantic Graph Size And Work

A future semantic budget may include definition count, fields per shape,
projection count, callable count, graph edges, and total traversal steps.
These measures should be deterministic and independent of wall-clock timing.

### SQL Artifact Size

Generated SQL artifact count and total encoded byte size may need limits before
larger language features or service integrations exist. Current SQL generation
is local and limited, so Slice 5 does not add an artifact limit.

### Diagnostic Count

Malformed input may produce many diagnostics even within source and token
limits. A future cap needs truncation semantics and a stable indication that
additional diagnostics were omitted. That would affect observable output and
requires a separate design.

### JSON Output Size

JSON output includes diagnostic messages and SQL artifact text. A future output
budget must preserve valid single-document JSON and must not truncate encoded
JSON arbitrarily. No JSON size limit or schema change is part of Slice 5.

### Optional Wall-Clock Policy

A service or batch runtime may eventually need cancellation or wall-clock
deadlines. Such a policy is environment-dependent, nondeterministic, and
separate from compiler structural budgets. It requires a runtime threat model
and is not a Phase 7 Slice 5 feature.

## Slice 5 Implementation Subset

Slice 5 should implement exactly two deterministic limits:

| Budget | Limit | Accepted boundary | Rejected boundary |
|---|---:|---:|---:|
| UTF-8 source size | 1 MiB (`1,048,576` bytes) | `<= 1,048,576` bytes | `>= 1,048,577` bytes |
| Raw lexer tokens | `200,000` non-EOF tokens | `<= 200,000` tokens | the `200,001`st token |

The implementation should use private module constants, for example:

```text
_MAX_SOURCE_UTF8_BYTES = 1_048_576
_MAX_NON_EOF_TOKENS = 200_000
```

Slice 5 must not add:

- CLI flags;
- environment-variable overrides;
- project or user configuration;
- `pietto.toml` interaction;
- public budget objects or APIs;
- dependencies.

These fixed limits establish one reproducible compiler baseline. Configurable
policy can be considered only after project configuration and trust boundaries
have separate accepted designs.

## Diagnostic Design

Slice 5 should add two parser diagnostics:

| Code | Severity | Meaning |
|---|---|---|
| `PIE-P1006` | error | UTF-8 source byte budget exceeded |
| `PIE-P1007` | error | Raw non-EOF lexer token budget exceeded |

Suggested stable messages are:

```text
Source exceeds the maximum supported size of 1048576 UTF-8 bytes.
Token count exceeds the maximum supported limit of 200000 non-EOF tokens.
```

All documentation, implementation, and tests must use the complete
`PIE-`-prefixed code. Resource failures are compiler diagnostics, not
`cli_errors`, and must not receive an invented CLI error kind.

For source-size failure, use a whole-source anchor at line 1, column 1, with
the supplied path when available and no fabricated end coordinates. For token
failure, use the line and one-based column of the first token beyond the
limit. Both results contain no AST.

Each hard budget failure should return its one budget diagnostic rather than a
partial collection of lexer/parser diagnostics. This keeps the failure
deterministic and prevents incomplete parsing details from obscuring the
containment reason. A future diagnostic-count design can address broader
diagnostic accumulation.

Expected externally visible behavior:

- no Python traceback or internal exception text;
- text mode renders the normal diagnostic record;
- JSON mode places the diagnostic in `diagnostics`, leaves `cli_errors` empty,
  and preserves schema version 1;
- `ok` is `false`;
- process exit code is `1`.

## API Behavior

### `parse_source()`

`parse_source()` should check the UTF-8 byte budget before creating the ANTLR
`InputStream`. An over-limit input returns `ParseResult(ast=None, ...)` with
`PIE-P1006`. The private counter should process bounded string chunks and stop
as soon as the limit is exceeded rather than retaining a second complete
encoded copy.

For in-budget input, lexer token collection enforces the non-EOF token limit.
The first over-limit token stops collection and produces `PIE-P1007` before
indentation injection, parser creation, or AST construction.

### `parse_file()`

`parse_file()` should preserve its existing public return type and file-error
behavior. It should:

1. open the input in binary mode;
2. read at most `1,048,577` bytes;
3. return `PIE-P1006` if the extra byte is present;
4. decode UTF-8 only when the byte budget passes;
5. continue through the same parser path and token budget as `parse_source()`.

An oversized readable file is therefore a parser/compiler error. A missing,
unreadable, or in-budget invalid UTF-8 file remains a file-read error handled
by the CLI with exit code `2`.

Source-size precedence is deterministic: if both source and token budgets
would be exceeded, `PIE-P1006` wins because tokenization never begins.

## CLI Behavior

### `check`

Text mode should:

- print no success text;
- render the parser budget diagnostic on stderr;
- return exit code `1`;
- stop before semantic analysis.

JSON mode should:

- emit exactly one JSON document plus its existing trailing newline on stdout;
- leave stderr empty;
- keep the current `check` top-level fields unchanged;
- include the parser diagnostic in `diagnostics`;
- leave `cli_errors` empty;
- set `ok` to `false`;
- return exit code `1`.

### `emit-sql`

Text and JSON modes should stop before semantic analysis, IR construction, and
the SQL backend. No SQL artifact is generated or printed.

When `--output` is present and the output path itself is valid:

- a parser budget failure must not create the output file;
- an existing output file must not be truncated or replaced;
- JSON reports `output.written: false`;
- JSON `artifacts` is empty;
- the process exits with `1`.

Current CLI ordering remains unchanged. Output-path validation and command
argument validation occur before source compilation, so an invalid output path
or unsupported dialect continues to produce its existing exit code `2` result
even if the source would also exceed a parser budget.

## JSON Compatibility

Slice 5 must use the existing JSON v1 diagnostic path. It must not add budget
fields, counters, limit metadata, CLI error kinds, or top-level keys.

The existing guarantees remain:

- one JSON document on stdout;
- one trailing newline;
- stderr empty for handled JSON results;
- `json.dumps(..., ensure_ascii=True)`;
- no plain-text presentation escaping inside structured JSON values.

Adding `PIE-P1006` and `PIE-P1007` to the diagnostic catalog does not change
the JSON schema because `code` is already a diagnostic string field.

## Security Boundaries

The source and token limits are an early deterministic containment layer. They:

- bound source bytes read or accepted by the parser facade;
- bound raw tokens retained before parser construction;
- reduce exposure to oversized single-file input;
- provide stable, testable failure behavior.

They do not:

- provide complete denial-of-service protection;
- replace parser or semantic recursion containment;
- bound AST nodes, expression depth, semantic graph work, diagnostics, SQL
  artifacts, or JSON output size;
- impose CPU or wall-clock deadlines;
- sandbox process memory;
- make future runtime, SQL execution, database, connector, schema, network, or
  Web behavior safe.

Any future runtime, database connection, connector execution, or schema
introspection capability still requires a separate threat model.

## Slice 5 Test Plan

Slice 5 should add small, generated test inputs rather than committing
megabyte-scale fixtures.

Parser API tests:

- `parse_source()` accepts exactly the byte limit and rejects one byte over;
- multi-byte Unicode input is measured in UTF-8 bytes rather than code points;
- `parse_file()` uses the same byte boundary and returns `PIE-P1006`;
- many small tokens within the source budget trigger `PIE-P1007` at the first
  token over the limit;
- the token diagnostic points to the first over-limit token;
- no traceback or internal control-flow exception leaks.

CLI tests:

- `check` text mode returns `1` and renders the error diagnostic;
- `check --format json` preserves the JSON v1 shape, has `ok: false`, has empty
  `cli_errors`, and returns `1`;
- `emit-sql` stops before semantic, IR, and SQL stages;
- `emit-sql --format json` has empty artifacts and preserves JSON v1;
- `emit-sql --output` does not create a new output;
- `emit-sql --output` preserves an existing output byte-for-byte;
- JSON output status is `written: false`;
- text and JSON paths contain no traceback;
- diagnostic codes and severity are exact;
- the old bare diagnostic-code scan remains clean.

Tests should generate boundary strings and files in `tmp_path`. They should
avoid adding large repository fixtures and should monkeypatch later compiler
stages where useful to prove short-circuiting.

## Slice 5 Non-Goals

Slice 5 must not implement:

- a complete structural depth budget;
- AST node counting;
- type-alias or relation traversal limits;
- semantic graph size or work budgets;
- diagnostic truncation or count caps;
- SQL artifact or JSON output size caps;
- wall-clock timeout or cancellation policy;
- CPU or memory sandboxing;
- fuzzing infrastructure;
- CLI flags, environment controls, or configuration;
- project or multi-file budgets;
- runtime, database, connector, schema, network, or Web budgets;
- recursive algorithm rewrites.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Limits reject legitimate large files | Start with conservative fixed limits, test exact boundaries, and gather real usage before considering configuration |
| API and CLI enforce different units | Centralize private constants and helper logic; define source size as UTF-8 bytes everywhere |
| The check happens after expensive work | Check file bytes before decoding and string bytes before ANTLR; stop token collection at the first excess token |
| Tests add large or slow repository fixtures | Generate inputs in tests and keep committed fixtures small |
| Configuration or environment knobs appear prematurely | Keep limits private and fixed in Slice 5 |
| Partial diagnostics make failures unstable | Return one deterministic budget diagnostic |
| JSON v1 changes accidentally | Reuse existing diagnostic serialization and assert the exact current top-level shape |
| Resource limits are presented as complete protection | Document the unbounded categories and retain separate runtime/database threat-model requirements |
| Diagnostic codes lose their canonical prefix | Use `PIE-P1006` and `PIE-P1007` everywhere and retain the repository scan |

## Acceptance Boundary For Slice 5

Slice 5 is complete only when the two fixed parser budgets behave consistently
through the parser APIs and all current CLI presentations, short-circuit later
compiler stages, preserve output files, and pass focused boundary tests.

Completion must not be described as a complete resource/depth budget or
complete denial-of-service protection.
