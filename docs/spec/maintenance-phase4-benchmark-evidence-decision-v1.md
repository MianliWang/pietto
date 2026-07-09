# Maintenance Phase 4 Benchmark Evidence Decision v1

## Purpose

Maintenance Phase 4 Slice 3 is **Benchmark Evidence Decision / No-change
Lock**. This docs/spec/tests-only contract records the Slice 2 local
safe-cohort benchmark evidence and locks the resulting no-change decision.

This is developer validation infrastructure documentation only. It is not a
Pietto language, public API, CLI/JSON, SQL, compiler, runtime, or database
feature, and it changes no validation behavior.

## Evidence Identity

The reviewed Slice 2 evidence is identified by:

- evidence path:
  `/tmp/maintenance-phase4-slice2-local-benchmark-evidence.txt`;
- CSV path: `/tmp/maintenance-phase4-slice2-local-benchmark-results.csv`; and
- JSON path: `/tmp/maintenance-phase4-slice2-local-benchmark-results.json`.

The run was local WSL2 direct-pytest safe-cohort evidence with
`effective_cpu=20`. It used direct pytest only. It included no wrapper track,
no `load`/`worksteal`, no full suite, and no CI experiment.

The seven configs were:

- `serial_control`;
- `ci_auto_cap4_loadfile`;
- `fixed4_loadfile`;
- `cpu50_10_loadfile`;
- `cpu75_15_loadfile`;
- `cpu90_18_loadfile`; and
- `cpu75_15_loadscope`.

## Evidence Consistency

The evidence, CSV, and JSON agreed during Gate 1 review. They contain 42 rows:
7 warmups plus 35 measured samples across 7 configs, with 5 measured samples
per config.

All 42 rows completed with exit 0 and reported `294 passed`, `0 failed`,
`0 skipped`, and `0 xfailed`. There was no retry, no unexplained flake, no
hang, no worker crash, and no stop condition. The run made no repository
change, no dependency change, and no CI action.

## Key Result And Threshold

The decision baseline was `ci_auto_cap4_loadfile`; its baseline median was
`1.714843s`. The fastest config was `serial_control`; its serial median was
`1.568251s`. The median improvement over baseline was `8.548%`.

The protocol requires at least a `10%` median-improvement threshold, no more
than 5% p90 regression, no material variance increase, and no reliability
regression. No row met threshold. `provisional_candidate` was `none`, and
there is no final CI winner.

## Normative No-change Decision

The Slice 3 decision is no change. The following boundaries are normative:

- no CI change is authorized;
- no `scripts/validate.py` change is authorized;
- no wrapper change is authorized;
- no worker cap/default change is authorized;
- no distribution mode change is authorized;
- no `load`/`worksteal` wrapper expansion is authorized;
- no cache policy change is authorized;
- no job-level CI split is authorized;
- no Pyright/pytest concurrency is authorized;
- no dependency change is authorized;
- no lockfile change is authorized; and
- no final CI winner is selected.

## Interpretation Boundaries

`serial_control` was fastest only on this local safe cohort. Its 8.548%
improvement was below the required 10% threshold. This result does not prove
that serial is best for the full suite. This local safe-cohort evidence does
not prove full-suite behavior or GitHub-hosted CI behavior.

The 10-, 15-, and 18-worker rows were slower on this cohort and the
high-worker rows showed more overhead and variance. That result is consistent
with pytest-xdist startup, collection, and scheduling overhead dominating a
small pure in-memory cohort. This is descriptive evidence, not universal
xdist proof.

Full-suite, wrapper-track, fresh-session/second-day, and hosted-CI evaluation
remain deferred. Each requires separate approval and none is bundled into
Slice 3.

## Preserved Current Behavior

The current CI command remains unchanged:

```bash
uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4
```

The local default remains serial. CI remains `auto` plus `--maxprocesses 4`
plus `loadfile`. pytest-xdist remains dev-only, and there are no global pytest
addopts. The workflow remains one validation job per Python 3.12/3.13 matrix
entry. Generated, golden, and package-smoke checks remain separate serial
post-validate checks. The setup-uv cache policy remains unchanged. Pyright and
pytest remain sequential inside fail-fast `scripts/validate.py`. The package
version remains `0.1.0`.

`.github/workflows/ci.yml`, `scripts/validate.py`, `pyproject.toml`, and
`uv.lock` remain unchanged.

## Non-goals And Preserved Boundary

Slice 3 performs no benchmark rerun, full pytest, `scripts/validate.py` run,
CI action, generated check, golden check, package smoke, or package build. It
adds no dependency or lockfile change.

Slice 3 adds no source/compiler/parser/grammar/generated, fixture/golden,
package, or public behavior change. It changes no README, AGENTS, package
version, release, tag, publish, upload, signing, or attestation surface.
