# Maintenance Phase 3 Developer Workflow v1

## Purpose

This specification records developer workflow guidance for completed
Maintenance Phase 3 validation features.

Slice name: Developer Workflow Docs.

This is developer workflow documentation only. It is not a Pietto language
feature, API feature, JSON feature, SQL feature, compiler feature, runtime
feature, or database feature.

## Validation Profiles

Maintenance Phase 3 developer workflow uses three profiles:

- `focused-dirty`;
- `local-fast`;
- `full-release`.

## focused-dirty Guidance

`focused-dirty` is for daily focused Gate 2 work in a dirty tree.

Use the exact approved Gate 2 allowlist. Run focused tests/static audits for
the current slice. Use `git diff --check`. Use new-file whitespace checks when
adding files. Use Ruff format/check on touched tests when applicable. Use test
Pyright when tests change.

Avoid unrelated dirty-path guard suites. Avoid full `scripts/validate.py` and
full pytest in dirty Gate 2 unless explicitly approved.

```bash
uv run pytest tests/test_current_slice.py
```

## Local Serial Fallback And Debug Workflow

Prefer focused serial pytest for initial diagnosis of failures/flakes. Use
serial fallback when debugging. Do not diagnose flakes first through broad
xdist. Use `--pytest-workers off` for explicit serial fallback.

```bash
uv run pytest tests/test_current_slice.py
uv run python scripts/validate.py --pytest-workers off --timings
uv run python scripts/validate.py --timings
```

## local-fast / Parallel Validation

Parallel validation is opt-in. Use `--timings` for observability. Prefer
`loadfile`. Use a maxprocess cap when needed. Keep serial fallback available.

```bash
uv run pytest -n auto --dist=loadfile
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

## full-release / Final Confidence

`full-release` validation includes `validate.py` plus
generated/golden/package-smoke checks and natural CI.

Generated/golden/package-smoke remain serial. Package smoke is not routine
dirty Gate 2 validation unless explicitly approved.

```bash
uv run python scripts/validate.py --timings
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
```

## CI Behavior

Current CI commands:

```bash
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
```

CI uses pytest worker flags only through `scripts/validate.py`. CI keeps
generated/golden/package-smoke as separate serial post-validate steps. No
job-level CI split yet. setup-uv cache policy remains unchanged. Local default
remains serial.

## Package Smoke Caveats

Package smoke is package/network/build-sensitive. It builds/installs in
temporary directories and validates installed CLI behavior.

Package smoke remains serial. It is not a release, publish, upload, signing,
or attestation operation. Do not use it as routine dirty Gate 2 validation
unless explicitly approved.

## When Not To Use Parallel Mode

Do not use parallel mode for:

- dirty-path guard suites outside the current allowlist;
- hash/private-surface locks unless reviewed for the dirty tree;
- generated/golden/package-smoke audit tests;
- package build, temporary venv, and installed CLI smoke tests;
- tests using fixed output paths, cwd/env mutation, subprocesses, shared
  caches, random, time.sleep, or broad repository scans unless reviewed;
- initial diagnosis of flakes/failures.

## Deferred Tuning

The following remain deferred:

- worker cap above 4;
- distribution mode change away from loadfile;
- Pyright/pytest concurrent execution;
- hidden concurrency inside `scripts/validate.py`;
- job-level CI split;
- generated/golden/package-smoke parallelization.

## Non-goals

Slice 8 makes:

- No `scripts/validate.py` change.
- No `.github/workflows/ci.yml` change.
- No `pyproject.toml` or `uv.lock` change.
- No dependency change.
- No global pytest addopts.
- No source/compiler/parser/grammar/generated/fixture/golden/package metadata
  change.
- No package version/release/tag/publish/upload/signing/attestation behavior.
