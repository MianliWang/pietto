# Phase77 S11/S25 recovery report

## Boundary

- Baseline for both isolated candidates: `f8ccd2c44a2d9adf431a496bd9bbae037783176f`.
- Recovered candidates: `candidates/s11` and `candidates/s25`. They are local
  clones and no canonical-worktree file, index, ref, worktree registration, or
  historical release note was edited.
- This report is a recovery ledger, not Gate 2, a qualification, a database
  result, publication, or release claim.

## S11 tuple `count_distinct`

The recovered change admits MySQL `COUNT(DISTINCT a, b, ...)` only for direct
`Int`, `Bool`, and `Text` fields. PostgreSQL keeps the CASE/ROW spelling.
The implementation does not deduplicate a repeated member: lowering rejects a
duplicate direct port, the pure boundary rejects its duplicate canonical port,
and compiled verification rejects a duplicate `read`/port. Different ports
remain different tuple members even when their rendered aliases coincide.

| Source edit call | Recovered candidate lines / purpose |
| --- | --- |
| `call_2aaa8e0d95ae4bdaa836036f6d14e7a7` | `project_sql_emission_aggregation.py:54,787-794,1284`; target admission and lowering |
| `call_c1788e7995fb490989d39e7f87c1c7f6` | `project_sql_emission_rendering.py:1200-1238`, `project_sql_emission_verification.py:8421-8456`; MySQL rendering and token replay |
| `call_2d1602fc6546404d9a2ed900540c84e2` | `tests/_pietto_sql_emission.py:10270-10275,11885-11982`; public-artifact decoder |
| `call_2792c9c50ccb4d0794df094bf9b3e675`, `call_c1a08c92022d44cf9aaf9ec66fe77c02` | `tests/test_sql_grouped.py:132-155,1736,1795-1800`; direct carrier and retained refusal coverage |
| `call_333ebe5731644c2894c375900a1f7f3e` | `tests/test_execution_compiled_families.py:334-356`; compiled replay coverage |
| `call_355436e41eb6453ab4c52a57af87e248` | `project_sql_emission_suggestions.py:479`; current refusal suggestion |
| `call_f6e113af90cc4a188be2528c0eaf5bc2` | `project_sql_emission_aggregation.py:659-670,1674-1679`, `project_compiled_verification.py:1472-1474`; lowering and compiled duplicate-port refusal |
| `call_e8d4cfa9a599473c9063429e13687514`, `call_727a5df6300c43fcad0f560c3c49dce5`, `call_4f69f90dddea47b0b412803c78231ed8` | `project_sql_emission_pure_boundary.py:2217-2239`, `tests/test_harness_sql_emission_portability.py:1007-1023`, `tests/test_execution_compiled_families.py:358-398`; pure duplicate refusal and compiled forged-input control |

## S25 single-file ASOF/FULL

The recovered change removes only the MySQL single-file refusal for an ASOF
JOIN in a relation with FULL JOIN emulation. Tests cover `LEFT` and `INNER`,
ASOF before/after/between FULL JOINs, derived ports, branch multiplicity,
right-only `IS NULL` checks, and CLI text/JSON output. Project emission remains
outside this candidate. Current language and `PIE-B1000` diagnostic text say
that native MySQL qualification is pending; the historical release notes were
not modified.

| Source edit call | Recovered candidate lines / purpose |
| --- | --- |
| `call_dd4e9b8d9ded4cb59dcf97971ed85fcb` | `src/pietto/sql/joins.py:113-121`; removes the obsolete refusal |
| `call_aa4ad96d2fd04a7a8f8be1a74b76543d`, `call_13b43938b43247c59e382d8daf33bb02` | `tests/test_sql_join_emission.py:2587-2802`; FULL-before/after/intermediate, LEFT/INNER, derived-port and CLI assertions |
| `call_ffb0cccc17c54d498dbc29489524a8d8` | `docs/language.md`; current capability wording |
| `call_31e318cd1cb44fbc8cede90f745e96a7`, `call_0a121ba3d3204792b5cb138e6001ab84` | `docs/spec/diagnostics.md:365`, `docs/release-notes.d/77-s25-mysql-asof-full.md`; diagnostic correction and unreleased fragment |

## Verification and limits

- Current recovery check: `git diff --check` passed for both candidates.
- Current recovery check: offline `UV_PYTHON=3.13.13 UV_OFFLINE=1 uv run
  python -m compileall -q ...` completed for all recovered Python paths. This
  is syntax compilation only, not a behavior result.
- No pytest, DB campaign, full Gate 2, download, commit, push, CI, release, or
  qualification was run during recovery.
- The old sessions describe focused tests/Ruff and a separate temporary
  qualification package. Those are historical tool outcomes only. Their raw
  logs were not present in the recovery candidates and have not been recreated
  or represented as new evidence.
- Not recovered into these source candidates: the old `/tmp` qualification
  packages and preregistration reports. They were external preparation assets,
  not tracked candidate source changes; recovering them would need a separate,
  explicit artifact scope.
