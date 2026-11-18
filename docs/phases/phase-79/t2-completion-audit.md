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
own publication: the batch's Gate 2 and natural CI are recorded by the
first documentation commit after its push, before the `0.2.2` release
commit (D79.21).

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
JOIN form by form.

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
(below), and the batch Gate 2's DuckDB extra start runs them again.

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
  independent audit. Owner: the lead, before the batch Gate 2.
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
  the specification; B2's batch audit compares them again.

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
publication; it is NOT_OBSERVED here (PL.07). The lead owns it, with B2's
profile of `43888270979`, before the `0.2.2` release commit.

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

## Budget, failures and Gate 2

The tier runs on its own ledger P79T2, `C61/F196/D4,850/S4` under PL.15
(D79.22); the self-join spent about `C0/F3/D95/S0` outside the slices'
allocations. The lead charges each workflow after it ends, on the
owner-held ledger outside Git. Failures are kept, never rerun as
replacements: U06's four dry runs on draft freezes, two of whose U1 runs
were refused by law 3 before the freeze, are outside the run and are not
v7 outputs. The batch Gate 2, its batch audit and its natural CI are the
lead's and are recorded after the push (D79.21).

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
- **Debt.** The independent integrity audit of U06's run; the batch's
  Gate 2, batch audit and natural CI, recorded after the push; the
  ten-slowest profile of the batch head; and the Gate 2 launcher's DuckDB
  extra start, which keeps running the route's owners without skips
  (78-6). Owner: the lead, each before the `0.2.2` release commit.
