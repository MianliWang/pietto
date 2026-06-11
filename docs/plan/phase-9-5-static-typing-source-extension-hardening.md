# Phase 9.5: Static Typing And Source Extension Hardening

## Status

**Phase 9.5 Static Typing And Source Extension Hardening is complete.**

Phase 9 is complete. Phase 9.5 establishes a blocking Pyright gate for
handwritten production source and makes `.pietto` the only official Pietto
source extension before any Phase 10 backend work.

## Goal

Strengthen repository maintainability without changing compiler behavior:

- run Pyright in standard mode over handwritten production source;
- isolate generated ANTLR artifacts and their inaccurate inferred types;
- fix real low-risk typing defects in handwritten code;
- migrate all active source files, fixtures, paths, documentation, and tests
  to the `.pietto` extension;
- preserve path-based CLI behavior for files with any suffix.

## Pyright Baseline And Boundary

The initial unconfigured `uvx pyright` run analyzed 114 files and reported:

- 818 errors and 131 warnings overall;
- 412 errors and 6 warnings in generated ANTLR files;
- 255 errors and 11 warnings in handwritten production source;
- 151 errors and 114 warnings in tests.

The blocking gate is intentionally limited to the 34 handwritten Python files
under `src/pietto`. Tests remain covered by Ruff and pytest and are not part of
the first blocking Pyright gate.

`pyrightconfig.json` uses standard mode, Python 3.12, the project virtual
environment, and `src` import resolution. It excludes
`src/pietto/generated` from the blocking file set and ignores diagnostics from
that same generated directory when imports pull it into the analysis closure.
It does not disable meaningful diagnostics globally.

Repository VS Code settings apply the same narrow
`src/pietto/generated/**` exclusion and diagnostic ignore to Pylance. This
keeps generated ANTLR noise out of the Problems view even when a generated
module is imported or opened, without lowering standard checking for
handwritten production source.

The ANTLR boundary remains local to `ast_builder.py`. Runtime code still
inherits from the generated visitor, while type checking sees only the dynamic
`visit` and `visitChildren` boundary. Generated parser contexts are treated as
dynamic only inside that adapter file. Pietto AST return types remain explicit
and checked.

## Typing Corrections

Phase 9.5 corrects:

- `ArgumentParser.error` overrides to return `NoReturn`;
- caught `SystemExit` normalization for `None`, integer, and message exit
  values;
- nullable lexer token results before token field access;
- the ANTLR `ListTokenSource` and `CommonTokenStream` annotation mismatch;
- generated visitor return and parser-context false positives at the AST
  boundary;
- generic immutable-mapping default inference;
- non-empty strongly connected component indexing;
- ANTLR error-listener parameter compatibility;
- future backend definition diagnostic access through a narrow protocol.

These changes preserve runtime behavior and public APIs.

## Source Extension Contract

`.pietto` is the only official Pietto source extension. All committed examples
and PostgreSQL source fixtures use it. Documentation, CLI examples, diagnostic
paths, project-planning globs, tests, and JSON golden paths use the same
extension.

The extension is a repository and documentation convention, not parser or CLI
syntax. The CLI continues to accept an explicit path and parse its contents
without validating the suffix.

## Security And Safety Review

The repository search found:

- no production `eval`, `exec`, subprocess, shell execution, or `os.system`;
- no broad production `except Exception`;
- one production temporary-file path, the existing guarded atomic SQL output
  writer;
- direct writes only in tests and the guarded CLI output path;
- SQL assembly confined to the existing PostgreSQL renderer, which routes
  identifiers and literals through dedicated quoting functions.

No security rewrite is required by this phase.

## Explicit Non-Goals

Phase 9.5 does not add or change:

- grammar, generated ANTLR files, or parser generation;
- language, parser, semantic, IR, SQL, CLI, JSON, or public API behavior;
- dependencies, `pyproject.toml`, or `uv.lock`;
- SQLGlot, MySQL, or a backend abstraction implementation;
- SQL execution, database access, connector runtime, or schema introspection;
- project or multi-file behavior, watch mode, LSP, or Web UI.

## Completion Result

Phase 9.5 is complete because:

- `uvx pyright` reports zero errors and warnings for handwritten production
  source;
- all committed Pietto examples and fixtures use `.pietto`;
- the repository contains no references to the former source suffix;
- path-based CLI behavior is covered with a non-`.pietto` temporary source;
- static extension and typing-boundary audits pass;
- generated ANTLR diagnostics are isolated in both Pyright and Pylance;
- the full formatting, linting, test, lockfile, dependency, diagnostic, and
  diff validation passes.

The completion run recorded:

- Ruff formatting and lint checks passed;
- `1,107` pytest tests passed;
- `uvx pyright` analyzed 34 handwritten production files with zero errors and
  zero warnings;
- `uv lock --check` resolved 19 locked packages successfully;
- `uv audit --locked` found no known vulnerabilities or adverse project
  statuses in 18 packages;
- the bare diagnostic-code and former-extension scans produced no output;
- `git diff --check` passed;
- no dependency, lockfile, grammar, or generated ANTLR file changed.

No Phase 10 implementation has started.
