# Phase81 route — pre-freeze assurance and the limited platform work

Phase81 owns the Phase 81 row of the [roadmap](../../roadmap.md#phase81-scope):
assurance before the Phase82 freeze for selected existing capabilities, and
the CPython 3.14 and Windows work that its Gate 1 approved. Its Gate 1 is
PL.50, the owner's answers of 2026-11-16 to the lead's Phase81 Gate 1
sheet, which PL.58 (1) adopted again on the new route of the owner's draft
plan for Phase81–83. On 2026-11-17 the owner dispatched r17, the next
revision of that plan, which the lead drafted and the owner reviewed
(PL.65, PL.66 (1)), and answered its open questions: Q1 is PL.66 (2), and
Q2 and Q3, the pushes of DuckDB B2's second tier and of E4B and E4B's
cutoff for `0.2.2`, are PL.64 (1) and (2). The plan, the sheet and
the lead's records are owner-held working records outside Git; this route
binds what they decide for Phase81.

Implementation is authorized from Gate 0 and ran beside `0.2.2`. No
Phase81 commit is pushed before the `0.2.2` release commit; from that push
on, PL.52's standing authorization covers Phase81's batches under D77.06's
conditions (PL.57 (2), PL.58 (2)). Phase81's content therefore ships in
`0.2.3` at the earliest (PL.51, PL.55, PL.66 (1)). This route authorizes
no tag, GitHub release, PyPI upload or extension Marketplace release.

The Gate 0 that the lead started on 2026-11-16 on `851ad83f`, which the
owner stopped, and its archived route are not revived (PL.54). Its
measurements are inputs that the [P01 record](#p01-record) rebinds.

## Gate 0

Gate 0 binds the newest published head whose natural CI has passed
(PL.50 Q1 A). It was rebound on 2026-11-28 from `900e8915` to `main` at
`d22981932b81d1d314fb2c4ebbe59b2b238cfa89` (tree
`2133efbb5e0b58c3f6116c8ff76347c9d80094d7`), 74 commits on `900e8915`:
DuckDB B2's second tier with Phase79's close, a dependency bump, seven
fixes and tests with the records of the owner's answers for `0.2.2`, the
`0.2.2` batch of 41 commits ending with its release commit `83e5dcd7`, the
record of its publication, the record that Pietto owns a compile-time
optimizer with a tooling bump and SQLite B2's second tier, DuckDB 2.0.1
and the fix of MySQL source reader refusals (PL.106), in eight pushes. At
the rebinding, at 11:22:35Z, `git ls-remote` gave that commit for
`refs/heads/main`, local `main` equalled `origin/main`, the working tree
was clean and no Git operation was in progress. Its natural exact-head CI
`46096387561`, push/main attempt 1, completed with success at 02:43:57Z
and passed all 21 jobs. Its CI health, read under PL.07 from 12:44:54Z to
12:45:08Z on 2026-11-28 with GET requests only, matched the head in all 15
artifacts and passed the head's own verifier; the status was
INSUFFICIENT_EVIDENCE with the current screen WATCH, and its signals are
advisory.
Phase81's commits were rebased onto that head. The lock changed after
`300f0a93`, so the CPython 3.14 reading of the
[P01 record](#p01-record)'s lock inputs was taken again for P04's two
allowlists on the rebased tree ([P04 record](#p04-record)); the rest of
the P01 record, taken on `300f0a93`, was not taken again.

The second binding was `main` at
`900e89156fe0136aef43b90bb2c750864cb6928b` (tree
`543876069818fb7db364f7a71f4bede4b045e44d`), two commits on `300f0a93`:
JF's J1 (`a5bd2c8e`) and the lead's records of PL.61–PL.66. At that
binding, at 20:22:37Z on 2026-11-17, `git ls-remote` gave that commit for
`refs/heads/main`, local `main` equalled `origin/main`, the working tree
was clean and no Git operation was in progress. Its natural exact-head CI
`44166283520`, push/main attempt 1, created at 20:09:29Z, completed with
success at 20:32:19Z and passed all 21 jobs. Its CI health, read under
PL.07 from 20:32:47Z to 20:33:01Z with GET requests only, matched the
head in all 15 artifacts and passed the head's own verifier; the status
was INSUFFICIENT_EVIDENCE with the current screen WATCH, as for the
first binding, and its signals are advisory.
The two commits change documentation and
`tests/test_repo_static_checks.py` only, and no product file, lock or CI
input, so the [P01 record](#p01-record), taken on `300f0a93`, stood.

The first binding was `main` at `300f0a93de74f0949671542f9df8d6d1c73f766e`
(tree `9fb0d7c3d266dcbc41a7006119a1a565989ba82c`), the batch of SQLite
B2's R1 and S16 with VR2's fix and DuckDB B2's Gate 2 and CI facts, four
commits on `6a0646b4`. At that binding, at 17:55:58Z on 2026-11-17, `git
ls-remote` gave that commit for `refs/heads/main`, local `main` equalled
`origin/main`, the working tree was clean and no Git operation was in
progress. Its [natural exact-head CI
`44042698462`](https://github.com/MianliWang/pietto/actions/runs/44042698462),
push/main attempt 1, was created at 07:57:27Z and completed with success at
08:16:26Z, passing all 21 jobs; each Windows job passed 24,787 tests with
252 skips.

The CI health of that run was read under PL.07 from 17:56:22Z to 17:56:41Z
with GET requests only. All 15 health artifacts matched the head by digest
and size, and the head's own health verifier passed. The status is
INSUFFICIENT_EVIDENCE, with the current screen WATCH. History is available
with three accepted samples (`44006845752`, `43946002245` and
`43902311675`) and none rejected, but none is comparable, since the runners
and the test set differ on both runtimes. The cost was incomplete, since the
aggregate job had not finished when it ran. The 23 signals are advisory:
18 long indivisible nodes in the shared-acquisition and two portability
groups of both runtimes, four groups with fewer units than workers, and one
shard imbalance to review on the 3.13 runtime. No Phase81 position changes
scheduling, topology or placement for them; P04's 3.14 jobs are the change
that PL.50 Q2 A approved.

Gate 0 consumes the [Phase80 audit](../phase-80/completion-audit.md), whose
handoff gives Phase81 the CPython 3.14, Windows and macOS claims of the
interop cells, which P04 declares on 3.14 only as measured and P05 leaves
out of the Windows claim with the other extras, with no macOS claim, and
the high-intensity assurance (P07, P08); the [Phase78
audit](../phase-78/completion-audit.md), which leaves the
`verify_project_sql_plan` debt with Phase81 and the owed ten-node profiles
open (P15, P16); Phase79's [B1
audit](../phase-79/completion-audit.md), [B2 first-tier
audit](../phase-79/b2-completion-audit.md) and [completion
audit](../phase-79/t2-completion-audit.md), which closed DuckDB B2's
second tier and with it Phase79 (D79.23); and the [MC completion
audit](../../mysql-catchup/completion-audit.md). Phase81 ran beside both
B2 lines (PL.50 Q1 A), and both have closed on `main`: SQLite B2's second
tier, after `0.2.2` (PL.64 (3)), with its
[record](../phase-78/route.md#b2-second-tier-record). The MC audit leaves
one debt due at this Gate 0 at the latest: `tests/test_sql_grouped.py`,
`tests/test_execution_compiled_bundle.py`, `tests/test_sql_rows.py` and
`tests/test_sql_project_scalar_expressions.py` have no loadfile cost
estimate in `ci/workloads.toml`, to be taken from a quiet four-worker
session or CI health. Gate 0 does not take it: 81-A changes all four
owners (P03, P09, P11), so an estimate taken before it would not describe
them. It goes to P16's acquisition review, owner the lead (field 28).

These [engineering lessons](../../references/engineering-lessons.md) bind
the positions named: 77-1 and 77-2 (P09–P11 state every route of an opened
form and test rule two); 77-3 and 80-2 (P04, P05: a Linux Gate 2 does not
see Windows failures, and a test is gated by its entry point's platform);
77-4, 77-5 and 78-8 (P08–P11: run the launch path before a freeze, and
check the engine endpoint before each dispatch); 77-6 (a changed workflow
continues fresh); 78-1 and 80-5 (the midpoint is a stop in the workflow
scripts, recorded where P16 reads it); 78-6 and 80-4 (P04: decide where an
extra runs without skips, and land the lock, classifiers and pins in one
commit); 78-7 and the post-Phase68 interlude (P15: a memo does not cross a
call or a CI shard, and verification is counted, not timed); and 80-1 (P17
and P04: check what a `-I` child imports). The lessons recorded after the
second binding bind these positions too: 78-10, 78-12 and 79-3 (P08: give
each cell's data a row that the nearest wrong reading changes, such as a
row that a LEFT JOIN matches with none; bind its campaign to the head, the
package and the Engine it reads, not to `main`; and rehearse the real
launch command before the run of record); 78-11 (P09–P11, written in
parallel: list their combinations with each other and with the cells on
`main` in P11's record, the last of the three, and give each a refusal
or a cell, with a test); and, of the
[MC audit](../../mysql-catchup/completion-audit.md#lessons), MC-4 (P08:
each concurrent campaign or review lane has a scratch directory of its
own) and MC-5 and MC-7 (P08 and P16: state a run-dependent fact once, in
the record that the run completes, and derive its counts and citations
from the run records).
78-9, 79-1, 79-2, 79-4, MC-1 to MC-3 and MC-6 bind no Phase81 position.

## Gate 1 record

| Id | Rule in this route | Source |
| --- | --- | --- |
| PL.50 Q1 A | Gate 0 binds a published head with green natural CI; Phase81 runs beside the B2 lines and the MySQL catch-up, the lead ordering one writer at a time | P01 |
| PL.50 Q2 A | CPython 3.14 in full CI (21 to 30 jobs), the verified profile, classifiers and badge; Gate 2 stays on 3.13; extras, the SQLite build, `save` and R2 on 3.14 are declared only as measured | P04 |
| PL.50 Q3 A, Q4 A | A Windows directory writer that holds the new directory's handle; CLI and `pietto.compiler` declared supported on Windows x86-64 with execution NOTRUN and the extras left out; Windows classifiers | P05 |
| PL.50 Q5 A; PL.40 D11 A; PL.87 (2) | The extension repository's `windows-latest` job runs its integration tests against an installed Pietto wheel; D11 A's small fixes (`.gitattributes`, core `0.1.12`, `0.2.0`, `0.2.1` and `0.2.2` in its CI matrix, and `0.2.2` in its Windows job, `node --test` on `windows-latest`, and its next version's documentation and test items) in the same authorization and the same one push | P06 |
| PL.66 (2) | PL.44 (c), the extension preview's `None:1:1`, joins P06 | P06 |
| PL.87 | P08's code adopted after an independent review, and the assurance material of the specification page it had added kept in its route record instead; CPython 3.14.5 downloaded and installed on the integration host; the midpoint report accepted, Phase81 continuing by the rebuild plan | P04, P08, [Midpoint](#midpoint) |
| PL.50 Q6 A; PL.40 D15 A | Verification reused only inside one public call, under the existing call-scoped law; done only with a measured benefit | P15 |
| PL.50 Q7 B (d) (a); PL.48 (2) | The diagnostic review within the existing codes, H3 (2) included | P03 |
| PL.50 Q8 A | A read-only review of Nullability v2, reported to the owner at the midpoint | P02 |
| PL.50 Q9 A; PL.40 D15 A | A bounded seeded generator and shrinker with independent oracles, a compile-time benchmark, a ten-node profile, and the import time of `pietto.execution` against a target set first | P07, P08, P17 |
| PL.50 Q12 A | The release tools in `scripts/`; CI runs only their dry run and self-tests | P14 |
| PL.48 (1), (3), (4) | H3's three semantic extensions, each with a two-database verification | P09–P11 |
| PL.44 (a), (b) | `pietto lsp` survives internal errors and drops stale diagnostics; a root nested through a symbolic link reports the overlap diagnostic | P12, P13 |
| PL.58 (3); PL.63 | Ledger P81 `C206/F618/D11,950/S14`, counted from zero since 2026-11-17, under PL.15, mapped onto the positions at Gate 0 | [Budget](#budget) |
| PL.57 (2); PL.58 (2); PL.66 (1) | Implementation beside `0.2.2`; pushes after its release commit under PL.52 | All |
| r17 (lead) | P17 as a position; the ledger mapping; P02's row 19 part alone waits for JF; P02 implements row 20's refusal if that is the decision; P15's deferral owner | P02, P15, P17, [Budget](#budget) |

The items that r17 marks as the lead's stay the lead's, and the owner may
still change them. Of P01's estimates the lead accepted two on 2026-11-17,
which the owner may also still change: row 20's reserve of `C6/F18/D200`
([Budget](#budget)) and, in [T2](#p17-import-time-target), that
`import pietto` loads no `pietto.*` submodule. These existing decisions
also bind Phase81: D74.09 (two-database qualification), D76.17 (how D is
counted), D77.06 (push conditions), D77.18 (review lanes), D77.19 (the
Docker Engine), D77.50 (native runs carried to a rebased commit), D77.63
(a defect of `main` is repaired on its own), PL.07 (CI health), PL.14
(engine slot locks), PL.15 and PL.51.

Not in Phase81: a memo across calls; dialect feature parity; MySQL nesting,
deeper interop nesting, PostgreSQL extensions, the SPI, the ADBC nested
route, a migrator, context completion, rename and semantic tokens; any
scheduler or topology refactoring; the extension's sync script and its
private imports, which go to Phase82's P05 by the freeze ledger; the second
tiers, JF and E4B, which have their own Gate 1s and ledgers (PL.58 (4),
PL.61); and repository cleanup, credential changes and extension releases.

## Acceptance

Each item is checked as true (what a user observes), present (the material
it needs) and connected (the path that must run end to end).

| Id | True | Present | Connected |
| --- | --- | --- | --- |
| 81-A1 | Current support and refusals are not changed by a known trust gap or an optimization | Row 20's trust decision, L113's disposition, positive and negative cases | Public compile entry, verification, dialect checks, result or refusal; a forged compiled record goes the way row 20 decides: refused, or a written trust boundary with its negative cases |
| 81-A2 | Codes, the needed order, PIE-B1004 and the five editor messages mean what they say | A code–entry–condition–document–test map, H3 (2) included | `check`, `emit-sql`, run time and LSP each match their documents; PIE-B codes do not reach LSP |
| 81-A3 | Core and CI install and run on CPython 3.14, with no regression on 3.12 and 3.13 | Version and lock, a coverage table of the 30 jobs | Built artifacts install, core entry points run, natural CI passes; native qualification is not inferred |
| 81-A4 | CLI, compiler and directory output really work on Windows x86-64 | Windows tests, failure, cleanup and path negatives, the claim matrix, an installed-wheel smoke | Run on Windows; a Linux Gate 2 does not stand in; execution and extras stay out |
| 81-A5 | The extension's call chain works with core `0.2.x` and on Windows | The extension CI matrix with core `0.1.12`, `0.2.0`, `0.2.1` and `0.2.2`, `.gitattributes`, `node --test` on `windows-latest`, the next version's documentation and test items, and the preview without `None:1:1` | Extension, core, LSP |
| 81-A6 | Tests find and reduce bounded errors reproducibly | Seeds, size and time bounds, failing inputs, reduction and oracle rules | Generate, supported entry, compare, reduce, minimal regression; no network, no new dependency |
| 81-A7 | H3 (1), (3) and (4) each deliver PL.48's meaning and no more | One-to-one binding to PL.48, two-database evidence for each, public differences | Each from its public entry to both databases |
| 81-A8 | `pietto lsp` stays up after an internal error while storing or publishing results, leaves no stale diagnostic on new text after a failed analysis, and reports the overlap of a root nested through a symbolic link | Both kinds of negative cases, the protocol and root identity rules | A bad request, its response and recovery, the next request; several roots, canonicalization, the published diagnostic |
| 81-A9 | The release tools are maintainable and self-test offline with no external write | The tools, their self-tests, failure-path tests, the permission gate | Dry run or self-test, preflight, refusal of an unpermitted publication |
| 81-A10 | No unknown fact is frozen as a promise; quality, performance, import time and residual risk can be checked again | The Nullability report, before-and-after performance tables, the import-time target and measurement, CI health, the acquisition review, the ten-node profile, Gate 2 durations, the completion audit and lessons | Fresh baseline, each position's result, one integrated validation, the public matrix, the next phase's intake |

Regression covers the qualified scope that `0.2.1` and the `0.2.2` lines
publish (SQLite `Bool` literals as fixed by PL.54), SQLite B2's second
tier, which `main` carries after `0.2.2` (PL.64 (3)), the existing refusal
codes and error types, the single-file and project boundary, exact numeric
and null behavior, result order and shape, package dependencies and import
direction, the bundle CODE_IDENTITY refusal (PIE-R1005) and the existing
Windows, 3.12 and 3.13 coverage, each bound to commands of the current test
owners when a position is expanded.

## Positions and order

A position number is a place, not an order. Each position, when expanded,
binds its exact inputs, write set, commands, acceptance and cost.

| Position | Delivers | Depends on |
| --- | --- | --- |
| P01 | Gate 0, CI health, the 30 fields, the lessons, the ledger mapping, S00's measurements rebound, P17's target ([P01 record](#p01-record)) | r17's dispatch |
| P02 | The read-only Nullability v2 review, reported at the midpoint; row 20's trust decision by the compiled and verifier owner, coordinated by the lead, before the first new consumer of compiled admission and before `compile_queries(...)`, with its implementation and negative cases if it refuses; L113, forged bundles that load JOIN-then-WHERE or `let` forms that `compile_query` refuses, joins it; row 19 is only checked against JF's closed decision | P01; its row 19 part also on JF's J1 and J3 |
| P03 | The diagnostic review: H3 (2), D6's MySQL half, the order of PIE-S2333 against PIE-S2104 and PIE-S2334, the null-safe JOIN premise error, the extra PIE-S2104 of `round(avg(x), 2)`, PIE-B1004 by (d) (a), and a catalog of the five editor messages; no code added or removed, no JSON shape changed | P01; a window of its own on `docs/spec/diagnostics.md` |
| P04 | CPython 3.14 in full CI (30 jobs), the verified profile, classifiers and badge; 3.14 extras, SQLite build, `save` and R2 declared as measured | P01 |
| P05 | The Windows directory writer and the CLI and compiler claim; execution NOTRUN; Windows classifiers | P01; the output contract locked |
| P06 | The extension repository: a `windows-latest` job on an installed wheel, D11 A's small fixes and PL.44 (c), one authorization and one push | P01; the core contracts it calls stable |
| P07 | A bounded deterministic generator and independent oracles (standard library) over the opened single-file and project forms | P01; P02's decisions that bound the generated range |
| P08 | The shrinker, the two-database differential, the in-process DuckDB and SQLite oracles, metamorphic relations, the compile-time benchmark and the ten-node profile | P07; the applicable qualification profiles; the Docker Engine |
| P09 | H3 (1): a `let` inside an aggregate's argument, read by value in both modes, inlined in single files, verified on both databases | P01; the Docker Engine |
| P10 | H3 (3): `min` and `max` of a numeric `let` in single files, verified on both databases | As P09; after P09 if they write the same files |
| P11 | H3 (4): a renaming `let` under GROUP BY in both modes, verified on both databases | As P09 |
| P12 | PL.44 (a): LSP survives internal errors and drops stale diagnostics; no error that must abort is swallowed | P01 |
| P13 | PL.44 (b): the overlap diagnostic for a root nested through a symbolic link | P01; after P12 if they write the same files |
| P14 | `publish_release.py` with its self-test and `release_prep.py` in `scripts/`; CI runs only the dry run and self-tests, never `--execute`; tokens only from the environment | P01 |
| P15 | `verify_project_sql_plan` under the existing call-scoped law (`once` in `project_verification_scope.py`); PL.50 Q6's key of version, configuration and semantic identity reconciled with the law's object identity in its design; tests show that a changed input never hits and count verifications per case | The semantic positions it touches stable; a profile showing the benefit; after row 20's implementation if both write the verification code |
| P16 | Integrated acceptance, final qualification, performance and health review, the acquisition review, the ten-node profile, Gate 2 durations, documents aligned, the completion audit and lessons | Every other position closed or moved out with reasons; P02's decisions, row 20's implementation included; P15 done or deferred |
| P17 | The import time of `pietto.execution` against the [target](#p17-import-time-target); a fix only where the public import surface stays | P01 |

P09–P11 run one after another unless independence, semantic dependence
and write sets are checked first; P12 and P13 likewise. Only the
measurements that consume compiled admission wait for row 20's decision;
P01, P07, P15 and P16 do not wait for row 19, since none of them reads the
JOIN facts (r17), and P16 waits for JF's J3 only through P02. If
P15 is not done, its memo row goes to the deferral table with `0.3.0`, the
Rust rewrite, as its owner.

## Midpoint

The midpoint came after P02, P03 and one real platform end-to-end sample,
and no later than half the expected use. The lane workflows stopped there
for the lead's report to the owner: S/H/L/K, then Q; H3's real size;
platform cost; shared write sets; whether P15 was still worth doing; the
ledger; whether the CI evidence applied; and Phase79's completion audit if
it had landed. The owner accepted the report on 2026-11-21: Phase81
continues by the rebuild plan (PL.87). The owner had answered the
Nullability question (PL.50 Q8 A) before the midpoint: v2 changes a public
type contract and goes to `0.3.0`, and Phase81 opens no Nullability
position (PL.69, [P02 record](#p02-record)). A real bug found in an
existing contract is still handled before the freeze.

P15 may leave without failing the line; diagnostic errors and invalid
qualification evidence may not. A position that grows beyond one
reviewable change shrinks to one verifiable result or returns to the scope
gate.

## Stop points

The workflow scripts carry these stop points; none relies on a person
stopping a lane in a dialog.

1. The midpoint above.
2. A ledger figure reaches its ceiling after PL.15's raises: Phase81 stops
   for the owner (PL.09). A position whose actual use clearly exceeds its
   mapped figure also stops for re-planning (r17 §11 item 3).
3. A required initiation field is `UNKNOWN`, an input is missing, a
   qualification environment is polluted, or the Docker Engine is not
   observed (D77.19): the affected work does not run.
4. Nullability, H3 or row 19 or 20 exposes a new public type, trust or
   serialization change, or an existing refusal path lets a form through.
5. A change would add or remove a PIE code or detail, change CLI JSON v1 or
   project JSON v2, a compiled record or `VERSIONS`: the lane stops for the
   owner.
6. P17 meets its target only by changing the public import surface.
7. CI policy or the baseline changes so that evidence is no longer
   comparable, or an unapproved topology, runtime or platform change is
   needed.
8. A position would consume JOIN facts before JF's J1 is on `main`.
9. The `0.2.2` release window, from the start of its final assembly to the
   push of its release commit (r17 3.4; PL.64 (2)): only pushes stopped,
   and Phase81 pushed nothing then anyway (PL.57 (2)); its implementation
   went on. The window closed when the release commit `83e5dcd7`
   was pushed on 2026-11-27.
10. `0.2.2`'s D2, from the push of its release commit to the tag, the
    GitHub release, the PyPI upload and the post-release documentation
    commit: every lane stopped (PL.56). D2 ended with the post-release
    documentation commit `395ba2be` on 2026-11-27, and Phase81's
    pushes under PL.52 begin after it.
11. The owner gives a new instruction, a current contract conflicts with
    r17, or the same contract is found still running elsewhere (r17 §11
    item 1).
12. The outcome of one of the four pre-freeze packages or of MC changes the
    freeze's scope (r17 §11 item 6).

## Budget

Phase81's ledger P81 is `C206/F618/D11,950/S14` (PL.58 (3)), counted from
zero since 2026-11-17 (PL.63), with PL.15's raise at 80% and a stop at a
ceiling. The mapping below is r17's, rebound at Gate 0; it is a planning
figure for each position, not a cap, and S14 is one shared pool.

| Position | C | F | D |
| --- | ---: | ---: | ---: |
| P01 | 0 | 0 | 300 |
| P02 (the Nullability review) | 0 | 0 | 100 |
| P03 | 46 | 138 | 1,500 |
| P04 | 8 | 25 | 300 |
| P05 | 18 | 55 | 650 |
| P06 | 5 | 15 | 250 |
| P07, P08 | 51 | 153 | 4,150 |
| P09 | 12 | 36 | 1,000 |
| P10 | 6 | 18 | 700 |
| P11 | 12 | 36 | 1,000 |
| P12, P13 | 6 | 18 | 300 |
| P14 | 4 | 12 | 250 |
| P15 | 20 | 60 | 600 |
| P16 | 4 | 10 | 300 |
| P17 | 4 | 12 | 150 |
| Reserve: row 20's decision and its possible refusal (P02) | 6 | 18 | 200 |
| Reserve: rebases beside the parallel lines | 4 | 12 | 200 |
| **Total** | **206** | **618** | **11,950** |

The two-database work, P08's differential (D3,000) and P09–P11 (D2,700),
is about 48% of D and needs the Docker Engine and PL.14's slot locks.
Row 20's reserve was estimated again at Gate 0, as r17 asks, on the
tentative [write set](#row-20s-write-set): cases added to two modules that
already refuse aggregate arguments, their two test owners, one page and a
fragment, under an existing code, which fits `C6/F18/D200`, so the reserve
stays. If P02 decides a written trust boundary or binds a larger write set,
the reserve is estimated again then. The rebase reserve, at about D100
each, was sized for two rebases onto `main`; Phase81 rebased more often,
before and after `0.2.2`, and the ledger as a whole follows PL.15.

## P01 record

P01 ran on 2026-11-17 on `300f0a93`, Gate 0's first head, in a fresh
worktree whose environment was synced offline from `uv.lock` with every
extra (CPython 3.13.13, SQLite 3.53.1, `pietto` editable from that
worktree). It changed no product file. S00's measurements of 2026-11-16 on
`851ad83f` are rebound as follows; the rebinding to `900e8915` changed
none of them, and the rebinding to `d2298193` did not take them
again ([Gate 0](#gate-0)).

- **Lock and CI inputs.** Between `851ad83f` and `300f0a93`, `pyproject.toml`,
  `uv.lock`, `ci/workloads.toml`, `scripts/ci_workloads.py` and
  `scripts/validate.py` are unchanged, so S00's CPython 3.14 reading stands:
  every one of the lock's 36 third-party packages has a cp314 Linux x86-64
  and win_amd64 wheel or is pure Python, at most manylinux_2_28; the
  offline cache has no cp314 wheel, so P04 downloads them (PL.10 (b)); the
  core alone runs on the host's CPython 3.14.4, where one fixture's
  `emit-sql` gave the same bytes and exit codes as on 3.13 for three
  dialects. `.github/workflows/ci.yml` changed
  only to add `tests/test_execution_api_sqlite_file.py` to both Windows
  jobs (PL.59).
- **Verification count.** One `compile_sql` or `compile_all_sql` call on a
  one-relation table fixture still runs `verify_project_sql_plan` 34 times
  on one plan object, on PostgreSQL and MySQL alike (requirements 14,
  source maps 7, inspection 4, emission verification 4, emission scopes 4,
  emission CLI 1), and `pietto check --project` none. The count is that
  fixture's, not a constant for every input.
- **Diagnostics.** The [diagnostics reference](../../spec/diagnostics.md)
  lists 191 codes (S 137, R 34, P 10, B 9, I 1); 184 appear in `src`, every
  one documented, and the other seven are marked retired or historical.
- **Tests.** 569 test files. The Windows jobs run the 452 files of the
  parser, semantic, IR, plan, SQL, project, CLI and results areas and
  `tests/test_execution_api_sqlite_file.py`.
- **Nullability v2.** No proposal text exists in the tree or its history
  (S00), so P02 starts from the Phase72 handoff and the current language
  rules, as PL.50 Q8 A allows.

### P17 import-time target

The target was written before any measurement on `300f0a93` (r17: set
the target first, then measure, then repair); after the first two runs,
T2's base was made a paired measurement, as below. On review, before any
P17 work, a validity rule for each timed group was added, and T2's
`import pietto` part became a module check, since the measure's 0.1 ms
rounding of an import of about 0.1 ms cannot show 5%. No threshold of T1
changed. S00's earlier "at most 0.15 s" was never approved and is not
used.

- **Machine and environment.** The integration host (WSL2, Linux
  6.18.58.1, 32 logical CPUs), one-minute load below 4 when a measurement
  starts and no Gate 2 running; CPython 3.13.13; an environment synced
  offline from `uv.lock` with every extra, with `pietto` editable from the
  measured worktree; importing `pietto.execution` needs only
  `antlr4-python3-runtime` 4.13.2 and the standard library.
- **Measure.** In a new `python -I -c` process, the wall time of one import
  statement under `time.perf_counter`, without interpreter start-up.
- **Warm cache.** Bytecode of the tree and its dependencies present; one
  discarded run, then 21 runs: median, minimum and maximum.
- **Cold cache.** One run with `-X pycache_prefix` set to a new empty
  directory, so every module compiles again while the file cache is warm:
  reported, with no target.
- **Validity.** Each timed group of `pietto.execution` or `pietto.compiler`
  records the one-minute load at its end. A group whose end load is 4 or
  more, or one of whose runs exceeds twice the group's minimum, is void: it
  is kept in the evidence and the whole group is measured again. A void
  group is never judged, and no threshold moves.
- **Controls.** The same measure for `import pietto.compiler`; for
  `import pietto`, the `pietto.*` modules it loads, with its time observed
  only; and one `-X importtime` run.

| Id | Target, judged at P17's closure on the same host and measure |
| --- | --- |
| T1 | Warm `import pietto.execution`: median at most 0.100 s, maximum of the 21 runs at most 0.150 s |
| T2 | Warm `import pietto.compiler`: median at most 5% above its base, measured in the same session alternately on P17's base tree and on its fix, so deferred imports do not move the cost to the compile entry; `import pietto` loads no `pietto.*` submodule |
| T3 | The public import surface stays: the names of `pietto.execution.__all__`, each name's object and behavior when read, the module's statement that importing it loads no database driver, no PyArrow and no saved-result job module, and the existing tests |

T1–T3 together are PASS. If T1 is reachable only by changing the public
import surface, P17 stops and the lead reports to the owner (stop point
6); the target is not lowered silently. Other interpreters and platforms
are observed only.

The baseline on `300f0a93` followed the target. Its second run, which
started at 18:09:47Z with a one-minute load of 3.75, is the reference:

| Import | Median | Minimum | Maximum |
| --- | ---: | ---: | ---: |
| `pietto.execution`, warm | 0.6004 s | 0.5414 s | 0.7112 s |
| `pietto.compiler`, warm | 0.5169 s | 0.4933 s | 0.5494 s |
| `pietto`, warm (at the 0.1 ms rounding; it loads no `pietto.*` submodule) | 0.0001 s | 0.0001 s | 0.0001 s |
| `pietto.execution`, cold (one run, 363 bytecode files written) | 1.7145 s | | |

The shared host's load rose during both runs, to 7.36 in the second; the
first, which started at a load of 2.78, gave warm medians of 0.492 s for
`pietto.execution` and 0.5794 s for `pietto.compiler`, and its cold figure
is void, since `-I` ignores `PYTHONPYCACHEPREFIX`. Under the validity
rule both runs' timed groups are void: each ended at a load above 4, and
the first's `pietto.compiler` group reached 1.1283 s against a minimum of
0.4611 s. The figures are therefore a scale, not a fixed base, which is why
T2 compares with a base measured beside the fix. One `-X importtime` run
puts 583 ms of 621 ms under `pietto.execution._errors`, through
`project_execution` (577 ms), `project_result_contract` (471 ms) and
`project_sql_plan` (332 ms), as the `0.2.1` survey found. Besides
`_errors`, `_handle`, `_query`, `_sqlite` and `_duckdb` import that stack
at module level, and `_sqlite` reads `adapter.STORAGES`
of `project_sqlite_emission` there (its `FUNCTIONS` come from
`project_sqlite_sql`, which imports only the standard library), so
deferring `_errors`' imports alone cannot meet T1.

### Row 20's write set

If P02 decides that a forged compiled `median(id * 2)` is refused, the
refusal is checked where the compiled replay already refuses aggregate
arguments and operators: `src/pietto/_project/project_completed_semantics.py`
and `src/pietto/_project/project_compiled_verification.py`, with their
cases in `tests/test_execution_compiled_bundle.py` and
`tests/test_execution_compiled_families.py`, `docs/execution.md` and a
release-note fragment, under the existing PIE-R1004 details; a new detail
is stop point 5. MC's PL.49 item also changes
`project_completed_semantics.py`, so the refusal was to go after MC on
`main`, and P15 after it if both wrote
`project_sql_plan_verification.py`. P02 bound the final write set when it
decided, and the refusal reached `main` before MC, as `e15846fb` in the
existing-defect batch ([P02 record](#p02-record)).

## P02 record

P02 ran on 2026-11-17 on Gate 0's head `900e8915` with this route on
top, which changes only documentation, in a fresh worktree synced offline
from `uv.lock` (CPython 3.13.13, `pietto` editable from that worktree),
with no database. It changed no tracked file; its probes built bundles
with the test owners' helpers and changed their records in memory. It
stopped at stop point 4 on Nullability v2 and on row 20, and the owner
answered both in a dialog on 2026-11-17, ahead of the
[midpoint](#midpoint), which therefore no longer carries the Nullability
question; the decision rows are PL.69 and PL.70 (1).

- **Nullability v2.** With no proposal text (P01), the review read the
  Phase72 handoff's item, "the external nullability v2 proposal and
  general narrowing after `x is not None`", against the current rules: a
  bare type is never None, `T | None` may be None and a field of a source
  without a shape is unknown; an INNER JOIN proves the direct field
  leaves of its `on`'s top-level `and` operands non-null; WHERE does not
  refine, OR gives no proof, and arithmetic outside a `def` body's check
  has unknown nullability ([language](../../language.md), [nullability
  contract](../../spec/nullability-propagation-contract-v1.md)). On
  `900e8915`, `explain --project` reports `amount` after `where amount is
  not None` as `nullable`, `amount if amount is not None else 0` as
  `nullable`, `id + 1` over a non-null `id` as `unknown`,
  `coalesce(amount, 0)` as `non_null` and a field that an INNER JOIN's
  `on` tests with `is not None` as `non_null`, and passing that `amount`
  to a `def` parameter of type `Int` is PIE-S2395. Any narrowing after
  `x is not None` therefore changes, for sources accepted today, the
  nullability that the relation column view, the semantic metadata
  artifact, project JSON v2's emission columns, the result schema,
  `pietto.interop`'s admission and compiled records carry, and which
  `def` arguments and relationship rows bind: it changes a public type
  contract (PL.50 Q8 A). The owner chose not to take it before the
  freeze: Phase82 freezes the current rules, and Nullability v2 goes to
  `0.3.0` as a breaking change (PL.51). Phase81 opens no Nullability
  position, and P07 generates nullability by the current rules.
- **Row 20.** A forged compiled bundle still loads through `load_bundle`
  when its records give an aggregate an argument that `compile_query`
  refuses with PIE-S2315: `median`, `stddev`, `variance`, `pstdev`, `min`,
  `max` or `count_distinct` of a row expression, or `sum` of `value % 2`
  or `value / 2`, each written into a VERIFIED PostgreSQL bundle with the
  result type kept. The replay restates emission's carrier law for such an
  argument but not the source's argument law, while the [execution
  guide](../../execution.md) says that only queries `compile_query` can
  produce are loaded. A bundle that another consistent project would
  produce, such as one whose declared key was changed (JF's J0), is the
  trust boundary the guide already states. The owner decided to refuse the
  first kind: the replay restates the source's argument law by function
  and shape (`sum` and `avg` of fields under `+`, `-`, `*` and unary
  signs, alone or with an `Int` or `Float` literal or parameter, `count`
  of its counting shapes, `count_distinct` of a `lower` and `trim` chain
  over `Text`, `string_agg` of `Text`, a direct read for every other
  function) and refuses what that law does not admit with PIE-R1004 and
  its existing details, so no PIE code, detail, JSON shape, compiled
  record or `VERSIONS` changes, and valid bundles keep their bytes. The
  second kind stays the guide's trust boundary. The refusal repairs an
  existing defect on its own (D77.63), in a repair commit outside P02,
  pushed under PL.13 (b): once the owner's second answer had held it until
  a forgery read through a `let` was refused too (PL.70 (2)), it was
  published as `e15846fb` in the existing-defect batch that ends at
  `65c22852`, on 2026-11-20, whose natural CI `44808726926` passed all 21
  jobs, and it shipped in `0.2.2`. This placement supersedes r17's "P02
  implements row 20's refusal" and the P02 position's "with its
  implementation"; the answer names no ledger, so the repair's cost stays
  on row 20's reserve in Phase81's ledger ([Budget](#budget)). Reading the
  code narrows [its write set](#row-20s-write-set) to the derivation and
  the independent verification in `project_completed_semantics.py`, cases
  in `tests/test_execution_compiled_families.py` and a release-note
  fragment; the repair commit bound the final one, those files and the
  roadmap's Phase82 freeze row 20. When P09 widens the source law, the
  replay's restatement changes with it, with a compiled case.
- **L113.** The JOIN-then-WHERE, ON and QUALIFY forms have been refused
  since `0.2.1` (`4553fa1a`), and their tests pass on `900e8915`. A
  bundle built past emission's law with an inclusive chain, a
  conditional, `abs`, a cast or a membership test in a `let` after a
  JOIN is refused on both targets with PIE-R1004 `COMPILED_OPERATOR`,
  except MySQL's `abs`, which emission refuses before any bundle exists.
  A forged bundle with no columns stays a known low and was not probed
  again.
- **Row 19.** The freeze ledger row, PL.61, PL.62 and J1 (`a5bd2c8e`)
  agree, and the adapters' fence passes. Row 20's refusal reads no JOIN
  fact. P01, P07 and P15 consume none as long as P07 and P08 compare only
  public outputs; P15 adds no reader, but the plan's verification calls
  the compiled aggregate evidence, so P15 and J2 rebase in the order they
  reach `main`. This part closes with JF's J3, which follows the `0.2.2`
  release commit (PL.61 (4)), and P16 waits for J3 only through P02.
- **A known low.** An aggregate argument's `operation` record whose
  `operator` is a string of other than two characters, such as `"%"`,
  instead of a role and a token, makes `load_compiled` raise an unnamed
  `ValueError`, which `load_bundle` reports as PIE-R1999 instead of
  PIE-R1008; a string of two characters unpacks and is refused with
  PIE-R1008, and any string in an `operation` record elsewhere is refused
  with PIE-R1008 `COMPILED_OPERATOR`. The load still fails closed; the
  misclassification is recorded as a known low.

## P03 record

P03 ran on 2026-11-17 on the route's candidate `6fa66291`, in a fresh
worktree synced offline from `uv.lock` (CPython 3.13.13, `pietto` editable
from that worktree). Each item was first measured through its public entry,
`pietto check`, `check --project` or `emit-sql --project`, on PostgreSQL
and MySQL where emission takes part.

Two items are documentation, in the
[diagnostics reference](../../spec/diagnostics.md):

- **The order of PIE-S2333 against PIE-S2104 and PIE-S2334.** Measured: a
  relation that a failed input stops, read with `from` (a query with an
  unknown field) or by a relation with JOIN inputs (a relation `let` whose
  ORDER BY key names its own output), reports a `first` or `last` call
  over JOIN rows (PIE-S2334) or, over other rows, one without an internal
  `order by` (PIE-S2104) beside the input's error, while an order key that
  may be None, a key that is no direct field and a generator test's unknown
  field wait for the fix.
- **The catalog of the five editor-only messages**, a section of the
  reference: condition, severity and range, and the exact text as
  `src/pietto/_lsp.py` and `src/pietto/_project/check.py` write it, with
  the count `two` or digits and the code-point list form. Their test
  owners are `tests/test_cli_lsp.py` and `tests/test_project_check_partial.py`.

The other five change what `check`, `check --project` or `emit-sql
--project` reports, each by its cause, with a test that fails before the
change. None adds or removes a PIE code or detail or changes a JSON shape;
the [release-note fragment](../../release-notes.d/81-p03-diagnostic-review.md)
lists each change.

| Item | Entry and case | Before | Cause | Change and test |
| --- | --- | --- | --- | --- |
| H3 (2), PL.48 | `check --project`: `min` or `max` of a `let` whose known type they refuse, as `max(l)` after `let l = label`, a `Bool`, `UUID` or enum `let`, or a computed `Text` one (`lower(label)`), with or without GROUP BY | a bare PIE-S2333 at the relation; a single file reports PIE-S2314 at the call | `_single_file_grouping_diagnostics` (`aggregate_grouped_clause_facts.py`) sent every `let:` name in a `min` or `max` argument to the project's own route | such a name is read as a single file reads it when its known type is one that `is_supported_extrema_argument` refuses; numeric ones keep the project route. `tests/test_project_grouped_aggregate_project_row_schema.py` |
| D6, MySQL half | `emit-sql --project --dialect mysql`: PIE-B1004 `sum_int_aggregate_range_proof_missing` | the generic evidence suggestion, shared with 38 other details in `project_sql_emission_suggestions.py` | — | one sentence after it on MySQL only, whose wording the owner approved (D81.01); `tests/test_sql_conditional_aggregates.py` |
| Null-safe JOIN premises | `emit-sql --project`, a null-safe JOIN `on` cell (INNER S1 of `Int` and of `Float`), PostgreSQL and MySQL, no `operator_environment` or `identifier_case`, or another value | PIE-B1003 `scalar_projection_requires_later_slice` (four), `match_condition_not_in_row_domain` and `join_shape_not_admitted_in_slice7`, without the premise | with the cell open the statement reports PIE-B1004 `operator_environment_declaration_missing` or `identifier_case_declaration_missing` (PIE-B1005 for another value); rule two (`as_main_if_refused`) then reports main's derivation, where the cell is shut and the JOIN shape is refused before any realization, so `_emission_blockers` checked neither the operator premises (only with scalar nodes or a realization) nor the naming premise | main's derivation of a statement that is a cell as written (`nullsafe_join_cell(..., as_written=True)`) checks the operator premises, as the open cell does, and the naming premise from its planned units, as for a refused realization; both follow the shape refusals and precede the source blockers. `tests/test_sql_project_scalar_expressions.py` |
| `round` of a refused aggregate | `check` and `check --project`, for example `round(avg(x), 2) if True else 0` (PIE-S2310), `round(avg(x), 2)` in `where` (PIE-S2308), `round(avg(avg(x)), 2)` (PIE-S2311), `round(avg(label), 2)` of a `Text` field (PIE-S2314), `round(avg(None), 2)` (PIE-S2315) and `round(quantile(x, 2.0), 2)` (the aggregate's own PIE-S2104) | a bare PIE-S2104 `Invalid arguments for function round` at the call beside that refusal; with two arguments, as `round(avg(label), "x")`, the digits are now checked once the aggregate is fixed | the aggregate is Unknown where its position or its own check refuses it, so `_round_value_type` (`semantic/expressions.py`) failed closed again | no PIE-S2104 when the value is an aggregate call over fields of known type (`has_unknown_field_reference`). `tests/test_semantic_functions.py`, `tests/test_project_grouped_aggregate_project_row_schema.py` |
| PIE-B1004 by (d) (a) | `emit-sql --project`, PostgreSQL and MySQL: `k = scalar same.id` beside `n = 9223372036854775807 + 1` (PostgreSQL) or `q = ratio / ratio` (MySQL), `same` the only `let`, capturing `rows` and reading the source `other`; no `identifier_case` or another value | PIE-B1002 `arithmetic_outside_physical_range` or PIE-B1003 `float_division_not_realized`, then PIE-B1004 `identifier_case_declaration_missing` (PIE-B1005 `identifier_case_declaration_mismatch`); without the refusal the statement verifies with one unit and no premise | the refused-realization branch of `_emission_blockers` kept the earlier rule that any other definition needs a named stage, and the inlined `let` is one | decided by `planned_unit_count` alone, which skips an inlined capturing `let`, so two over the sources `other` and `third` drop the premise too; a statement whose `let` reads the query `up`, alone or beside one over `other`, keeps it, as that query is a named stage. `tests/test_sql_rows.py` |

The (d) (a) change differs from the owner's text. PL.44 (d) and Q7
(d) (a) of PL.50 name a statement whose only `let` is an inline capturing
one that *reads another query*, saying its realization would not need the
premise. Measured, such a statement has two units: without the refusal it
is BLOCKED by PIE-B1004 `identifier_case_declaration_missing`, and its SQL
names the query as a stage (`WITH` on PostgreSQL and MySQL), so it keeps
the premise. What changed is a statement that reads the source `rows`
and whose one inline capturing `let` reads the source `other`, or whose
two read `other` and `third`: emitted as one unit, it reported a premise
it does not need. A statement whose `let` reads the query `up`, alone or
beside one over `other`, keeps the premise.

On 2026-11-18 the owner answered both points that this record left open
(D81.01). The owner approved this narrower reading of (d) (a), as it was
put: a statement refused during realization whose only `let` is an inline
capturing one that reads a source no longer reports the `identifier_case`
premise, and one whose `let` reads another query reports it as before.
The owner also approved D6's MySQL sentence as P03 landed it: `On MySQL,
the project sum(Int) forms that emit are listed in
docs/language.md#mysql-project-sumint-forms.`

Left, for the lead: `round` of a value with an unknown name, directly, through
a `let` with an error of its own or inside an aggregate (`round(nosuch, 2)`,
`round(bad, 2)`, `round(sum(nosuch), 2)`), still reports the bare
PIE-S2104 beside PIE-S2102; telling a missing name from a field of unknown
type, where PIE-S2104 is the only refusal, is another check than the one
above. The [LSP diagnostics
contract](../../spec/lsp-diagnostics-v1.md#diagnostics) writes `two project
roots` where the server writes the count, such as `3`, for more roots, and
says that the first three lists are in code-point order, where the roots
follow their `projectRoots` order: P12 or P13. The
[roadmap](../../roadmap.md) drops the five items; the
[status](../../status.md) names none of them.

## P05 record

P05 ran on 2026-11-17 on the route's candidate `6fa66291`, in a fresh
worktree synced offline from `uv.lock` (CPython 3.13.13), under PL.50 Q3 A
and Q4 A.

- **Dependency.** The output contract it depends on was already locked: the
  batch section of [project CLI JSON v2](../../spec/project-cli-json-v2.md)
  and the owner's batch emission approvals of 2026-10-31 and 2026-11-01 fix
  the batch document, the `artifacts/NNNNNN.json` names, the manifest as the
  completion point, the refusal of an existing DIR and the error kinds, and
  no unpublished candidate changed `src/pietto/_batch_output.py` or that
  section. P05 changes no byte of a document, artifact or manifest and no
  error kind; only the message of `batch_output_platform` names Windows and
  CPython 3.12.4.
- **Writer.** `src/pietto/_batch_output.py` keeps the Linux descriptor
  writer unchanged and adds Q3 A's path writer for Windows. It creates DIR
  and `DIR/artifacts` with `os.mkdir(path, 0o700)`, which from CPython
  3.12.4 gives a Windows directory a protected access list for only its
  owner, SYSTEM and Administrators, so Windows with an earlier CPython keeps
  `batch_output_platform`. It holds each directory through a `CreateFileW`
  handle that shares reading and writing but not deletion and opens a
  reparse point itself; it refuses a directory that is not plain or whose
  path no longer names the held directory, and checks the parent and both
  directories before each file and each rename. It writes each file under an
  exclusive `.pietto-*.tmp` name, checks that file's identity and bytes just
  before it installs it with `os.rename`, which fails on an existing name on
  Windows, and checks the installed name's identity after; it checks every
  artifact's bytes and identity and the project inputs before it renames the
  manifest last. On failure it removes only files whose identity is still
  its own, and a directory, once its own handle is closed, only through a
  new handle with delete access whose identity it checks. The path logic
  takes the pin, the rename and the removal as arguments, so its tests run
  on Linux with a no-follow descriptor, a hard link and a checked `rmdir`,
  and on Windows with the real calls.
- **Claim.** README, the project guide, the capability page and the
  release-note fragment `81-p05-windows-output.md` claim the CLI (`check`,
  `emit-sql`, `fmt`, `explain` and `lsp`) and `pietto.compiler` on Windows
  x86-64 with CPython 3.12 and 3.13, with execution not claimed and no
  extra, as the execution guide says, and the first three mark the claim
  as not in `0.2.2`;
  the classifiers become `Operating System :: POSIX :: Linux` and
  `Operating System :: Microsoft :: Windows`. The Windows jobs already run
  every test owner of that surface, which lies in their eight areas
  (`test_cli_lsp.py` for `lsp`, `test_sql_compile_api.py` for
  `pietto.compiler`); each now also runs `scripts/package_smoke.py` without
  an extra. On Windows the smoke takes stdout's LF line ends as written,
  compares stderr with its CRLF line ends made LF, expects the directory
  output, which holds from CPython 3.12.4 (the 3.12 and 3.13 Windows jobs
  run 3.12.10 and 3.13.15; on an earlier Windows CPython the smoke reports
  the designed `batch_output_platform` as a failure), and skips, among the
  installed `_project` modules it imports, only the job and saved-result
  modules that need `fcntl`.
- **Evidence.** The host is Linux, so every Windows statement above is
  derived until the batch's natural CI runs. Pyright checked the Win32 calls
  for the Windows platform; the tests simulate Windows' no-replace rename
  and the pin, which on Linux does not hold the name; CRLF sources, a text
  stream that writes CRLF and a missing `fcntl` were simulated on Linux.
  The claim holds only once both Windows jobs, 3.12 and 3.13, pass; a
  failure is kept and repaired in a child, and the claim does not ship
  before that.
- **Residual risk.** DIR's ancestors, and DIR from its creation until the
  writer holds it, are resolved by path, so someone who can delete entries
  in DIR's parent can move the output elsewhere; the writer never replaces
  an existing file. The owner-only access list does not keep out the
  owner's other processes or Administrators, whose change to a file fails
  the command except between a check and the rename or after the manifest.
  The project CLI JSON v2 page states both. Derived, not run on Windows: on
  a volume that keeps no access lists, such as FAT32 or exFAT, the
  directories get none, so every local user is in that position; the
  pages state it beside the access list.
- **Owner answers (D81.02).** On 2026-11-18 the owner chose that the CLI's
  text on stdout ends its lines with LF on Windows too, kept the residual
  risk as stated above, and accepted `supported` in the Linux column of the
  capability page's rows for the Python compile API and `pietto lsp`. Before
  a command runs, `main` in `src/pietto/cli.py` sets a text stdout's
  newline to LF; stderr keeps the platform's newline, CRLF on Windows, and
  `--output` files, the batch directory and the bytes that the CLI writes
  to stdout's buffer, `fmt`, `migrate` and `lsp` among them, are unchanged.
  A detached stdout, or one whose pending output fails to flush at that
  step, exits `2` as an unwritable stdout does. CLI JSON v1, project CLI JSON v2
  and the release-note fragment state it; `tests/test_cli_output.py` gives
  stdout and stderr text streams that write CRLF, as Windows' do, and
  expects LF on stdout and CRLF on stderr, and gives `main` a closed and a
  detached text stdout.
- **Review repair.** The candidate's review found that DIR inherited its
  parent's access, so another user could replace a staged manifest, which
  was renamed without a later check, and that cleanup removed a directory
  by path after its check. The repair creates the directories owner-only,
  checks each staged file before and its installed name after the rename,
  removes directories through a checked handle, and adds the parent,
  swapped, changed, substituted, hard link and cleanup faults that the
  review's surviving mutants asked for. It also corrects the capability
  page, which claimed `pietto.compiler` and `lsp` on Windows but only
  CI-tested them on Linux, and the roadmap's paragraph, which still
  described the state before P05.

## P12 record

P12 takes PL.44 (a) on the route's base `6fa66291`, with the scope that
the [roadmap's Phase81 row](../../roadmap.md#phase81-scope) states: an
internal error of `pietto lsp` outside the analysis of a document or a
root, while it stores or publishes a result or answers a request, no
longer ends the server, and a failed analysis no longer leaves its old
diagnostics on the new text. Its write set is `src/pietto/_lsp.py`,
`tests/test_cli_lsp.py`, the [LSP diagnostics
contract](../../spec/lsp-diagnostics-v1.md) and a release-note fragment.

- **Change.** One guard covers each unit's whole analysis, its check, the
  storing of its facts and the publishing of its diagnostics; a failure
  there clears every diagnostic set that the unit published and drops its
  facts. Each message, and each request answered after an analysis, has
  its own guard; a failed request receives JSON-RPC `-32603` `Internal
  error`. Messages that arrive during an analysis are handled under their
  own guard, so their errors are never taken for the analysis's.
- **Errors that end the session.** Closed standard output (`_Closed`)
  passes every guard and still ends the session with status 1; an
  interrupt or `SystemExit`, which are not `Exception`, is never caught; a
  framing error still stops the reader as before. A standard error that
  cannot be written changes none of these outcomes: its report is dropped.
- **Before and after.** In a `pietto lsp` process made to raise
  `RuntimeError` for marked texts, `6fa66291` left version 1's diagnostics
  on version 2 after a failed analysis and exited with 1 when publishing
  version 3 failed; with P12, version 2's set is cleared, the failed
  completion request receives `-32603`, versions 4 and 5 publish, and the
  session exits with 0.
- **Tests.** Four new tests, sixteen cases, in `tests/test_cli_lsp.py`: a
  failed check, store or publish, for a file and for a root, clears the
  older set, a waiting hover or workspace symbol request sees none of its
  facts and the next version is served; an error answering a request at
  once or after an analysis, or handling `didOpen`, answers only that
  request with `-32603`; closed output or an interrupt while answering or
  publishing ends the session without the internal-error report; and with
  a standard error that cannot be written, a framing error still stops the
  session and an internal error still lets it go on. On `6fa66291` ten of
  the sixteen new cases failed and the six guards passed. Removing the
  `_Closed` re-raise from any guard fails a closed-output case, keeping
  the facts in `_failed` fails the root's publish case, and an unguarded
  standard error write fails the standard error case.
- **Roadmap.** At integration, the single writer of the roadmap's Phase81
  row records this fault tolerance as landed with P12.

## P13 record

P13 takes PL.44 (b) after P12, which writes the same files. Its write set
is `src/pietto/_lsp.py`, `tests/test_cli_lsp.py`, the [LSP diagnostics
contract](../../spec/lsp-diagnostics-v1.md) and a release-note fragment.

- **Root identity.** M02's rule, under which only a root is resolved and
  never a file's own links, now also decides which roots select a file: a
  path under a root as written stands for that root's real path joined
  with the rest, and every root that selects that real-path form under its
  own spelling selects the file. The rule only adds roots to a spelling
  that a root selects as written, as no root publishes under another
  spelling. The owner of such a spelling that two roots select is both
  roots, so each spelling publishes only the overlap diagnostic, as for
  roots nested as written; a spelling that only one root selects, or that
  no root selects as written, keeps its former owner.
- **Before and after.** With `**/*.pietto` at an outer root and a symbolic
  link to its nested project `sub` as the second root, `6fa66291`
  published PIE-S2701 at both `port/sub/inner.pietto` and
  `link/inner.pietto`; with P13 both URIs show only the overlap
  diagnostic, measured in a `pietto lsp` process on Linux with CPython
  3.13.13. Where the outer root does not select `sub/`, the outer root's
  spelling of the file is still checked alone, as at `6fa66291`, and so,
  measured in process, is a spelling under a third root that does not
  select the file while two linked roots do.
- **Tests.** One new test in `tests/test_cli_lsp.py`, with either the
  inner or the outer root given through a link, and with the outer root
  selecting the file or not. The two overlap cases failed on P12's commit;
  the two others, where the outer root's spelling is checked alone, pass
  there and failed on a first form of P13 that took that spelling for the
  inner root's and so published nothing at it. All four pass with P13,
  and a host that cannot link directories skips them.
- **Residuals.** A document opened under a third spelling, under the real
  paths of both roots but under neither as written, is still checked
  alone, as M02's rule keeps its spelling; and when a document is open
  under one root's spelling, that root checks its buffer while the other
  root reads the file from disk. Both stay known limitations of the alpha
  server.
- **Roadmap.** At integration, the single writer of the roadmap's Phase81
  row records this overlap as landed with P13.

## P14 record

P14 ran on 2026-11-17 on the route's candidate `6fa66291`, in a fresh
worktree synced offline from `uv.lock` (CPython 3.13.13). Under PL.50 Q12
A it moves the release tools that `0.2.1` used and `0.2.2` copied, from
the previous release's directory outside Git, into the repository; `0.2.2`
used its copies, since Phase81 was not in it.

- **Tools.** `scripts/publish_release.py` and `scripts/release_prep.py`
  keep their logic, formatted by Ruff, and their text names no host path,
  release or commit. Three changes: `--execute` is refused where `CI` or
  `GITHUB_ACTIONS` is set, before a token is read or a git command runs,
  which is 81-A9's permission gate, so CI can run only the dry run and the
  tests; `--ci-jobs` is required, since P04 takes CI from 21 to 30 jobs
  and a default would go stale; and `release_prep.py` drops its `selftest`
  command, whose cases moved to the tests.
- **Self-tests.** They are now tests of the repository area's existing
  owner, `tests/test_repo_release_notes_fragments.py`: every case of the
  copied `publish_release_selftest.py` (17 token cases, 7 token-header
  checks, 33 wheel and sdist binding checks, and 23 stale-text samples of
  four patterns) and the six link-grammar cases of `release_prep.py
  selftest`. The fixture version is `7.8.9`, which no release uses, and
  the fixture commit's module is `src/pietto/cli.py` instead of
  `src/pietto/a.py`, so that the same commit serves a real dry run. The
  fake tokens with real public prefixes are split in the source, so that
  no secret scanner reads a token shape there.
- **Failure paths.** New tests run `scripts/publish_release.py` with `-I
  -B` on a release-ready repository made in the test: the dry run exits 0
  with no `PREFLIGHT` line, the digests of both files and the release
  notes' anchor; a wrong tree, an unassembled fragment and a fill
  placeholder each give their `PREFLIGHT` line; and `--execute` with
  `CI=true` stops with nothing written. In process, `CI` and
  `GITHUB_ACTIONS` each stop `--execute` before any git or HTTP call.
  `release_prep.py bump` writes nothing while one version owner is
  missing, and `fill` refuses a draft part that holds the fill
  placeholder the preflight refuses. Another test reads the current
  `docs` and `README.md` with the preflight's stale-text patterns and
  finds no match except README's links to main, which `bump` pins, so a
  document that the next release's preflight would refuse fails before
  it merges.
- **No external action.** No test reads a credential or opens a network
  connection: `--execute` runs only against fakes of git, the preflight,
  HTTP and `uv`, or up to one of its refusals, and git runs only in the
  test's temporary repository, without the user's configuration. `ci.yml`
  is unchanged; CI runs the tests in its existing pytest jobs, on Linux
  only, since the Windows jobs do not run the repository area. The
  `--execute` path itself is still verified only by a real release.

For the next release the checklist runs this test owner where it ran the
two self-tests and calls both scripts from the release commit's tree.

## P15 record

P15 ran on 2026-11-18 on the route's commit `6fa66291`, in a fresh
worktree whose environment was synced offline from `uv.lock` (CPython
3.13.13, `pietto` editable from that worktree). Row 20's implementation
(`98caa107`, published as `e15846fb`) writes
`project_completed_semantics.py`, not the plan verification, so P15 does
not follow it. Its write set is
`src/pietto/_project/project_sql_plan_verification.py`,
`src/pietto/_project/project_sql_emission_cli.py` and
`tests/test_project_verification_scope.py`; P05's hunks in the emission
module are batch output checks that P15 does not touch. The profile and
the paired measure are working records outside Git, and only the
profile's output was kept. The profile's run after the change is not
paired with its run before, so their wall times do not compare; the
benefit is the paired measure's below.

- **Profile.** Before any change, each public call was counted and timed
  with the complete plan check wrapped, on PostgreSQL and MySQL alike.
  `compile_sql` of P01's one-relation table, of a parameterized query, of
  a cross join and of a grouped self-join each ran the check 34 times on
  one plan, as P01 found. A chain of 8 filtered tables of 7 columns ending
  in a grouped self-join ran it 34 times for that query and 306 times for
  its 9 plans under `compile_all_sql`; a chain of 24 tables of 13 columns
  34 and 850 times (25 plans; that batch then exceeds the 64 MiB output
  limit). The check took 30% to 39% of a single call and 35% to 38% of a
  batch, at a one-minute load near 19. `pietto check --project` runs no
  plan check, so it gains nothing. The benefit was enough to go on.
- **Change.** `ProjectSQLPlanVerification` runs its complete check through
  the existing `once`, marked by the identity of its six inputs: the
  plan, the completed semantic result, the analysis bundle, the selected
  owner, the literal policy and the envelope, after an absent envelope
  becomes the plan's own. A failed check raises inside `once`, so no mark
  records it and every call reports its issues again; outside a scope
  every call checks, as before. The emission module opens a scope at two
  new entries: a single `emit-sql --project` or `compile_sql` call, from
  its emission through its document, and each owner of a batch, from its
  emission through its document, so no owner's plan outlives its item, as
  the batch's release of each outcome already intended. A scope around the
  whole batch was measured first: on the 8-table chain it raised the
  batch's traced peak from 15.2 MiB to 18.2 MiB, growing with each owner.
- **Key.** PL.50 Q6 names version, configuration and semantic identity.
  Under the law the key is object identity, which holds all three within
  one call. A mark lives only in one call of one process, so the code
  version cannot change under it, and nothing is persisted or shared
  across processes; a stored or cross-process result is verified again
  when loaded, as before. The configuration that the check reads, the
  literal policy and the envelope, is in the key; the configuration file,
  the contract and the dialect reach the check only through the objects
  built from them. The semantic identity is that of the semantic result,
  the bundle and the owner. Object identity is stricter than a content
  key: equal but distinct objects check again, and a mark keeps its
  objects alive, so no identity is reused in a scope.
- **After.** On the same inputs each call checks each plan once: 34 to 1
  for every single call, 306 to 9 and 850 to 25 for the batches. Paired
  in one process, with `once` bypassed for the base and the order
  alternating, median times fell by 38.6% for P01's table on PostgreSQL
  (0.0537 s to 0.0329 s, 21 pairs), 31.1% for the grouped self-join on
  MySQL (0.1214 s to 0.0836 s, 21 pairs), 33.9% for the 8-table chain's
  query (0.7673 s to 0.5072 s, 9 pairs) and 38.5% for its batch
  (3.0939 s to 1.9018 s, 5 pairs), on the shared host at a one-minute load
  near 20. Tests count the checks and never time them (78-7).
  `compile_query` runs 38 checks instead of 48 on PostgreSQL and 70
  instead of 80 on MySQL, saved only inside the existing
  `prepare_live_template` scope.
- **Tests.** In `tests/test_project_verification_scope.py` the plan check
  is the eighth memoized body, and both entries are in the inventory. Two
  budget routes, `compile_sql` of a three-table chain's `result` on
  PostgreSQL and `compile_all_sql` of its three tables on MySQL, assert
  on each of two calls that each plan is checked exactly once (one and
  three plans), that every check a hit skipped would have passed, and
  that both entries are reached. A new test calls the check in one scope
  with each of its six inputs changed in turn: an equal but distinct plan
  passes once, each of the five others fails on every call with
  `root_continuity` or `literal_transport`, and the original inputs are
  checked once; a plan changed between calls is checked again and
  refused. The foreign-object refusal covers the new body. On the product
  code of `6fa66291` eight of these tests fail: the budget of the two
  emission routes, with 34 checks of one plan, and of the existing live
  route, with 11; the shadow test of both emission routes; the inventory
  and entry-coverage tests; and the new test.
- **Checks.** Ruff format and lint over the tree and both `pyright` runs
  of `scripts/validate.py`, with no error. Pytest with 8 workers, in an
  environment with every extra: the scope owner, 60 passed, and the 14
  emission, compile API, plan and execution owners that reach the plan
  check or the emission entries, 1,832 passed; then one run of the whole
  tree in the core environment of `uv sync --locked`: 31,290 passed and
  140 skipped. Not run: the authoritative Gate 2, databases, Windows and
  CPython 3.12.
- **Residuals.** `compile_query`'s emission still runs outside any scope,
  and its document is serialized in `pietto.execution`, so a scope at its
  emission alone would leave that document's five checks outside it. At
  integration, the single writer of the roadmap narrows its deferral row
  for this memo to that residual: 38 checks in one `compile_query` call
  on PostgreSQL and 70 on MySQL, five of them while `pietto.execution`
  serializes the document. The row's owner is P16, which keeps it in
  Phase81 or, as for an undone P15, moves it to `0.3.0`. P16 also aligns
  the post-Phase68 interlude record, which still counts seven memoized
  checks.

## P17 record

P17 ran on 2026-11-17 on this route's commit `6fa66291` (Gate 0's head
`900e8915` with the route). The fix was made and measured in a fresh
worktree, and the base in a second fresh worktree of `6fa66291`, each with
its own environment synced offline from `uv.lock` with every extra
(CPython 3.13.13, `antlr4-python3-runtime` 4.13.2, `pietto` editable from
that worktree). The measuring script and its output are working records
outside Git.

- **Cause.** `pietto/execution/__init__.py` imported `_errors`, `_handle`
  and `_query` at module level, and with them the project compiler:
  `import pietto.execution` loaded 224 `pietto` modules and `hashlib`.
- **Fix.** The package imports those three owners when one of their 16
  names is first read, as it already did for the saved-result names. Only
  `_access`'s seven access, input, premise and limit classes are imported
  with it, and the import now loads three `pietto` modules. No other
  product module changed: `_errors`, `_handle`, `_query`, `_sqlite` and
  `_duckdb`, the write set named
  [below](#single-writers-and-the-other-lines), were not written, so the
  second tiers' changes to them need no order with P17. DuckDB B2's JOIN
  candidate changes only the docstring of `__init__.py`, in another hunk.
- **Surface (T3).** On both trees `__all__` is the same list, each name
  reads as an object of the same module and qualified name, and `dir()`
  lists every name; the docstring's statement holds unchanged. Each of the
  47 names imported on first read, these 16 and the saved-result names,
  imports `hashlib` then (one process each), so the [execution guide](../../execution.md#effects)'s
  effects table and its refused-environment paragraph now place `hashlib`
  there; it is still imported before any refusal of `execute`. The
  existing test of the job subsystem, renamed for the import surface it now
  pins, also asserts that `import pietto` loads no `pietto.*` submodule,
  that importing `pietto.execution` loads only `pietto`, `pietto.execution`
  and `_access`, not `hashlib`, and that `dir()` lists every public name;
  it already checked that every public name resolves to its owner.
- **Measure.** P01's: a new `python -I -c` process per run, with
  `time.perf_counter` around one import statement; one discarded warm run
  per tree and import, then 21 rounds in each of which the base and the
  fix ran once, the first of the two alternating; P01's validity rule; and
  one cold run per tree with `-X pycache_prefix` set to a new empty
  directory. It started only with no Gate 2 running and a one-minute load
  below 4; the shared host's load had been 12 to 20 for the 25 minutes
  before.

| Import, warm, 21 runs (s) | Base median | Minimum | Maximum | Fix median | Minimum | Maximum | End load |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `pietto.execution`, from 21:14:08Z | 0.4945 | 0.4864 | 0.5087 | 0.0091 | 0.0085 | 0.0094 | 3.40 |
| `pietto.compiler`, from 21:14:21Z | 0.4733 | 0.4500 | 0.4912 | 0.4729 | 0.4583 | 0.4835 | 3.59 |

The first `pietto.execution` pair, from 21:08:38Z, is void and kept: it
ended at a load of 4.44 (medians 0.5257 s on the base and 0.0093 s on the
fix). The cold runs took 2.5407 s on the base, writing 363 bytecode files,
and 0.0613 s on the fix, writing 37. `import pietto` loads no `pietto.*`
submodule on either tree (0.0008 s and 0.0006 s, observed only). One
`-X importtime` run of the fix puts 7.9 ms of its 9.3 ms under `_access`,
through `dataclasses` and `inspect`.

- **Verdict.** T1 PASS: the fix's median is 0.0091 s, at most 0.100 s,
  and its maximum 0.0094 s, at most 0.150 s. T2 PASS: `pietto.compiler`'s
  median on the fix is 0.08% below its base's, within 5% above it, and
  `import pietto` loads no `pietto.*` submodule. T3 PASS, as above. So P17
  is PASS on this host and measure; other interpreters and platforms were
  not measured. The time the import no longer spends is spent when a name
  such as `compile_query` is first read.
- **Checks.** Ruff format and lint over the tree, both `pyright` runs of
  `scripts/validate.py` with no error, and `scripts/release_notes.py check`.
  Pytest with 8 workers on the fix: the execution API, interop, docs and
  release-notes owners, 940 passed; the other execution, results, IR, plan
  and compiled-project owners, 7,018 passed and 60 failed. Of those, 59
  assert that PyArrow is not installed and fail the same way on the base in
  the same environment, and the 60th,
  `test_order_witness_is_at_existing_descriptor_layer`, asserts that its
  worker has not loaded PyArrow and passes alone on both trees. The results
  and execution API owners in an environment without extras: 1,390 passed,
  138 skipped. Not run: the authoritative Gate 2, databases, Windows and
  CPython 3.12.

## Single writers and the other lines

The lead sets the order and a later arrival rebases. At the first
binding, at 17:59:58Z on 2026-11-17, these unpublished candidates touched
files that Phase81 positions write, besides JF's J1 and the lead's records
commit, which `900e8915` published:

- the MySQL catch-up's G1, G2 and E4 and the existing-defect repair of
  `Float` underflow: `docs/capabilities.md`, `docs/language.md`,
  `docs/project-package.md`, `docs/execution.md` and, for G1 and G2,
  `docs/spec/diagnostics.md`;
- SQLite B2's S14 and S15: `docs/capabilities.md`, `docs/language.md`,
  `docs/spec/diagnostics.md`, and for S15 `src/pietto/execution/_sqlite.py`;
- DuckDB B2's types and arithmetic: `README.md`, `docs/capabilities.md`,
  `docs/execution.md`, `docs/project-package.md`,
  `docs/spec/diagnostics.md`, `src/pietto/execution/_duckdb.py` and
  `src/pietto/execution/_errors.py`.

P17's write set is the `pietto.execution` modules that import the project
stack at module level (`_errors`, `_handle`, `_query`, `_sqlite`,
`_duckdb`). It starts once P01 is done; the lead orders it and the second
tiers' changes to `_errors`, `_duckdb` and `_sqlite` under the single-writer
rule, and whichever reaches `main` later rebases onto the other (r17 8.2).
P03's window on `docs/spec/diagnostics.md` is placed between those of MC,
DuckDB's U08 and SQLite's S13b. `ci.yml`,
`pyproject.toml`, `uv.lock` and `ci/workloads.toml` have one writer, P04
and P05 in turn, changing only what PL.50 approved. P15 has a window of its
own on `project_sql_plan_verification.py`, which the second tiers do not
touch. `docs/decisions.md` has one writer, the lead. The language,
capability, project, execution and README pages, `docs/roadmap.md`,
`docs/status.md` and `docs/development.md` have one writer at a time at
integration. Containers follow PL.14, with the engine endpoint checked and
`DOCKER_HOST` set explicitly before each dispatch; pytest runs with
one-minute load below 24 and 8 workers per lane.

## Initiation-gate fields

| # | Field | Binding |
| ---: | --- | --- |
| 1 | Live authority | Gate 0 above: `d2298193` (tree `2133efbb`), `origin/main` equal, clean, natural CI `46096387561` 21/21 and its health; bound before on `900e8915` (tree `54387606`) with natural CI `44166283520` 21/21 and its health, and first on `300f0a93` (tree `9fb0d7c3`) with natural CI `44042698462` 21/21 and its health; PL.50, PL.58 and PL.66 with the rows they cite. |
| 2 | Outcome | Trustworthy diagnostics, platform coverage, negative and integration evidence for selected capabilities; verification reused within one call where measured; an import-time target. Not dialect parity, not a correctness proof of the compiler. |
| 3 | Semantic model | Semantic analysis to the verified ProjectIR stays the authority; `docs/language.md` and the diagnostics reference; H3 (1), (3) and (4) extend `let` reads by value as PL.48 states; Nullability unchanged (PL.69). |
| 4 | Identity | Diagnostic identity (code, detail, position, order); a plan's identity within one public call for P15, with no reuse across calls, mutated objects, verification contexts or trust domains; platform identity (OS, architecture, Python patch); package identity; seed identity of generated cases; the core versions in the extension's matrix. |
| 5 | Construction states | A position is planned, a candidate, Gate 2 passed, pushed under PL.52, which covers Phase81 since `0.2.2`'s D2 ended, then naturally green; a platform claim exists only after CI observes it on that platform. |
| 6 | Proof posture | Asserted: the decision rows. Derived: the cp314 lock reading. Observed: S00, P01, CI `44042698462` and `44166283520`, and Gate 0's head CI `46096387561`. Verified: Gate 2 and natural CI per batch. Unknown: the setup-python 3.14 SQLite build (P04), the Nullability proposal text (absent). Disproven: none yet. |
| 7 | Layer ownership | P02 the compiled verifier; P03 each code's emitting owner and the diagnostics page; P04 CI and packaging; P05 the CLI output writer; P06 the extension; P07, P08 tests and harness; P09–P11 semantic analysis and project emission; P12, P13 the LSP server; P14 `scripts/`; P15 `project_sql_plan_verification.py` and the call scope; P17 `pietto.execution`. |
| 8 | Dependency direction | Unchanged: `pietto.execution` imports `_project`, never the reverse; emitters re-decide no semantic fact; the generator reaches products only through public entries; tests import no test modules. |
| 9 | Versioning and migration | Inside `0.2.x`, `0.2.3` at the earliest; no change to serialized artifacts, compiled records, `VERSIONS`, CLI JSON v1 or project JSON v2; no code added or removed. |
| 10 | Requirements vs capabilities | Platform claims rest on observed CI per OS and Python; 3.14 extras and the SQLite build only as measured; native qualification never inferred. |
| 11 | Interchange | No new process or serialization boundary; P06 reaches the core through the installed wheel and `pietto lsp`'s stdio; P14's tools act offline in CI. |
| 12 | Execution | No new execution route; execution on Windows is NOTRUN; P08–P11's database runs use explicit containers under PL.14. |
| 13 | Resource lifecycle | P05's writer holds the new directory's handle, publishes complete output or cleans up on failure; P12 keeps the server alive and its state consistent after an internal error; each campaign removes its containers. |
| 14 | Security and trust | Row 20's trust decision; P05's path and link negatives on Windows; P14 reads tokens only from the environment and never executes in CI; cp314 wheels by lock hash under PL.10 (b); no new dependency; no network in P07 and P08. |
| 15 | Algorithms | A seeded standard-library generator with registered bounds; a shrinker that keeps the failure class; P15's per-call memo by the existing `once` law; P17's deferred imports, as `_SAVED_RESULT_OWNERS` already does. |
| 16 | Complexity | Generated sizes, depths and times bounded per registered campaign; P15 from 34 verifications to one per plan in a call on the P01 fixture, its memory freed at the call's end. |
| 17 | Invalidation | P15's memo dies with its call, and any changed input verifies again; lock or `pyproject.toml` changes redo the cp314 reading; a change of `pietto.execution`'s imports redoes P17's measure. |
| 18 | Cache | P15's call-scoped memo only, never persisted or shared across processes; a stored or cross-process result is verified again when loaded (PL.50 Q6); bytecode caches are environment, not authority. |
| 19 | Concurrency | The LSP server's request order (P12); P05's writer refuses or isolates concurrent writers of one output directory; lanes keep single writers; at most three containers per engine (PL.14). |
| 20 | Diagnostics | Existing codes only; H3 (2) moves projects to PIE-S2314; PIE-B1004 by (d) (a); the five editor messages get a catalog without PIE codes; row 20's refusal under PIE-R1004. |
| 21 | Inspection | `check`, `explain` and LSP stay read-only; P15 adds no inspection API, and its counts are taken by tests, not exposed. |
| 22 | UX | No new spelling, so the fmt and usability-row item is `NOT_APPLICABLE` (owner: the first Gate 1 that admits a spelling); H3 accepts existing spellings in more places; P03 improves texts within codes; P05 states Windows output errors. |
| 23 | Conformance | The diagnostics reference, CLI JSON v1, project JSON v2, the capability page and two-database receipts for H3. |
| 24 | Differential and fuzz | P07 and P08: valid corpora within the opened forms, seeds in the repository, each campaign registered before it runs, independent oracles and metamorphic relations; a reduction that changes the failure class or premise is not a minimal case. |
| 25 | Packaging | P04's classifiers, lock and cp314 wheels in one commit; P05's Windows classifiers; P14's tools outside the wheel; no generated file and no new dependency. |
| 26 | Support matrix | Now Linux x86-64 on CPython 3.12 and 3.13, with platform-neutral tests on Windows; after Phase81 also 3.14, and Windows x86-64 CLI and compiler with execution NOTRUN and no extras; macOS not claimed. |
| 27 | Release | Pushes under PL.52 after `0.2.2`'s D2 (PL.57 (2), PL.58 (2)); `0.2.3` at the earliest, and not before Phase81 is done (PL.94), after P16 closes and before the Phase82 freeze (PL.98 (3)); each release asked of the owner; P06's one push of the extension repository and no Marketplace release. |
| 28 | Readiness and deferrals | Closed: r17's dispatch (PL.66 (1)), JF's J1 on `main` (`a5bd2c8e`), Phase79's completion audit (D79.23), SQLite B2's second tier, the Nullability question (PL.69), the midpoint (PL.87) and the green natural CI `46096387561` of Gate 0's head `d2298193`. Deferred: JF's J3 for P02's row 19 part; P15's memo to `0.3.0` if not done; the MC audit's loadfile cost estimates of four test owners to P16's acquisition review; the owed ten-node profile to P16. |
| 29 | Slice route | P01, then P02–P07, P12, P14 and P17 as their dependencies allow; P08 after P07; P09–P11 and P12–P13 in turn; P15 after its profile; P16 last. Ready positions are batched: one Gate 2, one push, one natural CI, one commit each. |
| 30 | Repair and stop | The budget above under PL.15; the stop points above; a failed natural CI is kept and repaired in a new child, never rerun; failed runs and their evidence are kept. |

## Closure and handoff

Phase81 closes with P16's completion audit after the phase-end acquisition
review. It records the planned and actual positions, rework and its causes,
the three acceptance layers and regression, the ledger's use, where each
untaken item went, the applicable CI health, the acquisition review, the
ten-node profile, Gate 2 durations and the questions that changed a
decision. The handoff gives Phase82 its freeze inputs: the CPython matrix
and the Windows claim, the diagnostic catalog, row 20's outcome, the
Nullability decision and the import-time result.
