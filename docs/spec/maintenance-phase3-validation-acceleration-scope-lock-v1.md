# Maintenance Phase 3 Validation Acceleration Scope Lock v1

## Purpose

This specification locks validation acceleration scope before code, workflow,
dependency, package, or release changes.

Maintenance Phase 3 is Validation Pipeline Performance & Workflow Acceleration.
Slice 2 is Acceleration Scope Lock & Validation Profile Contract. Slice 2 is
docs/spec/tests-only and exists to define contracts for later acceleration
work without implementing them.

Ordering contract: add `--timings` before pytest worker flags.

## Audit Facts

The Slice 1 read-only runtime audit established these facts:

- `ruff format --check .`: about `0.05s`;
- `ruff check .`: about `0.13s`;
- production `pyright`: about `3.73s`;
- test `pyright`: about `10.32s test pyright`;
- full pytest: `5190 passed`, about `25.93s` wall-clock /
  `26.38s` pytest runtime;
- `scripts/check_generated.py`: about `0.68s`;
- `scripts/check_goldens.py`: about `0.06s`;
- `scripts/package_smoke.py`: package smoke network/cache-sensitive and about
  `10.33s` with network;
- `scripts/validate.py`: about `37.15s`;
- CI wall time: about `88s CI wall time`;
- CI authoritative validation: about `65-70s CI authoritative validation`;
- `pytest-xdist` is absent;
- generated, golden, hash/private-surface, dirty-path guard, and package
  smoke checks carry serial or clean-tree risk.

## Profile Contract

### A. focused-dirty

`focused-dirty` is for dirty Gate 2 slice work.

It requires:

- an exact approved allowlist;
- targeted tests/static audits only;
- `git diff --check`;
- Ruff format/check on touched tests when applicable;
- `uv run pyright --project pyrightconfig.tests.json` when tests change;
- focused pytest for the slice test;
- dirty paths limited to clean tree or the exact approved allowlist.

It excludes:

- unrelated dirty-path guards;
- full `scripts/validate.py`;
- full pytest;
- generated checks;
- golden checks;
- package smoke;
- CI;
- release operations unless explicitly approved.

### B. local-fast

`local-fast` is the future developer acceleration profile.

Serial default is preserved, and serial fallback must remain available. Add
`--timings` before pytest worker flags. Pytest worker flags are future work and
must remain opt-in through `scripts/validate.py`.

`local-fast` must not use global pytest addopts and must not set global pytest
addopts for `-n auto`. The preferred first xdist strategy is
`--dist=loadfile`.

### C. full-release

`full-release` is the authoritative validation profile.

It includes:

- `scripts/validate.py`;
- `scripts/check_generated.py`;
- `scripts/check_goldens.py`;
- `scripts/package_smoke.py`;
- natural CI after Gate 3 publish.

`full-release` may use an approved accelerated validate path only after later
implementation and proof. Serial fallback must remain available.

## Implementation Ordering

Later Maintenance Phase 3 work should proceed in this order:

1. Slice 3 adds `--timings`.
2. Slice 4 adds `pytest-xdist` and worker flags.
3. Slice 5 repairs parallel safety risks.
4. Slice 6 opts CI into capped parallel pytest.
5. Slice 7 optimizes other tools only from timing evidence.

`--timings` comes before pytest worker flags. The initial CI cap should be
4 workers once CI parallelization is implemented, unless later timing evidence
changes that contract.

## Serial-only Initial Checks

The following checks remain serial initially:

- `scripts/check_generated.py`;
- `scripts/check_goldens.py`;
- hash/private-surface tests;
- dirty-path guards;
- `scripts/package_smoke.py`.

Package smoke is network/cache-sensitive and remains serial initially.

## CI Policy

No job-level CI split is part of the first CI acceleration slice. First CI
parallelization should use `scripts/validate.py` worker flags once implemented.
The initial CI worker cap is 4 workers unless later evidence changes it.

uv cache changes should be audit-driven, not assumed. CI acceleration must not
change release, tag, publish, upload, signing, or attestation behavior.

## Non-goals

Slice 2 does not change:

- `scripts/validate.py`;
- `pyproject.toml` or `uv.lock`;
- dependencies, including no `pytest-xdist` addition;
- `.github/workflows/ci.yml`;
- source/compiler/public behavior;
- parser, grammar, generated files, Project JSON serializer, public JSON
  shape, public semantic API, IR, SQL, or CLI behavior;
- workflows, fixtures, goldens, runtime behavior, package metadata, lockfile,
  validation scripts, README.md, AGENTS.md, global roadmap files, or release
  files;
- package version, release, package, tag, signing, or attestation behavior.

Slice 2 does not implement `--timings`, pytest worker flags, xdist, CI
acceleration, job-level CI split, uv cache policy changes, package smoke
parallelism, generated/golden parallelism, or release operations.
