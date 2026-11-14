# Phase79 B1 completion audit

Phase79 B1 implements the limited DuckDB path of its [route](route.md): one
local, read-only query over one Arrow table that the caller supplies,
compiled for DuckDB `2.0.0` and run in process
([DuckDB Arrow route](../../spec/duckdb-arrow-route-v1.md)). Its decisions
are D79.01–D79.16, AD79.01, the third-dialect seam AD78.03 and the shared
PL rows that the route cites, in the [decision record](../../decisions.md). B1 is one
vertical: this audit closes B1, not Phase79. It records delivery,
qualification and the acquisition review, and hands over to Phase78 and to
a Phase79 B2. The batch that publishes S08 determines B1's completion
through its Gate 2 seal and natural exact-head CI; this document does not
certify its own publication.

## Baseline and publication boundary

Gate 0 is bound to `ab972f362c433b234a74f542c5d274d22c8cdeae` (tree
`821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`) with natural CI `42831340276`
(PL.02). The lane worked on `ab972f36`; the chain was integrated onto
`a015afcf` on 2026-11-13 and, after `0.1.12` was published, replayed onto
`ab594829` on 2026-11-14 in the same order, one commit per slice. B1 has one
release-note fragment, `79-s01-duckdb-arrow-route.md`, which S01's commit
adds; each later slice checks its own lines there and adds no second
fragment (the specification's open items), and on the replayed chain only
S08 changes it. Phase77 closed with `0.1.12`, so the replay carried every
Phase77 slice. The route's Gate 0 has the Phase77 overlap measured again on
the published head; B1 did not measure it, so it is NOT_RECORDED. This
departs from the route: Phase77 had closed before the replay, so no
unpublished Phase77 write set was left to overlap, and the replay compared
each slice's changed lines on the published tree instead. Owner: the lead,
who records the overlap or this omission before the batch Gate 2 seal.

On the replayed candidate chain, B1 is PK `0dd333e4` (S05, shared with
Phase80), S01 `97c1377e`, S02 `3d25e016`, S03 `134a566b`, S04 `57ba2d79`,
S07 `471e4915`, the midpoint record `1029dd74` and S04's result-reader
wiring `cf460bda`. The wiring followed the `0.1.12` publication (D77.32),
as the owner's answer D77.83 (c) has it, and D77.83 (b) retires as moot
PL.04's midpoint clause, the step of bringing option C back that the
midpoint record did not carry out.
Phase78's SQLite B1 commits `c9b96365` to `faa46a2a` lie above S07 and below
the midpoint record. S06 has no commit on that chain. By the lead's rulings
of 2026-11-13 it seals as a fresh commit, and its commit goes below S07,
which depends on it, with S07 replayed on top (2026-11-13T19:02Z). S06 had
not sealed at the replay of 2026-11-14, so S07 still has no S06 below it.
The owner's answer on the order (PL.32; see the Phase78 handoff)
supersedes that ruling: S06 and S08 go on top of the chain, above the
Phase77 follow-ups `04a74539` and `01c3b7f4`, and the whole chain
publishes in one fast-forward push. S06 sealed on 2026-11-14 as `ff74023e`
on `cf460bda` and was restacked unchanged, with the same patch, as
`1abbc7d5`; D77.50 carries its run there, and that commit's message
records the comparison. The B1 commits of the batch are the eight above,
in that order, and S06 `1abbc7d5`. The owner's answers
and the lead's rulings for `0.2.0` (PL.30–PL.34, D79.16) are the commit
`0c645606` between S06 and S08, and S08 is the commit that adds this
audit. The batch's head, tree, Gate 2 and natural exact-head CI are facts
of this commit and after it, so the first documentation commit after the
batch publishes records them. Interior batch commits take the batch
head's result.

## Accepted scope

| Slice | Delivered |
| --- | --- |
| S00 | The package evidence: the PyPI fetch and install probe of 2026-11-10 (PL.05) and the offline cells in the probe's environment, recorded at the midpoint. No repository change. |
| S01 | The alpha specification, revised by S04 with the owner's later answers (D79.13–D79.15), and B1's only release-note fragment, `79-s01-duckdb-arrow-route.md`. |
| S02 | The `duckdb.arrow` connector of explicit-module projects, the `duckdb` project dialect and the family firewall of AD78.03, which lists `duckdb` and `sqlite`. |
| S03 | The independent adapter, `src/pietto/_project/project_duckdb_*.py`, with its own SQL AST, renderer and artifact verifier, and the plan's admission of `duckdb.arrow`. |
| S04 | `execute(route="duckdb_arrow")`, `DuckDBArrowInput`, the owned capture, the hardened session, the attempt's lifecycle and the DuckDB storage kinds, wired into the shared result readers on 2026-11-14 (D77.83 (c)). |
| S05 | The `execute-duckdb` extra and its installed cells, in the PK commit. |
| S06 | The native qualification (D79.07): attempt `s06-20261114T164751Z` of preregistration v5 judged U0, U1, U2 and U3 each ACCEPTED on its first attempt on 2026-11-14, on `cf460bda`'s tree, with no void and no rerun; D77.50 carries the run to `1abbc7d5`. |
| S07 | One real DuckDB Arrow query in the `arrow-ready` cell of natural CI. |
| S08 | The shared pages (below), the freeze-ledger rows, this audit and the B1 acquisition review; the specification is left unchanged (below). |

S08 applied the specification's shared-page hunks, one page at a time:
`docs/spec/diagnostics.md` (the `PIE-S2306`, `PIE-B1001`, `PIE-B1003`,
`PIE-R1001`, `PIE-R1002`, `PIE-R1004`, `PIE-R2002` and `PIE-R2006` rows),
`docs/execution.md` (a DuckDB Arrow route section, the support-matrix and
install rows, and the `duckdb_arrow` clauses of the `execute()` entry and the
errors section), `docs/project-package.md` (the dialect and the DuckDB
columns of the contract tables), `docs/language.md` (the connector),
`docs/capabilities.md` (the [DuckDB local path](../../capabilities.md#duckdb-local-path),
each row run once through `check --project` and `emit-sql --project
--dialect duckdb` on the S08 tree) and `docs/spec/project-cli-json-v2.md`
(the `duckdb` dialect value), which the specification's hunk list names
beside the route's write set. By the lead's ruling of 2026-11-13 the
64-field width statement of
`docs/execution.md` and the `PIE-R1004` row now name only the PostgreSQL
and MySQL routes.

S08 leaves `docs/spec/duckdb-arrow-route-v1.md` unchanged. S06's frozen
preregistration binds it by its sha256 (`b5559597…`, the route's midpoint
record), its checker refuses a run whose tree holds another specification,
and D77.50 carries S06's native run to the batch head only while the
experiment documents stay byte-identical. The specification's construction
state, which still says PLANNED, and its open items, which the deferrals
below settle, are therefore updated in the first documentation commit after
the batch that carries S06 is published (owner: the lead).

## Acceptance layers

**Observable.** The specification, the fragment, the capability rows and
the shared pages state each admitted form, refusal and limit. The fragment
now links the capability subsection and the execution section, and states
that the width refusal stays with the PostgreSQL and MySQL routes.

**Existing.** No Phase79 commit touches `tests/fixtures/golden/`. At the
midpoint, on `85577f75`, `scripts/check_goldens.py` verified 43 fixtures
and the firewall's three nodes passed; the goldens of the batch tree are
recorded by the first documentation commit after the batch publishes.
PostgreSQL and MySQL SQL bytes, contracts and diagnostics
are unchanged, and single files keep their output for `duckdb.arrow`.

**Connected.** The native matrix runs in process on the integration host
against `duckdb` `2.0.0` and `pyarrow` `26.0.1`, with no Docker and no engine
lock (D79.07); every unit was accepted on its first attempt (S06 above).
Natural CI runs one real query in the `arrow-ready` cell on CPython 3.12
and 3.13 (S07); the batch head's run is recorded after it publishes.
The batch Gate 2 also runs `tests/test_sql_duckdb_emission.py` and
`tests/test_execution_api_duckdb_arrow.py` in an `execute-duckdb`
environment, recorded as one extra pytest start (the lead's ruling of
2026-11-13).

## Compiled compatibility

`VERSIONS` is unchanged and no compiled record changed. `export_bundle`
refuses a DuckDB query (`PIE-R1004` `DUCKDB_BUNDLE_ENTRY`), and saved
results, relay and jobs do not take the route, so B1 adds nothing to migrate.
After a pin upgrade an old DuckDB contract is BLOCKED with `PIE-B1003`
`target_release_not_reviewed`.

## Route deferrals due at B1

- **NUL in `Text`** (D79.13), due before the batch Gate 2: S04's
  `test_a_nul_in_text_reaches_duckdb_and_the_caller_unchanged` and S06's
  frozen cell C14, whose table carries texts with NUL at the start, middle
  and end, cover it; C14 was accepted in U1, U2 and U3.
- **Result-reader wiring:** done on 2026-11-14 in `cf460bda` (D77.32,
  D77.83 (c)).
- **Informs:** the D79.01 refusal mapping, the D79.04 `-0.0` admission and
  AD79.01 were stated to the owner on 2026-11-11, before S01 bound and S04
  sealed, and stand with the specification's derived items (D79.12). This
  settles the specification's inform row.
- **Extension sync** (D76.12), due before the batch push, read as Phase78
  B1 read `sqlite.table` (its acceptance item 16): the extension's language
  sync test reads the keywords of `grammar/Pietto.g4`, the
  built-in names of `src/pietto/semantic/catalog.py`, `aggregates.py` and
  `window_semantics.py`, and the `pietto` blocks of `README.md`,
  `docs/language.md`, `docs/style.md`, `docs/worked-example.md` and every
  `examples/**/*.pietto` file. No B1 commit changes the grammar, those
  modules or an example, and S08's text in `docs/language.md` adds no
  `pietto` block, so `duckdb.arrow` is no catalog change, B1 needs no sync
  patch and the extension's corpus is unchanged. The lead's ruling is
  D79.16; no extension push is authorized.
- **Fragment:** the specification's fragment row closes with the batch
  audit's comparison of the fragment with the specification, which the
  first documentation commit after the batch publishes records.

## B1 acquisition review

Base: `ab594829`, onto which the chain was replayed (`a015afcf` before it,
with the same test changes above it). B1 adds two owners,
`tests/test_sql_duckdb_emission.py` (20 tests) and
`tests/test_execution_api_duckdb_arrow.py` (28 tests), and two helpers,
`tests/_pietto_sql_duckdb.py` and `tests/_pietto_execution_duckdb.py`, and
changes 15 existing test files: PK's `tests/test_release_installation.py`
and three helpers, S02's six connector, dialect, `fmt` and firewall owners,
which S03 also edits, S03's plan, compile-API and R2 owners, and S04's
error and optional-Arrow owners. In all, these 19 files take 23 changes,
one per commit and file, which add 3,157 lines and remove 24. PK's part,
`tests/test_release_installation.py` and its three helpers (199 lines
added, 2 removed), is shared with Phase80; this count includes it once, so
a Phase80 count that includes it covers the same lines. The three helpers
only extend constant tables (the extras' requirements, the expected wheel
metadata and the origin's extras). Their direct existing consumers,
checked here, compare against those tables and acquire nothing new:
`tests/_pietto_execution_installation_probe.py`,
`tests/_pietto_execution_matrix_check.py` and
`tests/test_execution_compatibility.py` read
`_pietto_execution_installation_check`;
`tests/_pietto_repo_arrow.py`, `tests/test_results_optional_arrow.py`,
`tests/test_release_packaging_smoke.py` and
`tests/test_execution_compatibility.py` read `_pietto_repo_package`; and
`tests/_pietto_results_product.py`, `tests/_pietto_execution_matrix_probe.py`,
`tests/test_results_consumer.py` and `scripts/phase68_executor_premise.py`
read `_pietto_results_consumer`. S07 changes no test. S06, counted apart
from these, adds the four frozen helpers
`tests/_pietto_execution_duckdb_native_*.py` (3,673 lines), which are the
preregistered experiment's bytes and acquire nothing that an owner reads,
and a 34-line harness self-test in the existing owner
`tests/test_harness_execution_api.py`; it adds no owner. The self-test
keeps its fresh interpreter, since only a fresh process shows that the
oracle runs without DuckDB.

Timings are the per-test times of the midpoint's first pytest output
(`-n 8`, 2026-11-13T17:42:55Z), one median `compile_query` measurement on
the S08 tree (0.050 to 0.060 s under a load near 20), and the S08 focused
pytest start (2026-11-14T16:43:35Z, `-n 8 --dist=loadfile`, nine files in
an `execute-duckdb` environment: 505 passed, none skipped; the execution
module's 29 nodes summed 15.98 s). Gate 2 distributes by file
(`--dist=loadfile`), so a module fixture is built once per run.

Consolidated, with equal assertions:

- `tests/test_execution_api_duckdb_arrow.py`: 19 compiles of the two B1
  queries (13 tests of the projection, 6 of the filtered query) now read two
  module fixtures, `filtered_query` and `projection_query`; a
  `CompiledQuery` is an immutable snapshot that `execute()` binds afresh.
  About 17 compiles fewer per run, about 0.9 s on the file's worker.
- `tests/test_sql_duckdb_emission.py`: the VERIFIED emission that the six
  forgeries and the `compile_query` cell read is one module fixture,
  `verified`; a forgery replaces the artifact and never changes it. Six
  emissions fewer per run.
- `tests/test_plan_target_profiles.py`: the pure-boundary cell of a
  `duckdb.arrow` source builds its project record once and assesses it for
  the three families, instead of three parametrized nodes that built the
  same record (0.448 to 0.541 s each at the midpoint); an assessment
  asserts that it leaves its record unchanged. Two record builds fewer.
- The adapter's import scan in `tests/test_sql_duckdb_emission.py` reads
  `REPOSITORY_FACTS.python(path).imported_modules` of the existing owner
  `tests/_pietto_repo_facts.py` in place of its own `ast` walk. Both take
  every `import` name and every `from` module; a module-less `from . import
  x` gave the walk an empty name and gives the owner none, and neither is
  banned. Structural only: the walk took milliseconds.

Kept fresh, each with its reason:

- The three child interpreters of the execution module (checks 1–8 import
  nothing, checks 9–13 import no DuckDB, a shadowing `_duckdb` on the path)
  and the adapter's child: absence of an import is observable only in a
  fresh process.
- The cell that forges the compiled template in place
  (`test_check_seven_refuses_a_forged_template_and_another_code_identity`)
  compiles its own query, and the cells of distinct bodies or contracts
  (the six operators, the NUL query, the out-of-range `Int`) compile theirs.
- Each attempt opens its own `:memory:` session, which is the property
  under test (nothing is pooled); the cancel and deadline cells keep their
  real threads and the 30 s watchdog bound.
- The firewall drives every entry per dialect, contract and output on the
  integrated tree, as AD78.03 asks at every replay; its inputs differ.
- The other emission cells read distinct inputs at about 0.04 s each (the
  module's 63 nodes summed 4.23 s at the midpoint); S02's connector cells
  use in-process `tmp_path` projects (0.96 s for 100 nodes).
- PK's installed wheel and sdist cells are independent install witnesses of
  package smoke.

Structural improvement: one existing-owner reuse, three module fixtures and
one record shared across families. Wall-time improvement: about 1.2 s of
worker time per run, estimated from the operation counts and the measured
compile time; no before-and-after run was made. The S08 run shows the
emission module at 3.69 s summed (4.23 s at the midpoint) and the shared
plan cell at 1.41 s (1.515 s for its three nodes at the midpoint), under
other loads and trees, so no measured gain is claimed: the record build
was not the plan cell's main cost. The bounded ten-slowest profile of
step 4 reads the final natural CI health after publication, so the first
documentation commit after the batch publishes records it, or NOT_OBSERVED
with its reason (PL.07). Owner: the lead; latest point: the Gate 2 seal of
the next batch that carries Phase78 or Phase79 work, which records its
result.

## Budget, failures and Gate 2

The ceiling is `C240/F720/D8200/S8` (D79.08, D79.09, PL.09) plus half of
PK's `C80/F240/D2400/S8`. The owner's raise of near-exhausted ceilings on
2026-11-14 changes neither: at 16:30Z Phase79 with its half of PK had used
about 40% of its D and less of the rest, below the 75% that qualifies
(PL.30). At the midpoint Phase79 had used at most C15, F71, D2,349 and S0.
By the row sum of the owner-held ledger through S06's seal at 17:05Z on
2026-11-14, Phase79 has used at most C17, F99, D3,432 and S0 of
`C240/F720/D8200/S8`, and with its half of PK at most C18, F118, D3,866
and S0 of `C280/F840/D9400/S12`. The S08 lane's work after 16:30Z, this
batch's assembly, its Gate 2 and its audit are charged after that row,
and the first documentation commit after the batch publishes records the
totals with them.

The route has the closeout read the CI health again, as the midpoint did.
That read is NOT_OBSERVED (PL.07): the lane that closed B1 holds no
read-only token, so it read no health of the newest published head,
`ab594829`, and the midpoint's read of `a015afcf` stays the last one.
Health is advisory, and the ten-slowest profile above reads the batch
head's own health after publication.

Failures are kept, never rerun as replacements: the midpoint's first
`pyright` pass, which ran without the run's interpreter; by the lead's
ledger, the S06 lane of 2026-11-13 that stopped BLOCKED for its missing
midpoint record and result-reader wiring; the integration chain INT1
(`01c3b7f4`, tree `7b0db316`), which passed its Gate 2 on 2026-11-14
(16:31:26Z to 16:42:21Z: 30,780 passed, 65 skipped) but was not pushed,
because its batch audit found that pushing it alone would publish SQLite
B1 before the complete DuckDB B1 (PL.31, PL.32), so that Gate 2 stands for
that tree only; the first offline sync of INT1's `execute-duckdb`
environment, which stopped before it installed anything because its cache
lacked `ruff` 0.17.4; and S08's first draft, which changed the
specification that S06's freeze binds until its review sent it back, so
the specification is restored byte for byte.

The batch Gate 2 runs once on this batch's final tree, with the DuckDB
extra start of the lead's ruling of 2026-11-13, and the first
documentation commit after the batch publishes records its result and
duration.

## Phase82 inputs

The [freeze ledger](../../roadmap.md#phase82-freeze-ledger) gains two rows:
the DuckDB Arrow route surface (the connector spelling and texts, the
dialect, the contract values, the compile refusals and their order, the
execute API, the capture limits, the session settings, the detail words and
the extra), and the error-class rule that `RequestRejected` carries the
PIE-R2xxx refusals of `execute()`'s own checks while the PIE-R1004 width
refusal covers only the PostgreSQL and MySQL routes.

## Phase78 handoff

- **Order.** SQLite B1 publishes only once DuckDB B1 has published or lies
  below it (AD78.02), and a change of that order needs the owner. On the
  candidate chain the SQLite commits lie above S07 and below the midpoint
  record and the wiring, and S06 and S08 are not on it. On 2026-11-14 the
  lead asked the owner which order holds: S06 and S08 sit above Phase78
  S01–S04 and publish with them in one push, or a strict restack puts S06
  below S07 and S06 to S08 below Phase78 S01. The owner answered that the
  same batch is fine (PL.32): S06 and S08 sit above Phase78 S01–S04, and
  both B1 batches publish in one fast-forward push, so SQLite B1 never
  reaches `main` before the complete DuckDB B1.
- **Seam.** AD78.03 holds on the integrated tree: the PostgreSQL and MySQL
  pipeline never receives `duckdb` or `sqlite`, and the firewall in
  `tests/test_repo_static_checks.py` lists both. SQLite B2's Gate 1
  decides, before any B2 code, whether it generalizes that firewall or
  builds its own pipeline (the route's deferral). The connector and dialect
  sets were written in a shape that SQLite's entries extend, and
  `project_sql_plan_target_assessment.py` maps each family as the pure
  boundary does.
- **Reading.** The Phase78 completion audit reads this audit.

## Phase79 B2 handoff

- **Owner decision, made.** Whether `0.2.0` also needs a B2 (`group by`
  with `count`, `sum`, `min` and `max`, then `order by` and `limit`) was
  the owner's. The route set its latest point at this audit, before any
  `0.2.0` request, and the owner's request of 2026-11-14 to release
  Phase78–80, which the lead reads as `0.2.0` (PL.31), came first. The
  owner then answered that `0.2.0` carries B1 only (PL.33), so B2 is not
  part of `0.2.0` and is not opened without its own Gate 1.
- **Gate 1 first.** B2 needs its own Gate 1. It inherits the adapter with
  its closed order of 33 compile rules, which B2 extends; the session
  settings and capture policy; the storage kinds; S06's native matrix with
  its Pietto-owned oracle; and the deferral of sqlglot as a test oracle to
  the first slice beyond projection and filter.
- **Deferred owners.** Other Phase79 forms (multi-source, JOIN, windows,
  more parameters, `Decimal`, temporal, `UUID` and nested types, bundles,
  saved, relay and job routes) wait for later Phase79 Gate 1s, and the
  Phase82 freeze lists each one that no Gate 1 takes as unsupported.
  Platforms beyond PL.05 belong to Phase81. Reminder 8 (JOIN facts, a
  forged compiled `median`) stays satisfied by exclusion: B1 has no JOIN
  and, since it refuses bundles, no new consumer of compiled admission. It
  passes to the first Phase79 slice that admits a JOIN or such a consumer.
- **Debt.** The ten-slowest profile above, and any finding it records; the
  specification's construction state and open items (owner: the lead;
  latest point: the first documentation commit after the batch that
  carries S06 is published).
