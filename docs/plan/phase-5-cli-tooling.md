# Phase 5: CLI and Developer Tooling Plan

## Status

**Phase 5 CLI scaffold: Complete.**

The initial scaffold provides the `pietto` console entry point, plain
`argparse` help, package version output, and stable usage exit codes. It does
not read Pietto files or invoke parser, semantic, IR, or SQL APIs.

## Public CLI

The current public surface is:

```bash
pietto --help
pietto --version
```

The console script calls:

```python
def main(argv: Sequence[str] | None = None) -> int:
    ...
```

The version comes from installed package metadata with a `0.1.0` fallback for
source-tree environments without metadata.

## Planned Slices

1. CLI scaffold: complete.
2. Single-file `check` command using parser and semantic APIs.
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
LSP/editor integration, a web UI, new grammar syntax, or advanced SQL
generation.
