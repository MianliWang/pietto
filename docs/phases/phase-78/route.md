# Phase78 route — SQLite B1, Gate 1 approved, Gate 0 bound (health and overlap pending)

Phase78 owns the Phase 78 row of the [roadmap](../../roadmap.md), SQLite deep
adaptation. On 2026-11-10 (America/Toronto) the owner approved the Gate 1 of
its first vertical, B1, with the recommended answers of the Gate 1 decision
sheet: single-file SQLite SQL for a flat subset, qualified in process on one
measured SQLite build. AD78.02 revises the schedule of AD78.01 so that B1 runs
beside Phase77 and Phase79; AD78.03 fixes the third-dialect seam it shares
with Phase79; D78.01–D78.05 bind its scope, value rules, target identity,
errors and budget; and the rows PL.01–PL.06 hold the answers shared with
Phase79, Phase80 and the editor core ([decision record](../../decisions.md)).
Local implementation in worktrees is authorized from Gate 0 (PL.01, PL.02).
No commit, push or release is authorized by this route; each batch push needs
the owner's authorization. SQLite is not a `0.2.0` requirement (decision row
"`0.2.0` and later versions"), and B1 closes as B1, not as Phase78.

Gate 0 binds the head and its natural CI; the read of that CI's eligible health and alerts and the re-measured Phase77 overlap are pending until the package's first implementation batch records them.

Before Gate 0, these runs happened besides paper records (PL.02). The PyPI
metadata and hash fetch and isolated install probe of PL.05 (a), which sheet
Q3 A authorizes, read PyPI JSON at 2026-11-10T11:32:46Z; the lead's record of
the owner's approval of Q3 A that day carries the earlier `modified` time
11:32:37Z. Earlier, during the read-only Gate 1 drafting and before that
approval, the SQLite draft ran an in-memory `sqlite3` probe that its critique
repeated, and the Phase80 draft took a PyPI reading. No authorization is
recorded for these two: they were unauthorized preparation, and their results
are not evidence. Phase78 Q0 measures the SQLite build and its listed cells in
the Gate 0 environment, and the PL.05 probe replaces the PyPI reading. Every
implementation slice starts from the published head that Gate 0 binds (PL.02).

## Starting point

Gate 1 was drafted on `569c365dbb66d48d87da4dfca0982e09d21d0061`, tree
`5561238f181887274dbadbdd5fa848998cfa1872`, an unpublished candidate of the
maintenance/editor batch. The batch was published instead as `befa5de8`,
`6a1eb9c9` and `ab972f36`. Gate 0 of every B1 lane is bound to that published
head, not to the draft head (PL.02): `main` at
`ab972f362c433b234a74f542c5d274d22c8cdeae`, tree
`821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`, whose natural exact-head CI
`42831340276`, push/main attempt 1, passed all 21 jobs. At that head it
rebinds branch, tree, remote, fast-forward state, CI run and attempt, and that
CI's qualified health and alerts (an absent history is not a green result).
The code that this route cites is the same on both heads. It also reads the
[Phase76 completion audit](../phase-76/completion-audit.md), the published
Phase77 batch facts, the Phase72–Phase76
[engineering lessons](../../references/engineering-lessons.md), and the
SQLite build of the integration environment (Q0).

Phase77 has no completion audit yet, so the gate obligation to consume the
previous completion audit is `NOT_APPLICABLE` for this Gate 1: Phase77 is in
progress and runs in parallel (PL.01). Its owner is Phase77 S27; if
that audit exists before S04, S04 reads it, and the Phase78 completion audit
always does.

## Scope

