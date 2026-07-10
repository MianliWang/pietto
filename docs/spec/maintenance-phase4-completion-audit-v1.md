# Maintenance Phase 4 Completion Audit / Status Lock v1

## Purpose

Maintenance Phase 4 is **Worker Strategy Benchmark & CI Split Evaluation**.
Slice 4 is **Completion Audit / Status Lock**, a docs/spec/tests-only
completion audit/status lock for Slices 1 through 3.

This is developer validation infrastructure documentation only. It is not a
Pietto language, API, JSON, SQL, compiler, runtime, or database feature.
Slice 4 changes no validation behavior and runs no benchmark.

## Conditional Completion

Maintenance Phase 4 is not complete during Gate 2. Slice 4 is not complete
during Gate 2. Gate 2 records only a conditional completion lock, and Slice 4
does not claim Gate 3 has already succeeded.

Phase 4 can be marked complete only after Slice 4 Gate 3 records:

- the final commit containing the exact Slice 4 allowlist;
- a normal push of that commit;
- successful natural CI finishing `completed / success`; and
- an exact headSha match between that natural CI run and the final commit.

If Gate 3 push or natural CI does not succeed, Phase 4 remains incomplete.
After successful Gate 3, Phase 4 is complete as a benchmark protocol,
controlled local evidence, and no-change decision phase only.

## Slice Inventory

The phase inventory is:

1. Slice 1: **Worker Strategy Benchmark Protocol**.
2. Slice 2: **Controlled Clean-local Benchmark Execution**.
3. Slice 3: **Benchmark Evidence Decision / No-change Lock**.
4. Slice 4: **Completion Audit / Status Lock**.

Slices 1 through 3 are complete. Slice 4 remains conditional on Gate 3.

## Slice 1 Baseline

Slice 1 delivered docs/spec/static-audit benchmark protocol only:

- commit `9bdf1aebce0dc5f7985c95f36bb0d20b0a996fb3`;
- subject `Add Maintenance Phase 4 worker benchmark protocol`;
- natural CI run `29054341393`;
- workflow/event `CI / push`;
- status/conclusion `completed / success`; and
- an exact headSha match between CI and the commit.

## Slice 2 Evidence

Slice 2 was evidence-only `/tmp` work and created no repository commit.
The durable reviewed facts are:

- `effective_cpu=20`;
- 7 configs;
- 7 warmups;
- 35 measured samples;
- 42 total runs;
- one warmup and five measured samples for every config;
- all direct-pytest safe-cohort rows exited 0 with `294 passed`;
- no failures, retries, hangs, worker crashes, or stop condition;
- fastest median `serial_control` at `1.568251s`;
- decision baseline `ci_auto_cap4_loadfile` at `1.714843s`;
- improvement `8.548%`, below the required `10%` median threshold;
- no row met threshold; and
- provisional candidate none.

## Slice 3 Baseline

Slice 3 delivered a docs/spec/tests-only no-change decision lock:

- commit `024b23a5a000cbedf0415880bf365173ad250db4`;
- subject `Add Phase 4 benchmark no-change decision`;
- natural CI run `29057920189`;
- workflow/event `CI / push`;
- status/conclusion `completed / success`;
- an exact headSha match between CI and the commit; and
- no final CI winner.

## Final No-change Decision

The Phase 4 evidence authorizes no implementation change:

- no CI change is authorized;
- no scripts/validate.py change is authorized;
- no wrapper change is authorized;
- no worker cap/default change is authorized;
- no distribution mode change is authorized;
- no cache policy change is authorized;
- no job-level CI split is authorized;
- no Pyright/pytest concurrency is authorized;
- no load/worksteal wrapper support is authorized;
- no dependency or lockfile change is authorized; and
- no final CI winner is selected.

## Preserved Current Behavior

The current CI command remains exactly:

```bash
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

The local default remains serial. CI remains
`auto/maxprocesses-4/loadfile`. The workflow remains one validation job
per Python 3.12/3.13 matrix entry. Generated, golden, and package-smoke checks
remain separate serial post-validate checks.

setup-uv remains `enable-cache: false`. Pyright and pytest remain
sequential inside fail-fast `scripts/validate.py`. pytest-xdist remains
dev-only, and there are no global pytest addopts.

`.github/workflows/ci.yml`, `scripts/validate.py`,
`pyproject.toml`, and `uv.lock` remain unchanged. There is no worker
cap/default/distribution change and no dependency/package/release behavior
change. The package version remains `0.1.0`.

## Future Work Boundary

The following work remains deferred:

- full-suite evaluation;
- wrapper-track evaluation;
- fresh-session/second-day repeat;
- hosted-CI evaluation;
- job-level CI split;
- Pyright/pytest concurrency; and
- load/worksteal wrapper support.

Each item requires separate approval. Phase 4 completion does not authorize
any of them.

## Release And Package Boundary

Slice 4 makes no package version bump. It includes no tag, no release, no
publish, no upload, no signing, and no attestation. The package version
remains `0.1.0`.

## Non-goals

Slice 4 performs no benchmark rerun, candidate pytest benchmark row, full
pytest, `scripts/validate.py` run, CI action, generated check, golden
check, package smoke, package build, dependency operation, or lockfile change.

Slice 4 adds no source/compiler/parser/grammar/generated, fixture/golden,
package, public, language, API, JSON, SQL, runtime, or database behavior
change. It changes neither `README.md` nor `AGENTS.md`. Gate 2
performs no commit, push, or manual CI action.
