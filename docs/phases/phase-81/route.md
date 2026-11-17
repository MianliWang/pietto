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

Implementation is authorized from Gate 0 and runs beside `0.2.2`. No
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
(PL.50 Q1 A). It was rebound on 2026-11-17 from `300f0a93` to `main` at
`900e89156fe0136aef43b90bb2c750864cb6928b` (tree
`543876069818fb7db364f7a71f4bede4b045e44d`), two commits on `300f0a93`:
JF's J1 (`a5bd2c8e`) and the lead's records of PL.61–PL.66. At the
rebinding, at 20:22:37Z, `git ls-remote` gave that commit for
`refs/heads/main`, local `main` equalled `origin/main`, the working tree
was clean and no Git operation was in progress. Its natural exact-head CI
`44166283520`, push/main attempt 1, created at 20:09:29Z, was still in
progress then; its result and CI health are pending, for the lead to
record, and the binding holds only once that CI passes. The two commits
change documentation and `tests/test_repo_static_checks.py` only, and no
product file, lock or CI input, so the [P01 record](#p01-record), taken
on `300f0a93`, stands.

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
open (P15, P16); and Phase79's [B1
audit](../phase-79/completion-audit.md) and [B2 first-tier
audit](../phase-79/b2-completion-audit.md). Phase79's own completion audit
waits for DuckDB B2's second tier (PL.57 (3)); Phase81 runs beside both
B2 lines (PL.50 Q1 A), so that audit is not a Gate 0 prerequisite, and the
midpoint and P16 consume it once it lands.

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
and P04: check what a `-I` child imports).

## Gate 1 record