| B1 delivers | Not in B1 |
| --- | --- |
| `pietto emit-sql FILE --dialect sqlite`, text and JSON, over `where`, `select`, `order by`, `limit`, `group by`, `count`, `min` and `max` on `Int`, `Text`, `Bool` and finite `Float` fields, from `sqlite.table("name")` with a bare table name (D78.01) | project mode, so `emit-sql --project --dialect sqlite` stays a usage error and `compile_query(dialect="sqlite")` keeps PIE-R1002; any execution or result-reading route; opening a caller's `.db` file |
| Declared premises: `STRICT` tables, BINARY collation, UTF-8, `Bool` as INTEGER 0/1; explicit `NULLS FIRST`/`NULLS LAST` equal to the PostgreSQL emitter's placement (D78.02) | arithmetic, division by zero, `Decimal`, `Date`, `Timestamp`, `UUID`, nested values, JOINs, windows, constants and `--set`, `LIKE`-style text functions, schema-qualified or attached names |
| CLI JSON v1 admits `"sqlite"` as a successful `dialect` value; new SQL and JSON goldens (D78.01) | a public `pietto.sql` SQLite emitter, a new `PIE-*` code, a new dependency, any cross-database parity claim |
| In-process qualification on the measured build only, with a runner-acceptance domain row of its own (D78.03) | qualification of any other SQLite build, including hosted CI's |

Every form outside the table fails closed with a deterministic diagnostic.
B2 (project mode), the execution and file-trust questions, checked
arithmetic and the remaining types each need their own Gate 1.

## Decisions adopted

| Id | Adopted answer | Route consequence |
| --- | --- | --- |
| PL.01–PL.04, PL.06 | The answers shared with Phase79, Phase80 and the editor core: parallel start, separate ledgers, lane rules and the previous-audit item (PL.01); Gate 0 and the work before it (PL.02); host pytest workers (PL.03); integration and version line (PL.04); the planning ledger (PL.06) | Lane and integration rules; Budget |
| AD78.01 | Small Pietto-owned adapters; sqlglot only as a test oracle | Unchanged except its schedule sentence; B1 adds no sqlglot |
| AD78.02 | Revises AD78.01's schedule (sheet Q7 A′): B1 is implemented in parallel; its SQLite entries in the shared connector and dialect-set lines wait until Phase79 S02 (sheet lane D2) has integrated them; B1 publishes after DuckDB B1 | S02 depends on Phase79 S02; publication order is DuckDB B1 then SQLite B1 |
| AD78.03 | Third-dialect seam (sheet Q9 A, ARCHITECTURE_DECISION): Phase79 S02 lands the shared connector and dialect-set hunks first, and its family firewall lists `sqlite`; Phase78 S02 adds the SQLite entries only after that, serially, so those lines have one writer at a time; SQLite B2's shape is decided in the B2 Gate 1 | S02 write set; the firewall reruns on every integrated tree |
| D78.01 | B1 scope and public surface (sheet Q7 A′; SQLite draft Q1 A, Q2) | Scope table above |
| D78.02 | Value rules: the lead's ARCHITECTURE_DECISION from the SQLite draft's Q4 (first option), not an owner answer; stated to the owner as inform, at the latest before S02 seals | S01 text, S02 refusals, Q0 cells |
| D78.03 | Target identity and in-process qualification (sheet Q7; SQLite draft Q3 A, Q8) | Q0, S03 |
| D78.04 | `PIE-B1000` refusals, native errors by `sqlite_errorname`, independent `sql/sqlite*.py` modules: the lead's ARCHITECTURE_DECISION from the SQLite draft's Q5 and Q6, stated to the owner as inform, at the latest before S02 seals | S02, S03; the B2 seam choice is deferred to the B2 Gate 1 (AD78.03) |
| D78.05, D78.06, PL.09 | Cumulative `C80/F240/D2300/S3` from sheet §3.2, Phase78's own ledger, which the owner chose on 2026-11-11 (D78.06), ending the D1500 stop point, and doubled to `C160/F480/D4600/S6` on 2026-11-12 (PL.09) | Budget section |
| D78.07 | `scripts/validate.py` declares `--pietto-sqlite-class=qualified`, so the authoritative Gate 2 runs the native cells on the qualified build (owner, 2026-11-11) | S03 write set; Qualification method |
| D78.08 | The fixed PostgreSQL 18.6 image may run locally for the byte replays, under D77.02's conditions, on the Docker Engine (D77.19) (owner, 2026-11-11) | Qualification method; S03 |
| D78.09 | Identifiers use a quoting under which an unknown name is an error, with no new premise; no Teach observation; D78.02 and D78.04 stand as stated (owner, 2026-11-11) | S02; support matrix |
| D78.10 | The replay method under D78.08: one frozen, reviewed campaign that may contain void attempts and ends with its first `PASS` or `FAILED` run; its two hours are summed over all its attempts; the result is the lane's `tests/fixtures/sqlite/postgres_replay_v1.json` (lead) | Qualification method; S03 |
| D76.12, D76.13, D76.15, D76.17 | Extension sync rule; compiled `VERSIONS`; lane resource rules as PL.01 continues them; the D unit | B1 changes no compiled record, so `VERSIONS` stays; extension sync is deferred below |

