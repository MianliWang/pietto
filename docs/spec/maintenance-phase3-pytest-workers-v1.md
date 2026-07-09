# Maintenance Phase 3 Pytest Workers Contract v1

## Purpose

This contract defines the Maintenance Phase 3 Slice 4 adaptive pytest
multiprocessing surface.

The feature is a non-public developer workflow surface for `scripts/validate.py`.
It provides opt-in pytest multiprocessing after Slice 3 timing observability
while preserving serial validation as the default and as an explicit fallback.

## CLI Contract

`scripts/validate.py` accepts these pytest worker options:

- `--pytest-workers off`;
- `--pytest-workers auto`;
- `--pytest-workers logical`;
- `--pytest-workers <positive integer>`;
- `--pytest-dist loadfile`;
- `--pytest-dist loadscope`;
- `--pytest-maxprocesses <positive integer>`.

No worker flag means serial pytest and remains command-equivalent to:

```bash
uv run pytest
```

`--pytest-workers off` is an explicit serial fallback. It emits no `-n`, no
`--dist`, and no `--maxprocesses`.

Integer mode emits `-n <N>`. If `--pytest-maxprocesses <M>` is provided, the
worker count is capped to `min(N, M)`.

`auto` mode emits `-n auto`. If `--pytest-maxprocesses <M>` is provided, the
pytest-xdist max-process cap is passed as `--maxprocesses <M>`.

`logical` mode computes `max(os.cpu_count() or 1, 1)`, caps that value with
`--pytest-maxprocesses` when provided, and emits `-n <computed>`.

## Distribution Strategy

`--pytest-dist` supports `loadfile` and `loadscope`.

When workers are enabled and no distribution mode is supplied, the default
distribution mode is `loadfile`.

`--pytest-dist` is emitted only when workers are enabled. Supplying
`--pytest-dist` with default serial mode or `--pytest-workers off` is a parser
error before validation gates run.

## Maxprocesses Strategy

`--pytest-maxprocesses` is valid only when workers are enabled.

For integer workers and logical workers, the cap is applied before building the
pytest command. For auto workers, the cap is passed through to pytest-xdist as
`--maxprocesses <N>`.

Invalid worker values, zero or negative worker counts, arbitrary non-integer
worker strings, and invalid maxprocesses values fail before any validation
subprocess is invoked.

## Command Construction

`scripts/validate.py` keeps the non-pytest validation gates stable. Only the
tests gate command is resolved dynamically from parsed pytest worker options.

The default tests gate remains:

```bash
uv run pytest
```

Examples:

```bash
uv run pytest
uv run pytest -n 4 --dist=loadfile
uv run pytest -n 2 --dist=loadfile
uv run pytest -n auto --maxprocesses 4 --dist=loadfile
uv run pytest -n 4 --dist=loadfile
uv run pytest -n 2 --dist=loadscope
```

The command display line remains the resolved command printed with
`shlex.join()`. Fail-fast behavior, child output attachment,
`subprocess.run(command, cwd=REPO_ROOT, check=False)`, and return-code behavior
remain unchanged.

## Timings Composition

`--timings` is independent and composable with pytest worker modes. A developer
can run:

```bash
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

Timing output reports the same per-gate and total timing lines as Slice 3,
using the resolved pytest command for the tests gate.

## Dependency Policy

Slice 4 adds `pytest-xdist` only to the dev dependency group. It updates
`uv.lock` for that dev dependency and its transitive dependency.

Slice 4 does not add runtime dependencies and does not change package version
`0.1.0`.

## Non-goals

Slice 4 does not add global pytest addopts.

Slice 4 does not change `.github/workflows/ci.yml`. CI opt-in pytest
parallelization remains deferred to Slice 6.

Slice 4 does not parallelize generated checks, golden checks, package smoke,
hash/private-surface tests, or dirty-path checks. Generated, golden,
hash/private-surface, dirty-path, and package-smoke checks remain serial
initially.

Slice 4 does not change source/compiler behavior, parser, grammar, generated
files, Project JSON, public JSON shape, public semantic API, IR, SQL, fixtures,
goldens, package smoke, README.md, AGENTS.md, release files, package
publication, uploads, signing, or attestations.

## Future Relationship

Slice 5 is reserved for parallel safety audit and repairs.

Slice 6 is reserved for opt-in CI pytest parallelization using the worker flags
introduced here. The workflow remains serial until that later slice is
explicitly approved.