| Id | Rule in this route | Source |
| --- | --- | --- |
| PL.50 Q1 A | Gate 0 binds a published head with green natural CI; Phase81 runs beside the B2 lines and the MySQL catch-up, the lead ordering one writer at a time | P01 |
| PL.50 Q2 A | CPython 3.14 in full CI (21 to 30 jobs), the verified profile, classifiers and badge; Gate 2 stays on 3.13; extras, the SQLite build, `save` and R2 on 3.14 are declared only as measured | P04 |
| PL.50 Q3 A, Q4 A | A Windows directory writer that holds the new directory's handle; CLI and `pietto.compiler` declared supported on Windows x86-64 with execution NOTRUN and the extras left out; Windows classifiers | P05 |
| PL.50 Q5 A; PL.40 D11 A | The extension repository's `windows-latest` job runs its integration tests against an installed Pietto wheel; D11 A's small fixes (`.gitattributes`, core `0.1.12`, `0.2.0` and `0.2.1` in its CI matrix, `node --test` on `windows-latest`, and its next version's documentation and test items) in the same authorization and the same one push | P06 |
| PL.66 (2) | PL.44 (c), the extension preview's `None:1:1`, joins P06 | P06 |
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
| 81-A5 | The extension's call chain works with core `0.2.x` and on Windows | The extension CI matrix with core `0.1.12`, `0.2.0` and `0.2.1`, `.gitattributes`, `node --test` on `windows-latest`, the next version's documentation and test items, and the preview without `None:1:1` | Extension, core, LSP |
| 81-A6 | Tests find and reduce bounded errors reproducibly | Seeds, size and time bounds, failing inputs, reduction and oracle rules | Generate, supported entry, compare, reduce, minimal regression; no network, no new dependency |
| 81-A7 | H3 (1), (3) and (4) each deliver PL.48's meaning and no more | One-to-one binding to PL.48, two-database evidence for each, public differences | Each from its public entry to both databases |
| 81-A8 | `pietto lsp` stays up after an internal error while storing or publishing results, leaves no stale diagnostic on new text after a failed analysis, and reports the overlap of a root nested through a symbolic link | Both kinds of negative cases, the protocol and root identity rules | A bad request, its response and recovery, the next request; several roots, canonicalization, the published diagnostic |
| 81-A9 | The release tools are maintainable and self-test offline with no external write | The tools, their self-tests, failure-path tests, the permission gate | Dry run or self-test, preflight, refusal of an unpermitted publication |
| 81-A10 | No unknown fact is frozen as a promise; quality, performance, import time and residual risk can be checked again | The Nullability report, before-and-after performance tables, the import-time target and measurement, CI health, the acquisition review, the ten-node profile, Gate 2 durations, the completion audit and lessons | Fresh baseline, each position's result, one integrated validation, the public matrix, the next phase's intake |

Regression covers the qualified scope that `0.2.1` and the `0.2.2` lines
publish (SQLite `Bool` literals as fixed by PL.54), the existing refusal
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

The midpoint comes after P02, P03 and one real platform end-to-end sample,
and no later than half the expected use. The lane workflows stop there and
the lead reports to the owner: S/H/L/K, then Q; whether Nullability changes
a public type contract (PL.50 Q8 A); H3's real size; platform cost; shared
write sets; whether P15 is still worth doing; the ledger; whether the CI
evidence applies; and Phase79's completion audit if it has landed. If the
Nullability report says a public type contract changes, that change enters
Phase81 only with the semantics and budget the owner then approves, in a
position of its own with acceptance and regression before P16; otherwise it
waits for `0.3.0`. A real bug found in an existing contract is handled
before the freeze either way.

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
   push of its release commit (r17 3.4; PL.64 (2)): only pushes stop, and
   Phase81 pushes nothing then anyway (PL.57 (2)); its implementation goes
   on.
10. `0.2.2`'s D2, from the push of its release commit to the tag, the
    GitHub release, the PyPI upload and the post-release documentation
    commit: every lane stops (PL.56). Phase81's pushes under PL.52 begin
    only after D2 ends.
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
the reserve is estimated again then. Phase81
rebases onto `main` repeatedly before `0.2.2`; at about D100 each, the
rebase reserve covers two. Either reserve that runs out is rearranged at
the midpoint, and the ledger as a whole follows PL.15.

## P01 record

P01 ran on 2026-11-17 on `300f0a93`, Gate 0's first head, in a fresh
worktree whose environment was synced offline from `uv.lock` with every
extra (CPython 3.13.13, SQLite 3.53.1, `pietto` editable from that
worktree). It changed no product file. S00's measurements of 2026-11-16 on
`851ad83f` are rebound as follows; the rebinding to `900e8915` changes
none of them ([Gate 0](#gate-0)).

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
`project_completed_semantics.py`, so the refusal goes after MC on `main`,
and P15 after it if both write `project_sql_plan_verification.py`. P02
binds the final write set when it decides.

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
| 1 | Live authority | Gate 0 above: `900e8915` (tree `54387606`), `origin/main` equal, clean, natural CI `44166283520` and its health pending for the lead; first bound on `300f0a93` (tree `9fb0d7c3`) with natural CI `44042698462` 21/21 and its health; PL.50, PL.58 and PL.66 with the rows they cite. |
| 2 | Outcome | Trustworthy diagnostics, platform coverage, negative and integration evidence for selected capabilities; verification reused within one call where measured; an import-time target. Not dialect parity, not a correctness proof of the compiler. |
| 3 | Semantic model | Semantic analysis to the verified ProjectIR stays the authority; `docs/language.md` and the diagnostics reference; H3 (1), (3) and (4) extend `let` reads by value as PL.48 states; Nullability unchanged unless the owner approves at the midpoint. |
| 4 | Identity | Diagnostic identity (code, detail, position, order); a plan's identity within one public call for P15, with no reuse across calls, mutated objects, verification contexts or trust domains; platform identity (OS, architecture, Python patch); package identity; seed identity of generated cases; the core versions in the extension's matrix. |
| 5 | Construction states | A position is planned, a candidate, Gate 2 passed, pushed after the `0.2.2` release commit, then naturally green; a platform claim exists only after CI observes it on that platform. |
| 6 | Proof posture | Asserted: the decision rows. Derived: the cp314 lock reading. Observed: S00, P01 and CI `44042698462`. Verified: Gate 2 and natural CI per batch. Unknown: the setup-python 3.14 SQLite build (P04), the Nullability proposal text (absent), the result of CI `44166283520` (pending). Disproven: none yet. |
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
| 27 | Release | Pushes after the `0.2.2` release commit under PL.52; `0.2.3` at the earliest; each release asked of the owner; P06's one push of the extension repository and no Marketplace release. |
| 28 | Readiness and deferrals | Closed: r17's dispatch (PL.66 (1)) and JF's J1 on `main` (`a5bd2c8e`). Pending for the lead: the green natural CI of Gate 0's head `900e8915`. Deferred: Phase79's completion audit (DuckDB B2's second tier), consumed at the midpoint or P16; JF's J3 for P02's row 19 part; P15's memo to `0.3.0` if not done; a Nullability contract change to the owner at the midpoint; the owed ten-node profile to P16. |
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
