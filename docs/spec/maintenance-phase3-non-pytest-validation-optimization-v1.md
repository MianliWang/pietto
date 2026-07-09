# Maintenance Phase 3 Non-Pytest Validation Optimization Contract v1

## Purpose

This contract locks Maintenance Phase 3 Slice 7 non-pytest validation
optimization decisions after Slice 6 CI timing evidence.

This is developer validation infrastructure. It is not a Pietto language
feature, public API feature, JSON feature, SQL feature, compiler feature,
runtime feature, or database feature.

## Evidence Source

Slice 7 uses natural CI run `29009063082`.

That run was the natural CI run for commit
`41a3ec38ddc30fbdcb3348253c976e36dc7be7b9`.

The run completed successfully, and the run `headSha` matched the commit.

## Timing Summary

The timing evidence from run `29009063082` is:

- Python 3.12 job duration: about `116s`;
- Python 3.13 job duration: about `97s`;
- Python 3.12 authoritative validation step duration: about `92s`;
- Python 3.13 authoritative validation step duration: about `75s`;
- Python 3.12 lockfile: `0.011s`;
- Python 3.12 format: `0.192s`;
- Python 3.12 lint: `0.147s`;
- Python 3.12 production typing: `10.826s`;
- Python 3.12 test typing: `15.380s`;
- Python 3.12 tests: `65.534s`;
- Python 3.12 total: `92.091s`;
- Python 3.13 lockfile: `0.015s`;
- Python 3.13 format: `0.220s`;
- Python 3.13 lint: `0.128s`;
- Python 3.13 production typing: `9.116s`;
- Python 3.13 test typing: `15.136s`;
- Python 3.13 tests: `50.362s`;
- Python 3.13 total: `74.977s`;
- generated check: around `1s` per matrix job;
- golden check: sub-second to about `1s` per matrix job;
- package smoke: about `8s` on Python 3.12 and about `6s` on Python 3.13.

## Decision: Ruff Unchanged

ruff remains unchanged because ruff format/check remain negligible.

Slice 7 makes no ruff workflow, script, dependency, lockfile, or config change.

## Decision: Pyright Unchanged

pyright remains unchanged for now.

Pyright is a meaningful non-pytest cost, about `24-26s` combined in the CI
`scripts/validate.py` run. Slice 7 records that cost but does not change
pyright config, split pyright into another job, or change type-checking
workflow topology.

Any pyright split remains deferred to a future explicit slice.

## Decision: Generated/Golden Unchanged

generated/golden remain serial and unchanged.

Generated and golden checks remain cheap and deterministic. Slice 7 keeps them
serial and makes no script or workflow change.

## Decision: Package Smoke Unchanged

package smoke remains serial and unchanged.

Package smoke is about `6-8s` in this CI run and remains
package/network/build-sensitive. Slice 7 does not parallelize, skip, weaken, or
move package smoke, and does not change `scripts/package_smoke.py`.

## Decision: Cache Unchanged

setup-uv cache policy remains unchanged.

The workflow keeps setup-uv `enable-cache: false`, and keeps runner-temp
`UV_PROJECT_ENVIRONMENT` and `UV_CACHE_DIR` configuration. Cache changes remain
audit-driven and deferred.

## Decision: Job-Level Split Deferred

job-level CI split remains deferred.

Slice 7 adds no job-level CI split and leaves the existing workflow topology
unchanged.

## Decision: More Aggressive Pytest Worker Tuning Deferred

more aggressive pytest worker tuning remains deferred.

The current CI pytest worker strategy remains:

```bash
--pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

Slice 7 does not raise `--pytest-maxprocesses` above 4, does not change away
from `--dist=loadfile`, and does not switch to a more aggressive distribution
strategy.

Any future change to worker cap, distribution strategy, or broader pytest
partitioning must be benchmark-driven and separately approved. More aggressive
pytest worker tuning should use multiple CI timing samples or a dedicated
worker-strategy benchmark, not a single run.

## Decision: Pyright/Pytest Concurrent Execution Deferred

Pyright/pytest concurrent execution remains deferred.

Slice 7 does not run Pyright and pytest concurrently, does not add hidden
concurrency inside `scripts/validate.py`, and does not change
`scripts/validate.py` fail-fast serial semantics.

Concurrent execution would complicate logs, change failure ordering, reduce
diagnosis clarity, and compete with pytest-xdist for CPU and memory. If
Pyright/pytest parallelism is considered later, prefer an explicitly approved
CI job-level split evaluation rather than hidden concurrency inside
`scripts/validate.py`.

hidden concurrency inside scripts/validate.py is rejected for now.

## Non-Goals

Slice 7 makes:

- No `.github/workflows/ci.yml` change.
- No `scripts/validate.py` change.
- No `scripts/check_generated.py` change.
- No `scripts/check_goldens.py` change.
- No `scripts/package_smoke.py` change.
- No `pyproject.toml` or `uv.lock` change.
- No dependency change.
- No package version, release, tag, publish, upload, signing, or attestation
  behavior.
- No source/compiler behavior, parser, grammar, generated files, fixtures,
  goldens, Public JSON, IR, SQL, CLI compiler behavior, Project JSON
  serializer, public semantic API, runtime behavior, or database behavior
  change.
- No full pytest, full `scripts/validate.py`, package build, generated check,
  golden check, package smoke, or timing benchmark command in Gate 2.

no behavior/workflow/script/dependency change in Slice 7.
