# Phase 5: CLI and Developer Tooling Plan

## Status

**Phase 5 single-file check command: Complete.**

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
pietto check file.pie
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

It returns `0` when no ERROR diagnostics exist, `1` for parser or semantic
ERROR diagnostics, and `2` for usage or file-reading errors. A successful
check prints `OK: path`. It does not build Semantic IR or emit SQL.

## Planned Slices

1. CLI scaffold: complete.
2. Single-file `check` command using parser and semantic APIs: complete.
3. Stable plain-text diagnostic rendering.
4. Single-file `emit-sql --dialect postgres` command.
5. File and output handling hardening.
6. Phase 5 completion audit.

Each command will explicitly orchestrate existing phase-specific APIs. Phase 5
will not add `compile_to_ir()`, `compile_to_sql()`, or another public compiler
convenience wrapper.

## Non-Goals

The Phase 5 MVP does not include database or SQL execution, connector runtime,
schema introspection, project configuration, multi-file analysis, watch mode,
JSON output, LSP/editor integration, a web UI, new grammar syntax, or advanced
SQL generation. The `emit-sql` command is not implemented yet.