PL.05 (dependencies, packaging and the shared lane PK) and the editor rows
ED.03–ED.06 do not bind B1, which adds no dependency and edits no editor
code; neither do the D79 and D80 rows, except where AD78.03 names Phase79
S02.

## Slices

Slice ids follow the release-note fragment rule; B2 slices continue from
S05 under their own Gate 1. Each slice binds its exact base tree, inputs,
write set, commands and acceptance when it is expanded; the table fixes
coverage, dependencies and the draft allocations of D78.05.

| Slice | Content | Write set | Checks and acceptance | Depends on | C/F/D/S |
| --- | --- | --- | --- | --- | --- |
| Q0 | Gate 0 rebind and probe matrix | None in the repository; the lane's own folder | Records interpreter, `sqlite_version()`, `sqlite_source_id()`, `PRAGMA compile_options` and each raw result; measures the pending cells (NaN and ±Inf into `STRICT` REAL; ±0 under `=`, GROUP BY, DISTINCT, `min`, `max`; `NULLS FIRST`/`LAST`; non-ASCII `Text` order; `Bool` in `STRICT` INTEGER; result types of `count`, `min`, `max`); repeats the build observation in the Gate 0 integration environment and on the CPython 3.12.13 on `PATH` | Gate 0 on the published D77.04 head `ab972f36` and its CI (PL.02); no probe cell runs before it | 0/0/100/0 |
| S01 | SQLite rules text | `docs/language.md` (a new SQLite section; the connector paragraph names `sqlite.table`); `docs/release-notes.d/78-s01-sqlite-single-file.md` | `scripts/release_notes.py check`; the existing docs owners; every `pietto` block as `pietto fmt` writes it; each stated rule matches a Q0 cell | Q0 | 10/30/150/1 |
| S02 | Single-file emitter and CLI dialect | New `src/pietto/sql/sqlite*.py`; `src/pietto/cli.py` (`_select_sql_emitter`); the SQLite entries, added only on top of the integrated Phase79 S02 lines and charged to this ledger (AD78.03), in `src/pietto/semantic/source_connectors.py` (`sqlite.table`), `src/pietto/ir/lowering.py`, the `cli.py` dialect set `_ENABLED_SQL_DIALECTS` and the `src/pietto/parser_api.py` header `dialect` hint set; `docs/spec/cli-json-v1.md`; `docs/spec/diagnostics.md` (the PIE-B1000 row); new `tests/test_sql_sqlite_emission.py`; new `tests/fixtures/golden/emit_sqlite_*` with `scripts/check_goldens.py`; in-place edits of `tests/test_sql_mysql_golden_corpus.py` and the existing header-hint owner; the S01 fragment | Focused pytest; Ruff; Pyright on `src` and on the changed tests (lesson 72-1); `scripts/check_goldens.py`, each new golden reviewed by a human with its input; repository-wide owners on the integrated tree (72-2); PostgreSQL and MySQL bytes of the existing goldens and documentation examples unchanged; each B1 form emits or refuses with its listed text; `tests/test_execution_api_postgres_rows.py:616` unchanged; the AD78.03 firewall still keeps `sqlite` out of the project PostgreSQL/MySQL pipeline | S01; Phase79 S02 in the integration tree | 30/90/800/1 |
| S03 | In-process qualification | New `tests/test_sql_sqlite_native.py`; a flat `tests/_pietto_sql_sqlite_*.py` helper only if shared; `tests/conftest.py` if an environment class option is needed; `scripts/validate.py` (the `--pietto-sqlite-class=qualified` declaration, D78.07); `docs/spec/validation-runner-acceptance-v1.md` (a new domain row); `docs/development.md` (SQLite target validation); `ci/workloads.toml` only if the CI workload governance requires a declaration | Native cells against oracles written before the run; a fabricated-output self-test fails every fail-open shape (72-4); PostgreSQL replays bind the bytes they ran (72-5); a forged non-qualified build is refused; skips are counted beside passes (75-3); a failed cell is first a question about its judge (74-1); a form without a passing cell ships refused (73-6). The runner-acceptance specification, `docs/development.md`, `scripts/validate.py` and `ci/workloads.toml` are VR2 acceptance rule paths, so the B1 batch runs its whole Gate 2 on the integration host, and under the owner's 2026-10-27 decision its natural CI is not recorded as a new bootstrap, so the Teach split stays void (PL.05, [validation runner acceptance](../../development.md#validation-runner-acceptance)) | S02 | 25/75/600/1 |
| S04 | B1 closeout | `docs/capabilities.md` (a new SQLite section, not new columns); the fragment's known limitations; this route (B1 record and B2 handoff); the roadmap freeze ledger; `docs/status.md` | B1 acquisition review against the B1 base; docs owners; CI health and alerts read; Gate 2 duration recorded | S03; publication after DuckDB B1 | 10/30/250/0 |
| B2 | Project mode | Its own Gate 1 | — | The AD78.03 seam (Phase79 S02 and S03); Phase77 S26/S27 | own ledger |

