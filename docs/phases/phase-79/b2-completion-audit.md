# Phase79 B2 completion audit

Phase79 B2 is the second slice of the Phase79 [route](route.md#b2--the-second-slice):
tier 1 of PL.47 on the
[DuckDB Arrow route](../../spec/duckdb-arrow-route-v1.md), which lets one
query over one `duckdb.arrow` source group with `count`, `sum`, `min` and
`max`, filter groups with `having`, order and limit its rows, and compare
fields and outputs with literals and parameters of four types, within higher
capture limits. Its decisions are PL.47, PL.50 and PL.54 beside B1's
D79.01–D79.16, AD79.01 and AD78.03 in the
[decision record](../../decisions.md). B2 is one
vertical: this audit closes B2's tier 1, not Phase79. It records delivery,
qualification and the acquisition review, and hands tier 2 to the owner's
plan (PL.54).
The batch that publishes T08 determines B2's completion through its Gate 2
seal and natural exact-head CI; this document does not certify its own
publication, and the first documentation commit after that batch is
published records the batch's facts here.

## Baseline and publication boundary

Gate 0 is bound to `8cb9d9de53e7ebf78a592ac85be206023c0f4dde` (tree
`b2ad91b2b9065680a121c5a19146c1e339c4b5ce`) with natural CI `43767179471`
(the route's [Gate 0](route.md#b2-gate-0-and-live-authority)). As the route
orders, `0.2.1`'s batch 2 and the interop relief were published first, as one
batch ending at `851ad83fafda9804e2bb4aa124241a74b1d237e7`, whose natural
exact-head CI `43814266697`, push/main attempt 1, passed all 21 jobs on
2026-11-16 (finished 06:26:35Z). B2's chain, the route commit and T01
included, was replayed onto that head and every later slice was built on it,
one commit per slice: the route `b6ee2f91`, T01 `862fa5f7`, T02 `73a93c55`,
T03 `c2c9f7fb`, T04 `ab132a7f`, T05 `24a8864e`, T06 `d68bd072`, T07
`bfe127bf` and T08, the commit that adds this audit. These are local
candidate commits; a later replay changes their ids, and the batch's record
names the published ones. The Phase81 Gate 0 that the owner then stopped
(PL.54) read the health of `851ad83f`
with the read-only token (PL.07) on 2026-11-16 at 06:31Z to 06:32Z:
INSUFFICIENT_EVIDENCE with no comparable sample, current screen WATCH, and
among its 24 advisory signals `SHARD_IMBALANCE_REVIEW` for the 3.13 runtime,
up from WATCH at `43767179471`, and `SHARD_IMBALANCE_WATCH` for 3.12. The
lane that wrote this audit holds no token and cites that reading. Health is
advisory; the batch's Gate 2 binds the health of its own base.

B2 has one release-note fragment, `79-t02-duckdb-grouping.md`, which T02
adds; T03, T04, T05 and T08 edit their own lines there and add no second
fragment (the specification's open items). B2 publishes as one batch under
PL.52's standing push authorization on D77.06's conditions. T02's
suggestions name forms that T03 and T04 open, so no part of the chain is
pushed without the rest.

## Accepted scope

| Slice | Delivered |
| --- | --- |
| T00 | The offline probe before Gate 0 that PL.47 allowed, outside the repository; its facts are the specification's [B2 pin facts](../../spec/duckdb-arrow-route-v1.md#b2-pin-facts-t00) and are not qualification evidence. |
| T01 | B2's specification, written as a section of the route specification before any B2 code, with the refusal texts that the owner agreed to as written (PL.50). |
| T02 | `group by` with `count()`, `count(f)`, `sum` of an `Int` field and `min` and `max` of an `Int` or `Float` field, an aggregate without `group by`, and `having`; `sum` written as `CAST(sum(...) AS BIGINT)`; rules 7a and 7b and the rewritten suggestions; B2's release-note fragment. |
| T03 | `order by` and a static `limit`, with qualified or restated keys and NULLS clauses that place NULL as the PostgreSQL emitter does; rule 8a. |
| T04 | `where` and `having` comparisons with literals and parameters of four types, NULL tests, `and`, `or` and `not`, the typed literal and parameter spellings and several parameters, bound in `execute()`; rules 8, 8b and 9. |
| T05 | Capture limits of 1,048,576 rows and 256 MiB of the selected columns in the order rows, schema, bytes, values; `memory_limit` 1 GiB; the `default_collation` read-back. |
| T06 | The native qualification v6: S06's four helpers evolved in place, attempt `p79b2-t06-20261116T094519Z` judged U0, U1, U2 and U3 each ACCEPTED on its first attempt on 2026-11-16, with no void and no rerun (below). |
| T07 | Three B2 queries beside B1's in the `arrow-ready` cell of natural CI, through package smoke; `ci.yml` unchanged. |
| T08 | The shared pages, the freeze-ledger row, the specification's construction state and open items with its B2 section emptied and removed, this audit and B2's acquisition review. |

T08 applied the specification's B2 hunks
([shared-page hunks](../../spec/duckdb-arrow-route-v1.md#shared-page-hunks)),
one page at a time: `docs/spec/diagnostics.md` (the `PIE-B1003`,
`PIE-R1002`, `PIE-R2006` and `PIE-R3003` rows), `docs/execution.md` (the
query, capture, session and failure items of the DuckDB Arrow route section
and the support-matrix row), `docs/project-package.md` (the DuckDB part of
the `operator_environment` row), `docs/capabilities.md` and `README.md` (the
DuckDB local path, each capability row run once through `check --project`
and `emit-sql --project --dialect duckdb` on T08's tree), `docs/roadmap.md`
(the Third dialect paragraph and the freeze-ledger row) and
`docs/status.md` (the Phase79 DuckDB B1 row's sentence on B2).
`docs/language.md` needs no change: its `duckdb.arrow` paragraph defers to
the specification. No other target's page changes. The route has SQLite
B2's S16 edit the shared pages before T08; S16 had not reached `main` when
T08 wrote them, so T08 wrote first, and whichever of the two batches is
pushed later rebases onto the other.

The run of the capability rows found one shared-page sentence that the code
contradicted: `docs/project-package.md` said that `operator_environment` is
needed for an ordering or a limit, while a DuckDB statement needs it only
with a `where` or a `having`, as the specification's premise table states;
an `order by`, a `limit`, a `group by` or an aggregate alone was VERIFIED
without it. T08 corrected that row. T07's review handed T08 the capability
page's "one real query", which now says four, B1's and B2's; the B1 audit's
sentence on S07's one query describes B1 and stays.

## Acceptance layers

**Observable.** The specification, the fragment, the capability rows and
the shared pages state each opened form, each form kept refused and each
limit. Each capability row was recorded on T08's tree: the five forms
marked yes were VERIFIED, and each refused form reported exactly the
blockers its cell names.

**Existing.** Emission tests live in `tests/test_sql_duckdb_emission.py`
and execution tests in `tests/test_execution_api_duckdb_arrow.py`. No B2
commit touches `tests/fixtures/golden/`, a PostgreSQL or MySQL emitter or
the firewall of `tests/test_repo_static_checks.py`; B2's `src` changes are
the DuckDB adapter (`project_duckdb_emission.py`, `project_duckdb_sql.py`,
`project_duckdb_result.py`) and `execution/_duckdb.py`. The batch Gate 2
reruns the golden and package checks and the firewall on the batch tree.

**Connected.** `compile_query` builds a live query only from a VERIFIED
document; `execute()` runs real DuckDB in T06's U1–U3, and U2 and U3 run the
installed wheel on CPython 3.13.13 and 3.12.13. Natural CI's `arrow-ready`
cell runs one B1 and three B2 queries through package smoke on both
Pythons (T07); T07 ran that cell on both Pythons on the integration host
and showed with negative controls that a wrong order or a wrong value
fails it. B2's pytest cells skip on every CI job, none of which installs
`execute-duckdb` (lesson 75-3): in T07's CI-shaped environment
`tests/test_execution_api_duckdb_arrow.py` had 7 passes and 27 skips,
every skip "the capture needs PyArrow", where the integration host had 34
passes. The batch Gate 2 records the same pair on the batch tree.

## Compiled compatibility

`VERSIONS` is unchanged and no compiled record changed. B1's DuckDB
documents keep their bytes, and T04 states the same for T02's and T03's
statements in its commit. A B2 document
may carry the `physical_type` values `duckdb_double`, `duckdb_varchar` and
`duckdb_boolean` beside `duckdb_bigint`, and columns that name a
`group_key`, an `aggregate` and a `function`. `export_bundle` still refuses a
DuckDB query (`PIE-R1004` `DUCKDB_BUNDLE_ENTRY`), and saved results, relay
and jobs do not take the route, so B2 adds nothing to migrate.

## Route items due at B2

- **Inform of the derived rows.** The specification's open item names B2's
  derived rows, due before T02 sealed. That point was missed: T02 sealed
  first. The lead's status report to the owner of 2026-11-16 named the item
  overdue and listed part of it. Owner: the lead, who states the whole list
  to the owner before the batch Gate 2 and closes the row in the first
  documentation commit after that.
- **Fragment.** T08 compared the fragment with the specification and found
  no rule that differs. It added the links to the capability page and the
  execution guide and the qualified platforms; B2's batch audit compares
  them again.
- **Extension sync** (D76.12), read as B1 read it (the
  [B1 audit](completion-audit.md#route-deferrals-due-at-b1)): no B2 commit
  changes `grammar/Pietto.g4`, `src/pietto/semantic/catalog.py`,
  `aggregates.py`, `window_semantics.py`, an example or a `pietto` block of
  `README.md`, `docs/language.md`, `docs/style.md` or
  `docs/worked-example.md`. B2 adds no spelling, so it needs no sync patch,
  and no extension push is authorized.
- **`having` coverage.** T06's cell C18 qualifies `having` over `Int`
  outputs (`count` and `sum`) only. No native cell covers a `having` over a
  `Text` or `Bool` key or a `Float` `min` or `max`; their evidence is C20's
  four-type `where` cells and five
  probes of T06's reviewers (`having note > "a"`, `low < 0.0`, `low == z`
  with `z = -0.0`, `ok == True` and `note <= t` with `t` holding NUL), each
  equal to the hand result. The capability page and the fragment state
  `having` qualified as one form, which C18 represents; for the other
  output types it stands on that evidence until a v7, whenever one runs,
  adds the cells. Owner: the lead, who decides whether the public pages
  say so.
- **Memory margin.** L13's statement fails with `OutOfMemoryException` at
  the 1 GiB `memory_limit`, as v6 expects, and T06's reviewers saw it
  succeed at 1.25 and 1.5 GiB and fail again at 2 GiB: the margin is narrow
  and not monotone. L13 does not separate the `memory_limit` value; C10's
  read-back does. A new pin or a v7 first measures that statement around
  1 GiB.
- **Integrity audit.** The route asks for an independent integrity audit
  of T06's verdict. The audit that read the saved outputs, digests and
  verdicts was run by T06's own lane after the run; two independent
  read-only reviews of the lane's head followed, found errata in the
  preregistration's text and the margins above, and changed no frozen file,
  saved output or verdict. Owner: the lead, who records whether those
  reviews stand for the independent audit or has one read the saved run
  before the batch Gate 2.
- **Midpoint.** The route places B2's midpoint after T02–T05 are integrated
  and before T06, with a record and the owner's tier-2 decision. The lane's
  dispatch ran T06 after T05 without that stop, and no midpoint record was
  written before T06; the lead reported the missing stop to the owner on
  2026-11-16. The owner answered after T06–T08 had run, T06's
  preregistration having been frozen and its run made before the answer:
  tier 1 is pushed as it stands, and tier 2 goes into the owner's plan.
  PL.54 records that answer as the midpoint's record (see the
  [handoff](#phase79-handoff)).

## B2 acquisition review

Base: `851ad83f`, onto which the chain was replayed. B2 adds no test owner
and no helper. It changes two owners, `tests/test_sql_duckdb_emission.py`
(20 test functions to 32, 723 lines added and 12 removed) and
`tests/test_execution_api_duckdb_arrow.py` (28 to 33, 262 added and 21
removed); the shared helper `tests/_pietto_sql_duckdb.py` (50 added and 2
removed, the 2 its docstring); the four frozen helpers
`tests/_pietto_execution_duckdb_native_*.py` (1,558 added and 90 removed),
which are the preregistered experiment's bytes and acquire nothing that an
owner reads; and the harness self-test in `tests/test_harness_execution_api.py`
(8 added and 5 removed), which keeps its fresh interpreter for the oracle.
`tests/_pietto_sql_duckdb.py` gains the statements `GROUPED`, `ORDERED` and
`PREDICATED` with their SQL and changes no existing value, so its direct
existing consumers, `tests/_pietto_execution_duckdb.py`,
`tests/test_sql_compile_api.py` and `tests/test_cli_project_emit_sql.py`,
acquire nothing new.

Timings are those of T08's focused pytest start (2026-11-16, 10:50:42Z to
10:50:59Z, `-n 4 --dist=loadfile`, seven files in the lane's environment
with every extra: 482 passed, none skipped). The emission owner's 132 nodes
summed 3.85 s, of which B2's 51 new nodes 1.18 s; the execution owner's 34
nodes summed 14.98 s, of which B2's six (five new and one renamed) 4.58 s.

Classified:

- **Repeated acquisition, kept.** A VERIFIED emission of `PREDICATED` is
  made twice in the emission owner (its placeholder order and its forged
  predicates) and of `ORDERED` twice (its order rules and its forged
  grouped artifact), each 0.03 to 0.05 s. The forgery cells replace the
  artifact they read, so sharing would need a module fixture that copies
  it; at about 0.08 s per run this is low-value repetition, which the
  procedure does not consolidate. Owner: the next slice that edits the
  owner, if it measures more.
- **Distinct inputs, fresh.** Each parametrized form of the emission owner
  (`FILTER_FORMS`, `GROUPED_FORMS`, `ORDERED_FORMS`, `SHAPES`,
  `BROKEN_PREDICATES`) writes and emits its own project or checks its own
  AST, and the node-limit cells emit one project per limit; their inputs
  differ.
- **Execution, fresh.** The execution owner's B2 cells compile the
  statements they run and open their own `:memory:` session per attempt,
  which is the property under test (nothing is pooled).
- **The frozen helpers** are T06's experiment and change only by a new
  preregistration; the harness self-test starts one fresh `-I` oracle
  interpreter, since only a fresh process shows that the oracle runs without
  DuckDB.

Structural improvement: none needed; wall-time improvement: none claimed;
no-gain: the two repeated emissions above. The bounded ten-slowest profile of
step 4 reads the final natural CI health of the batch head after
publication; it is NOT_OBSERVED here (PL.07) and is owned by the first
documentation commit after publication.

## T06's run on the T08 tree

T06's run was made on the lane head `6895d347` (tree `67127ffc`) with the
specification digest `38d8bfa2…` that its frozen helpers bind
(`SPEC_SHA256`). T06's repair `d68bd072` then narrowed the specification's
`having` text, T07 changed `scripts/package_smoke.py` and documentation, and
T08 changes documentation only, so the specification now has the sha256
`46fda42fbda97fda06c486065dbe67dcee38b7a83b17f22153736ea65c8a7a85` and a
rerun of v6 on this tree is refused by its checker for that digest and
needs a v7. D77.50 carries the accepted run: on `6895d347` and on T08's
tree the `src`, `tests` and `grammar` trees and `pyproject.toml` and
`uv.lock` are the same Git objects (`src` `6d09914a…`, `tests`
`cfa2b526…`, `grammar` `eb25ec59…`, `pyproject.toml` `c85ed001…`,
`uv.lock` `015f5dca…`), so the compiler, the frozen helpers and every
document of the experiment that the compiler derives are byte for byte the
same, with the same pins and runtime. The wheel that U2 and U3 installed
(`969610d1…`) carries the `README.md` of its tree in its metadata; T08
changes that file, so a wheel built from T08's tree has other bytes from the
same `src`.
U2's and U3's install steps ran the tree's `scripts/package_smoke.py`,
`f53bf498…` on `6895d347` and `a18d6be1…` on T08's tree. T07 changed only
its installed check, which now runs B2's queries beside B1's; the build and
the installed closure are unchanged, and T07's package smoke on its own
tree built a wheel with the same sha256, `969610d1…`.

The published batch ends at `107df991` (tree `a348295c`), the lead's typing
repair, first committed as `e1570b5e`, whose message alone was then amended
with its Gate 2 line. Since T06's integrity audit was the lane's own, the
lead had v6 re-checked independently, and the re-check judged it
ACCEPTED_CONFIRMED: it checked the seven frozen digests, the start copies,
the run commands, exit statuses and times, the record counts and the
negative control, and its own re-judgment of the stored outputs with the
frozen checker gave the stored verdicts. The specification's sha256
moved after the freeze, from the frozen `38d8bfa2…` to `2bbb130e…` at
T06's repair `d68bd072` and to `46fda42f…` at T08 `a5615003` and the published head,
while `src`, `grammar`, `pyproject.toml` and `uv.lock` are the same Git
objects and the frozen helpers are byte for byte the same, so D77.50
carries the run to the published tree. That tree's `tests` differs from
T08's only by the typing repair, in `tests/test_sql_duckdb_emission.py`,
which is not a helper. The run's command record, written 4 s after the
freeze, is among the run's digested evidence, as section 8 of the
preregistration allows.

## Budget, failures and Gate 2

B2 runs on Phase79's ledger, `C240/F720/D8200/S8` plus half of PK, raised
by PL.15 when a dimension reaches 80% of it; tier 1 plans about
`C60/F190/D5,050/S4`. By the owner-held ledger's last row, at 07:55Z on
2026-11-16, Phase79 had used about D4,331 (53% of D8,200), with T00 at D30
and the Gate 0, route and T01 work, a stopped first round and a Phase81
sheet revision included, at D282 and F3; the ledger's D30 counts the probe
lane's Bash commands, and the route's T00 row keeps the probe's own count,
D26. T02–T08, their reviews and repairs included, are charged after their
workflow ends. Owner: the lead, on the ledger outside Git.

Failures are kept, never rerun as replacements: T02's first candidate
`28279098`, T04's `98eb2a4f`, T05's `f1e6c6fa` and T07's `74b256c7`, each
replaced before delivery; T06's rehearsals, of which the second's U1
was REFUSED by law 3 on cell C18 before the freeze, and T06's run tree
`6895d347`, whose specification the repair then changed (above); and T07's
first negative-control attempt, which was void. Each slice was reviewed
independently before it was delivered.

Gate 2 has not run: it runs once on the batch's final tree, on the
integration host, because `docs/development.md` is on a VR2 acceptance rule
path. The first documentation commit after publication records here its
tree, start and end, the `scripts/validate.py` and pytest durations with the
worker count and the passed and skipped counts, its package smoke, the
DuckDB extra start with the two DuckDB owners' passes, and the natural
exact-head CI with its jobs.

## Phase82 inputs

The [freeze ledger](../../roadmap.md#phase82-freeze-ledger)'s DuckDB Arrow
route row now names B2's surface: the compile refusals with B2's details and
suggestions, the grouped, ordered, limited and predicated forms with their
SQL spellings and `physical_type` values, the capture limits with their
check order, and the session's 1 GiB `memory_limit` and `default_collation`
read-back. The route stays alpha until the Phase82 freeze rules on it.

## Phase79 handoff

- **Tier 2, the owner's plan.** Several sources and JOINs with a
  multi-input execute API (the sheet's Q3), `Date`, `Timestamp` and
  `Decimal`, and computed columns go into the owner's plan for the later
  phases, as the owner answered at B2's midpoint after T06–T08 had run
  (above; PL.54). Tier 1 closes as it stands, and until a phase of that plan
  opens such a form, the Phase82 freeze rules on each by its ledger row.
- **Opened.** Grouping with `count`, `sum`, `min` and `max`, `having`,
  `order by` and `limit`, and `where` and `having` predicates over literals
  and parameters of `Int`, `Text`, `Bool` and `Float`, within 1,048,576 rows
  and 256 MiB of the selected columns.
- **Kept refused, and why.** `sum` of a `Float`, since DuckDB returns an
  infinity on overflow and the checked spelling that T00 saw has no
  qualification cells (the lead, by the Phase82 freeze, since the midpoint
  answer did not rule on it);
  `avg` of an `Int` or a `Float`, beyond PL.47's tier and with the same
  overflow for a `Float` (the owner); a `Text`
  literal that holds NUL, since T00 saw only the parser keep it (the lead,
  by the Phase82 freeze); comparisons of two reads or of an `Int` with a
  `Float` and a bare `Bool` test, since PL.47 names comparisons with
  literals and parameters; computed values, keys and order keys, other
  aggregates, `distinct`, windows, set operations, relation lets, derived
  sources and JOINs; `Decimal`, `Date`, `Timestamp`, `UUID` and nested
  fields; `--literal-policy bind-safe`; bundles, saved results, relay, jobs
  and R2; single-file `--dialect duckdb`; and other DuckDB releases and
  platforms. The route's [B2 deferrals](route.md#b2-deferrals) name each
  one's owner and latest point.
- **Reminder 8.** It stays satisfied by exclusion: B2 has no JOIN and, since
  bundles still refuse DuckDB, no new consumer of compiled admission. It
  passes to the first slice that admits a JOIN.
- **Debt.** The derived-rows inform, the integrity-audit record and the
  `having` and memory-margin items above; the ten-slowest profile of the
  batch head; and the Gate 2 facts, which the first documentation commit
  after publication records.
