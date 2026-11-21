# Phase79 completion audit

Phase79 delivered the limited DuckDB path in three parts on the
[DuckDB Arrow route](../../spec/duckdb-arrow-route-v1.md): B1, one projection
over one `duckdb.arrow` source ([B1 audit](completion-audit.md)); B2's first
tier, grouping, `having`, order, limit and predicates
([B2 audit](b2-completion-audit.md)); and B2's second tier, which this audit
closes: `Date`, `Timestamp` and `Decimal(p, s)` fields, `Int` and `Float`
arithmetic in the final projection, several sources joined by `inner` and
`left` equality JOINs over a tuple of inputs, one source read twice
included, and every result read in batches. The second tier's decisions are
D79.17–D79.30 in the [decision record](../../decisions.md), and its route
is the [second-tier section](route.md#b2--the-second-tier) of the Phase79
route. The earlier audits stay as written; this one adds the second tier's
delivery, qualification and acquisition review, and Phase79's handoff.

Phase79 is done when the batch that carries this audit is pushed and its
natural exact-head CI is green (D79.23). This document does not certify its
own publication: a documentation commit after the push recorded the
batch's Gate 2, reviews and natural CI in
[Budget, failures and Gate 2](#budget-failures-and-gate-2).

## Baseline and publication boundary

The tier's Gate 0 froze `main` at `300f0a93`, whose natural CI passed all
21 jobs on 2026-11-17 (the route's
[tier 2 Gate 0](route.md#tier-2-gate-0-and-base)). JF's J1 then reached
`main` at `900e8915`, whose natural exact-head CI `44166283520` completed
with success on all 21 jobs at 20:32:19Z by the lead's record, so the whole
tier, its JOIN part included, was integrated on that head as one batch.
Its chain, one commit per slice except as the route states: the records
`ff9431c9` (U01), the types `bd0c4305` and the batch reading `a0ffadb2`
(U02), the arithmetic `ba0ee6da` (U03), the several inputs and JOINs
`cc767d38` (U04 and U05), one source read twice `ba330186` (the self-join
lane's `919951b8`, replayed), the qualification `71a495a3` (U06), package
smoke `b95e8413` (U07) and the closeout that adds this audit (U08). These
are local candidate commits on `refs/pietto-candidates/p79t2-int`; a later
replay changes their ids, and the batch's record names the published ones.
The lane that wrote this audit holds no token and read no CI health; the
batch's Gate 2 binds the health of its own base (PL.07).

The tier writes four release-note fragments, one for each family:
`79-u02-duckdb-types.md`, `79-u03-duckdb-arithmetic.md`,
`79-u02-duckdb-batch-reading.md` and `79-u05-duckdb-join.md`; the self-join
edits the JOIN fragment, and U08 adds the qualified platforms to each and
no fifth fragment. They are assembled with `0.2.2`. The batch publishes as
one push under PL.52 on D77.06's conditions (D79.21): the records cite
forms that the later commits open, so no part of the chain is pushed
without the rest.

## Accepted scope

| Slice | Delivered |
| --- | --- |
| U00 | The offline probe before Gate 0, outside the repository; its facts are the specification's [tier 2 pin facts](../../spec/duckdb-arrow-route-v1.md#tier-2-pin-facts-u00) and are not qualification evidence. |
| U01 | The decision rows D79.17–D79.28 and the route's second-tier section. |
| U02 | `Date`, `Timestamp` and `Decimal(p, s)` with `p` at most 38: capture, contract, result binding, literals and parameters; then every result read in batches from DuckDB's record batch reader, its charge, `transaction` and failure causes (D79.20, D79.27, D79.30). |
| U03 | `Int` arithmetic by range proof (rule 7c, D79.25) and `Float` arithmetic with its overflow and underflow checks (D79.18, D79.26) in the final projection. |
| U04, U05 | A tuple of inputs matched by name, the capture limits per input and over all inputs, `inner` and `left` equality JOINs read from the verified plan, and the declared key check under a joined aggregation (D79.19, D79.24, D79.28). |
| Self-join | One source read twice through a row-input alias, two reads with their own fields and registered names over one input (D79.29). |
| U06 | The native qualification v7: the four helpers evolved in place, the harness self-test, and one run in which U0, U1, U2 and U3 were each accepted on their first attempt on 2026-11-18 ([below](#the-v7-run)). |
| U07 | Three second-tier queries beside B1's and B2's four in the `arrow-ready` cell of natural CI, through package smoke: `Int` arithmetic, `Date` and `Decimal` fields filtered by a `Date` parameter, and an inner JOIN over a tuple of inputs. |
| U08 | The shared pages, the freeze-ledger row, status, D79.30, the fragments' qualified platforms, this audit with the acquisition review, and Phase79's lessons. |

U08 applied the closeout hunks that the specification lists under
[shared-page hunks](../../spec/duckdb-arrow-route-v1.md#shared-page-hunks):
the `PIE-R1002` row of `docs/spec/diagnostics.md` now counts a column once
for one source read twice, as for two sources with one key, as the owner
admitted it (D79.29); the native evidence of `docs/execution.md`'s
support-matrix row, of the capability page and of `README.md` names U06's
run and drops "not qualified yet"; the capability page states the measured
peak and the seven queries of the `arrow-ready` cell; the freeze ledger's
DuckDB row names the second tier's surface; and `docs/status.md` the
tier's state. Each family's pages and fragment landed with its code
earlier in the chain. No other target's page changes.

## Acceptance layers

**Observable.** The specification, the four fragments, the capability
rows and the shared pages state each opened form, each form kept refused
and each limit. U06's cells C23–C28 and the changed C02a, C11, C12, C15,
C18 and C22 judge them, and the route's pytest owners cover every refused
JOIN form by form, the `any(...)` filter beside JOINs and rules 9 and 8b
beside a refused JOIN since the
[post-hoc batch audit](#the-post-hoc-batch-audit)'s repairs, which found
them unpinned.

**Existing.** Emission tests live in `tests/test_sql_duckdb_emission.py`,
execution tests in `tests/test_execution_api_duckdb_arrow.py` and the
`Float` details in `tests/test_execution_api_errors.py`. No tier 2 commit
touches `tests/fixtures/golden/`, `grammar/`, `src/pietto/generated/`, a
plan module, a PostgreSQL or MySQL emitter or the firewall of
`tests/test_repo_static_checks.py`; its `src` changes are the DuckDB
adapter, `execution/_duckdb.py`, `_handle.py`, `_access.py`,
`__init__.py`, `_errors.py`, `project_execution_reader.py` and the DuckDB
part of `project_result_binding.py`.

**Connected.** `compile_query` builds a live query only from a VERIFIED
document; `execute()` runs real DuckDB in U06's U1–U3, and U2 and U3 run
the installed wheel on CPython 3.13.13 and 3.12.13. Natural CI's
`arrow-ready` cell runs seven real queries through package smoke on both
Pythons. The execution owner's cells skip on every CI job, none of which
installs `execute-duckdb` (lesson 75-3); on the integration host the
`execute-duckdb` environment ran the three DuckDB owners with none skipped
(below). The batch Gate 2's DuckDB extra start ran the execution and
emission owners again, none skipped, and the errors owner, whose DuckDB
cell needs no DuckDB, ran in its core validation
([Gate 2](#budget-failures-and-gate-2)).

## Compiled compatibility

`VERSIONS` is unchanged and no compiled record changed. A second-tier
document may carry the `physical_type` values `duckdb_date`,
`duckdb_timestamp` and `duckdb_decimal`, columns of arithmetic, and the
JOIN's source reads, each with its own registered name. `export_bundle`
still refuses a DuckDB query (`PIE-R1004` `DUCKDB_BUNDLE_ENTRY`), and saved
results, relay and jobs do not take the route, so the tier adds nothing to
migrate.

## Route items due at the second tier

- **`having` coverage** (the [B2 audit](b2-completion-audit.md#route-items-due-at-b2)):
  closed. C18's four new forms, each in both input orders, qualify a
  `having` over a `Text` key, a `Bool` key and a `Float` `min`, the last
  against a literal and against a parameter bound to `-0.0`.
- **Memory margin** (the same audit): closed as a record. C28's `memory
  margin` ran L13's statement around the 1 GiB `memory_limit` in U1, U2 and
  U3; by the lead's ruling it is recorded, not judged, and stated in the
  run's evidence outside Git, not on the public pages. L13 itself failed
  as v6 expects.
- **The batch reading's peak** (the route's stop on peaks, lesson 78-3):
  judged. C28's `sorted read` stayed within the specification's bound in
  every unit, and the declared key check's capture within its own
  ([below](#the-v7-run)); no stop was reached.
- **Integrity audit.** The route asks for an independent integrity audit
  of U06's verdict, by an auditor outside the lane (74-1). The lane
  re-checked its own outputs after the run (below); that is not the
  independent audit. An audit outside the lane was recorded clean in the
  lead's record before the batch Gate 2, but its report was lost
  with the integration host's disk after 2026-11-18T17:25Z, as were the
  run's saved outputs. A re-check outside the lane read what survives
  on 2026-11-21 ([below](#the-v7-run)). The audit was owed before the
  batch Gate 2, the one deadline that applied; the audit recorded then
  left no report, so the batch Gate 2 ran before the re-check that now
  stands for it. By the lead's ruling of 2026-11-21 (1), the re-check is
  recorded as the integrity audit, with its limit stated: it could not
  re-judge the lost outputs.
- **Midpoint.** The route draft's midpoint after the types and the
  arithmetic has no record in the route; the stops that took its place,
  the owner's two previews of the texts (D79.26, D79.29) and the lead's
  ruling to integrate the tier on `900e8915` as one batch, are in the
  decision record and the lead's working record outside Git. Owner: the
  lead, who states the midpoint's facts in the batch's record if the
  owner asks for them (80-5).
- **Extension sync** (D76.12), read as B1 and B2 read it: no tier 2 commit
  changes `grammar/Pietto.g4`, `src/pietto/semantic/catalog.py`,
  `aggregates.py`, `window_semantics.py`, `docs/style.md` or
  `docs/worked-example.md`; it adds no spelling, so no extension sync patch
  is needed and none is authorized.
- **Fragments.** U08 compared each fragment's qualification sentence with
  the specification; the batch's reviews do not record a second
  comparison ([below](#budget-failures-and-gate-2)). On 2026-11-21 each of
  the four sentences names the specification's releases and platforms,
  `duckdb` `2.0.0` with `pyarrow` `26.0.1` on CPython 3.12 and 3.13,
  Linux x86-64 with glibc 2.28 or later.

## Tier 2 acquisition review

Base: `900e8915`, the tier's integration head; this is also Phase79's
phase-end review, since B1's and B2's first-tier reviews stand
([B1](completion-audit.md#b1-acquisition-review),
[B2](b2-completion-audit.md#b2-acquisition-review)). The tier adds no test
owner and no helper. It changes three owners:
`tests/test_sql_duckdb_emission.py` (32 test functions to 58, 1,050 lines
added and 45 removed; 228 collected nodes), `tests/test_execution_api_duckdb_arrow.py`
(33 to 54, 1,092 added and 38 removed; 56 nodes) and
`tests/test_execution_api_errors.py` (14 to 15, 37 added); the shared
helpers `tests/_pietto_sql_duckdb.py` (192 added and 6 removed) and
`tests/_pietto_execution_duckdb.py` (73 added and 6 removed); the four
frozen helpers `tests/_pietto_execution_duckdb_native_*.py` (3,152 added
and 99 removed), the preregistered experiment's bytes, which acquire
nothing an owner reads; and `tests/test_harness_execution_api.py` (one line).
`tests/_pietto_sql_duckdb.py` gains the typed and joined headers, their
contracts and statements, and `source_entry` a `relation` argument whose
default keeps every earlier value, so its other direct consumers,
`tests/test_cli_project_emit_sql.py`, `tests/test_sql_compile_api.py` and
`tests/test_sql_sqlite_project_emission.py`, acquire nothing new.

Timings are those of the focused run on U07's tree (2026-11-18, 01:37:25Z
to 01:37:52Z, `-n 4 --dist=loadfile`, the three owners in the lane's
`execute-duckdb` environment: 368 passed, none skipped, 26.51 s). Summed
over nodes, the execution owner took 25.06 s, its slowest node, the
operator bags, 4.36 s; the emission owner 7.69 s; the errors owner 0.57 s.

Classified:

- **Execution, fresh.** Each execution cell compiles the statement it runs
  and opens its own `:memory:` session per attempt, which is the property
  under test (nothing is pooled); the new cells add types, arithmetic,
  batches, inputs and JOINs, each over its own tables.
- **Distinct inputs, fresh.** The emission owner's new parametrized forms
  (typed, arithmetic, joined and refused JOIN forms) each write and emit
  their own project; their inputs differ.
- **Repeated acquisition, kept.** As B2 found, a few forgery cells emit a
  VERIFIED statement that another cell also emits, then replace the
  artifact they read; at a few hundredths of a second each this is
  low-value repetition that the procedure does not consolidate. Owner: the
  next slice that edits the owner, if it measures more.
- **The frozen helpers** change only by a new preregistration, and the
  harness self-test keeps its one fresh `-I` oracle interpreter, since only
  a fresh process shows that the oracle runs without DuckDB.

Structural improvement: none needed; wall-time improvement: none claimed;
no-gain: the repeated emissions above. The bounded ten-slowest profile of
step 4 reads the final natural CI health of the batch head after
publication: the natural exact-head CI `44225459194` of `df8817d3`
([Gate 2](#budget-failures-and-gate-2)) ran from 02:44:33Z to 03:07:00Z
on 2026-11-18 (1,347 s), and its 21 jobs took 11,223 s in all (jobs API,
start to completion, without queueing); the longest was Compiler /
Package 3.13 at 1,228 s. Its health was read on 2026-11-21 at about
15:57Z through the owner's read-only token (PL.07): the 15 `ci-health`
artifacts match the digests the API lists, the workflow summary passes
`verify_workflow_health` of that head's `scripts/ci_workloads.py` with
the run's own context, each runtime and partition artifact equals its
part of the workflow summary, and the `[ci-health]` lines of the
aggregate job's log agree. The status is INSUFFICIENT_EVIDENCE with a
WATCH screen. History read 4 candidates and accepted 3 (`44166283520` of
the tier's base `900e8915`, `44042698462` and `44006845752`) with none
rejected, but none is comparable: each differs in its test set, and the
two older ones in their runner images and the 3.13 domain too. Each
Python collected 31,546 nodes, 121 more than at `900e8915`; 31,400
passed and 146 were skipped. The only alert that needs no history is the
structural `FEWER_UNITS_THAN_WORKERS` (plan- and emission-portability, 3
nodes on 4 workers, on both Pythons). The provisional ones are
`SHARD_IMBALANCE_REVIEW` on both Pythons (longest over median 1.85 on
3.12 and 2.05 on 3.13, general-runtime-1 the longest each time) and
`LONG_INDIVISIBLE_NODE` 18 times, the same nine child-process nodes on
each Python. Every shard ran on runner image `20261111.196.1`, as at
`900e8915`.

Ranked by setup, call and teardown time, 12 nodes above the tenth
in-process one on Python 3.13 were left out because their time is spent
in child processes, of the kinds the [B1 profile](completion-audit.md#b1-acquisition-review)
names: the differential process cells of `test_harness_ir_differential.py`,
`test_harness_plan_conformance.py` (its setup is that acquisition) and
`test_harness_plan_portability.py`; the six checkout, relocated and
installed standalone batches of the two portability files; the two fresh
source-free processes of `test_execution_compiled_source_free.py`; and
`test_harness_execution_api.py::test_checkout_consumer_cases_satisfy_the_checker`,
whose module fixture starts a fresh `-I` worker for each consumer case.
B1's profile set the DuckDB native checker's self-test apart, since the
split between its fresh `-I` oracle interpreter and its in-process check
was not observed. It is counted in process here: on the integration
host the frozen oracle took 4.1 s and the frozen checker's self-test
46.7 s on CPython 3.13.13 ([the re-check](#the-v7-run)).

| Node | Job | 3.13 s | 3.12 s | Where the time is |
| --- | --- | ---: | ---: | --- |
| `test_harness_target_conformance.py::test_data_only_receipt_controls_have_nonempty_positive_denominators[postgres]` | Runtime 3.13 / general-runtime-1 | 184.4 | 188.7 | setup, 179.9 s: the module fixture `valid_receipts` |
| `test_harness_execution_api.py::test_the_duckdb_native_checker_accepts_honest_units_and_refuses_each_fabricated_shape` | Runtime 3.13 / general-runtime-2 | 128.5 | 148.1 | call, the frozen checker's self-test |
| `test_harness_sql_emission_portability.py::test_every_admitted_artifact_exports_corresponds_and_decodes[postgres]` | Runtime 3.13 / shared-acquisition | 93.4 | 155.8 | call |
| `test_harness_sql_emission_portability.py::test_every_admitted_artifact_exports_corresponds_and_decodes[mysql]` | Runtime 3.13 / shared-acquisition | 82.6 | 135.1 | call |
| `test_harness_target_conformance.py::test_empty_text_anchor_requires_the_observed_var_string_type` | Runtime 3.13 / general-runtime-1 | 45.7 | 51.4 | call; the fixture was already built on its worker |
| `test_repo_reader_acquisition.py::test_shared_facts_match_legacy_text_ast_import_and_identifier_acquisition` | Runtime 3.13 / general-runtime-2 | 38.4 | 45.5 | call |
| `test_execution_compiled_bundle.py::test_mysql_lpad_and_now_cells_are_derived_in_linear_work[words-_chained_lets]` | Runtime 3.13 / general-runtime-3 | 31.8 | 26.9 | call |
| `test_sql_values.py::test_the_static_values_bound_is_no_emission_guarantee[postgres-1000-64-blockers2]` | Runtime 3.13 / general-runtime-3 | 30.5 | 24.3 | call |
| `test_repo_test_layout.py::test_no_test_reads_the_mutable_status_or_roadmap` | Runtime 3.13 / general-runtime-1 | 30.2 | 29.0 | call |
| `test_sql_values.py::test_the_static_values_bound_is_no_emission_guarantee[mysql-1000-64-blockers3]` | Runtime 3.13 / general-runtime-3 | 29.1 | 23.3 | call |

Seven of the ten ids are in B1's profile of `43645308189`; new are the
DuckDB checker's self-test and the two `test_sql_values.py` bound nodes,
a test that B1's profile saw leave its list. On Python 3.12 the same six
lead, in another order, and of the other four `test_repo_test_layout.py`'s
node and the `[words-_chained_lets]` cell are the same;
`test_project_r2_proposal.py::test_r2_refuses_a_paired_mysql_form_before_any_workspace`
(27.2 s) and the `[pair-_beside_a_capture]` cell (25.6 s) take the places
of the two `test_sql_values.py` nodes (24.3 s and 23.3 s).

The checker's self-test is the tier's one node among the ten. It took
46.5 s on 3.13 and 46.9 s on 3.12 in the health of `44166283520`, whose
workflow summary matches the digest this head's history lists, on the
same runner image, and 128.5 s and 148.1 s here; between the two heads
only U06 changed the files it runs, and its v7 checker judges 225
reports, the five honest ones and 220 fabricated shapes. It is kept
deliberately: the oracle and the checker are frozen bytes that change
only by a new preregistration (above), and the node's shard,
general-runtime-2, is not the longest on either Python. The cProfile
half of step 4 is NOT_OBSERVED: none of the ten ran alone under cProfile,
because the integration host was not quiet during this read (other
lanes held it, at one-minute loads from 14 to 47), so no verifier-runs,
call-count or self-time finding is recorded, and no performance claim
rests on the table beyond the checker's split above. The Windows jobs
are outside partition health by design, so their nodes are not ranked.
GitHub's rendered Job Summary has no REST endpoint and was not read; the
summary was regenerated from the artifact with `summary_markdown`.
Health is advisory, and nothing here changes scheduling, topology or
test selection. B2's profile of `43888270979` belongs to the
[B2 audit](b2-completion-audit.md).

## The v7 run

Preregistration v7 was frozen in place at 2026-11-18T01:24:45Z, with v7's
sha256 `f7962d31…`, `FROZEN.sha256` `88400bc5…`, the specification's
`f52aa9b2…` and the lane head `71a495a3`; the specification's digest was
the lane's own, so nothing was rebound. C26's self-join cells are admitted
cells and their forward refusal `self join key repeated` the declared key
check. The run `p79t2-u06-20261118T012524Z` ran each step once, in order,
behind the host gate, from 01:25:35Z to 01:36:03Z: U0 ACCEPTED with 72
records (26 skip lines), and U1, U2 and U3 ACCEPTED with 633 records each,
with no void and no retry. U0, U1 and U2 ran CPython 3.13.13 and U3
3.12.13, U1–U3 with `duckdb` `2.0.0` (pragma `v2.0.0`, `d54cbbe3df`) and
`pyarrow` `26.0.1`; U2 and U3 built the same wheel `44c964a6…`.

Observed within the judged laws, in U1, U2 and U3: C28's capture peaks
of at most 145,576, 446,444 and 224,612 KiB for the `Int` key check, the
`Text` key check and no key check, against bounds of 273,409, 771,071 and
347,136 KiB; the sorted read's 4,096 batches, its ids falling from
1,048,575 to 0, and its run peak of at most 206,504 KiB against
1,180,672 KiB; a `Float` `+` that leaves binary64 at row 131,073 failing
with `PIE-R3003` `DUCKDB_FLOAT_OVERFLOW` and `cause` `OSError` after 408
delivered batches of 256 rows, and at row 2,049 with no batch; a left JOIN's six rows in batches of 4 and 2; a fan-out cut after
one batch of 256 rows; and the byte cut after two batches at 54 bytes.

After the run the lane re-checked its outputs: the seven frozen digests,
each unit's frozen copies and start copies, the regenerated
`expected.json`, the frozen checker's re-judgment of the saved outputs
(the saved verdicts), record counts, no producer error, a clean lane at
`71a495a3` and C12's network namespace. This is the lane's own check, not
the integrity audit (above). D77.50 carries the run to the batch's tree:
U07 and U08 change only `scripts/package_smoke.py`'s installed check and
documentation, the specification among it, so its digest moves from
`f52aa9b2…` and a rerun of v7 on the final tree is refused for that
digest, while `src`, `tests`, `grammar`, `pyproject.toml` and `uv.lock`
are the Git objects of `71a495a3`. The wheel's metadata carries
`README.md`, which U08 changes, so a wheel of the final tree has other
bytes from the same `src`.

The re-check outside the lane, on 2026-11-21, read what survives. The
run's directory, with every unit's saved outputs, was lost with the
integration host's disk; the qualification folder survives, with the
freeze, the run commands, each step's console output and the lane's
digests and self-check. What it read agrees with the verdicts. The
folder's 29 listed digests and the seven frozen ones (`FROZEN.sha256`
`88400bc5…`) hold, and the four frozen helpers are byte for byte those
of `71a495a3` and of the published `df8817d3`. The two scripts are the
ones the run commands name; the host gate held before each of the six
steps, which ran once each, in order, from 01:25:35Z to 01:36:03Z, each
with exit status 0, and U0, U1, U2 and U3 each printed ACCEPTED, U0 after
its 26 skip lines. The run directory's list of 871 digests, which the
folder's digests bind, gives every unit the freeze's start copies and
its `expected.json` (`1a82f426…`), and U2 and U3 one wheel, `44c964a6…`.
The frozen oracle, run again in a fresh `-I` interpreter with neither
DuckDB nor PyArrow loaded, wrote that `expected.json` byte for byte on
CPython 3.13.13 and on 3.12.13; its 30 cells declare 633 sub-cases, the
record count of U1, U2 and U3, and U0's four cells 46, which with the
26 skip lines make U0's 72. As the negative control, the frozen
checker's self-test on it accepted the four honest units and the other
admitted outcome and gave each of its 220 fabricated shapes the refusal,
VOID or DEGRADED it must get. `src`, `tests`, `grammar`,
`pyproject.toml` and `uv.lock` are the same Git objects at `71a495a3`
and at `df8817d3`, as D77.50's carry states. The re-check could not
re-judge the saved outputs with the frozen checker, as B2's re-check
did for T06, nor read each unit's identity, C12's namespace or the
observations above, which only the lane's own run record and self-check
now state.

## Budget, failures and Gate 2

The tier runs on its own ledger P79T2, `C61/F196/D4,850/S4` under PL.15
(D79.22); the self-join spent about `C0/F3/D95/S0` outside the slices'
allocations. The lead charges each workflow after it ends, on the
owner-held ledger outside Git. Failures are kept, never rerun as
replacements: U06's four dry runs on draft freezes, two of whose U1 runs
were refused by law 3 before the freeze, are outside the run and are not
v7 outputs.

No review over the whole published chain is recorded as its batch audit.
By the lead's record and the P79T2 ledger, the chain was reviewed in
parts: the first batch, U01 with the types and the arithmetic, by a
batch audit with two lenses on 2026-11-17, whose medium findings were
fixed and verified clean, with a second round asked for; U01–U05,
integrated on `900e8915`, by three lenses, one of them on the merged
correctness, verified clean with two low layout items that U06 took up;
the self-join by two lenses and a verification; U06's preregistration
by two lenses, verified clean; the run by the audit outside the lane
(above); and U07 and U08 by one lens, whose five lows `13962f7e` and
`8dac5fca` repaired, verified clean. Their reports were in the workflow
journals that the disk loss took, and only the record's results survive.
By the lead's ruling of 2026-11-21 (2), a batch audit of the whole chain
ran post hoc ([below](#the-post-hoc-batch-audit)).

The batch Gate 2 ran once, on the batch's final tree `3aeb74f2`
(`8dac5fca`), on the integration host, because `docs/development.md` is
on a VR2 acceptance rule path, on 2026-11-18: its preflight began at
02:22:14Z, and `scripts/validate.py` ran from 02:25:01Z to 02:37:49Z with
the qualified storage and SQLite classes and passed in 768.5 s, with
pytest at 671.21 s on 20 workers (31,384 passed, 162 skipped, none
failed, of 31,546 collected). Its package smoke (02:37:49Z to 02:39:55Z)
built the `0.2.1` wheel and sdist and passed the core and
`execute-duckdb` cells, the latter with a real `duckdb_arrow` query, and
the five interop cells; the six interop consumers and the sdist member
check followed and passed. The DuckDB extra start (02:42:00Z to
02:42:40Z) passed 284 tests of `tests/test_execution_api_duckdb_arrow.py`
and `tests/test_sql_duckdb_emission.py`, the 56 and 228 nodes of the
acquisition review, on 2 workers in an `execute-duckdb` environment,
none skipped; the `sqlite_file` route's file then passed 80 tests in the
same environment, none skipped (02:42:40Z to 02:43:23Z). The tree was the
same before and after. The run sealed `8dac5fca`, whose message alone was
then amended with its Gate 2 line into `df8817d3`, and `900e8915..df8817d3`,
11 commits, was pushed under PL.52 (D79.21) at 02:44:31Z by the lead's
record. Its natural exact-head CI
[`44225459194`](https://github.com/MianliWang/pietto/actions/runs/44225459194),
push/main attempt 1, passed all 21 jobs from 02:44:33Z to 03:07:00Z:
Python, Compiler / Package and Windows on 3.12 and 3.13, the six runtime
jobs of each Python (shared acquisition, plan and emission portability
and the three general runtime shards), Target postgres, Target mysql and
the target conformance aggregate.

The Gate 2 launcher that ran this Gate 2 was lost with the integration
host's disk. The launcher rebuilt on 2026-11-20 keeps the DuckDB extra
start (78-6): after the validation, the package smoke, the interop
consumers and the `sqlite_file` route's file, it runs
`tests/test_execution_api_duckdb_arrow.py` and
`tests/test_sql_duckdb_emission.py` in an `execute-duckdb` environment,
with `duckdb` `2.0.0` and `pyarrow` `26.0.1`. Each of its four runs on
2026-11-20 passed that step with 284 tests, none skipped; the last, the
Gate 2 of `100bd786`, the tree of `65c22852`, ran it from 20:07:47Z to
20:08:01Z. The launcher does not itself refuse a skip in that step; the
count is read from the step's log.

## The post-hoc batch audit

The chain `900e8915..df8817d3` had its batch audit post hoc on
2026-11-21, by the lead's ruling: one round on `main` `65c22852`,
focused on issues across slices, with four lenses (semantics, readers,
tests, records) and three skeptics for each finding of medium or worse.
None was high. Nine mediums were confirmed by all three skeptics, two of
them one defect that two lenses found, and nine lows were kept; each is
an existing defect of `main`, repaired under PL.13 (b) by a commit on
`65c22852` that joins the `0.2.2` batch (O-1):

- A grouped `order by` an arithmetic output, which rules 1–29 passed and
  rule 30 then refused as PIE-B1008 `plan_ast_correspondence`, is rule
  8a's (fix: refuse a grouped DuckDB order key that reads arithmetic).
- Rule 5 named an admitted JOIN or the statement for an `any(...)` filter
  after the JOINs; it names the `any(...)` (fix: report DuckDB rule 5 at
  an any(...) beside admitted JOINs).
- Five stated rules had no pin, so a mutant loosening each passed every
  owner: the capture's checks of every later input, the JOIN whose kind
  makes arithmetic nullable in a chain, rule 16's JOIN and operand counts,
  the refusal of `Decimal` arithmetic, and rules 9 and 8b beside a refused
  JOIN. Five test commits pin them, and each pin fails with its rule
  loosened.
- The sql-emission v2 contract gave DuckDB no `Decimal`, `Date` or
  `Timestamp` parameter tag (docs: state DuckDB's parameter tags in the
  sql-emission v2 contract).
- The lows: two test commits pin that an aggregate over one source checks
  no declared key and the route's skip of empty batches and its
  `batch_rows` check; two documentation commits bring the specification,
  the roadmap, the route and the arithmetic note up to the tier's close
  and narrow lesson 79-1; and this record states the integrity audit's
  deadline ([above](#route-items-due-at-the-second-tier)).

The audit's report and its skeptics' votes are kept in the lead's record
outside Git.

## Phase82 inputs

The [freeze ledger](../../roadmap.md#phase82-freeze-ledger)'s DuckDB Arrow
route row now names the second tier's surface: the three types with their
storages, `Int` arithmetic by range proof and checked `Float` arithmetic,
`inner` and `left` equality JOINs with one source read twice, a tuple of
inputs with the capture limits per input and over all inputs and the
declared key check, and the reading of every result in batches. The route
stays alpha until the Phase82 freeze rules on it.

## Next-phase handoff

- **Opened.** On DuckDB `2.0.0` with `pyarrow` `26.0.1`, CPython 3.12 and
  3.13, Linux x86-64: B1's projection; B2's grouping, `having`, order,
  limit and predicates; and the second tier's types, arithmetic, JOINs over
  several inputs, one source read twice included, and batch reading.
- **Kept refused, and why.** `right`, `full` and `cross` JOINs, other
  `on` forms and `Decimal` keys, which D79.17 kept out of T1; `/`, `%`,
  `Decimal` arithmetic, nested arithmetic and computed keys, predicates and
  aggregate arguments, outside T3; `sum` and `avg` of a `Float` or a
  `Decimal` and `avg` of an `Int`, as the B2 audit states; a `having` over
  a `Date`, `Timestamp` or `Decimal` output; `UUID` and nested fields;
  `--literal-policy bind-safe`; bundles, saved results, relay, jobs and R2;
  single-file `--dialect duckdb`; and other DuckDB releases and platforms.
  Each stays refused until a Gate 1 opens it, and the Phase82 freeze rules
  on the surface by its ledger row.
- **Phase82.** The freeze ledger's DuckDB row (above), and its JOIN key
  and grain row, which PL.61 decided and JF's J2 aligns before Phase82's
  Gate 1; the route reads JOIN facts only from the verified plan.
- **Debt.** None of the tier's own: the lead ruled that the re-check of
  U06's run stands for its integrity audit, and the chain's batch audit
  ran post hoc, its repairs joining the `0.2.2` batch (above). The
  ten-slowest profile's one finding, the checker's self-test, is kept,
  and the rebuilt Gate 2 launcher keeps the DuckDB extra start (above).