The dialect-owned qualified-build constant lands in S03, not in S01 as the
sheet's draft row put it. This is IMPLEMENTATION_FREEDOM: B1 has no
production caller of the constant, so it lands with its first caller, the
qualification owner; it is not imported from `project_job_workspace.py`, and
it moves to `src/pietto/sql/` only when a production caller needs it. S01
states the rules; the build appears in the support matrix of S04.

### Usability row

| Spelling | Canonical form | Example | Refusal experience | Discoverability |
| --- | --- | --- | --- | --- |
| `sqlite.table("name")` | The existing call syntax, unchanged by `pietto fmt`; no grammar change | `source users: User = sqlite.table("users")` | A dotted or attached name fails `check` with the connector rules' `PIE-S2306` at the string (S01 confirms; another code needs the owner); a B1-excluded form fails `emit-sql` with `PIE-B1000` and a SQLite reason | `--dialect` help lists `sqlite`; `language.md` SQLite section; capability page SQLite section |

### Midpoint and unfreeze

**Midpoint (after S02 is accepted on the integration tree).** Each B1 form
emits with a reviewed golden or refuses with its listed text; the ledger's
measured rate projects within D78.05, with the replay count and D spent; the
latest published head's CI health and alerts are read; the acquisition
reserve for S04 is re-estimated; Phase79 S02 status is recorded, Phase77
S21–S24 are recorded as moved to the nested work package (D77.32), and the
sheet Q2 option-C check of PL.04 is done. S03 opens only after the midpoint
passes.

**Unfreeze conditions.** These need the owner: a form beyond D78.01; a new
`PIE-*` code or a public text outside the rows S02 lists; a dependency,
container, database run or network access beyond the PostgreSQL byte replays
of D78.08; executing SQL in the product or opening a caller's file; project
mode; an extension-repository push; a change of the AD78.02 publication
order; any ledger cap.

**B1 closure.** S01–S04 are accepted on the integration tree, Gate 2 passes
on the batch tree, and the batch publishes after the `0.1.11` cut and after
DuckDB B1 under its own push authorization, with green natural exact-head CI.
Phase78 closes later, after B2 and the third whole-tree test pass, with its
completion audit and next-phase handoff.

## Dependencies and pins

