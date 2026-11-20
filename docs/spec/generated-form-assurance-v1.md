# Generated-Form Assurance Harness v1

The bounded assurance of PL.50 Q9, which PL.58 places in Phase81's P07 and
P08 ([decisions](../decisions.md)): a seeded generator and shrinker, the
existing two-database differential, in-process DuckDB and SQLite for their
opened forms only, reviewed metamorphic relations, and a compile-time
benchmark and ten-node profile. It uses only the standard library and the
project's own tools, adds no dependency, and its default tests use no
network. The import time of `pietto.execution` that Q9 also names has no
slice in Phase81's route yet (PL.58) and is not measured here.

## Corpus and default tests

`tests/_pietto_harness_generated_forms.py` writes, for one seed and profile,
a bounded case of the opened single-file and project forms, and an oracle of
its result types and nullability that never imports `pietto`. Seeds 0 to 39
of its two profiles are the registered campaign, pinned by a corpus digest;
a generator change registers a new campaign. Default pytest is deterministic
and offline:

| Owner | What it holds |
| --- | --- |
| `tests/test_harness_generated_forms.py` | Each case against the oracle through single-file `check`, `explain` and `emit-sql` and the project routes `compile_sql`, `explain --project`, `compile_query` and `export_bundle`. |
| `tests/test_harness_shrink.py` | Deterministic, bounded shrinking (`tests/_pietto_harness_shrink.py`). A predicate keeps the original failure's class: a candidate that fails for another reason, such as a compilation that is not `VERIFIED`, is not taken. |
| `tests/test_harness_generated_forms_metamorphic.py` | Six rewrites of each registered case against the original's public outputs, with no oracle. |
| `tests/test_harness_generated_forms_engines.py` | Each case's own SQL in an in-memory SQLite database, and the product's SQLite SQL compared with it only on the measured build, under the SQLite class of [SQLite target validation](../development.md#sqlite-target-validation): elsewhere the oracle, the witnesses' reach and the project columns are checked, and then `hosted-refusal` keeps the refusal, `qualified` fails and `report` skips with a counted `PIETTO_NOT_RUN sqlite-native` line. DuckDB runs where the `execute-duckdb` extra is installed, with one Arrow input per source a statement reads, and is skipped otherwise. |
| `tests/test_harness_generated_forms_differential.py` | The pure parts of the registered two-database campaign: seeds 0 to 999 of the narrow profile, their rows, the SQL that loads them and the comparison. |
| `tests/test_harness_performance.py` | That the benchmark and profile entries measure the expected workload and keep each output; it judges no timing. |

## The two-database campaign

The registered campaign runs only explicitly, on Linux, against one owned
PostgreSQL 18.6 and one owned MySQL 8.4.12 container, through the public
`compile_query` and `execute()` on `postgres_rows` and `mysql_rows`:

```bash
uv sync --extra execute-postgres --extra execute-mysql
uv run python tests/_pietto_harness_generated_forms_differential.py --directory DIR
```

Its prerequisites are the Docker Engine at `unix:///var/run/docker.sock`
with the pinned images of `tests/phase66_target_pins.json`, and the
engine-slot locks (D77.02), whose holder exports
`PIETTO_ENGINE_SLOT_POSTGRES_SUFFIX` and `PIETTO_ENGINE_SLOT_MYSQL_SUFFIX`.
That lock tool is not in this repository; without the suffixes the campaign
refuses before it opens anything. `--first` and `--stop` run part of the
seeds, and only a run of all 1,000 is the registered campaign.
`DIR/report.json` records the corpus and helper digests, each seed's
observations and the cleanup. The campaign passes only with a `COMPLETE`
report, no disagreement and every cleanup `success`; no other evidence, the
default tests included, stands in for it.

## Compile-time benchmark and ten-node profile

`tests/_pietto_harness_performance.py` holds two workloads, kept apart:

- **The compile-time benchmark** times the public `compile_sql` over the
  registered generator corpus: each case of seeds 0 to 39 compiled as a
  project for PostgreSQL, and also for MySQL in the narrow profile, 120
  compilations per pass. It is a synthetic compiler workload, not ten
  nodes. The project files are written once, as UTF-8 with LF line ends,
  before any timing; one untimed warmup pass and five timed passes run by
  default, each after `gc.collect()`, timed by `time.perf_counter_ns`. The
  report gives the median pass in seconds, each unit's median, the status
  and SHA-256 of each output, and whether every pass gave the same outputs.
- **The ten-node profile** is step 4 of
  [phase-end acquisition consolidation](../development.md#phase-end-acquisition-consolidation):
  ten in-process pytest nodes of a natural CI's health, each alone in a
  fresh process under cProfile, profiled from setup to teardown. By default
  they are the ten of the [Phase78 audit](../phases/phase-78/completion-audit.md#b2-acquisition-review),
  from the health of natural CI `44006845752`; a newer health's ten are
  given with `--nodes-file`. Each node reports its phase seconds under the
  profiler, the runs of the verifier bodies that
  `tests/test_project_verification_scope.py` counts per top-level call, the
  product functions called most often, the top self time and its child
  processes, so that a child-dominated node is recorded as such.

Run each command from the repository root with the same Python and the same
`PYTHONHASHSEED` for both checkouts, on a quiet host. The newer checkout is
named with `--product-root` (its `src/pietto` compiles the same corpus) or
`--checkout` (its own tests run):

```bash
PYTHONHASHSEED=0 uv run python tests/_pietto_harness_performance.py compile --directory OUT/base
PYTHONHASHSEED=0 uv run python tests/_pietto_harness_performance.py compile --directory OUT/newer --product-root NEWER
uv run python tests/_pietto_harness_performance.py compare OUT/base/report.json OUT/newer/report.json
PYTHONHASHSEED=0 nice -n 19 uv run python tests/_pietto_harness_performance.py profile --directory OUT/profile
PYTHONHASHSEED=0 nice -n 19 uv run python tests/_pietto_harness_performance.py profile --directory OUT/profile-newer --checkout NEWER
```

`compare` refuses two reports that are not the same measurement (workload,
corpus, units, warmup, repeats, unit, clock, Python and hash seed) and
otherwise prints them side by side; no timing makes it fail. This page
records no measurement: results belong to the audit that reads them, with
their reports' environment.
