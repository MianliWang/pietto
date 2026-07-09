# Maintenance Phase 3 CI Pytest Parallelization Contract v1

## Purpose

This contract defines the Maintenance Phase 3 Slice 6 conservative CI opt-in
to pytest multiprocessing through existing `scripts/validate.py` worker flags.

This is developer validation infrastructure. It is not a Pietto language
feature, public API feature, JSON feature, SQL feature, compiler feature,
runtime feature, or database feature.

## CI Command Contract

The GitHub Actions authoritative validation command is:

```bash
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

This command uses existing Slice 3 and Slice 4 `scripts/validate.py` flags. It
does not change local default behavior. Running `uv run python
scripts/validate.py` without worker flags remains serial.

## Serial Post-Validate Preservation

These workflow steps remain separate serial post-validate checks:

```bash
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
```

Generated checks, golden checks, package smoke, hash/private-surface checks, and
dirty-path checks are not folded into pytest-xdist and are not parallelized by
Slice 6.

## Matrix And Job Topology

Slice 6 keeps the Python 3.12 / 3.13 matrix.

Slice 6 keeps a single validation job per matrix entry. No job-level CI split
is introduced in Slice 6. Job-level split remains deferred.

## Cache Decision

Slice 6 keeps setup-uv `enable-cache: false`.

Slice 6 keeps the existing runner-temp environment configuration:

```text
UV_PROJECT_ENVIRONMENT=$RUNNER_TEMP/pietto-venv
UV_CACHE_DIR=$RUNNER_TEMP/uv-cache
```

Cache changes remain audit-driven and deferred.

## Safety And Fallback

Local serial default remains unchanged. Serial fallback remains available
through:

```bash
uv run python scripts/validate.py --pytest-workers off
```

`--pytest-maxprocesses 4` is the conservative CI worker cap.

`--pytest-dist loadfile` is the first approved CI distribution mode.

Timing output from `--timings` is developer validation evidence only and is not
a public output contract.

## Non-goals

Slice 6 does not change `scripts/validate.py`.

Slice 6 does not change `pyproject.toml` or `uv.lock`.

Slice 6 does not add dependencies.

Slice 6 does not add global pytest addopts.

Slice 6 does not parallelize generated checks, golden checks, package smoke,
hash/private-surface tests, dirty-path checks, package builds, temporary venvs,
or installed CLI smoke tests.

Slice 6 does not move package smoke.

Slice 6 does not change source/compiler behavior, parser, grammar, generated
files, fixtures, goldens, Public JSON, IR, SQL, CLI compiler behavior, Project
JSON serializer, public semantic API, runtime behavior, or database behavior.

Slice 6 does not change package version `0.1.0` and does not perform release,
tag, publish, upload, signing, or attestation operations.