| Input | Status |
| --- | --- |
| SQLite library | Seen on 2026-11-10 by the SQLite draft's in-memory probe and its critique's repeat, unauthorized preparation that is not evidence (PL.02): CPython 3.13.13 in the canonical repository's `.venv` links SQLite `3.53.1`, source id `2026-05-05 10:34:17 c88b22011a54b4f6fbd149e9f8e4de77658ce58143a1af0e3785e4e6475127e9`, the same triple as `QUALIFIED_SQLITE` (`src/pietto/_project/project_job_workspace.py:59-110`), compile options including `ENABLE_MATH_FUNCTIONS` and `ENABLE_PERCENTILE`. `/usr/bin/python3` 3.14.4 links SQLite `3.46.1`. Pending Q0: the Gate 0 integration environment's build, the CPython 3.12.13 build, and the full compile-option comparison |
| Python packages | None added; stdlib `sqlite3` cannot be pinned by `pip`, so identity is the build triple. No `pyproject.toml` or `uv.lock` change; PL.05 and lane PK add nothing here |
| Hosted CI SQLite builds | Unobserved; not qualified whatever they are (CPython 3.12.14 and 3.13.15, runner table row 0b) |
| sqlglot | Not introduced by B1 (AD78.01 permits it only as a test oracle) |
| Phase79 S02 (sheet lane D2) | Lands the shared connector and dialect-set hunks first (AD78.03); it writes them in a shape that the SQLite entries extend, and its family firewall test lists `sqlite`. Only after it has integrated does Phase78 S02 add the SQLite entries, serially on the integrated lines and on this ledger, so those lines have one writer at a time |
| Extension sync | Whether `sqlite.table` is a built-in catalog change under D76.12 is read from the extension's sync inputs in S01. Known at Gate 1: `src/pietto/semantic/catalog.py` has no connector entries; the connector spellings live in `src/pietto/semantic/source_connectors.py:21-23`. If it is a catalog change, the sync is prepared as an unpushed, reviewed patch in a lane folder; its commit and push wait for the extension-repository authorization (sheet Q4, not approved). B1 does not depend on it; the exact owner is the extension lane after its authorization, at the latest before the release request that carries B1 |

## Qualification method

Qualification is in process (D78.03): the standard-library `sqlite3` on
`:memory:` or a test-owned file under the pytest base temporary directory,
`STRICT` fixtures, only on the measured build, with no Docker, engine lock
or network. Each cell records the source, emitted SQL bytes, fixture data and
raw result. Oracles are Pietto-owned expected results written before the
run, `tests/_pietto_ir_bag_null_oracle.py`, and byte replays of
existing PostgreSQL outputs in the D76.09 (1) shape: re-emit the PostgreSQL
statement, compare bytes, and reuse its saved result only when the bytes are
unchanged. A new PostgreSQL run is authorized only to produce these replays,
with the fixed PostgreSQL 18.6 image under D78.08; a MySQL run is outside
Phase78's authority and stops the lane. Controls cover NULLs, ±0, `Text`
case and non-ASCII order, `Int` extremes, `Bool` values and row
permutations, as a finite matrix rather than every permutation.

The new runner-acceptance domain row states its premise (the exact build
triple) per runner; row 3 (job-store storage) is not borrowed. As in the
job-store storage classes ([development](../../development.md)), hosted CI
asserts the refusal, a run meant to provide the build fails when it is
absent, and any other run prints a counted skip line. The authoritative
Gate 2 is a run meant to provide the build: `scripts/validate.py` declares
`--pietto-sqlite-class=qualified` (D78.07). SQL byte and golden tests run
everywhere.

## External reference

