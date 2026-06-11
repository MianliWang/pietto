# Phase 5: CLI and Developer Tooling Plan

## Status

**Phase 5 CLI MVP: Complete.**

The initial scaffold provides the `pietto` console entry point, plain
`argparse` help, package version output, and stable usage exit codes. The
single-file `check` command now reads one Pietto file, parses it, runs semantic
analysis, renders ordered diagnostics, and returns a status based on ERROR
diagnostics.

## Public CLI

The current public surface is:

```bash
pietto --help
pietto --version
pietto check file.pietto
pietto emit-sql file.pietto --dialect postgres
pietto emit-sql file.pietto --dialect postgres --output out.sql
```

The console script calls:

```python
def main(argv: Sequence[str] | None = None) -> int:
    ...
```

The version comes from installed package metadata with a `0.1.0` fallback for
source-tree environments without metadata.

`check` reports diagnostics as:

```text
path:line:column CODE severity: message
```

Diagnostics preserve compiler order and always go to stderr. The current
`Diagnostic` model always contains line and column coordinates; when its path
is absent, the CLI uses the checked file path.

It returns `0` when no ERROR diagnostics exist, `1` for parser or semantic
ERROR diagnostics, and `2` for usage or file-reading errors. A successful
check prints `OK: path`. It does not build Semantic IR or emit SQL.

`emit-sql` explicitly runs parse, semantic analysis, IR construction, and the
PostgreSQL backend. It writes ordered SQL artifact text to stdout, separated by
one blank line, and writes every phase's diagnostics to stderr. Parser,
semantic, IR, or backend ERROR diagnostics return `1`; usage, unsupported
dialect, and file errors return `2`. PostgreSQL is the only supported dialect.
By default artifacts go to stdout. `--output path` overwrites one file with the
same ordered, blank-line-separated artifact text and leaves stdout empty.
Regular output files are replaced only after a complete same-directory
temporary write. The input file cannot also be the output, and symbolic-link
output paths are rejected without following them. Diagnostics remain on
stderr. Missing parent directories and file write errors return `2`; the CLI
does not create project output directories.

Diagnostic and CLI error records remain plain text. C0 control characters and
DEL in user-controlled paths or diagnostic text are rendered as visible
escapes such as `\n`, `\t`, `\x00`, and `\x1b`, so one compiler record cannot
forge additional terminal or CI log lines.

## Planned Slices

1. CLI scaffold: complete.
2. Single-file `check` command using parser and semantic APIs: complete.
3. Stable plain-text diagnostic rendering: complete.
4. Single-file `emit-sql --dialect postgres` command: complete.
5. File and output handling hardening: complete.
6. Phase 5 completion audit: complete.

Each command will explicitly orchestrate existing phase-specific APIs. Phase 5
will not add `compile_to_ir()`, `compile_to_sql()`, or another public compiler
convenience wrapper.

## Non-Goals

The Phase 5 MVP does not include database or SQL execution, connector runtime,
schema introspection, project configuration, multi-file analysis, watch mode,
JSON output, color output, source snippets, LSP/editor integration, a web UI,
new grammar syntax, or advanced SQL generation. The CLI emits SQL text only.
It does not connect to PostgreSQL, execute SQL or connectors, inspect schemas,
or add `compile_to_ir()`, `compile_to_sql()`, or another compiler convenience
wrapper.

The completion audit covers the public commands, exit codes, stdout/stderr
routing, output-file behavior, all committed examples under `check`, supported
SQL-emitting examples, compiler-stage isolation, legacy diagnostic codes, and
the absence of runtime or database behavior.
