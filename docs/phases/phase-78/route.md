# Phase78 route — SQLite B1 published, B2's first tier closed by S16

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

B1 is published ([B1 record](#b1-record)). On 2026-11-15 the owner approved
the Gate 1 of the second vertical, B2 (PL.47); the [B2 route](#b2-route)
binds its Gate 0, decisions, slices and rules, and Phase78 closes with B2's
slice S16. S16 closes it with the [B2 record](#b2-record) and the
[completion audit](completion-audit.md); B2's second tier goes to the
owner's plan (PL.54, PL.58), and the [B2 second tier](#b2-second-tier)
binds its own Gate 1 answers (D78.14) and route.

Gate 0 binds the head and its natural CI. The route left the read of that CI's eligible health and alerts and the re-measured Phase77 overlap to the package's first implementation batch; B1 recorded neither, as the Q0 row of the [B1 record](#b1-record) states.

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
| D78.11 | Revises D78.10's two-hour clause, which keeps its text: no attempt starts once the campaign's summed two hours are spent, and each attempt runs under the time that remains as an outer limit, `timeout --foreground --preserve-status -s TERM`, never `-k` (lead) | Qualification method; S03 |
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
| S03 | In-process qualification | New `tests/test_sql_sqlite_native.py`; a flat `tests/_pietto_sql_sqlite_*.py` helper only if shared; `tests/conftest.py` if an environment class option is needed; `scripts/validate.py` (the `--pietto-sqlite-class=qualified` declaration, D78.07); `tests/test_ci_validation_entrypoint.py` (that gate's expected command); `tests/fixtures/sqlite/postgres_replay_v1.json` (the PostgreSQL replay result, D78.10); `docs/spec/validation-runner-acceptance-v1.md` (a new domain row); `docs/development.md` (SQLite target validation); `ci/workloads.toml` only if the CI workload governance requires a declaration | Native cells against oracles written before the run; a fabricated-output self-test fails every fail-open shape (72-4); PostgreSQL replays bind the bytes they ran (72-5); a forged non-qualified build is refused; skips are counted beside passes (75-3); a failed cell is first a question about its judge (74-1); a form without a passing cell ships refused (73-6). The runner-acceptance specification, `docs/development.md`, `scripts/validate.py` and `ci/workloads.toml` are VR2 acceptance rule paths, so the B1 batch runs its whole Gate 2 on the integration host, and under the owner's 2026-10-27 decision its natural CI is not recorded as a new bootstrap, so the Teach split stays void (PL.05, [validation runner acceptance](../../development.md#validation-runner-acceptance)) | S02 | 25/75/600/1 |
| S04 | B1 closeout | `docs/capabilities.md` (a new SQLite section, not new columns); the fragment's known limitations; this route (B1 record and B2 handoff); the roadmap freeze ledger; `docs/status.md` | B1 acquisition review against the B1 base; docs owners; CI health and alerts read; Gate 2 duration recorded | S03; publication after DuckDB B1 | 10/30/250/0 |
| B2 | Project mode | Its own Gate 1, approved in PL.47; see the [B2 route](#b2-route) | — | The AD78.03 seam (Phase79 S02 and S03); Phase77 S26/S27 | own ledger |

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
completion audit and next-phase handoff. The third whole-tree test pass ran
outside Phase78, in batch 2, the maintenance batch after `0.2.1`, and meets
that condition of Phase78's closure (PL.49).

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

## B1 record

B1 is published (item 13). Its lane side was ready in round 15 on the lane
base `ab972f36`. On 2026-11-13 the lead integrated S01–S04 as one commit
each on the published `main` `a015afcf`, after the `0.1.11` release commit
`d03d6e4b`, above the commits of the shared lane PK, Phase79 S01–S04 and
S07, and Phase80 IB1 (S01–S05 and PK-80) in the same candidate chain; the PK
commit carries Phase79 S05. On 2026-11-14, after `0.1.12` was published, the
chain was replayed onto the published `main` `ab594829` in the same order,
each slice still one commit, and S01's commit carries B1's only
release-note fragment, `78-s01`, which S02–S04 share (PL.04); unless it
says otherwise, this record names the commits of the chain on `a015afcf`.
Phase80 S06 (IB2) is not in the chain, since its route lands it after
IB1's natural CI; B1 does not wait for it. DuckDB B1 is
Phase79 S00–S08; at the replay onto `a015afcf`, S06 and S08 were not below
SQLite in that chain: S06 was only a candidate commit off it, and S08 was
not yet written. Under AD78.03 the shared
connector and dialect-set hunks of S02 were replayed onto the integrated
Phase79 S02 lines (six files, ten conflicting hunks, resolved by the
integration rehearsal's rules), and the family firewall passed on the
integrated tree. The lead ran B1's Gate 2 on the integration host on the
batch tree (items 12 and 13). B1 publishes after the `0.1.11` cut
(PL.04) and after DuckDB B1 (AD78.02; checklist item 27), so only once
Phase79 S06–S08 have published or lie below S01. Whether one push that
carries both B1 batches meets AD78.02 needs the lead's or the owner's
ruling, and a change of that order needs the owner (unfreeze conditions).
The owner answered on 2026-11-14 that it does: Phase79 S06 and S08 sit
above S01–S04, and the whole chain publishes in one fast-forward push
(PL.32).

| Slice | State | Evidence |
| --- | --- | --- |
| Q0 | Build triple and probe cells measured. SQLite `3.53.1` with the qualified source id under the integration venv's CPython 3.13.13 and the host's user-local CPython 3.12.13 and 3.13.13; the host's system CPython 3.14.4 links `3.46.1`, not qualified. The raw cells cover STRICT types, NaN and ±Inf, ±0, NULLS placement, Text order, Bool storage, aggregate types, Int extremes and quoting | the Q0 summary of the lane's Q0 and S01 run of 2026-11-10; Gate 0 rebind: `ab972f36` with natural CI `42831340276`, 21 of 21 jobs ([Starting point](#starting-point)); that CI's health and alerts were not read (NOT_OBSERVED, PL.07). The re-measured Phase77 overlap that this route's opening leaves to the package's first implementation batch is NOT_RECORDED: B1 did not measure it again (owner: the Phase78 lead; this cell is the record of the omission, and the first push's Gate 2 sealed the tree that carries it) |
| S01 | `language.md` SQLite section and the fragment `78-s01-sqlite-single-file.md`, lane-reviewed; integrated as one commit; the fragment stayed off the chain until `0.1.12` was published and joined this commit in the replay of 2026-11-14 (PL.04; [status](../../status.md)) | `p78-review-s01-20261110`, `p78-s01-fix2-review-20261110` |
| S02 | `src/pietto/sql/sqlite*.py`, CLI dialect, connector entries, CLI JSON and diagnostics rows, goldens and `tests/test_sql_sqlite_emission.py`, lane-reviewed; integrated as one commit. Upstream `check` now refuses an `Int` literal outside the signed 64-bit range (PIE-S2364), so the emitter test's case for it and that item of the PIE-B1000 list were dropped at integration | `lane-p78-s02-20261110T175728Z`, `r4-review-p78-s02`, `r5-review-p78-s02` |
| S03 | `tests/test_sql_sqlite_native.py`: 105 cells (76 matrix, 20 BAG/NULL oracle, 5 Python oracle, 4 premise controls), all agreeing with their prewritten oracles on the first native run; a coverage law over 109 (clause, type, operator) forms derived from the emitter's vocabulary; a per-test runtime witness; the runner-acceptance row 9 and the `development.md` section. Native runs: CPython 3.13.13 only, class `qualified`, `sqlite_build` refusal null, 46 compile options. Integrated as one commit and sealed on 2026-11-13: on the integrated tree the three SQLite owners passed (220 tests: 136 native, 40 emission, 44 entrypoint; 105 `cell` and 4 `golden` properties, `sqlite_build` refusal null, 46 compile options), and the replay test binds the integrated PostgreSQL bytes | `lane-p78-s03r7-20261110T205022Z` (its first and third pytest junit outputs hold the `cell` properties), reviews `r6-review-p78-s03`, `r7-review-p78-s03`; round 8 fixed review r7's two low findings (witness wording, ledger file count); round 9 (`r9-p78`): `scripts/validate.py` declares `--pietto-sqlite-class=qualified` (D78.07), the importer scan of `tests/test_sql_sqlite_emission.py` resolves relative imports, and the PostgreSQL replay is preregistered but not run (in the lane's ignored working folder); round 10 (`r10-p78`): `scripts/validate.py` refuses a conflicting `PIETTO_SQLITE_CLASS` before any gate, and the replay preregistration is v2 (in the same ignored working folder, v1 kept), still not run; rounds 11 to 13 (`r11-p78` to `r13-run-p78`): v2.1 and v2.2 reviewed, v2.2's run void by a driver defect before any container, v2.3 reviewed CLEAN and its run `PASS`; round 14 (`r14-p78`): the result landed as `tests/fixtures/sqlite/postgres_replay_v1.json` with `test_each_postgres_replay_binds_the_bytes_it_ran`, and S03 is sealed on the lane side (the lane's S03 seal record); round 15 (`r15-p78`): review r14's three low findings fixed and the two hours summed over the campaign's attempts; integration run `p78close-20261113T155742Z` (its first pytest output and junit) |
| S04 | This record, the capability section, the freeze-ledger row and the status row, integrated as one commit; the fragment's known limitations are in the S01 fragment. Each capability row was run once through `check` and `emit-sql --dialect sqlite` on the integrated tree | the lane's drafts of rounds 8 to 17, in its ignored working folder; the capability probe script of integration run `p78close-20261113T155742Z` and its second output (the first output came from an earlier version of that script, whose constant row failed `check` with PIE-P1000, and no saved script reproduces it); the `is not None` of the expression row in the repair round `px78r1-20261113T162030Z`, by its probe script and output |

**S03 write set (owner, 2026-11-11, D78.07).** The owner chose that the
authoritative validator declares the `qualified` SQLite class. S03 therefore
also writes `scripts/validate.py` (its pytest gate declares
`--pietto-sqlite-class=qualified` beside `--pietto-storage-class=qualified`)
and `tests/test_ci_validation_entrypoint.py` (the gate's expected command
and the option's registration). `scripts/validate.py` is a VR2 acceptance
rule path, as `docs/development.md` and the runner-acceptance specification
already are, so the batch rule is unchanged: B1 runs its whole Gate 2 on the
integration host, and its natural CI records no new bootstrap, so the Teach
split stays void (PL.05; owner, 2026-10-27). The Gate 2 interpreter, the
integration `.venv`'s CPython 3.13.13, links the measured build: release,
source id and all 46 compile options in order (observed 2026-11-11T09:34:55Z
with the host's user-local CPython 3.13.13, the lane venv, the integration
`.venv` and the user-local CPython 3.12.13, in round 9's comparison record).
On a build other than the measured one that still passes the validator's
storage pre-check, the native tests fail the pytest gate with
`PIETTO_SQLITE_REQUIRED <category>`; they never skip. A
`PIETTO_SQLITE_CLASS` other than `qualified` in the environment is refused
with exit 2 before any gate, as a conflicting `PIETTO_STORAGE_CLASS` is, so
it is no validation start. The lead decided in round 14 that S03 also holds
`tests/test_ci_validation_entrypoint.py`, and that the replay result lands
as `tests/fixtures/sqlite/postgres_replay_v1.json`; since the S03 seal the
S03 write-set cell names both.

### B1 acceptance list

| # | Item (route row) | State |
| ---: | --- | --- |
| 1 | Native cells against oracles written before the run (S03) | Met on the measured build, CPython 3.13.13 only: the lane venv on the round-14 tree (round 14's second pytest output) and an integration worktree's `.venv` on the integrated S03 tree (2026-11-13), each with 105 `cell` and 4 `golden` properties and `sqlite_build` refusal null |
| 2 | A fabricated-output self-test fails every fail-open shape (72-4) | Present; it runs on every runner and passed in round-7 pytest 3 and on the integrated tree |
| 3 | PostgreSQL replays bind the bytes they ran (72-5) | **Met.** Authority D78.08 (owner, 2026-11-11), method D78.10 and D78.11. One campaign on the pinned PostgreSQL 18.6 image, Docker Engine of Docker Desktop 4.99.0 (Engine 29.9.3), one owned container with `--pull=never --network none`, under the engine lock: attempt 1, preregistration v2.2, 16:28:55Z, `VOID` (exit 6) by a driver defect before any container existed, charged; attempt 2, v2.3 (review r13 CLEAN), 17:39:05Z to 17:39:10Z, `PASS` (exit 0): 105 of 105 entries (the 101 law cells and the 4 golden statements), `ZERO_SIGN` declared on `select-every-type` and `group-order-by-max`, the three bare-literal columns as `numeric`, cleanup `success` (round 13's run record; run `p78-pg-replay-20261111T173905Z`). The two hours are summed over all attempts of the campaign, no attempt starts once they are spent, and each attempt runs under the campaign's remaining time as an outer limit (`timeout --foreground`, so the signal reaches the driver alone), which the frozen driver takes as a stop signal (D78.11, which revises D78.10's two-hour clause; the frozen driver timed each run from its own start; offline drills `r16-p78` and `r16-review-p78`). The campaign's two attempts ran before that rule, wrapped only in `setsid -w nice -n 19`, with no outer limit (the run records of rounds 12 and 13); their outer wall times, 1.32 s and 4.21 s (2 s and 5 s as the rule charges them), kept the campaign inside the two hours. Network-namespace evidence corrected: the round-13 probe used a namespace after `ip link set lo up`, not a fresh one (a fresh one has `lo` down and an empty IPv4 route file); the real container showed the lo-up state. Landed in round 14: `tests/fixtures/sqlite/postgres_replay_v1.json` and `test_each_postgres_replay_binds_the_bytes_it_ran`, which re-emits each PostgreSQL statement and compares its sha256, binds the fixture rows, oracle and carriers, and runs on every runner with no database; 18 mutation witnesses behaved as written beforehand (and, in round 15, the three witnesses of the fixture-set assertion), and the frozen generator on the landed tree changes only the input hash of the test file itself (the lane's S03 seal record). The replay test passed again on the integrated tree on 2026-11-13, so no entry needs a new campaign |
| 4 | A forged non-qualified build is refused (S03) | Met (forged-build tests) |
| 5 | Skips are counted beside passes (75-3) | Met for the module's own classes. **Decided by the owner on 2026-11-11 (D78.07):** `scripts/validate.py` declares `--pietto-sqlite-class=qualified`, so on a non-qualified build the authoritative run fails instead of skipping (S03 write set above). B1's Gate 2 still checks its junit for 105 `cell` properties and `sqlite_build` refusal null |
| 6 | A failed cell is first a question about its judge (74-1) | No cell failed on the first native run or since |
| 7 | A form without a passing cell ships refused (73-6) | Met by the coverage law on the measured build: every emitted (clause, type, operator) form has a cell |
| 8 | VR2: whole Gate 2 on the integration host; natural CI is no new bootstrap; Teach split void (S03) | Lane side done: B1 changes three VR2 rule paths (`docs/development.md`, the runner-acceptance specification, `scripts/validate.py`) and not `ci/workloads.toml`. Gate 2 is the lead's, on the integration host, on B1's batch tree, whose publication order item 13 states; `scripts/validate.py` joins the VR2 paths B1 changes, with the same rule. Runner row 9's Teach column stays Not observed: the owner kept the default on 2026-11-11 (D78.09), no observation and no claim |
| 9 | B1 acquisition review against the B1 base (S04) | Below; its bounded profile, from the health of the final natural exact-head CI, [`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189), is that review's last item |
| 10 | Docs owners (S04) | Passed on the final round-9 tree: review r9's first pytest output (632 passed, the seven `test_repo_*` owners among them). Round 10 changed `docs/development.md`, `scripts/validate.py` and the entrypoint test; the same 17 files passed on the round-10 tree (round 10's first pytest output, 636 passed). Round 14 changed `docs/development.md` again (the replay paragraph) and added the replay fixture and test; the same 17 files passed on the round-14 tree (round 14's second pytest output, 637 passed; an earlier start that round ended in a pytest usage error before collection and is kept). Round 15 changed the replay test and the fixture's `regeneration` text; the same 17 files passed on the round-15 tree (round 15's first pytest output, 637 passed). On the first integrated S04 tree, `5c31ff86`, 14 files passed (the integration run's second pytest output, 580 passed): eleven of those 17 and `tests/test_project_explain.py`, `tests/test_semantic_source_connectors.py` and `tests/test_sql_mysql_connector_semantic_surface.py`. The other six were not rerun there: `tests/test_ci_loadfile_scheduling.py`, `tests/test_ci_validation_typing_stages.py`, `tests/test_ci_validation_workload_scheduling.py`, `tests/test_ci_workflow.py`, `tests/test_harness_validation_resource_guard.py` and `tests/test_harness_validation_runner_receiver.py`. All of them rerun at Gate 2 on the batch tree |
| 11 | CI health and alerts read (S04) | The lead's read of the health of the first push's natural exact-head CI, [`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189): INSUFFICIENT_EVIDENCE with a WATCH screen, given in full with the profile in the last item of the [B1 acquisition review](#b1-acquisition-review); what the read cannot observe is NOT_OBSERVED with its reason (PL.07) |
| 12 | Gate 2 duration recorded (S04) | Met: the batch Gate 2 ran on 2026-11-14 from 21:43:45Z to 21:52:57Z on tree `58f5e2810fe016c63def144a8eec81e1389c6248`, with `--pietto-sqlite-class=qualified`: `scripts/validate.py` took 542.2 s, of which pytest took 489.42 s with 20 workers (30,779 passed, 65 skipped); the package smoke and the DuckDB extra start followed it |
| 13 | S01–S04 accepted on the integration tree; Gate 2 on the batch tree; publication after the `0.1.11` cut and DuckDB B1 under its own push authorization, with green natural exact-head CI (B1 closure) | Published: S01–S04 are four of the 23 commits on `ab594829` that were fast-forward pushed together under PL.31 on 2026-11-14 at 21:54:54Z, ending at `94b4097a5ec3e1fa5936e352d5b63bf84ec4d688` (tree `58f5e2810fe016c63def144a8eec81e1389c6248`), after the `0.1.11` cut (PL.04). Phase79 S06 and S08 sit above them in that push, so SQLite B1 reached `main` only together with the complete DuckDB B1, which meets AD78.02 by the owner's answer (PL.32). Gate 2 on that tree: item 12; its batch audit's one real bug, the owner-answer times of PL.30–PL.32, was fixed before that Gate 2, with no real bug left. Natural exact-head CI: [`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189), push/main attempt 1, passed all 21 jobs |
| 14 | Midpoint record after S02 (route) | Not recorded. S03 opened in the lane on 2026-11-10, before S02 reached an integration tree, so the midpoint was not held where the route puts it; S02 first reached one on 2026-11-13, over the integrated Phase79 S02. This record claims no midpoint |
| 15 | D78.02 and D78.04 stated to the owner as inform before S02 seals | Met: first stated in the lead's list of pending owner items of 2026-11-10 (item 11), which records no time; the owner took both as inform on 2026-11-11 (D78.09) |
| 16 | Extension sync input of `sqlite.table` (D76.12, S01) | Read in S04, not in S01: the extension's `tests/sync_language.py` (extension `041797e`) reads the keywords of `grammar/Pietto.g4`, the built-in names of `src/pietto/semantic/catalog.py`, `aggregates.py` and `window_semantics.py`, and the `pietto` blocks of `README.md`, `docs/language.md`, `docs/style.md` and `docs/worked-example.md` and every `examples/**/*.pietto` file. B1 changes no grammar and none of those modules, so `sqlite.table` is no catalog change under D76.12 and B1 needs no sync patch; B1 adds no `pietto` block and no example either, so the extension's corpus is unchanged |
| 17 | Phase77 completion audit read by S04 if it exists | Absent at `ae48f00a`, `e0116e41` and `a015afcf` (`docs/phases/phase-77/` holds only `route.md`). Present at `ab594829` and read in the replay of 2026-11-14: its handoff keeps B1 after DuckDB B1 (AD78.02, item 13), leaves the `verify_project_sql_plan` debt to Phase78 only if B2 changes project SQL emission, and keeps the Phase78–80 fragments off `main` until `0.1.12` is published, which it now is (S01 row). The Phase78 completion audit reads it again |

### B1 acquisition review

Base: `2a18113e`, the PK-80 commit of the chain replayed onto `ab594829`
(`dee6fd46` on `a015afcf`, with the same test changes above it); Phase79
S07, between it and S01, changes no test file. The lane counted against its
base `ab972f36`. New:
`tests/test_sql_sqlite_emission.py` (41 tests in the lane, 40 on the
integrated tree), `tests/test_sql_sqlite_native.py` (136 tests since round
14), `tests/fixtures/sqlite/` (the golden input and, since round 14, the
PostgreSQL replay result) and the two `emit_sqlite_single_file` goldens.
Changed: `tests/conftest.py` (the `--pietto-sqlite-class` option) and 16
existing owners, 17 test files with 191 lines added and 53 removed,
`tests/test_ci_validation_entrypoint.py` among them. The lane counted 17
owners and 18 files, 502 lines added and 45 removed, against `ab972f36` in
round 10, its copy of Phase79 S02's lines and their tests included. Timings
are the per-test sums of round-7 pytest 1 (`-n 8`): emission 2.40 s, native
0.81 s.

- Native cells open a fresh `:memory:` connection per test, and a
  module-scoped fixture observes the build once per worker module. Both are
  kept: per-cell isolation, and D78.03's re-observation of the running build.
- The coverage law re-emits the program of every cell but the premise
  controls (0.281 s). It is kept: it runs on runners where no cell runs, so
  it cannot reuse cell outputs.
- `test_the_cli_alone_dispatches_the_sqlite_backend`, 2.08 s in round 7,
  the slowest B1 node, parses every `src/pietto/**/*.py` with `ast.parse` to
  find importers of `pietto.sql.sqlite`. Since round 9 it resolves a
  relative `from` against the file's package and counts `from P import x` as
  `P.x` too, so `from ..sql.sqlite import ...` and `from ..sql import sqlite`
  are found (review r8's mutants). `tests/test_sql_mysql_api.py:238` and
  `:292` walk the same files but read them as text. The existing owner
  `tests/_pietto_repo_facts.py`
  (`REPOSITORY_FACTS.python(path).imported_modules`) does not resolve
  relative names (review r8: `sql` and `sql.sqlite` for those mutants), so a
  migration to it first needs that resolution there; until then the fresh
  parse is kept, with this reason. The scan of the three SQLite modules' own
  imports also stays fresh: the owner drops a module-less `from . import x`,
  which the test refuses. The time split and any gain are unmeasured. Owner:
  the Phase78 lead, at the latest before B1's Gate 2 seal.
- The edits of existing owners add in-process `cli.main` usage-error checks
  and `tmp_path` projects (connector checks in
  `tests/test_semantic_source_connectors.py`); no subprocess, database or
  session fixture was added.
- The round-14 replay test (0.481 s in round-14 pytest start 2, `-n 8`)
  parses, analyses and lowers each law cell's program and the golden source
  once more through the module's `_ir` and emits PostgreSQL bytes; the
  coverage law does the same front-end work for the SQLite emitter. It is
  kept fresh: the two tests emit for different backends, and sharing `_ir`
  results across tests would be new shared state in the module. The native
  module's per-test sum was 1.619 s in that run. Measured, not consolidated;
  the acquisition owner decides with the rest of this list.
- No consolidation was applied, so there is no structural or wall-time
  improvement to report. The bounded profile of step 4 (the ten slowest
  in-process nodes of the final natural CI health under cProfile):
  natural exact-head CI
  [`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189)
  of `94b4097a`, push/main attempt 1, ran from 21:54:59Z to 22:14:04Z on
  2026-11-14 (1,145 s) and passed all 21 jobs, which took 11,094 s in all
  (jobs API, start to completion, without queueing); the longest was
  Windows 3.12 at 1,132 s. Its health was read at 22:15Z through the owner's
  read-only token (PL.07): the 15 `ci-health` artifacts match the digests
  the API lists, the workflow summary passes `verify_workflow_health` of
  that head's `scripts/ci_workloads.py`, and the `[ci-health]` lines of the
  aggregate job's log agree. The status is INSUFFICIENT_EVIDENCE with a
  WATCH screen. History read 4 candidates and accepted 3 (`43603167533`,
  `43600539878`, `43590596831`) with none rejected, but none is comparable:
  each differs in its test set (345 more nodes now) and in the runner
  images of its shards.
  Each Python collected 30,844 nodes; 30,795 passed and 49 were skipped. The
  only alert that needs no history is the structural
  `FEWER_UNITS_THAN_WORKERS` that predates Gate 0 (plan- and
  emission-portability, 3 nodes on 4 workers, on both Pythons). The
  provisional ones are `SHARD_IMBALANCE_REVIEW` on both Pythons (longest
  over median 1.54 on 3.12 and 1.82 on 3.13, general-runtime-1 the longest
  each time) and `LONG_INDIVISIBLE_NODE` 18 times, the same nine
  child-process nodes on each Python as in the Gate 0 run. Both comparisons
  with Gate 0 rest on the editor core's midpoint read of the Gate 0 run
  `42831340276` on 2026-11-11 (E-C route,
  [midpoint](../../editor/ed03-route.md#midpoint-unfreeze-and-closure)), not
  on a read at Gate 0; this package did not read that run's health. There is
  no finish-spread, startup, cost or repeat signal; the health's own cost is
  partial, as always, because it is written before Windows 3.12 and the
  aggregate job finish. The general-runtime shards that ran on runner image
  `20261111.370.1` (all three on 3.12, general-runtime-1 on 3.13) took 878
  to 1,029 s, and the two on `20261111.127.1` took 531 to 538 s; the cause
  is not established.

  The Python 3.13 health records 126 slowest nodes: 30 for each of the
  shared-acquisition and three general-runtime partitions and 3 for each
  portability partition. Ranked by setup, call and teardown time, 15 nodes
  above the tenth in-process one were left out because their time is spent
  in child processes, of the same kinds and number as in the E-C profile:
  the differential process cells of `test_harness_ir_differential.py`,
  `test_harness_plan_conformance.py` (its setup is that acquisition),
  `test_harness_plan_portability.py` and
  `test_harness_sql_emission_portability.py`; the six checkout, relocated
  and installed standalone batches of the two portability files; the two
  fresh source-free processes of `test_execution_compiled_source_free.py`;
  and three nodes of `test_harness_execution_api.py` whose module fixture
  starts a fresh `-I` worker for each consumer case. One more is set apart:
  `test_harness_execution_api.py::test_the_duckdb_native_checker_accepts_honest_units_and_refuses_each_fabricated_shape`
  (23.8 s, Runtime 3.13 / general-runtime-3), new with Phase79 S06, starts
  one fresh `-I` oracle interpreter and then checks in process; its split
  between the two is not observed.

  | Node | Job | 3.13 s | 3.12 s | Where the time is |
  | --- | --- | ---: | ---: | --- |
  | `test_harness_target_conformance.py::test_data_only_receipt_controls_have_nonempty_positive_denominators[mysql]` | Runtime 3.13 / general-runtime-1 | 182.2 | 208.9 | setup, 178.1 s: the module fixture `valid_receipts` |
  | `test_harness_target_conformance.py::test_receipt_corruption_is_rejected_without_any_resource[postgres-missing]` | Runtime 3.13 / general-runtime-3 | 113.0 | 197.7 | setup, 110.4 s: the same fixture |
  | `test_harness_target_conformance.py::test_data_only_receipt_controls_have_nonempty_positive_denominators[postgres]` | Runtime 3.13 / general-runtime-2 | 111.8 | 195.4 | setup, 108.7 s: the same fixture |
  | `test_harness_sql_emission_portability.py::test_every_admitted_artifact_exports_corresponds_and_decodes[postgres]` | Runtime 3.13 / shared-acquisition | 108.6 | 130.1 | call |
  | `test_harness_sql_emission_portability.py::test_every_admitted_artifact_exports_corresponds_and_decodes[mysql]` | Runtime 3.13 / shared-acquisition | 98.8 | 117.7 | call |
  | `test_harness_target_conformance.py::test_empty_text_anchor_requires_the_observed_var_string_type` | Runtime 3.13 / general-runtime-1 | 44.3 | 56.1 | call; the fixture was already built on its worker |
  | `test_repo_reader_acquisition.py::test_shared_facts_match_legacy_text_ast_import_and_identifier_acquisition` | Runtime 3.13 / general-runtime-3 | 32.6 | 59.0 | call |
  | `test_execution_compiled_bundle.py::test_mysql_lpad_and_now_cells_are_derived_in_linear_work[pair-_beside_a_capture]` | Runtime 3.13 / general-runtime-1 | 28.0 | 32.8 | call |
  | `test_repo_test_layout.py::test_no_test_reads_the_mutable_status_or_roadmap` | Runtime 3.13 / general-runtime-1 | 26.6 | 30.2 | call |
  | `test_execution_compiled_bundle.py::test_mysql_lpad_and_now_cells_are_derived_in_linear_work[words-_chained_lets]` | Runtime 3.13 / general-runtime-2 | 22.7 | 37.1 | call |

  Seven of the ten ids are in the E-C profile of `43181411369`. New are the
  two `test_mysql_lpad_and_now_cells_are_derived_in_linear_work` cells, which
  by their source compile and export MySQL programs of m × m cells for m
  of 4, 8 and 16 to prove a linear-work count law, and
  `test_repo_test_layout.py::test_no_test_reads_the_mutable_status_or_roadmap`,
  which by its source reads the string literals of every test file through
  the shared repository facts. The two `test_sql_values.py` bound nodes
  (20.7 s and 19.9 s) and
  `test_semantic_capability_facts.py::test_private_module_has_only_authorized_window_strategy_compiler_consumer`
  (21.2 s) left the list. On Python 3.12 the same seven lead and the two
  `lpad` and `now()` cells follow; its tenth in-process node is
  `test_sql_values.py::test_the_static_values_bound_is_no_emission_guarantee[postgres-1000-64-blockers2]`
  (31.5 s), and `test_repo_test_layout.py` is the twelfth.

  The cProfile half of step 4 is NOT_OBSERVED (PL.07): this reading ran no
  pytest, so none of the ten ran alone under cProfile, no verifier-runs,
  call-count or self-time finding is recorded, and no performance claim
  rests on the table. The Windows jobs are outside partition health by
  design, so their nodes are not ranked. GitHub's rendered Job Summary has
  no REST endpoint and was not read; the summary was regenerated from the
  artifact with `summary_markdown`, the function CI writes it with. Health
  is advisory, and nothing here changes scheduling, topology or test
  selection.

Ledger: the rows of the lead's Phase78 ledger sum to about `C8/F55/D1830/S0`
through its row of 16:01Z on 2026-11-13, before Gate 2 (C counts its upper
bounds), against `C160/F480/D4600/S6`. Its row of 15:32Z states a running
total of about D4463 instead, about D137 below the cap. Before Gate 2 the
lead ruled that the row sums hold, since that running total counted three
subtotals twice; PL.30 apportions Phase78 at about D2,350 of 4,600 to 16:30Z
on 2026-11-14. The owner chose D2300 on
2026-11-11 (D78.06), so D78.05's D1500 stop point no longer applies, and on
2026-11-12 doubled every budget (PL.09; Phase78 from `C80/F240/D2300/S3`).
Gate 2 duration: item 12.

## B2 handoff

PL.47 answered this handoff; the [B2 route](#b2-route) binds it.

- **Gate 1 first.** B2 (project mode) needs its own Gate 1. Before any B2
  code it decides whether SQLite generalizes the AD78.03 family firewall or
  builds its own pipeline. It depends on Phase79 S02 and S03 and on Phase77
  S26/S27.
- **What B2 inherits.** The independent `src/pietto/sql/sqlite*.py` modules
  and their PIE-B1000 reasons (D78.04). The qualification owner
  `tests/test_sql_sqlite_native.py`, with its SQLite class, runtime witness
  and a coverage law read from the emitter's vocabulary, so a form that B2
  adds to that vocabulary has no passing law until it has a cell.
  `QUALIFIED_SQLITE_BUILD` stays in that test until a production caller
  needs it, then moves to `src/pietto/sql/`.
- **Owner items.** Decided on 2026-11-11: the validator declares the
  `qualified` SQLite class (D78.07), the Teach column of runner row 9 stays
  Not observed (D78.09), and the PostgreSQL byte replay (72-5) is
  authorized (D78.08). The replay passed on 2026-11-11 (D78.10). B2
  inherits `tests/fixtures/sqlite/postgres_replay_v1.json` and its rules
  (D78.10, D78.11): a campaign's two hours are summed over its attempts,
  no attempt starts once they are spent, and each attempt runs under the
  remaining time as an outer limit (`timeout --foreground`); an entry keeps
  its saved rows only while its PostgreSQL bytes, fixture rows, oracle and
  carriers are unchanged, and a form B2 adds has no replay until a new
  campaign under a reviewed preregistration delta runs it. On 2026-11-11
  (about 17:05Z) the owner ratified the lead's 10:15Z pull of the pinned
  images by digest.
- **Deferred owners.** Execution and caller-file trust (its own Gate 1,
  Phase78 lead); arithmetic, division by zero, the remaining types, JOINs
  and windows (B2 or later Gates 1); the SQLite capability-facts profile
  (editor capability-facts Gate 1); the third whole-tree test pass (after
  Phase77 S27, before the Phase78 completion audit); the Phase77 completion
  audit (Phase77 S27). B1 needs no extension sync (acceptance item 16).
- **Q0 facts B2 meets.** On the measured build, as raw Q0 cells: a signed
  64-bit overflow and an out-of-range literal become `REAL`, a `Float`
  overflow becomes an infinity, zero divisors give NULL, a NaN is stored as
  NULL while infinities are kept, a `STRICT` `REAL` column stores `-0.0` as
  `0.0`, `LIKE` folds ASCII case, and a double-quoted name that names no
  column reads as text.

## B2 route

On 2026-11-15, by about 21:14Z, the owner approved the Gate 1 of SQLite B2
with the recommended answer of every question of the sheet that the lead
drafted under PL.41 (PL.47; the sheet is a working record outside Git). B2
means the first tier: 1a, project-mode SQLite SQL from a separate adapter
with the T1 base and the T2 aggregates, which single files also gain except
`sum`; and 1b, the read-only execution of a caller's SQLite file, whose
answers serve as the separate trust Gate 1 that D78.01 requires. The second
tier (JOINs, range-proved `Int` arithmetic, windows) is asked at the
[B2 midpoint](#b2-midpoint-and-unfreeze) and gets a ledger of its own.
Phase78 closes with S16. Local implementation in worktrees is authorized
from Gate 0; no commit, push or release is authorized by this route, each
push and each release needs the owner, and B2's first tier enters `0.2.2`
(PL.47, PL.55). The
[SQLite project specification](../../spec/sqlite-project-v1.md) holds the
contract values, the order of compile refusals with every detail, and the
handling of each SQLite difference.

### B2 starting point

Gate 0 is S05, on 2026-11-16 from 00:06:09Z to 00:13:13Z, on the newest
published head after `v0.2.1` was published and the natural CI of its
post-release documentation commit passed (PL.47, PL.02): `main` =
`origin/main` = `8cb9d9de53e7ebf78a592ac85be206023c0f4dde`, tree
`b2ad91b2b9065680a121c5a19146c1e339c4b5ce`, the commit that holds PL.46 to
PL.48. The repository was clean, with no Git operation in progress, and the
remote branch matched without a fetch. Its natural exact-head CI
`43767179471`, push/main attempt 1, passed all 21 jobs and finished at
22:21:37Z on 2026-11-15. Its health, read through the owner's read-only token
(PL.07), passed `verify_workflow_health` of that tree's
`scripts/ci_workloads.py` over its 15 `ci-health` artifacts: status
INSUFFICIENT_EVIDENCE with a WATCH screen, history available with 3 samples
accepted, none rejected and none comparable, cost incomplete. Health is
advisory and does not hold Gate 0. Phase77 has its completion audit, so no
Phase77 slice runs beside B2 and no overlap was measured again; the overlap
that matters now is the second `0.2.1` maintenance batch (M11 to M14) and
DuckDB B2, which the [single-writer order](#b2-single-writer-order) bounds.
S05 did not read the Phase79 and Phase80 completion audits; S16 reads them.
An earlier S05 attempt, begun at 22:29:35Z on 2026-11-15, stopped before it
finished; its record is kept unchanged and is not evidence.

Before Gate 0, PL.47 authorized offline probes outside the repository, in one
process at the lowest priority, for writing the specifications only and not
as qualification evidence; the SQLite probe ran on 2026-11-15 from 21:24Z to
21:27Z. Earlier, during the Gate 1 drafting and before PL.47, the sheet's
revision ran two in-memory `sqlite3` probes with no recorded authorization:
they were unauthorized preparation, and their results are not evidence (as
PL.02 records for B1's drafting probe). S05 ran the authorized probe's two
scripts again, byte for byte, in the Gate 0 environment, and only that run is
evidence.

S05 observed, on CPython 3.13.13 in the integration venv and the host's
user-local CPython 3.12.13 on Linux x86-64 (glibc 2.43):

- **Build.** Both link SQLite `3.53.1` with the source id `2026-05-05
  10:34:17 c88b22011a54b4f6fbd149e9f8e4de77658ce58143a1af0e3785e4e6475127e9`
  and the same 46 compile options, the triple of `QUALIFIED_SQLITE` and of the
  native tests' `QUALIFIED_SQLITE_BUILD` (D78.03).
- **Probe cells.** All four runs ended with code 0 and an empty stderr. Apart
  from their environment and timing sections, the two interpreters' outputs
  are identical line for line (259 lines of the main probe, 12 of the
  follow-up), and both equal the pre-Gate 0 outputs. Each row of the
  specification's [differences table](../../spec/sqlite-project-v1.md#differences-from-postgresql-and-mysql)
  states its observation, among them four cells the sheet added for Gate 0:
  the compensated summation of `avg`, an index that changes a `sum` result,
  `abs` and text casts of `-0.0`, and a `STRICT` `ANY` column. The
  specification's [execution](../../spec/sqlite-project-v1.md#execution)
  section lists the facts that S11 implements, among them the other four:
  the `sqlite_errorname` `unknown` (code 3091) of a `STRICT` type error, the
  authorizer's read with no database name for `count(*)`, a broken view
  beside a sound table, and the default busy timeout of 5.01 s.
- **Range evidence.** Through the DuckDB adapter, the independent adapter
  that B2 follows, the declared `int_range` of a direct field reached the
  adapter's facts unchanged (`0..1000000`, `-5000..0`, `-7..9`), and the
  adapter imports from `project_sql_emission_*` only the names of the sheet's
  whitelist. That reader's `_domain` takes no family, so the SQLite contract
  reader reads a field's `int_range` the same way (*derived*, not measured on
  SQLite); S08 locks the import whitelist with a test. The range proof of
  derived expressions stays in the PostgreSQL/MySQL pipeline, for the second
  tier.
- **Timing.** Only on CPython 3.13 with a warm cache, on a table of
  1,048,576 rows and 85 MiB: the value scan 0.193 s, `integrity_check` of the
  table 1.411 s, a grouped query 0.486 s, Python-side UTF-8 decoding 0.14 s.
  This is not evidence. S12 measures a 256 MiB file with a cold cache on both
  interpreters; if the check and query do not fit 20 s there, the file cap
  goes down and the deadline stays (PL.47). S12 measured on the integration
  host on 2026-11-16: one attempt per file through `execute()` with the
  default limits, each file evicted from the page cache first (residency 0
  read back), 1,048,576 rows, CPython 3.13.13 and 3.12.13 within 0.6 s of
  each other. Three indexes and ASCII notes at 255 MiB took 9.6 to 10.5 s;
  no index and multi-byte notes at 242 MiB, 8.4 to 9.7 s; 25 indexes on a
  `Bool` column at 251 MiB, 11.8 s; 13 mixed indexes at 239 MiB, 15.7 to
  17.4 s; and 13 indexes on randomly keyed columns at 253 MiB ran past the
  deadline (`PIE-R3001`; 26.4 s under a 120 s deadline, measured only),
  where 117 MiB took 10.9 s and 151 MiB 14.8 to 15.2 s, about 0.1 s per
  MiB. So the file cap is 128 MiB; the row cap and the deadline stay.
- **`avg` rounding.** SQLite's `AVG(CAST(x AS REAL))` uses compensated
  summation. S05 found this within the existing rules, which leave the
  summation of a binary64 average to the target, and recommended that the lead
  decide it and inform the owner, as for the NULL order; the lead ruled it
  within those rules (the specification's differences table).

### B2 decisions adopted

| Id | Adopted answer | Route consequence |
| --- | --- | --- |
| PL.47 (sheet Q1 B) | Gate 0 on the newest published head after `v0.2.1` and its post-release commit's CI; integration after the second maintenance batch; B2 is the first tier; Phase78 closes with S16; a second tier gets its own ledger; each release approved on its own, `0.2.2` at the earliest | Starting point; slices; budget |
| PL.47 (Q1′ A) | Offline probes before Gate 0, for the specifications only | Starting point |
| PL.47 (Q2 A) | A separate SQLite project adapter, `src/pietto/_project/project_sqlite_*.py`, that leaves the PostgreSQL/MySQL pipeline and the published DuckDB code unchanged. This is the shape AD78.03 left to this Gate 1, and AD78.03 stands. Imports follow a symbol whitelist: the plan-layer seam modules of AD78.03, and from `project_sql_emission_*` only the names that the DuckDB adapter imports today, with `blocker_suggestion` called with no family | S08; the firewall test checks the names |
| PL.47 (Q3 b, Q3b A) | T1 in project mode; T2 (`having`, `count_distinct`, `avg(Int)`) in both modes; `sum(Int)` in project mode only where the contract's `int_range` lies on one side of zero | S08, S10; specification admission |
| PL.47 (Q11 B) | Project SQL writes `COLLATE BINARY` at each `Text` comparison, ordering, grouping, deduplication and `min` or `max`; it revises D78.02's `BINARY` premise in project mode only, and single files keep it | S08, S10 |
| PL.47 (Q5 B, Q6a A, Q6b (i)) | Tier 1b: the read-only `sqlite_file` route behind eleven defences, a file of at most 256 MiB (128 MiB after S12's timing, by the sheet's Q6a (8)), at most 1,048,576 rows per source table, the attempt within `ExecutionLimits.seconds`, results under the `ExecutionLimits` defaults, the `arrow` extra reused, and a bounded value and integrity check in the same read transaction before each run that refuses `Text` holding NUL; with Q6a and Q6b it is D78.01's trust Gate 1 | S11, S12 |
| PL.47 (Q7 A″) | In-process qualification and one PostgreSQL replay, R1, in 1a on one PostgreSQL slot, which D78.08's authorization of B1's replay did not cover | [Qualification and replay](#b2-qualification-and-replay) |
| PL.47 (Q8 A) | Qualified on Linux x86-64 with one SQLite build and CPython 3.13.13 and 3.12.13; other platforms emit SQL without executing it | S09, S12; support matrix |
| PL.47 (Q10 A) | Ledger P78B2, which PL.15 now covers | [Budget](#b2-budget) |
| PL.47 (lead) | NULLS clauses that place NULL as the PostgreSQL emitter does, as D78.02 did for single files | S08 |
| Kept | D78.02 apart from that revision; D78.03 (one build triple; a version is no identity); D78.04 (no new `PIE-*` code, independent single-file modules, no general dialect registry); AD78.03 (the PostgreSQL/MySQL pipeline never receives `sqlite`; the shared connector and dialect lines have one writer at a time); D78.10 and D78.11; PL.02, PL.07, PL.15, PL.17; PL.40's D5 A, D9 A, D14 A and D15 A | Throughout |

### B2 scope

| B2 delivers | Not in B2 |
| --- | --- |
| Project `sqlite.table` sources; `emit-sql --project --dialect sqlite`, text and JSON v1/v2, with or without `--all`; `compile_sql` and `compile_all_sql`; the T1 forms and the T2 aggregates of the specification | The second tier until the midpoint and the owner; `Decimal`, `Date`, `Timestamp`, `UUID` and nested values; `Float` `sum` and `avg`; text functions and `LIKE`; `--literal-policy bind-safe` |
| Single-file `having`, `count_distinct` and `avg(Int)`; single-file `Bool` literals written `1` or `0` (PL.54) | single-file `sum(Int)`; any change to PostgreSQL, MySQL or DuckDB bytes |
| Tier 1b: `compile_query(dialect="sqlite")` and the `sqlite_file` route over a caller's `STRICT` tables | writing, query bundles, saved results, relay, jobs and R2 on SQLite; a content digest of the file; another build or platform; sqlglot at run time (AD78.01); any parity claim across databases |

### B2 slices

Slice ids continue from S05 (B1 used Q0 and S01 to S04). Each slice is one
commit; it binds its exact base tree, inputs, write set, commands and
acceptance when it is expanded, and documentation changes with the slice
that changes behavior. S06 writes the 1a release-note fragment
`78-s06-sqlite-project-mode.md`, which S07 to S10 edit; S11 writes
`78-s11-sqlite-file-route.md`, which S12 edits; S16 edits both. The
fragments and the specification describe what their batch delivers, so they
reach `main` only in a batch that carries the slices they describe.

| Slice | Content | Write set | Checks and acceptance | Depends on | C/F/D/S |
| --- | --- | --- | --- | --- | --- |
| S05 | Gate 0 and the probe matrix | None in the repository | Done: [starting point](#b2-starting-point) | PL.47 | 0/0/200/0 |
| S06 | Specification and route | New `docs/spec/sqlite-project-v1.md`; `AGENTS.md` (the alpha list); this route (this section and its pointers above); `docs/release-notes.d/78-s06-sqlite-project-mode.md` | `scripts/release_notes.py check`; `tests/test_repo_docs_links.py`, `tests/test_repo_release_notes_fragments.py`, `tests/test_repo_docs_examples.py` | S05 | 5/15/150/0 |
| S07 | The shared seam, one commit (lesson 80-4) | `src/pietto/semantic/source_connectors.py` (`sqlite.table` in `EXPLICIT_MODULE_CONNECTORS`, its non-empty literal argument checked in explicit-module projects only); the three family mappings in `src/pietto/_project/project_sql_plan_target_assessment.py` (two) and `src/pietto/_project/project_sql_plan_pure_boundary.py` (one); `tests/test_repo_static_checks.py` (the firewall for both families, the SQLite branch still stopping at the argument check); the S07 [shared-page hunks](../../spec/sqlite-project-v1.md#shared-page-hunks) of `docs/language.md` and `docs/capabilities.md` | `tests/test_semantic_source_connectors.py`, `tests/test_project_capability_target_matrix.py` and the pure boundary's owner; a project `sqlite.table` checks, and PostgreSQL, MySQL and DuckDB emission refuse it as the specification states; single-file connector diagnostics unchanged | S06; the second maintenance batch integrated | 10/30/350/1 |
| S08 | The T1 adapter, wiring and documentation | New `src/pietto/_project/project_sqlite_contract.py`, `project_sqlite_sql.py` and `project_sqlite_emission.py`; `src/pietto/_project/project_sql_emission_cli.py` (`DIALECTS`, dispatch, usage); `src/pietto/cli.py` (usage); `src/pietto/execution/_query.py`, so that `compile_query` keeps `PIE-R1002` for `sqlite` until S11; the S08 [shared-page hunks](../../spec/sqlite-project-v1.md#shared-page-hunks); new goldens | New owner `tests/test_sql_sqlite_project_emission.py`; `tests/test_sql_compile_api.py` and `tests/test_cli_project_emit_sql.py` in place; the firewall's SQLite emission branch flips while its `compile_query` branch still asserts `PIE-R1002`; the import whitelist test; PostgreSQL, MySQL and DuckDB goldens unchanged; Pyright on `src` and the changed tests (72-1); repository-wide owners on the integrated tree (72-2); a rule test with one statement refused for an unrelated reason (77-2); `compiler.py` unchanged, since `_emit` reaches the adapter through `run_project_emit_sql` | S07 | 30/90/900/1 |
| S09 | T1 native qualification | `tests/test_sql_sqlite_native.py` (project cells; the coverage law reads the adapter's vocabulary too); `docs/spec/validation-runner-acceptance-v1.md` and `docs/development.md` only if their SQLite rows change | Native cells on CPython 3.13.13 and 3.12.13 against prewritten oracles; skips counted beside passes (75-3) | S08 | 15/50/480/1 |
| S10 | T2 aggregates in both modes | The adapter's files; `src/pietto/sql/sqlite_relations.py`; the S10 shared-page hunks; the specification; goldens; the fragment | `tests/test_sql_sqlite_emission.py` and `tests/test_sql_sqlite_project_emission.py`, each form opened in the branch that refused it (74-4); native cells in `tests/test_sql_sqlite_native.py`, among them the `sum` order cells and `avg` against `math.fsum` divided by the count; `having` guards for aliases and bare columns | S09 | 15/45/500/1 |
| R1 | PostgreSQL replay campaign | A reviewed preregistration delta outside Git; a new replay fixture under `tests/fixtures/sqlite/` and its test | [Qualification and replay](#b2-qualification-and-replay) | S10 | 5/15/300/0 |
| — | Midpoint, after S10 integrates | This route | [Midpoint](#b2-midpoint-and-unfreeze) | S10 | in S16 |
| S11 | The `sqlite_file` route | First the external reference record of untrusted SQLite files; new `src/pietto/execution/_sqlite.py`; `src/pietto/execution/_query.py`, `_access.py`, `_handle.py`, `__init__.py`; the bundle, job, saved and R2 refusals; result binding through its own storage module; `QUALIFIED_SQLITE_BUILD` moved to `src/pietto/sql/`; `docs/execution.md`; `README.md`; the `PIE-R1001` row of `docs/spec/diagnostics.md` at a time the lead schedules apart from Phase81's diagnostic review (P03, PL.58); the specification's execution section; its fragment | New owner `tests/test_execution_api_sqlite_file.py`; `tests/test_execution_api_queries.py`, `test_execution_api_errors.py` and `test_execution_api_results.py` in place; request checks before any file opens; admission before binding (80-3); tests gated by entry point and platform (80-2); `project_result_binding.py` and `project_execution_reader.py` edited serially with MySQL catch-up and R2 work | S09, beside S10 | 30/90/1,000/1 |
| S12 | Native qualification of the route and its trust controls | `tests/test_execution_api_sqlite_file.py` (native classes); `tests/test_harness_execution_api.py` (the fabricated-output checker, shared with DuckDB B2's T06); the VR2 documents | Every defence and value check of PL.47 with a control cell on test-owned files, the cells the sheet lists and S05 added among them; the 256 MiB timing; Windows CI asserts the refusal: both Windows jobs run this file (PL.59), whose native cells assert the route's own refusal there and skip, and whose two cells that need POSIX, removing the working directory and the workspace names that import `fcntl`, skip themselves | S11 | 25/75/1,000/1 |
| S16 | First-tier closeout and the Phase78 completion audit | `docs/roadmap.md` (the freeze-ledger SQLite row, the deferral table); `docs/status.md`; this route (B2 record); new `docs/phases/phase-78/completion-audit.md` with the second-tier and next-phase handoff; `docs/references/engineering-lessons.md`; the fragments' known limitations | The acquisition review against B2's base; documentation owners; the Gate 2 duration; CI health read; the Phase79 and Phase80 completion audits read | R1, S12, and the third whole-tree pass of the second maintenance batch | 10/30/350/0 |
| Tier 2 | S13 JOINs, S14 range-proved arithmetic, S15 windows | New adapter modules | As S08 and S09, with two replays | The midpoint and the owner | own ledger |

Order: S05 → S06 → S07 → S08 → S09 → S10 → R1 → midpoint → S16, and
S09 → S11 → S12 → S16. The first batch is S06 to S12, published while R1
still waits for the Docker Engine, and the second R1 with S16 (PL.59, in
place of the split into 1a, S06 to S10 with R1, and 1b, S11 and S12 with
S16); each batch has one Gate 2 and one natural CI. Every authoritative
Gate 2 of a batch that changes the native qualification runs on the
integration host with `--pietto-sqlite-class=qualified` (D78.07).

### B2 single-writer order

The lead fixes it; a later arrival rebases.

- **Shared seam.** The connector set, the dialect sets and the three family
  mappings change in S07 alone, in one commit (AD78.03, 80-4).
- **Second maintenance batch first.** S07 and every later integration start
  on the head that batch publishes, since it rewrites much of `tests/`; S06,
  a documentation commit, is replayed onto it. New files come first and
  shared hunks last, each step's changed lines compared before and after
  (74-2, 75-1).
- **Plan hot files.** `project_sql_plan_target_assessment.py` and
  `project_sql_plan_pure_boundary.py`: SQLite S07 first; DuckDB B2's T02,
  if it must touch them, after it; MySQL catch-up and pure-boundary repairs
  serialize on them too.
- **Shared pages.** `docs/language.md`, `docs/capabilities.md`,
  `docs/project-package.md`, `docs/execution.md`, `docs/spec/diagnostics.md`,
  `docs/roadmap.md`, `docs/status.md` and `README.md` have one writer at a
  time at integration: SQLite S07, S08, S10, S11 and S16 and DuckDB B2's
  T08 in the order they integrate. `docs/spec/diagnostics.md` is written at
  times the lead schedules apart from Phase81's diagnostic review (P03,
  PL.58).
- **Shared tests and VR2 pages.** `tests/test_harness_execution_api.py`
  (SQLite S12, DuckDB T06), `tests/test_sql_compile_api.py` (SQLite S08,
  DuckDB T02 if needed) and `docs/development.md` have one writer at a time.
- **Every integrated tree** reruns the repository-wide owners and the
  AD78.03 firewall (72-2). The two B2 lines have no publication order: each
  fails closed.

### B2 qualification and replay

Qualification is in process on the measured build, as for B1 (D78.03), now on
CPython 3.13.13 and 3.12.13 (Q8): native cells over `:memory:` or test-owned
files under the pytest base temporary directory, oracles written before the
run, a fabricated-output self-test that fails every fail-open shape (72-4),
skips counted beside passes (75-3), a failed cell first a question about its
judge (74-1), and a form without a passing cell shipped refused (73-6).
Native cells run on the integration host; Teach does not run them (D78.09),
and hosted CI asserts the refusal and runs the byte and golden tests.

R1 is one campaign after S10, under D78.08's conditions, which PL.47 extends
to it: the pinned PostgreSQL 18.6 image on the Docker Engine, one owned
container with `--pull=never --network none`, holding one of the three
PostgreSQL slot locks. Its entries are T1's new project PostgreSQL bytes and
every T2 form: `having`, `count_distinct`, `avg(Int)` and the one-sided
`sum(Int)`. The `avg` entries pass on data whose sum does not depend on the
order, and a cancelling case is recorded as an observed difference, not a
failure, unless the lead's `avg` ruling says otherwise. The fixture's name is
IMPLEMENTATION_FREEDOM.

**Void rules** (D78.10, D78.11). The manifest, expectations, judge, driver,
exit codes and void rules are frozen and reviewed before each attempt. The
campaign ends with its first run that ends `PASS` or `FAILED`; before that
it may contain void attempts, each kept and charged to P78B2. When a void
attempt's cause lies in the frozen package or a reviewed runtime value, the
next attempt waits for a revision that passed review; otherwise it runs the
same package under a new run id. A run that never started is no attempt. The
campaign's two hours are summed over all its attempts, void ones included; no
attempt starts once they are spent, and each runs under the time that
remains, less the driver's cleanup, as an outer limit
(`timeout --foreground --preserve-status -s TERM`, never `-k`). A `FAILED`
campaign runs again only after its integrity audit finds a judge defect and
an erratum is written. Another campaign beyond R1 needs the owner.

**Reuse and invalidation.** An entry of `postgres_replay_v1.json` or of R1's
result keeps its saved rows only while its PostgreSQL bytes, fixture rows,
oracle and carriers are unchanged (D78.10); a form that B2 adds has no replay
until R1 runs it. A native cell binds the build triple it observed and the
bytes it ran, so a byte change reruns it and a golden changes only with its
review. A change of the connector set, the three family mappings or the
dialect sets reruns their consumers: `check --project`, the PostgreSQL,
MySQL and DuckDB emitters, `pietto lsp` through `check`, and the firewall.

**R1 record.** The campaign ran once on 2026-11-17 and ended `PASS` (exit 0)
with its first attempt, after the first lane had stopped before any freeze
because the host could not reach the Engine. Its package is B1's
preregistration v2.3 with a delta outside Git: r1, frozen at 05:22:23Z, had
an independent review that found two medium and eleven low issues; r2,
frozen at 05:50:09Z, answers each and was reviewed before the attempt
(D78.10). Attempt: run `p78b2-r1-20261117T055630Z`, 05:57:08Z to 05:57:23Z,
outer wall time 14.68 s, charged 15 s of the two hours (D78.11); the pinned
PostgreSQL 18.6 image on Docker Desktop 4.99.0 (Engine 29.9.3), one owned
container with `--pull=never --network none`, PostgreSQL slot lock 2 of 3,
removed by its label with no container, network or volume left. 124 entries
passed: the 14 single-file `_T2_CELLS` and 110 project cells, 12 of them
with bound arguments, each argument sent as its physical type's OID, format
and bytes; `ZERO_SIGN` on `project-select-every-type` and
`project-group-order-by-max`, as their single files in B1, and `AVG_ORDER`
on `t2-avg-int-cancelling` and `project-t2-avg-int-cancelling`, each value
one of the left-to-right sums the manifest listed before the run. Not
entries: B1's 105 entries, reused because their bytes, fixtures, oracles and
carriers are unchanged; 3 premise controls and 44 `-nocase` variants
(SQLite-only premises; a variant's program and PostgreSQL contract equal its
base cell's); 28 project cells that the PostgreSQL project pipeline refuses
with `PIE-B1003` (`Bool` comparisons). R1 does not verify: (1) `having`
with `Int`, `Text` and `Float` query parameters, since the only such cell,
`project-t2-having-parameters`, also compares a `Bool` parameter; (2) a
`Bool` query parameter echoed in `select` or read bare in `where`, which the
cells hold only beside refused `Bool` comparisons; (3) binding a `pg_bool`
argument at all; (4) the `Bool`-name cells in either mode; (5) the
one-sided `sum` overflow, whose SQLSTATE 22003 stays inferred, since only
the in-range bounds ran. The result is
`tests/fixtures/sqlite/postgres_replay_r1.json`, bound by
`test_each_r1_postgres_replay_binds_the_bytes_it_ran`.

### B2 midpoint and unfreeze

**Midpoint (after S10 integrates).** Each T1 and T2 form emits with a
reviewed golden or refuses with its listed text; R1's result; the ledger's
measured rate projects the first tier and records whether PL.15 raised a
figure; the newest published head's CI health is read; S05's facts are
restated (the range evidence, the integrity check and the UTF-8 check);
1b's progress; the state of DuckDB B2 and of Phase81's diagnostic review
(P03, PL.58); and the owner decides
which second-tier items (T3 JOINs, T4 arithmetic with the sheet's Q4, T5
windows, two replays) open and with what ledger. T3 first restates the
roadmap's Reminder 8 (JOIN facts of compiled replay and live analysis, the
forged compiled `median`) or gets the semantic and ProjectIR owner's
ARCHITECTURE_DECISION; the first tier meets it by exclusion, since it opens
no JOIN and refuses bundles. The midpoint record goes into this route's B2
record (80-5).

**Unfreeze conditions.** These need the owner: a form beyond PL.47's;
a new `PIE-*` code or a public text outside the specification's tables; a
dependency, extra or pin; a container run beyond R1, or any MySQL run;
another build or platform; SQLite bundles, saved results, jobs or R2; a
looser defence or value check; an extension-repository push; any ledger
ceiling.

### B2 risks

1. **The caller's file.** Malformed files, objects posing as sources,
   out-of-domain values and indexes that disagree with their table can give
   wrong results or reach a library defect. The eleven defences, the value
   and integrity check, S12's controls and a documented boundary that claims
   no memory safety of the library bound it; 1b can be withdrawn at the
   midpoint without touching 1a.
2. **SQLite's numeric and text meaning.** Partial-sum overflow, collation,
   identifier case and affinity differ from Pietto's rules. The
   specification's differences table, the one-sided `sum`, the explicit
   `COLLATE BINARY` and R1 bound it; a form measured otherwise stays refused.
3. **Shared surfaces.** DuckDB B2, Phase81's diagnostic review (P03,
   PL.58) and the second maintenance batch share pages, tests and the plan
   hot files. New files first, the one-commit seam and the single-writer
   order bound it.

### B2 initiation-gate checklist

| # | Field | Answer |
| ---: | --- | --- |
| 1 | Live authority | Gate 0 on `8cb9d9de` (tree `b2ad91b2`) with natural CI `43767179471` and its health (PL.07); PL.47 and the decisions it keeps; Phase79 and Phase80 completion audits read by S16; Phase78's own audit written by S16 |
| 2 | User/product outcome | SQLite in project mode, the common aggregates, and an optional read-only run over a caller's file; not other builds, writing, other types, bundles, jobs, R2 or parity across databases |
| 3 | Semantic reference model | Project semantics (`ProjectSQLPlan`), the Float value contract and checked `Int`; the PostgreSQL emitter's result for the same source is the reference (R1). Roots: AST, project semantic facts, the plan |
| 4 | Identity model | Source occurrence; `sqlite.table` names one exact bare table, equal to the contract's `relation.name`; the dialect name is no qualification; target identity is family, release, source id and compile options; the run's input is the caller's path with its schema and values checked again in one snapshot each attempt, with no content digest |
| 5 | Construction states | Refused, emitted (bytes and golden) or qualified (a passing native cell); only qualified forms publish |
| 6 | Proof posture | Asserted: emission premises (`STRICT`, UTF-8, domains). Observed: S05's cells and S12's timing. Derived: SQL bytes, the one-sided `sum` equivalence, the SQLite range read. Verified: S09 and S12 cells, R1. Unknown: nothing. Disproven: that the check and query of a 256 MiB file fit 20 s (S12); that the integrity check runs only Pietto's code within the deadline, since it computes the file's index and generated-column expressions (S12's review), so the source check refuses them |
| 7 | Layer ownership | Semantic connector checks own the spelling; the plan layer is unchanged; `_project/project_sqlite_*` owns SQLite lowering, rendering, refusals and verification; the CLI and `compile_query` own dispatch; `execution/_sqlite.py` owns the route and file checks; tests own qualification |
| 8 | Dependency direction | The symbol whitelist of the decisions table; no other pipeline module; the firewall test checks the names; the PostgreSQL/MySQL pipeline never receives `sqlite` |
| 9 | Versioning and migration | CLI JSON v1 unchanged; project documents keep their v1/v2 envelopes with one more `family`; compiled records unchanged, so `VERSIONS` stays (D76.13); no migration |
| 10 | Target requirements versus provider capabilities | Requirements are the premises and forms; provider evidence is the measured triple; other builds are not qualified, not unsupported |
| 11 | Interchange | SQL text, CLI JSON and the compiled document cross the boundary, and in 1b a `ResultBatch`; the database file does not: Pietto reads it and copies nothing |
| 12 | Execution | Only in 1b, owned by `execution/_sqlite.py`: in process, read-only, `premise=None`, `isolation="stable"`, its resources and effects listed in the specification |
| 13 | Resource lifecycle | One connection and one read transaction per attempt, rolled back and closed in `finally`; deadline and cancel through the progress handler and `interrupt()`; tests keep files under the pytest base temporary directory |
| 14 | Security and trust | The defences and value check of PL.47; no network, no extension loading, no writes, no SQL from the file executed; no claim of the library's memory safety |
| 15 | Algorithms and data structures | The existing plan walk and a direct tree renderer in the DuckDB adapter's shape; nothing new |
| 16 | Complexity posture | Emission linear in the plan; the run's check linear in the source tables plus the integrity check, under 128 MiB, 1,048,576 rows per table and `ExecutionLimits.seconds` |
| 17 | Invalidation | [Reuse and invalidation](#b2-qualification-and-replay) |
| 18 | Cache | None; each qualification run and each attempt observes and checks again |
| 19 | Concurrency | One unshared connection per attempt; one connection per test cell, safe under xdist; lanes under PL.01 and PL.03; R1 under the slot locks |
| 20 | Diagnostics | No new code; `PIE-B1003`, `PIE-B1001`, `PIE-B1004` and `PIE-B1000` with the specification's details and reasons, in its rule order; S11's `PIE-R` details |
| 21 | Inspection | `check` and `explain` stay read-only and dialect-neutral; no SQLite inspection command |
| 22 | UX | One spelling, `sqlite.table("name")`, kept by `pietto fmt`; the specification's usability row; refusals name SQLite and the reason |
| 23 | Conformance | The language guide's SQLite sections, the specification, the CLI and project JSON specifications, the contract tables, diagnostics, golden policy; the finite native matrix on the measured build |
| 24 | Differential and fuzz assurance | Prewritten oracles, the BAG/NULL oracle, R1. Fuzzing and reduction are `NOT_APPLICABLE`: the forms are a closed finite set that the native matrix enumerates; owner of high-intensity assurance: Phase81 |
| 25 | Packaging | No dependency, extra or lock change (`arrow` reused); no grammar change; new modules enter the wheel, so Gate 2 runs the package check |
| 26 | Support matrix | Linux x86-64, CPython 3.13.13 and 3.12.13, one build; SQL text everywhere CI runs; D5 A stands for the extras |
| 27 | Release, deprecation, and EOL | The `0.2.x` after its Gate 2, `0.2.2` at the earliest, each release approved by the owner; an alpha surface in the release notes and freeze ledger; rollback by revert; no deprecation |
| 28 | Readiness and exact deferred owners | Prerequisites: Gate 0, S05, the second maintenance batch before S07; deferrals in the table below |
| 29 | Slice route | [B2 slices](#b2-slices); non-goals in [B2 scope](#b2-scope) |
| 30 | Repair and stop conditions | P78B2's ceilings with PL.15; stop at a ceiling, an unproved build or input identity, a needed code or text outside the specification, a dependency, a container run beyond R1, an extension push, a trust regression, or a replay that changes an existing meaning; failed candidates and runs are preserved; no commit or push without authorization |

The usability row is the specification's. The external reference record of
untrusted SQLite files is [below](#b2-external-reference-untrusted-sqlite-files);
1a opens no file, so it was `NOT_APPLICABLE` before S11.

### B2 external reference: untrusted SQLite files

S11 wrote this record before its code, in the gate's eleven-item shape.

| # | Field | Untrusted SQLite database files |
| ---: | --- | --- |
| 1 | Snapshot/date | 2026-11-16 (UTC). SQLite's own guidance on database files of uncertain provenance (its "Defense Against the Dark Arts" page, with its URI filename, WAL and authorizer pages) as the S11 lane knew it, not re-read, since the lane worked offline; the measured build `3.53.1` through S05's probe and S11's development runs on the integration host. Only S12's cells are qualification evidence |
| 2 | Problem/constraints | A caller hands Pietto a file whose bytes no one vouches for: a malformed file can reach a library defect, its schema is SQL that SQLite parses when it opens the file, its objects can pose as tables, its values can break domains that a `STRICT` table does not enforce, and its indexes can disagree with their table. Pietto may only read it, in process, on one build, within the attempt's deadline |
| 3 | Semantic/identity model | The file is named by its path; what counts is what one read transaction sees, checked again in every attempt, with no content digest. A source is one `STRICT` table of `main` with exactly the contract's name and columns. A native error is identified by its extended result code; `sqlite_errorname` is no identity |
| 4 | Layering/dependency direction | Upstream puts the defences in the application around trusted SQL: open flags and URI parameters, `sqlite3_db_config`, PRAGMAs, an authorizer and a progress handler. Pietto keeps them in `execution/_sqlite.py`; besides its fixed checks, the adapter's verified statement is the only SQL it prepares |
| 5 | Algorithms/data structures/complexity | `PRAGMA integrity_check` walks every page of the table and its indexes, linear in their size, and upstream advises it (or `quick_check`, which skips the comparison of indexes with their table) before any other statement. The value check is one scan of the table and a Python decode of each `Text` value |
| 6 | Interface/version/capability model | The `mode=ro` URI; `SQLITE_DBCONFIG_DEFENSIVE`, `SQLITE_DBCONFIG_TRUSTED_SCHEMA` and `SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION`; `PRAGMA query_only`, `cell_size_check` and `mmap_size`; the authorizer, the progress handler, `sqlite3_interrupt`, the busy timeout, `sqlite3_limit` and `sqlite3_hard_heap_limit64`. CPython 3.12's `sqlite3` reaches each of them except the heap limit |
| 7 | Testing/operational lifecycle | One connection and one read transaction per attempt, closed in `finally`; tests build their own files, malformed and hostile ones included, under the pytest base temporary directory; nothing outlives an attempt |
| 8 | Pitfalls/migration costs | A URI built by concatenation lets a file name inject parameters (S05: `weird?mode=rwc&immutable=1#frag.db` created `weird`); `immutable=1` ignores locks and reads old rows; a 0-byte file and `/dev/null` open as empty databases, and opening a FIFO blocks; SQLite opens the `-wal`, `-journal` and `-shm` files beside the file itself, so a FIFO there blocks it too, and it deletes the `-wal` file beside a 0-byte database (S11's review); Python's default busy timeout waits 5 s; `SQLITE_IGNORE` reads a column as NULL silently; `count(*)` reaches the authorizer with no database name; in rollback-journal mode a reader blocks the caller's writers; a read-only reader of a WAL file creates its missing `-wal` and `-shm` files and leaves them (observed by S11), and truncates and rebuilds an existing `-shm` file, through a hard link too (S11's review); `integrity_check(name)` checks only that table and its indexes, and a numeric argument is an error limit, not a name; it computes the file's index expressions, partial-index `WHERE` clauses and virtual generated columns for every row, without the authorizer and within single steps the progress handler does not split (S12's review: a 12 KiB file ran 94.5 s and 1.2 GB under a 20 s deadline); no application check proves the library's memory safety on malformed input |
| 9 | Disposition | Adopt: the percent-encoded `mode=ro` URI, the regular-file check of the file and of the `-wal`, `-journal` and `-shm` files beside it, defensive mode with trusted schema off and no extension loading, `query_only`, `cell_size_check` on and `mmap_size` 0 (upstream's list for untrusted files, added by the re-check below), an allow-or-deny authorizer, the progress handler and `interrupt()`, a busy timeout inside the deadline, one read transaction, and `integrity_check` of the source before any of its rows is read. Adapt: the integrity check covers the source table and its indexes, not the whole file, since an attempt reads nothing else beyond the schema SQLite parses; it runs only once the source has no index with an expression key or a `WHERE` clause and no generated column (S12's review), so every expression it computes is Pietto's own. Not adopted: `sqlite3_limit` reductions, since every statement and expression that runs is then Pietto's own and the authorizer refuses `ATTACH`; the heap limit, which is process-wide and would bound every other SQLite user in the process, where the 128 MiB file cap bounds the input instead |
| 10 | WHAT_NOT_TO_COPY | `immutable=1`; URI concatenation; `quick_check` as the integrity check; Python's default busy timeout; `SQLITE_IGNORE`; `sqlite_errorname` as an error's identity; SQLite messages as Pietto text; declared `NOT NULL`, `CHECK` or column types as proof of the values; a passing integrity check as proof of the domains; the job store's `QUALIFIED_SQLITE` constant as a shared owner |
| 11 | Pietto owner affected | `execution/_sqlite.py`, `_project/project_sqlite_result.py`, the specification's [execution](../../spec/sqlite-project-v1.md#execution) section, `docs/execution.md`, S12's control cells |

Re-check of Q6a and Q6b against this record (S11). No answer is loosened:

1. `integrity_check` of the source runs right after the schema reads, before
   the row count, the value scan and the statement; the sheet's Q6b (i)
   listed it after the value scan, and upstream checks before reading.
2. Defence 2 also sets `cell_size_check` on and `mmap_size` to 0, and reads
   them back with the other settings.
3. The integrity check stays scoped to the source table and its indexes
   (row 9).
4. A NUL in `Text` is found while each value's bytes are decoded in Python,
   in the pass that checks UTF-8, instead of by `instr`; the refusal is the
   same.
5. The value check also checks each `Text` value's `max_characters`, which
   the contract's domain states and the DuckDB route checks (D79.04); this
   closes the specification's open item.
6. A `Text` parameter that holds NUL is refused (`PIE-R1006`), since PL.47
   admits no NUL in `Text`.
7. The WAL companion files of row 8 are an effect the execution
   documentation states; the database's own content is never written.

### B2 deferred owners

| Item | Owner and latest point |
| --- | --- |
| The second tier (T3 to T5, the sheet's Q4 arithmetic, windowed `sum`) | The owner at the midpoint; if approved, a follow-up package that the Phase78 completion audit hands over, with its own ledger; unclaimed items are unsupported at the Phase82 freeze |
| Reminder 8 | Met by exclusion in the first tier; restated before T3 opens, or the semantic and ProjectIR owner's ARCHITECTURE_DECISION |
| Naming a native error by its extended `sqlite_errorcode` instead of `sqlite_errorname`, since a `STRICT` type error's name is `unknown` (D78.04 named them by name) | The lead, as an ARCHITECTURE_DECISION, D78.12, recorded after a first audit of S06–S12 found it missing and before the audit of the batch that publishes them; S11 implements it (the code, and the message where the code is not enough) |
| Run-time guarded arithmetic, `Float` arithmetic, `/` and `%` | A later Gate 1 with a use case; Phase82 freeze input |
| Admitting `Text` that holds NUL | A later SQLite execution Gate 1 |
| Other builds, Windows and macOS | Not qualified (PL.40 D9 A, D5 A); the Phase82 support matrix |
| The SQLite capability-facts profile | The editor capability-facts Gate 1 |
| SQLite bundles, saved results, relay, jobs and R2 | Later execution and recovery owners; Phase82 freeze input |
| The third whole-tree test pass | The second maintenance batch (PL.40 D14 A), before the Phase78 completion audit |
| `verify_project_sql_plan`'s memo | Phase81 (PL.40 D15 A) |

### B2 budget

P78B2 is B2's own cumulative ledger (PL.47): `C100/F300/D3,700/S5` for 1a
(S05 to S10, R1 and S16) and `C60/F180/D2,300/S3` more for 1b, together
`C160/F480/D6,000/S8`. These are ceilings, not targets; the slice allocations
above are planning figures that sum to `C145/F440/D5,230/S6`. Under PL.15 a
figure that reaches 80% of its ceiling gains half of itself, and the lead
reports each raise; reaching a ceiling still stops the work for the owner.
The sheet's drafting and the probes before Gate 0 move to P78B2 by the PL.06
precedent. P78B2 closes with S16; a second tier gets its own ledger. The lead
keeps the running ledger, and each lane reports its commands (D, D76.17) and
pytest starts (F).

### B2 record

S16 writes this record, the midpoint's included (80-5), and the
[completion audit](completion-audit.md) records its checks. The first tier
is complete: S05 to S12, R1 and S16, on the ledger P78B2.

**First batch, published.** S06–S12 were integrated one commit each on
`main` and published as one batch with the decision record that precedes
them, the diagnostics rows, the decision rows of PL.59 and D78.12, the
Windows CI change (PL.59 (2)) and the MySQL catch-up's Gate 1 record
(PL.59 (3)): 13 commits on `64a7f885`, fast-forward pushed under PL.52 on
2026-11-16 at 20:04:45Z by the lead's record, ending at
`31859bc66a6f53d301491dcaed9ad9111c94e089` (tree
`8e8a9fba8f04402c2276b012836ae6b56165dc11`). Its Gate 2 sealed that tree
(the [completion audit](completion-audit.md#gate-2-durations)), and its
natural exact-head CI `43946002245`, push/main attempt 1, succeeded: the CI
health of `44006845752` accepts it into its history as a natural successful
attempt 1 on `main`. The pure verifier fidelity repair followed as its own
batch, four commits ending at `6a0646b4` (PL.20, PL.60), which is not
Phase78's.

**Second batch.** R1 `a47a5713` on `6a0646b4`, S16 above it and, above
S16, the VR2 fix that lets a split Gate 2's local receipt accept the
route's counted ARROW skip and, above the fix, the documentation commit
that records the Gate 2 and CI facts of DuckDB B2's batch in its
[audit](../phase-79/b2-completion-audit.md#budget-failures-and-gate-2)
(by the lead's record of 2026-11-17), with one
Gate 2 and one natural CI (PL.59 (3)); they were published as one batch
under PL.52, ending at `300f0a93` (tree `9fb0d7c3`), on 2026-11-17 at
07:57:25Z by the lead's record, and `0.2.2` carries it (PL.55, PL.59). A
documentation commit after its publication recorded its Gate 2 and its
natural exact-head CI `44042698462`, which passed all 21 jobs, in the
[completion audit](completion-audit.md#gate-2-durations).

| Slice | Commit | Delivered |
| --- | --- | --- |
| S05 | none | Gate 0 and the probe matrix ([starting point](#b2-starting-point)) |
| S06 | `e990fc49` | The [specification](../../spec/sqlite-project-v1.md), this route's B2 sections and the 1a fragment |
| S07 | `287783db` | The shared seam in one commit (80-4): `sqlite.table` among the explicit-module connectors and the three family mappings; PostgreSQL, MySQL and DuckDB emission refuse the source |
| S08 | `accbadfa` | The separate adapter `src/pietto/_project/project_sqlite_*.py` with the T1 forms, the CLI and compile API dispatch, and the import whitelist test |
| S09 | `08e96540` | Native T1 project cells under CPython 3.13.13 and 3.12.13 and a second coverage law over the adapter's vocabulary |
| S10 | `2a805acf`, `371cc8f0` | The T2 aggregates in both modes and their native cells; then single-file `Bool` literals written `1` and `0` (PL.54 (1)) |
| S11 | `1845e1b5` | `compile_query(dialect="sqlite")` and the `sqlite_file` route, with the [external reference](#b2-external-reference-untrusted-sqlite-files) and D78.12's naming of native errors |
| S12 | `dd7e3b5f` | The route's native cells under both interpreters and the 128 MiB cap from its timing |
| Batch records | `00ac418f`, `2d910d34`, `a6c89521` | The diagnostics rows; PL.59, D78.12 and the batch rule; both Windows jobs run the route's test file |
| R1 | `a47a5713` | The PostgreSQL replay, `PASS` ([R1 record](#b2-qualification-and-replay)) |
| S16 | `1580aaa1` | This record, the roadmap and status rows, the specification's construction state, the Phase78 lessons and the completion audit |

No golden fixture file was added: project bytes are pinned in
`tests/test_sql_sqlite_project_emission.py` and in the native cells'
prewritten oracles, and the single-file golden changed only for the `Bool`
literals (PL.54 (1)).

**Midpoint (after S10).** The lane that ran S06 to S10 stopped after S10's
review, before S11. The lead's record of 2026-11-16 at 08:25Z holds S10's
state and its review's `Bool` finding, and the owner answered the `Bool`
question (PL.54 (1)) and the midpoint (PL.54 (2)) later that day in the
dialogs PL.54 records. No midpoint record was written then; S16 writes it
from the repository's records:

- **Forms.** Each T1 and T2 form emitted with pinned bytes or refused with
  its listed text on S10's tree, and on the published tree the coverage law
  finds a native cell for every form the adapter's vocabulary emits.
- **R1.** Not run at the midpoint: it waited for the Docker Engine (PL.54
  (2)), and its first lane stopped before any freeze because the host could
  not reach the Engine (PL.56). It ran on 2026-11-17 and passed (above).
- **Ledger.** By the lead's ledger at the stop: at most C5, F48, D1,603 and
  S0, 27% of D6,000; no figure reached 80%, so PL.15 raised none. No
  projection of the tier was recorded then; the completion audit gives the
  ledger after R1.
- **CI health.** The newest read before the stop was that of `851ad83f`,
  INSUFFICIENT_EVIDENCE with a WATCH screen (the
  [Phase79 B2 audit](../phase-79/b2-completion-audit.md#baseline-and-publication-boundary));
  S16 reads that of `44006845752`.
- **S05's facts.** The SQLite contract reader reads a field's `int_range` as
  the DuckDB adapter does (*derived*), and the import whitelist test locks
  the adapter's imports. S11 implements the integrity and UTF-8 checks as
  the specification's execution section lists them; S12's review found that
  the integrity check computes the file's index expressions and generated
  columns, so the source check refuses them (checklist row 6).
- **1b.** S11 and S12 had not started; they ran after the owner's answer.
- **Beside B2.** DuckDB B2 had passed its own midpoint without a stop and
  was answered later (PL.54 (4)); Phase81, and with it its diagnostic
  review, was stopped (PL.54, PL.58).
- **Owner's decision.** "Finish the first tier; the second tier goes into my
  plan" (PL.54 (2)). The second tier (S13 JOINs, S14 range-proved
  arithmetic, S15 windows) comes before the Phase82 freeze, with its own
  Gate 1 and ledger (PL.58 (4)); P78B2 closes with S16.

Of the [deferred owners](#b2-deferred-owners), D78.12 is recorded and
implemented by S11, and the third whole-tree test pass ran in batch 2
(PL.49); the others keep their owners.

## B2 second tier

On 2026-11-17 the owner answered the Gate 1 of B2's second tier (D78.14):
S13, INNER and LEFT JOINs of `sqlite.table` sources with their execution on
the `sqlite_file` route; S14, range-proved `Int` arithmetic; and S15,
windows over one source read; two PostgreSQL replays, R2 and R3; and the
ledger P78T2. Its two batches are pushed under a standing authorization
once the `0.2.2` release commit is pushed (PL.64 (3)), so the tier is not
in `0.2.2`. The tier is done before the Phase82 freeze, which moves later
if it must (PL.58 (4), D78.14 (1)). The
[SQLite project specification](../../spec/sqlite-project-v1.md) holds the
contract; this section binds the tier's Gate 0, slices, order, stop points,
replays and budget.

### B2 second tier starting point

Gate 0 was first bound on 2026-11-17 to `6a0646b4` and, once the R1 and S16
batch was published, rebound read-only at 08:01:48Z to `300f0a93`, tree
`9fb0d7c3`, whose natural CI `44042698462` passed all 21 jobs. S14 and S15
started from that head. Before the first batch integrated, `main` moved to
`900e89156fe0136aef43b90bb2c750864cb6928b`, tree `54387606`, which adds
JF's J1 (`a5bd2c8e`, PL.61, PL.62) and the decision record of the owner's
answers; the first batch integrates on it. Its natural exact-head CI
`44166283520`, push/main attempt 1, passed all 21 jobs and finished at
20:32:19Z. Its health, read through the owner's read-only token (PL.07),
passed `verify_workflow_health` of that tree's `scripts/ci_workloads.py`
over its 15 `ci-health` artifacts: status INSUFFICIENT_EVIDENCE with a
WATCH screen, history available with 3 samples accepted, none rejected and
none comparable, cost incomplete. Health is advisory.

Before Gate 0, D78.14 (2) authorized offline probes; one probe script ran
at 07:53Z on CPython 3.13.13 and 3.12.13 over memory databases. It ran
again, byte for byte, on `900e8915`'s environment at 20:31Z: each
interpreter's output equals its earlier one line for line, apart from
3.12's line on the build triple, which now reads `true` where the earlier
run could not import Pietto, and the two interpreters' outputs are equal
apart from their environment lines. Both link SQLite `3.53.1` with the
source id and the 46 compile options of `QUALIFIED_SQLITE`. The
specification's differences rows rest on these probes and on the slices'
native cells; only the native cells are qualification evidence.

### B2 second tier slices

Slice ids continue S13 to S15 as the Gate 1 named them; S13 splits into
emission (S13a) and execution (S13b). Each slice is one commit, binds its
exact base, write set, commands and acceptance when it is expanded, writes
its own release-note fragment and opens each form in the rule that refused
it (74-4). Each opened form names every entry point it reaches and has a
cell on each (77-1).

| Slice | Content | Write set | Checks and acceptance | Depends on | C/F/D/S |
| --- | --- | --- | --- | --- | --- |
| SP | The specification's second-tier rows, this section and D78.14 | `docs/spec/sqlite-project-v1.md`; this route; `docs/decisions.md` | `scripts/release_notes.py check`; `tests/test_repo_docs_links.py`, `tests/test_repo_release_notes_fragments.py`, `tests/test_repo_docs_examples.py` | Gate 0 | 1/10/200/0 |
| S14 | `Int` `+`, `-`, `*`, unary `-` and `abs` in `select` and `where`, and all but `abs` as the argument of `avg` and `sum`; `check` refuses the rest of T4 b on every target, such as arithmetic in `having` or in the argument of `min` and `max` (D78.15); an interval proof in a new adapter module that reads only the contract's `int_range` and the plan's literals and imports no pipeline module (lead, an ARCHITECTURE_DECISION); rule 9b; rules 9, 10 and 35 rewritten | New `src/pietto/_project/project_sqlite_range.py`; `project_sqlite_emission.py`, `project_sqlite_sql.py`; the specification; its shared-page hunks; its fragment | `tests/test_sql_sqlite_project_emission.py`; native cells in `tests/test_sql_sqlite_native.py` at each operator's bounds and one past them, the minimum literal, `abs` of the minimum, a one-sided `sum` of a product and arithmetic in `where`; PostgreSQL, MySQL and DuckDB bytes unchanged; the import whitelist test | Gate 0 | 3/20/450/1 |
| S15 | `row_number`, `rank` and `dense_rank`, a window `count`, `min` or `max`, and a window `sum` in the frames of D78.14 (4), over one source read; inline `OVER` with NULLS clauses and `COLLATE BINARY` at `Text` keys; the authorizer's three ranking functions; rules 5b and 5c | `project_sqlite_emission.py`, `project_sqlite_sql.py`; the authorizer's functions in `src/pietto/execution/_sqlite.py`; the specification; its shared-page hunks; its fragment | S14's owners; native cells for ties and NULL keys, `COLLATE NOCASE` keys, each frame's `count`, `min` and `max`, each admitted frame's `sum` at its bounds and one past, and refused sliding frames; a window query on the route over 1,048,576 rows inside the 20 s deadline | Gate 0, beside S14 | 4/25/650/1 |
| R2 | PostgreSQL replay of the new bytes of S14 and S15 | A reviewed preregistration delta outside Git; a new fixture under `tests/fixtures/sqlite/` and its test | [Replays](#b2-second-tier-qualification-and-replay) | The first batch integrated; P2 | 2/10/300/0 |
| S13a | The JOINs of D78.14 (3), with grouping and aggregates on joined rows; `single_matches` and `relationship_matches` stay refused; aliases `s0` to `sN`; rules 5 and 5a; `compile_query` writes the SQL | `project_sqlite_contract.py` (each source's contract), `project_sqlite_emission.py`, `project_sqlite_sql.py`; the specification; its shared-page hunks, `docs/project-package.md` among them; its fragment | Native cells for each JOIN kind, NULL keys, `COLLATE NOCASE` keys, self-joins, LEFT rows under a later `where` and grouping on joined rows; the adapters' fence of PL.62 (2) and a firewall that the adapter reads no JOIN `properties` | J1 on `main` (PL.61 (2)); its shared hunks after the first batch | 4/25/700/1 |
| S13b | The route over a JOIN: every source table's defences and checks in the one read transaction, the authorizer over every source table, the bounded read and the uniqueness check of D78.14 (5) and (6) | `src/pietto/execution/_sqlite.py`, `project_sqlite_result.py`; `docs/execution.md`; the specification's execution section; `README.md`; the diagnostics rows | `tests/test_execution_api_sqlite_file.py`: each source's bad objects and values; two tables joined on a key; a fan-out past `max_rows`; errors after the stop; duplicate keys refused, `-0.0` and `0.0` as one key, keys that differ only in case on a `COLLATE NOCASE` column delivered; a JOIN without aggregates not scanned; two tables near 128 MiB timed with the check | S13a | 4/25/650/1 |
| R3 | PostgreSQL replay of the new bytes of S13 and of S13 with S14 | As R2 | As R2 | S13a; P2 | 2/10/300/0 |
| C | Closeout: this section's record, the roadmap's freeze-ledger row and deferral table, the status page, the fragments' known limitations, the lessons and the acquisition review | As listed | Documentation owners; CI health | R3, S13b | 1/10/250/0 |
| Integration | Per batch: rebase, integration, a one-round audit, repairs and Gate 2 | — | The repository-wide owners and the AD78.03 firewall on the integrated tree (72-2); Pyright over the tests too (72-1) | Each batch | 6/40/800/0 |

The first batch is SP, S14, S15 and R2, the second S13a, S13b, R3 and C.
They publish together as one batch, each slice one commit, with one Gate 2
of the final tree on the integration host with
`--pietto-sqlite-class=qualified` (D78.07) and one natural CI on its head.

### B2 second tier order and stop points

The lead fixes the order; a later arrival rebases.

- **Adapter and specification.** S14, S15 and S13a change
  `project_sqlite_emission.py` and `project_sqlite_sql.py`, and every slice
  changes the specification. S14 and S15 were written in parallel from
  `300f0a93`; they integrate as SP, S14, S15, then S13a, each rebased onto
  the one before, new files first and shared hunks last (75-4).
- **Execution route.** S15 changes only the authorizer's functions in
  `src/pietto/execution/_sqlite.py`, before S13b.
- **Shared pages and tests** keep the B2 rule of one writer at a time;
  `docs/spec/diagnostics.md` is written apart from Phase81's diagnostic
  review (P03, PL.58). S13a's firewall follows J1's fence in
  `tests/test_repo_static_checks.py`.
- **Hot files.** No slice is expected to touch the plan's
  `project_sql_plan_target_assessment.py` and
  `project_sql_plan_pure_boundary.py` or the results'
  `project_result_binding.py` and `project_execution_reader.py`.

| Stop | Where | Who decides |
| --- | --- | --- |
| P0 | Before the first batch integrates: Gate 0's CI, its health and the probe's second run | The lead |
| P1 | Before the first batch integrates: the specification's *derived* rows checked | The lead, who informs the owner |
| P2 | Before each replay's freeze: the Docker Engine's endpoint and the slot locks | The lead |
| P3 | The midpoint, after the first batch integrates and before S13a writes a shared hunk | See below |
| P4 | Before S13a writes code, J1 on `main` | The owner, through JF |
| P5 | A ledger ceiling after PL.15; a form beyond D78.14; a change to the plan layer or the PostgreSQL or MySQL pipeline; a new code or a public text outside the specification's tables; a looser defence; a hot file | The owner |
| P6 | A batch's push: after its Gate 2 passes and the `0.2.2` release commit is pushed, under D77.06's conditions; a failed natural CI stops for a new child commit | The lead, under PL.64 (3) |

**Midpoint (P3).** Each form of S14 and S15 emits with reviewed bytes or
refuses with its listed text; R2's result; the probe's second run against
the first; P78T2's measured rate projects the tier and records whether
PL.15 raised a figure; the newest published head's CI health is read; the
state of JF, `0.2.2`, DuckDB's second tier, E4B and Phase81, and the
distance to Phase82's Gate 1. From these the lead judges whether S13 is
done before the planned freeze and, if not, asks the owner whether the
freeze moves or the scope narrows (D78.14 (1)). The record goes into this
section (80-5).

### B2 second tier qualification and replay

Native cells follow the [B2 rules](#b2-qualification-and-replay) under
CPython 3.13.13 and 3.12.13. R2 and R3 each follow R1's conditions and
method (D78.08, D78.10, D78.11): the pinned PostgreSQL 18.6 image on the
Docker Engine, never another runtime in its place, one owned container with
`--pull=never --network none` holding one of the three PostgreSQL slot
locks, two hours summed over a campaign's attempts as an outer limit, and
no MySQL run. Each preregistration delta derives from R1's frozen package,
is reviewed before it freezes and is checked with its real launch command
and arguments (77-4); the engine's endpoint is read before dispatch
(77-5).

- **R2** covers S14's arithmetic in `select`, `where` and the arguments
  of `avg` and `sum` at the bounds, a one-sided `sum` that reaches the
  maximum included; and S15's rankings with ties and NULL keys, each
  frame's `count`, `min` and `max` of an `Int`, and each admitted frame's
  `sum` up to the bounds. The cells one past the bounds and an overflowing
  `sum` stay SQLite controls, as in R1, and the three forms that PostgreSQL
  project emission does not write have native cells only and no entry,
  which the owner ruled enough to open them (D78.15, D78.16).
- **R3** covers S13's JOINs (INNER, LEFT, NULL keys, self-joins, grouping
  and aggregates on joined rows) and the bytes of S13 with S14; `COLLATE
  NOCASE` keys run natively with their base cell's oracle and have no R3
  entry.
- A `row_number` entry compares only results that do not depend on the
  order of peers. R1's declared differences `ZERO_SIGN` and `AVG_ORDER`
  carry over; a new difference is written before the freeze, never after
  the run.
- Each campaign's fixture is a new file under `tests/fixtures/sqlite/`
  with a test that binds the bytes it ran, as R1's does. An entry of R1 or
  of `postgres_replay_v1.json` is reused only while its bytes, fixture
  rows, oracle and carriers are unchanged (D78.10).
- A campaign ends with its first run that ends `PASS` or `FAILED`; void
  attempts are kept and charged to P78T2; a `FAILED` campaign runs again
  only after its integrity audit finds a judge defect and an erratum is
  written. A campaign beyond R2 and R3 needs the owner.

### B2 second tier budget

P78T2 is the tier's cumulative ledger, `C40/F200/D5,000/S5`, counted from
zero and covered by PL.15 (D78.14 (8)). The slice allocations above sum to
`C27/F175/D4,330/S4` beside Gate 0's own work; the rebases while the
batches wait for `0.2.2`, about D100 each, are not in them. These are
ceilings and planning figures, not targets. The lead keeps the running
ledger, and each lane reports its commands (D, D76.17) and pytest starts
(F).

### B2 second tier record

C writes this record; the midpoint's goes here too (80-5).
