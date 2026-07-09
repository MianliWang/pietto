# Maintenance Phase 3 Validation Timings Contract v1

## Status

Maintenance Phase 3 Slice 3 adds optional validation timing observability before
any pytest worker flags, dependency changes, or CI acceleration work.

This contract is developer workflow documentation only. Timing output is not a
Pietto language feature, public API, JSON schema, SQL surface, compiler
artifact, runtime behavior, or package release surface.

## Purpose

`scripts/validate.py --timings` records elapsed time for the existing
authoritative local validation gates. The goal is to make later acceleration
decisions evidence-driven while preserving deterministic serial validation and
the serial debug fallback.

`--timings` must precede worker flags in the Maintenance Phase 3 route. Slice 4
may add opt-in pytest worker flags only after Slice 3 timing output exists and
the worker contract is separately approved.

## Default Behavior Preservation

Running `uv run python scripts/validate.py` without `--timings` preserves the
existing validation semantics:

- the same `GATES` order;
- the same pre-gate status line:
  `[validate] {name}: {shlex.join(command)}`;
- no timing lines;
- serial execution;
- child process output attached to the parent streams;
- `subprocess.run(command, cwd=REPO_ROOT, check=False)`;
- fail-fast return of the first nonzero child exit code;
- `0` only after every gate succeeds.

The existing gates remain:

1. `lockfile`: `uv lock --check`
2. `format`: `uv run ruff format --check .`
3. `lint`: `uv run ruff check .`
4. `production typing`: `uv run pyright`
5. `test typing`: `uv run pyright --project pyrightconfig.tests.json`
6. `tests`: `uv run pytest`

## Timing Output Contract

`--timings` is optional. When passed, `scripts/validate.py` keeps the existing
pre-gate status line exactly and writes timing lines to stdout.

Per-gate timing line:

```text
[validate] {name} completed in {elapsed:.3f}s
```

Total timing line:

```text
[validate] total completed in {elapsed:.3f}s
```

Timing uses Python standard-library `time.perf_counter()`.

## Success Behavior

On success with `--timings`:

- each gate emits its existing pre-gate status line;
- each completed gate emits one per-gate timing line;
- after the final gate succeeds, the script emits one total timing line;
- the return code remains `0`.

## Failure And Fail-fast Behavior

On failure with `--timings`:

- gates before the failure emit their normal status and timing lines;
- the failed gate emits its normal status line;
- the failed gate emits its timing line before the script returns;
- the script emits one total timing line before returning;
- no later gates run;
- the return code remains the failed child command return code.

## Stdout And Stderr Policy

Validation status lines and timing lines are stdout developer workflow output.
Child command stdout and stderr remain attached to the parent process streams.
Argparse errors may use normal argparse stderr behavior and must not invoke any
validation gate.

## Non-goals

Slice 3 does not add:

- `--pytest-workers`;
- `--pytest-dist`;
- `--pytest-maxprocesses`;
- `pytest-xdist`;
- profile flags such as `local-fast`;
- global pytest addopts;
- dependency changes;
- `pyproject.toml` or `uv.lock` changes;
- `.github/workflows/ci.yml` changes;
- job-level CI split;
- generated, golden, or package smoke expansion;
- package version, tag, release, publish, upload, signing, or attestation
  behavior;
- source/compiler/parser/AST/semantic/IR/SQL/CLI public behavior changes.

## Future Relationship To Worker Flags

Future Slice 4 worker flags must be opt-in, must preserve serial fallback, and
must not reinterpret `--timings` as a worker-selection profile. Timing output is
observability only; it does not imply parallel execution.