| # | SQLite, measured build |
| ---: | --- |
| 1 | SQLite `3.53.1` with the source id above, via CPython 3.13.13, as the unauthorized in-memory draft probe of 2026-11-10 saw it; not evidence until Q0 measures it. Upstream documentation was not re-read for this route; documented introduction versions (STRICT, NULLS FIRST/LAST) are verified by Q0 on the build instead |
| 2 | Embedded engine with no server; dynamic typing unless `STRICT`; the library comes with the interpreter, and compile options change the function set |
| 3 | Seen by that draft probe, not evidence: `9223372036854775807 + 1` gives REAL `9.223372036854776e+18` without error; `sum()` overflow raises `integer overflow`; `1e308*10` gives `inf`; `7/0` and `7%0` give NULL; `-7 % 2` is `-1` and `1/2` is `0`; `'a' = 'A'` and `'a' < 'B'` are false under BINARY; `-0.0` is transported but `CAST(-0.0 AS TEXT)` is `'0.0'`; NULL sorts first in ascending order; `round(2.5)` is `3.0` |
| 4 | Pietto produces SQL text only; the engine is chosen by the caller's interpreter, never by Pietto's package |
| 5 | Pietto relies on statement meaning only, not on engine algorithms |
| 6 | Identity through `sqlite_version()`, `sqlite_source_id()` and `PRAGMA compile_options`, which the job store already reads |
| 7 | In-process connections, no service lifecycle; tests own open and close |
| 8 | Silent REAL promotion, infinities, NaN into NULL (unmeasured), ASCII case-insensitive `LIKE` (unmeasured), a column `COLLATE NOCASE` breaking the premise, and the library differing between interpreters |
| 9 | Emit only forms whose meaning matches Pietto's law on the measured build; refuse arithmetic; declare the physical premises |
| 10 | WHAT_NOT_TO_COPY: type affinity coercion, REAL promotion, NULL from a zero divisor as a Pietto rule, engine-default NULL placement, NOCASE or `LIKE` folding, and the job store's constant as a shared owner |
| 11 | `language.md` SQLite section (S01), `sql/sqlite*` (S02), the qualification owner (S03), the capability page (S04) |

## Lane and integration rules

- B1 keeps its own cumulative ledger (D78.05); from the approval on it does
  not draw on Phase77's (PL.01, PL.06).
- Lanes follow the lane rules of PL.01 and the pytest worker rule of PL.03;
  Gate 2 shares the integration host under PL.01.
- Under PL.04, no B1 code, test, golden or release-note fragment
  (`78-s01-sqlite-single-file.md`) reaches `main` before the `0.1.11` cut.
  New files come first and shared hunks last; replays happen only at Phase77
  published-batch boundaries and carry the base delta with plumbing, each
  step's changed lines compared before and after (lessons 74-2, 75-1).
- Every lane starts from the latest integration head and is rebased onto it
  again before delivery; its brief names the base tree, and a verifier checks
  that tree first. A lane writes only under its own folder with absolute
  repository paths (75-4).
- Repository-wide owners and the AD78.03 family firewall run on every
  integrated tree. Shared documentation pages (`language.md`,
  `capabilities.md`, `diagnostics.md`, `cli-json-v1.md`, `development.md`, the
  runner table, roadmap, status, decisions) are edited serially at integration.
- Each slice that changes what a program can observe writes or edits its
  release-note fragment in `docs/release-notes.d/`.
- Only the lead records owner answers; a relayed owner message is not an
  answer for a lane (72-3).

Route and decision records (documentation only, with no code and no
release-note fragment) may reach `main` before the `0.1.11` cut, in a Phase77
batch under D77.06 or in a documentation and tool batch under D77.14;
Phase78–80 code and fragments may not. By the lead's ruling (PL.04, lead,
inform), this route reaches `main` in a Phase77 batch under D77.06, because
the batch also carries a Phase77 repair, counted on Phase77's ledger, that
returns PIE-B1003 refusals of project `/` and `%` instead of crashing. D77.14,
a rule for a whole documentation and tool batch, does not cover it.

## Risks

1. **A moving base.** The remaining Phase77 slices and Phase79 S02 move
   under B1 before it can publish. New files first, the D400 replay reserve,
   published-batch replay boundaries and the Q2 option-C check of PL.04 bound
   it.
2. **One qualifying build.** Hosted CI cannot run the native cells and a
   skipped test can pass without running. The explicit environment class,
   counted skips and byte tests on every runner bound it.
3. **Shared surfaces.** The connector and dialect sets are shared with
   DuckDB, and the extension sync cannot be pushed under this approval.
   The AD78.03 order on those lines (Phase79 S02 first, then Phase78 S02,
   one writer at a time), serial
   documentation edits and the recorded extension deferral bound it.

