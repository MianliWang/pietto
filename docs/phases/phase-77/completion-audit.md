# Phase77 completion audit

Phase77 implements its [route](route.md): S01–S07, S09, S12, S13, S15, S19,
S20, S26 and S27, after D77.26 and D77.32 moved S21–S24 to the nested work
package and D77.35 moved the Wave A slices to the Wave A work package. The
decision rows added S06's `same_value` in a JOIN `on` (D77.41, D77.52), the
two `now()` slices (D77.42, D77.43), R2's first-step refusal (D77.67) and
the narrow openings R02 and R08 (D77.26). Its decisions are D77.01–D77.75,
AD77.01–AD77.03 and the shared rows PL.01–PL.26 of the
[decision record](../../decisions.md). This audit records delivery and
database acceptance. The batch that publishes S26, this audit and the
`0.1.12` release commit determines phase completion through its Gate 2 seal
and natural exact-head CI; this document does not certify its own
publication and records no release result.

## Baseline and publication boundary

The phase baseline is Phase76's published `main` at
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`, tree
`460e3e135d1dcb0b926928bc2632a889410f258a`. Gate 0 is bound to the head of
the maintenance/editor batch (D77.04), `ab972f362c433b234a74f542c5d274d22c8cdeae`,
tree `821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`, with natural CI
`42831340276` (21/21), and Gate 1 is D77.08–D77.13 in the route.

`0.1.11` carried Phase76 and the repairs published before its cut (PL.21);
its release commit `d03d6e4b` was published on 2026-11-13 (PL.25, PL.26).
Phase77's product slices then published in four `0.1.12` batches. The last,
ending at `e18d3673a4d4151d0bb73eafdfe8c68fe24745f8` (tree
`9b7bc006fad6a2f9cff43e0bb91cee01c245a2e9`), was fast-forward pushed on
2026-11-14 at 11:33:30Z by the lead's ledger, and
[natural exact-head CI `43590596831`](https://github.com/MianliWang/pietto/actions/runs/43590596831),
push/main, completed with success at 11:52:47Z and passed all 21 jobs. The
first batch's head `d068b0cb` keeps its failed CI `43485587196` (19 of 21
jobs: two test defects on the Windows jobs); the test-only child `0541765a`
repaired it and its CI `43493658185` passed. Interior batch commits take
their batch head's result. S26 (`0928aac0`) and this audit are local
candidates on `e18d3673` that change only documentation; by the lead's
ruling they publish with the `0.1.12` release commit as one batch.

## Accepted scope

Each row's release note, assembled into the `0.1.12`
[release notes](../../release-notes.md), states the exact forms, the SQL, the
refusals kept and the R2 boundary. MySQL R2 refuses every form below that
opens on MySQL (D77.67). A ready raw result only allowed the next
experiment; each opening rests on a run of Pietto's own emitted SQL on
PostgreSQL 18.6 and MySQL 8.4.12.

| Slice or line | Delivered, on MySQL projects unless stated | Commit, batch | Acceptance |
| --- | --- | --- | --- |
| S01 | Checked `Int` `+`, `-`, `*`, unary `-` and `abs` over nullable `BIGINT` fields as a whole SELECT item; MySQL error 1690 outside signed 64 bits | `65f75708`, third | Numeric R4 re-run ready (D77.15); the emitted-SQL experiment `MATCHED` on both databases in its seventh freeze, carried by D77.50. Its fifth and sixth freezes ended `UNQUALIFIED_RECEIPT` and are kept; the sixth's stall was a `main` defect that `60076a51` repaired (D77.63). |
| S02 | A direct `sum` of such a field as the guarded `SUM` (AD77.03) in its cell | `65f75708`, third | The numeric R4 guard cells matched on the text and prepared routes; the same emitted-SQL run. |
| S03 | Conditional, JOIN and two-level `sum(Int)` in nine forms; a statement whose only blocker on `main` was PIE-B1004 there is VERIFIED (D77.53) | `adff0bce`, third | Raw activity ready; the emitted-SQL experiment `MATCHED` in its second freeze. |
| S04 | Nothing: `Int` statistics keep PIE-B1003 (R04) | — | Eight MySQL `Int` statistics fell outside their bound (D77.29, D77.34). |
| S05 | `Float` statistics of one nullable field in its shape | `f7ce41e9`, first | `CANDIDATE_EMISSION_MATCHED` over 32 statements, carried to the rebased commit (D77.45, D77.50). |
| S06 | `==`, `!=`, `not (!=)`, `same_value` and `not same_value` of two `Float` row reads in 25 forms | `f41e6863`, first | 25 forms and 21 cells `CANDIDATE_EMISSION_QUALIFIED` on both databases (D77.47, D77.50). |
| S06 `same_value` in a JOIN `on` | On both targets, INNER, LEFT and RIGHT JOIN `on` cells; the MySQL `Float` cells stay refused (O7) | `10e29939`, fourth | Phases 1 and 2 `QUALIFIED`; the PostgreSQL full receipt `FULL_RECEIPT_PASSED`; the MySQL full receipt is the `Target mysql` job of CI `43590596831` (D77.52, D77.71, D77.72). |
| S07 | `Float` GROUP BY, DISTINCT and UNION DISTINCT keys in its cells | `08024040`, second | 8 forms and 6 cells `CANDIDATE_EMISSION_QUALIFIED` on both databases. |
| S09 | `Decimal(p, s)`, `Date` and `Timestamp` header parameters in its cells | `271c6c14`, second | 26 forms with 90 bindings `CANDIDATE_EMISSION_MATCHED`; the `MYSQL_MISMATCH` freeze is kept, and `UUID` is withdrawn (D77.57). |
| S12 | `lpad` and `now()` in its position | `b768d63d`, second | Both halves accepted, the MySQL half in its seventh freeze with the `mysql_rows` witness (D77.44, D77.56). |
| S13 | Ordered `first` and `last` on the `Int`, `Float`, `Text` and `Decimal` carriers in its forms, with a changed suggestion (D77.40) | `abf10555`, second | Attempt 2 accepted; attempt 1 `UNQUALIFIED` is kept (D77.58). |
| S15 | `Int %` and `Float %` in its cell | `2a6159b3`, third | Eighth freeze, one accepted run per database. |
| R08 (S15) | `Int /` where a literal proves the quotient, six forms | `d0ea1db6`, fourth | First stage-2 run void (D77.74); the new freeze `ACCEPTED_FOR_OPENING`, 48 of 48 entries matched per database (D77.75). |
| R02 (S06) | `Float` NOT EXISTS in four forms | `96430bc3`, third | Seventh freeze void (D77.61); eighth freeze `QUALIFIED` on both databases. |
| R01 (S06) | A repair: a `Float` `in` or `not in` over a let with `capture` lines in a WHERE is refused | `812144cb`, third | The third freeze's counterexample (D77.62). |
| S19, S20 | Nothing: direct `sum(Decimal)` and scalars over aggregates keep their refusals (R17, R09) | — | D77.23, D77.29. |
| `now()` outputs | A PostgreSQL `now()` output executes and exports with the fixed civil `Timestamp` meaning, as S12's MySQL one does; other `Timestamp` and `UUID` outputs without a source meaning are refused at execution | `a5c8c691`, `10407b3b`, first | D77.42. |
| `now()` in `relay_live` and R2 | `relay_live` and PostgreSQL R2 run the `now()` reads R2 can bind; MySQL R2 refuses them | `a6332646`, first | PostgreSQL native qualification `pass: true` (D77.43, D77.49). |
| R2's first-step refusal | MySQL R2 refuses a form that `0.1.11` refused, with PIE-R1004 `PUBLIC_R2_UNQUALIFIED_FORM`, before any workspace access or connection | `75d658d1`, fourth | MySQL 8.4.12 verification, 382 of 382 entries (D77.67, D77.68, D77.73). |
| Repairs | A MySQL rows read after a server error; project stages over rows without fields; the three PL.23 repairs | `60076a51`, `2d05babe` (third); `efd6a3ba`, `26021566`, `3458ee3b` (first) | D77.63, D77.64, PL.23. |
| S26 | Acquisition, capability, cadence and package closure | `0928aac0`, with the release batch | The route's [S26 closure record](route.md#s26-closure-record). |
| S27 | This audit, AD77.03, the lessons, the handoff and the Phase82 inputs | with the release batch | Documentation only; no form opens and no refusal changes. |

The Wave A work package is not Phase77 (D77.35, D77.36) but published in its
window, on Phase77's ledger (D77.55): S25 `ad54f94d` in the first batch, S16
`6e50893a` and S10 `13c6ab53` in the second, and S08 `dec3fcc1`, S11
`739f3ae0`, S14 `9b7b914f` and S17 with S18 `e3c6d035` in the third. Each
opens only statements that are, names aside, byte for byte its paired forms;
every other Wave A form keeps `main`'s refusal with no target. The package
has no slice left. The nested work package (D77.32) has not started: it has
no ledger until its Gate 1, and S21's fourth freeze stays outside Git as an
input, not as evidence.

## Retained exceptions and open owner items

The S26 closure record's table lists every MySQL refusal that the `0.1.12`
release request names under J12 (3), with its decisions. The approved
exceptions are project `sum(Int)`, met only in the S01 and S03 forms,
`stddev` of an `Int`, which has no target (D77.34), and nested results,
which go to the nested work package (D77.32). The owner confirmed the D77.07
packet on 2026-11-12 (D77.26). Four items entered it later with their
fail-closed default (D77.16) and wait for the owner, each keeping its
refusal with no target:

1. a target for the other MySQL `sum(Int)` forms;
2. D77.52's O7, a MySQL `Float` `same_value` in a JOIN `on`;
3. C04's E4, `Float` arithmetic and sign on fields, which S15 took to no run;
4. C06's MySQL `UUID` header parameter, whose reopening needs a new
   preregistered run and a decision on its carrier (D77.57).

These are also open for the owner:

- An R2 job that fails closed at its first page reports `terminal` `FAILED`
  with no public reason, and the path itself is unchanged. On MySQL D77.67
  refuses every Phase77 form that met it before R2 starts. On PostgreSQL
  S06's `same_value` in a JOIN `on`, new in `0.1.12`, still reaches it
  (its release note, the R2 boundary), as does the existing unsupported
  expression domain.
- S12's `functools.lru_cache(maxsize=1)` on `_reads_captured_field` is a new
  production cache, which S26 referred to the owner without changing code.
- Whether a Wave A file with carriage returns should pair; the default keeps
  byte for byte pairing (D77.36).
- The three questions that D77.32 left to the owner with defaults: the
  nested package's ledger, PL.04's midpoint clause and when Phase79 S04
  wires its result reader. D77.32 also had the lead bring sheet Q2 option C
  back at the midpoint; the lead found it moot after the `0.1.11` cut and
  did not, a deviation of the lead that this audit reports.

## Acceptance layers

**Observable.** Each opened form has its release note with the SQL, the
details it changes and the refusals it keeps, and the
[capability page](../../capabilities.md) rows that S26 completed. S13
changes one suggestion (D77.40); the `now()` output slice changes execution,
not SQL or JSON (D77.42).

**Existing.** PostgreSQL public output of every form that `main` emitted is
unchanged except by the authorized changes below, and S06's `same_value` in
a JOIN `on` opens on PostgreSQL in D77.52's form. The authorized changes are
PL.19's `bigint` arithmetic and the other repairs that `0.1.11` lists, and
in `0.1.12` the refusal of outputs without a source meaning (`10407b3b`),
the R2 diagnostic order of `a6332646` (D77.49), the refusal on both targets
of a project WHERE or JOIN over rows without fields, which was VERIFIED
with SQL that no database parses (`2d05babe`, D77.64), the PL.23
frame-offset diagnostic and single-file MySQL guards, and the twelve
test-only modules leaving the wheel. On MySQL `0.1.12` also refuses R01's
`Float` membership (`812144cb`, D77.62), reports the SQLSTATE of a server
error after the first rows (`60076a51`, D77.63) and refuses in R2 the forms
that `0.1.11` refused (`75d658d1`, D77.67, D77.68). A statement still
refused reports exactly `main`'s blockers on both targets (D77.37): each
opening's tests pin mixed and refused statements against `main`, and a gap
for a 257-character label found when S05 and S06 were stacked was repaired
before their batch.
No whole-corpus byte comparison like Phase76's 1,727 entries was recorded;
the per-batch D77.50 comparisons cover the carried runs only.

**Connected.** The native runs above bind their tree, wheel, images and
seeds; a run carried to a rebased or stacked commit lists both sides'
digests (D77.50, D77.59). Phase77's frameworks ran on the Docker Engine
(D77.19) under the engine-slot locks (D77.02, PL.14); the Wave A campaigns
used rootless podman and are not a Phase77 layer. On 2026-11-13, from about
09:34Z to 15:54Z, the Docker Engine was down after a host restart and every
Docker Engine activity stopped at its precheck, recorded as not run. MySQL TLS
trusts the given CA and the system store (D77.55 (11)). The thirteen native
probe children that `3458ee3b` changed have no recorded native run since;
S26 set their owner and latest point.

## Compiled compatibility

`VERSIONS` stays `(8, 1, 8, 1)`: no Phase77 slice changed a compiled record
(D77.12, D77.22). A bundle or saved job still binds the code identity of the
Pietto that wrote it, so `0.1.12` refuses those of `0.1.11` and the three
upgrade actions of the [Phase76 audit](../phase-76/completion-audit.md#compiled-compatibility)
apply unchanged: recompile, read old results by their own contract, and run
again only as a new execution.

## P76-PERF dispositions

| PERF | Final disposition |
| --- | --- |
| 1 | Each slice's commit message names the Project SQL readers it changed; `tests/test_project_verification_scope.py`, unchanged since `f8ccd2c4`, passed in full in every batch's Gate 2. PostgreSQL bytes changed only as authorized above. Met. |
| 2 | S26 collected the operation counts of S01, S03, S09, S12, S15, R08 and R2's refusal (D77.73). S05, S06, S07, S13, R01, R02, S06's JOIN `on`, the stages over rows without fields and the `now()` slices recorded none; no superlinear finding is known, and the PIE-B1007 limit stays 32768. Met where recorded; the rest is not measured. |
| 3 | No production memo was added. S12's module-level cache is referred to the owner. The `verify_project_sql_plan` debt stays debt with S26's owner and latest point. The profile that would read verifier runs per call has not run (below). |
| 4 | The repository-fact oracle and its three named test files are unchanged; its corpus follows `src/pietto` and passed in every later Gate 2. Retained. |

## Acquisition, budget, failures and profile

S26 reviewed `f8ccd2c4..e18d3673`: three new shared helpers, four module
fixtures and three LSP processes, all kept; no consolidation and no gain.

The ceiling is `C560/F1700/D70000/S24` (D77.02, D77.03, D77.05, D77.18,
PL.09); nested and Wave A work stays on Phase77's ledger (D77.32, D77.55
(16)). Final totals are not recorded: the lead's ledger, outside Git, leaves
D to be apportioned for the waves from 2026-11-13T13:43Z on. Its last
estimate, at 06:27Z that day, was about D 36,300 and F 545, about half and a
third of the ceiling.

Failures are kept, never rerun as replacements. The first run of each
2026-11-11 framework was void through a framework defect; the 2026-11-12
documentation batch's first Gate 2 aborted under memory pressure; the first
`0.1.12` batch failed natural CI on Windows. Void or unqualified native runs
whose cause was the experiment, each kept with its erratum or new freeze:
S05's first run, S13's attempt 1 (D77.58), S01's fifth freeze (its judge
read another record shape than its client wrote, and its relay leaked
connections), S12's fifth-round MySQL half (D77.56), Wave A S16's second
MySQL freeze (it compared the driver's undecoded `Text` bytes with text
values), Wave A S17's first MySQL half (D77.60), R02's seventh freeze
(D77.61) and R08's first stage-2 run (D77.74). Runs that found a `main`
defect: S12's first PostgreSQL half (`now()` outputs, D77.42), S01's sixth
freeze (D77.63) and R01's third freeze (D77.62). Runs that kept a form
refused: S09's `UUID` (D77.57) and the 2026-11-11 raw runs behind S04,
S05's `sum` and `avg`, S13's four carriers and S15's `Int /`. MySQL HY000 counts as an environment failure in the S05, S01 and
S13 frameworks (D77.55 (10)). PL.17 records the deviation from PL.01's
pytest start conditions, and two Gate 2 runs used 8 workers, not D77.17's 20
(status). A resumed multi-lane workflow on 2026-11-14 restarted finished
agents for about a minute and changed no ref; it is kept in the ledger.

The required ten-node profile has not run. It reads the qualified health of
CI `43590596831`, the last product batch's; this audit's lane had no network
and no health access, so the profile is not observed here and no
performance claim rests on it. Owner, the lead; latest point, before the
Gate 2 seal of the batch that publishes this audit: the lead runs it there
if that CI's health can be read and records its result in that batch, and
otherwise records it there as not observed (PL.07) with the reason. The
E-C review's results stand for nodes that did not change.

## Gate 2 durations

Each row is the authoritative Python 3.13 run on the exact batch tree, with
20 workers unless stated (status records each).

| Batch | Head | Passed / skipped | pytest / all | Natural CI |
| --- | --- | --- | --- | --- |
| Phase77 Gate 1 | `a503167f` | 27,668 / 41 | 279.14 s / 335.2 s | `42886796164` |
| Editor core EB1 | `ae48f00a` | 27,688 / 41 | 277.99 s / 327.2 s | `42900771741` |
| EB1 record | `41e27e5c` | 27,688 / 41 | 268.78 s / 319.1 s | `42917583571` |
| Decisions of 2026-11-11 | `e0116e41` | 27,688 / 41 | 296.60 s / 363.2 s | `43053007162` |
| Decisions of 2026-11-11 and 12 | `864411cb` | 27,688 / 41 (8 workers) | 396.63 s / 443.2 s | `43181411369` |
| Repairs before the `0.1.11` cut | `4ef90859` | 27,758 / 41 (8 workers) | 445.11 s / 504.2 s | `43347023208` |
| `0.1.11` release commit | `d03d6e4b` | 27,758 / 41 | 313.10 s / 366.2 s | `43374277909` |
| After `0.1.11` | `a015afcf` | 27,758 / 41 | 278.76 s / 329.1 s | `43416974151` |
| First `0.1.12` | `d068b0cb` | 28,107 / 41 | 397.74 s / 484.5 s | `43485587196`, failed |
| Its CI repair | `0541765a` | 28,107 / 41 | 335.06 s / 408.2 s | `43493658185` |
| Second `0.1.12` | `e71f6aab` | 28,875 / 41 | 359.65 s / 429.3 s | `43549679582` |
| Third `0.1.12` | `86dafa98` | 30,004 / 42 | 410.42 s / 465.2 s | `43569642808` |
| Fourth `0.1.12` | `e18d3673` | 30,457 / 42 | 555.61 s / 625.4 s | `43590596831` |

The suite grew by 2,789 tests, and a full run on 20 workers went from about
280 s to 556 s of pytest. The batch that carries this audit records its own
Gate 2 in status.

## Lessons

The [engineering lessons](../../references/engineering-lessons.md#phase77)
hold them in full: an opening reaches every route of its form; rule-two
tests include statements refused for another reason; a Linux Gate 2 does
not see Windows test failures; a void run is a harness defect to fix with a
new freeze, after the launch path ran with its real arguments; check the
database engine before dispatching; and continue an edited workflow fresh.

## Next-phase handoff

**Phase78.** The roadmap's next phase is Phase78, SQLite. Its
[route](../phase-78/route.md) runs B1, single-file SQLite, beside Phase79
DuckDB B1 and Phase80 under PL.01–PL.06, and B1 publishes after DuckDB B1
(AD78.02). B2, project mode, needs its own Gate 1 and depends on the
AD78.03 seam and on Phase77 S26 and S27. Phase78's S04 reads this audit if
it exists before S04, and Phase78's completion audit always does. The first
Phase79 and Phase80 replays after its publication consume it (Phase80's S06
at the latest), and so does the next editor Gate 1. The Phase78–80 lanes are local candidates;
none is published, and their release-note fragments stay off `main` until
`0.1.12` is published, so that its assembly takes only Phase77's.

**What the lanes replay onto.** The published head carries Phase77's new
emission owners (`_project/project_sql_emission_paired.py`,
`_project/project_sql_emission_sum_forms.py`, `sql/mysql_paired.py`), the
test helpers `tests/_pietto_sql_float_cells.py`,
`tests/_pietto_sql_nullsafe_cells.py` and `tests/_pietto_sql_paired.py`,
the twelve modules that moved from `src/pietto` to `tests` with the pure
boundary among them, and the second MySQL derivation that `compile_query`
makes for R2 (D77.68). Every later MySQL opening closes as `main` under
rule two, joins the R2 test of D77.68 and states its R2 refusal (D77.73).

**Owner items and debts.** The open owner items above keep their defaults
until answered. The debts keep the owners S26 set: `verify_project_sql_plan`
(the phase-end consolidation of the next phase that changes project SQL
emission, so Phase78's if its B2 does) and the native probe children of
`3458ee3b` (the next native jobs campaign). The ten-node profile is owed as
stated above. The pure verifier fidelity repair (PL.20, D77.54) continues as
its own maintenance work; it is not part of Phase77 or `0.1.12`. Audit
finding 14, a root configured through a symbolic link (PL.23), is authorized
and not delivered.

**Release.** `0.1.12` follows this audit. Its release commit assembles the
`0.1.12` fragments, lists the J12 (3) refusals of the S26 closure record and
the known limitations, and records the owner's release authorization of
2026-11-14, which covers the tag and uploads under its gates.

**Phase82 inputs.** The [freeze ledger](../../roadmap.md#phase82-freeze-ledger)
gains `now()`'s output meaning with R2's recorded statement time, the MySQL
R2 boundary of rule two and paired forms, and MySQL forms that open only as
paired forms. `VERSIONS` is unchanged, and the nested public format keeps
its row with the nested work package.