## Initiation-gate checklist

| # | Field | Answer |
| ---: | --- | --- |
| 1 | Live authority | Drafted on `569c365d`; Gate 0 is bound to the published D77.04 head `ab972f36` with natural CI `42831340276`, and rebinds its health, the Phase76 audit and published Phase77 facts (PL.02). The Phase77 completion audit is `NOT_APPLICABLE` (in progress; owner Phase77 S27; PL.01) |
| 2 | User/product outcome | Deterministic SQLite SQL for single-file flat programs, text and JSON; not project mode, execution, file reading, arithmetic, other types, parity or a `0.2.0` requirement |
| 3 | Semantic reference model | Existing single-file semantics in `language.md`, the Float value contract and checked `Int`; the PostgreSQL emitter's result for the same source is the value, NULL and order reference. Roots: AST, semantic facts, single-file IR |
| 4 | Identity model | Source occurrence; `sqlite.table` names one exact bare table; the dialect name `sqlite` is not a qualification; target identity is family, release, source id and compile options together; no alias to the job store's constant; no fallback to a PostgreSQL or MySQL branch |
| 5 | Construction states | A form is refused, emitted (bytes and golden) or qualified (a passing native cell). Publication is legal only for qualified forms; an emitted form without its cell ships refused |
| 6 | Proof posture | Asserted: the physical premises. Observed: nothing yet; the draft probe is not evidence, and Q0 observes the build triple and probe cells. Derived: SQL bytes. Verified: S03 cells against prewritten oracles. Unknown: other builds and the pending Q0 cells. Disproven: nothing yet; arithmetic is refused as the fail-closed default, which needs no evidence (D78.02) |
| 7 | Layer ownership | Semantic connector checks own the spelling; IR lowering admits it; `sql/sqlite*` owns SQLite lowering, rendering and refusals; the CLI owns dialect selection and JSON; tests own qualification; no execution layer |
| 8 | Dependency direction | `sql/sqlite*` consumes IR and the shared SQL model; only the CLI dispatch imports it; it re-decides no semantics, imports no `_project` module and calls no helper with a binary family default |
| 9 | Versioning and migration | CLI JSON stays schema version 1 with one more successful `dialect` value; no compiled record changes, so `VERSIONS` stays (D76.13); no migration; the header `dialect` hint text for `sqlite` changes and is listed |
| 10 | Target requirements versus provider capabilities | Requirements are the premises and forms; provider evidence is the measured triple. A dialect name or version never implies support; other builds are not qualified, not unsupported. The capability section states check, emission, execution (none) and result reading (none) |
| 11 | Interchange | SQL text and CLI JSON cross the process boundary; no data, Arrow or files cross it; the compile API is unchanged |
| 12 | Execution | None in the product. Test-only in-process runs are authorized under D78.03, with no Docker, lock or network; the PostgreSQL byte replays run the fixed PostgreSQL 18.6 image under D78.08 |
| 13 | Resource lifecycle | Product: none. Tests open and close each connection themselves and keep files under the pytest base temporary directory; a failure leaves nothing outside it |
| 14 | Security and trust | No untrusted database bytes are opened (deferred to its own Gate 1); the emitter writes no `ATTACH`, `PRAGMA` or extension loading; names are quoted per part; the build triple is the trust input of every qualification claim |
| 15 | Algorithms and data structures | The existing IR walk and a direct tree renderer in the MySQL module shape; nothing new |
| 16 | Complexity posture | Linear in IR size; no search, graph or state growth; the golden and native matrices are finite |
| 17 | Invalidation | The connector set, IR connector admission, CLI dialect set and header hint set change; their consumers (`check`, both existing emitters, `migrate` hints, `pietto lsp` diagnostics through `check`, the extension sync input) are re-tested, goldens re-checked and the AD78.03 firewall rerun on each replay |
| 18 | Cache | None added; probe and build observations are evidence, not authority; each qualification run re-observes the running build |
| 19 | Concurrency | Product: none. Tests use per-test connections, safe under xdist; lanes follow PL.01 and PL.03 |
| 20 | Diagnostics | `PIE-B1000` with SQLite reasons in the existing backend order and source locations; no new code; native errors named by `sqlite_errorname`, never mapped to SQLSTATE; project `--dialect sqlite` stays a usage error (exit 2); refused-form tests change where they refuse (74-4) |
| 21 | Inspection | `check` and existing inspection stay read-only and dialect-neutral; no SQLite inspection command; inspection cannot open a form |
| 22 | UX | One spelling, `sqlite.table("name")`, kept by `pietto fmt`, with the usability row above; unsupported forms fail closed with a reason naming SQLite |
| 23 | Conformance | Normative: the `language.md` SQLite section, CLI JSON v1, diagnostics, the golden-fixture policy. Target matrix: the finite native matrix on the measured build with independent oracles |
| 24 | Differential and fuzz assurance | Prewritten oracles, byte-bound PostgreSQL replays, finite NULL, boundary and permutation controls, byte-stable goldens. Fuzzing and reduction are `NOT_APPLICABLE` for B1: its forms are a finite, closed set (the D78.01 subset over four types) that the golden and native matrices enumerate, and every other form is refused; owner of high-intensity assurance: Phase81 |
| 25 | Packaging | No dependency, extra or lock change; no grammar or generated-parser change; new goldens; the package check runs at Gate 2 because new modules enter the wheel |
| 26 | Support matrix | Byte output on CPython 3.12 and 3.13 wherever CI runs; native qualification only on the measured build on Linux; every other build, Windows and macOS not qualified |
| 27 | Release, deprecation, and EOL | Publishes after the `0.1.11` cut and DuckDB B1, each push separately authorized; rides the `0.2.0` line as an alpha surface listed in release notes and the freeze ledger; rollback is an ordinary revert; no deprecation |
| 28 | Readiness and exact deferred owners | Prerequisites: the published D77.04 head with CI, bound as `ab972f36` (PL.02); Q0; Phase79 S02 before S02. Deferred: B2 project mode (Phase78 B2 Gate 1); execution and file trust (its own Gate 1, Phase78 lead); arithmetic, division by zero, other types, JOINs, windows (B2 or later Gates 1); the SQLite capability-facts profile (editor capability-facts Gate 1); extension sync (extension lane after its authorization, before the release request carrying B1); third whole-tree test pass (own ledger, after Phase77 S27, before the Phase78 completion audit); Phase77 audit (Phase77 S27) |
| 29 | Slice route | Q0 → S01 → (Phase79 S02) → S02 → midpoint → S03 → S04; non-goals as in the scope table |
| 30 | Repair and stop conditions | D78.05 ceiling, as the owner chose it (D78.06) and doubled it (PL.09); stop at any cap, unproved build or input identity, a needed new code, public text, dependency, database run beyond D78.08 or extension push, a trust regression, or a replay that changes a Phase77 meaning. Failed candidates and runs are preserved; no commit or push without authorization |

## Budget

`C160/F480/D4600/S6` is the cumulative B1 ceiling, not a target or a
per-slice allowance: `C80/F240/D2300/S3`, recorded from sheet §3.2 (D78.05),
doubled on 2026-11-12 (PL.09). The option the owner selected at Gate 1
stated `D1500`, and on 2026-11-11 the owner chose `D2300`, which ended that
stop point (D78.06). The slice allocations above sum to
`C75/F225/D1900/S3` and `D400` is the replay reserve; both keep their
figures (PL.09), so `C85/F255/D2300/S3` is unallocated. D counts one per diagnostic command, and a loop
inside one command counts once (D76.17). The planning entry charged to Q0 is
the SQLite draft's 31 and this route's drafting 35 shell commands, plus any
later fix of this route and Phase78's share of the shared passes after the
approval. PL.06 records the shared sheet, critique, review, consolidation and
fix-pass commands once and keeps those before the approval on Phase77. The
lead keeps the running ledger; each lane reports its checks and repairs to
the integrator. At any cap the lead stops and asks; no handoff or lane
resets the ledger.
