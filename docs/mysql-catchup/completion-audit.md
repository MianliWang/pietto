# MC completion audit

MC, the MySQL catch-up work package, opened more of the MySQL project
`sum(Int)` forms family by family and E4's narrow `Float` cell,
prepared a measurement of MySQL R2's first page that did not complete,
without extending its precheck, and settled PL.49's two items. It is a
work package with no phase number (MC.01), not a phase. This audit checks
the closure items of its [route](route.md#closure-and-handoff) and ends
with the handoff. It publishes nothing: MC's slices, this audit and the
`0.2.2` release commit go to `main` as one batch (PL.85), and the
post-release documentation commit records the batch's Gate 2, its natural
exact-head CI and the published commit identities.

## Baseline and publication boundary

| Step | Fact |
| --- | --- |
| Gate 0 | `main` at `107df991a13096f4cc82c9966c509ac4faeff388` (tree `a348295cafd6977a54429013f22316a2adafba06`); natural exact-head CI `43888270979`, push/main attempt 1, passed all 21 jobs ([route](route.md#gate-0)). |
| Gate 1 | MC.01–MC.12, the owner's answers of 2026-11-16, and MC.13–MC.18, the lead's rulings, in the [decision record](../decisions.md#mysql-catch-up-mc-gate-1--owner-answers-and-the-leads-rulings-2026-11-16); revised by PL.67 and PL.73 (G1's counterexample and the cast of every grouped MySQL `SMALLINT` or `INT` extreme), PL.74 and PL.86 (parallel slices and pipelined freezes) and PL.91 (T1's second-level WHERE). |
| Slice base | Every slice was rebuilt on `65c22852`, the head that published the existing-defect repairs that G1's counterexample caused (PL.67, PL.71, PL.73), and every family freeze from 2026-11-24 on binds a slice on that head; the two freezes of 2026-11-17 bound the integration candidate `c94add48` of the day. No MC batch was pushed before the release batch (PL.85). |
| Chain | One commit per slice, in the route's order: G1 `45d62e7e`, G2 `b537d067`, E4 `475f14b3`, G3 `2db8d6fc`, G4 `927fbdc1`, G5 `f85b168d`, G6 `dcaacfca`, G7 `67b544c7`, G8 `db448b9d`, s03n `da5ab553`, D19 `a7452961` and P49 `24da889a`; the unread typed MySQL header repair (PL.95), the repair `45ce8e55` that narrows E4's cell to its qualified compositions ([Accepted scope](#accepted-scope)) and E4B's five commits ([E4B](#e4b)) follow them, then this audit. These are the batch's commits as published, each slice one commit. |

## Accepted scope

Each family opens under one structural law, witnessed by a preregistered
two-database matrix on PostgreSQL 18.6 and MySQL 8.4.12 (MC.03, MC.06); a
statement that the law matches and that has another blocker reports
`main`'s complete list (D77.37). The guarded SUM of S01 (AD77.03) is
unchanged. The [language reference](../language.md#aggregates-and-grouping)
states each cell, and each slice's release-note fragment lists its forms
and the neighbours that keep their refusal.

| Slice | Opens on MySQL | Forms in its list |
| --- | --- | ---: |
| G1 | a `sum` of a non-null `BIGINT` or an `INT` field, or of a `let` name that points to one field, in S02's cell | 14 |
| G2 | a `sum` beside `count`, `min`, `max`, `avg` and `count_distinct` of one field each, two or more `sum`s, and nullable, several and `INT` or `VARCHAR` grouping keys | 13 |
| E4 | `+`, `-` and `*` of a `DOUBLE` field and a `Float` literal and unary `-` of such a field, a whole SELECT item of one source with at most one WHERE, beside only field reads and other such operations, `*` under MC.05's underflow guard | 27 |
| G3 | HAVING, the `sum` read included, ORDER BY, the `sum` included, LIMIT and DISTINCT | 16 |
| G4 | relation aliases, a window declared and not read, imported sources, qualified reads and an upstream other than T1 and T2 | 15 |
| G5 | header parameters, read or not, and a bind-safe `?` | 18 |
| G6 | JOIN kinds, keys, carriers and ON orders beyond S03's J1–J3, two `sum`s over a JOIN and source tables with extra fields | 17 |
| G7 | compound tests, negative literals, C3 under `bind_safe_literals`, a conditional `sum` beside `count()` or a direct `sum`, and parentheses and qualified reads in C1–C4 | 13 |
| G8 | a third level and beyond, and the style page's two-level example with a non-null `amount` | 11 |
| s03n | the neighbours of S03 that G7 and G8 hand on (PL.74), T1's second-level WHERE over the bottom's count included (PL.91) | 12 |

The batch audit found that E4's cell also emitted on MySQL beside other
SELECT items, S12's `lpad`, `now()` and `date_of(now())` calls and S01's
checked `Int` operations among them, in statements that `0.2.1` and
`65c22852` refused: no E4 campaign or preregistered form covered such a
composition, and the test-side pure boundary rejected some of them. The
repair `45ce8e55` narrows the cell to what its forms qualified (lead):
each other SELECT item of the cell's query is a direct read of a source
field or another operation of the cell, and any other statement keeps
`main`'s blocker list under both literal policies. Emission, plain
verification and compiled replay apply the rule, and so does the pure
boundary. Its pins hold 26 such neighbours with `main`'s blockers, whose
forged artifacts every later reader refuses, and 24 statements that put
E4B's positions P1–P8 beside a `sum(Int)` of G1–G8 and s03n, which keep
`main`'s refusal; every MC and E4B list compiles to the same documents
with the repair as without it (D77.50), so every verdict stands.

MC changes no PostgreSQL SQL, PIE code or detail, JSON shape, compiled
record or `VERSIONS`: each family compares its PostgreSQL SQL with
`main`'s, and every statement it does not open keeps `main`'s blocker list
under both literal policies, which the slices pin in their owners. R2
`save_recoverable` and `recover` refuse every newly opened MySQL form with
PIE-R1004 `PUBLIC_R2_UNQUALIFIED_FORM` (D77.67, D77.68, D77.73). MC's
forms joined no generation input of the target conformance corpus (MC.17
(4)).

## Qualification

The families ran under MC's existing qualification (MC.06, MC.09, MC.17,
MC.18): one shared harness, derived from the second freeze of S03's
package, frozen and self-checked on its real launch path, including its
launcher self-checks on weakened launchers, and one list per family, each
frozen, reviewed and judged on its own. An alternative qualification
design and a disposable pilot were prepared and trialled for the owner on
2026-11-23 and not adopted; the families ran under the published rules.

- **Harness.** G1's first freeze and E4's raw stage ran on the third
  harness freeze, on 2026-11-17. The eleventh, placed on 2026-11-22,
  served G1, G2 and E4's emitted stage. From G7 on the product admits S03's
  control C3 under `bind_safe_literals`, so the harness's weakening step,
  which ran the reference list's witnesses on the candidate's product,
  could not freeze G7, G8, s03n or D19's lists; no freeze record was
  written. The twelfth round runs those witnesses on the reference product
  `65c22852`; its freeze passed MC.12's five lanes with low findings only
  and was placed on 2026-11-24 at 15:00:38Z. G3–G6, whose lists changed
  after the lead answered their preconditions' open questions, refroze on
  it uncounted (MC.17 (3), PL.86). G3 refroze once more, still before any
  campaign, after an erratum repaired its oracle's DISTINCT witness, which
  its freeze review had found vacuous (MC.09). G7 and G8 froze on it for
  the first time, and the freeze of each later list is in the table below.
- **Freeze reviews.** Each freeze of 2026-11-24 had five independent
  review lanes, record, steps, inputs, oracle and preconditions, with two
  skeptics for each finding of medium or higher (PL.86). The two freezes
  of 2026-11-17, G1's first and E4's raw stage's, were checked by the
  lanes that made them. The freezes of 2026-11-26 had the same five lanes:
  the first freezes of s03n, d19 and d19p, and the refreezes of d19 and
  d19p after d19's first campaign (below). Each review was CLEAN, with low
  findings only, d19p's first once the lead had ruled that d19p's own
  MySQL rehearsal, one of its preconditions, runs after the freeze, as
  d19's already did.
- **Campaigns.** One campaign per family on its freeze's engines, each
  in its own containers with its own label and campaign lock, at most
  three PostgreSQL and three MySQL containers at once (PL.14, MC.17 (2)).
- **Integrity audits.** MC.09 and the families' preregistrations ask for
  an integrity audit before a failed, void or unqualified run keeps a list
  refused or leads to a new freeze or attempt; E4's two lists also take
  their opening decision after the integrity audit, and D19's two
  preregistrations ask that two independent auditors audit d19's campaign
  before d19p's campaign starts. The lead had each campaign of 2026-11-24
  audited by two independent auditors, A and B: each recomputed the run's
  expectations with its own evaluator from the saved records, without the
  harness's judge, and each let the verdict stand. G1's failed first
  campaign had two integrity audits, one recorded with the campaign and a
  second beside a read-only native probe, and E4's raw stage had one,
  recorded with its campaign. The campaigns of 2026-11-26, s03n's and
  d19's two, were audited in the same way, each by two independent
  auditors, each of whom let the verdict stand.

### Verdict records

Each row is derived from the records by a derivation script: the
freeze whose package digest the campaign's receipt names, the campaign
attempt's `verdict.json`, and every integrity-audit report that names the
attempt, with the line that states its finding. Freeze paths are relative
to the MC package and the other paths to the evidence directory of the
same owner-held working records outside Git.

| List | Freeze | Campaign attempt and verdict | Integrity audits |
| --- | --- | --- | --- |
| G1, first | `freeze/g1/h-c94add48-20261117T090731Z` (harness `40da7a24`) | `mc/g1/campaign-8d03bcfbf6f40a87/20261117T092027Z-b200e6882a23ebb3f94a2316/verdict.json`, 2026-11-17 09:20:27Z–09:24:08Z: `MISMATCH`, 13 of 14 forms matched, not I6 | audit 1: `mc-g1-campaign-20261117T092021Z/audit/classification.txt`, line 3, re-judged `MISMATCH`, I6 on MySQL only; audit 2: `mc-g1-audit2-20261117T175618Z/classification.txt`, line 13, a real counterexample whose cause is in `main` |
| G1 | `freeze/g1/h-45d62e7e-20261124T105157Z` (harness `396f34ae`) | `mc/g1/campaign-9d805cf373dfc72e/20261124T120724Z-b7357cbc3c3adb2271b6fa24/verdict.json`, 2026-11-24 12:07:24Z–12:11:52Z: `MATCHED`, 14 of 14 forms matched | A: `mc-family-freezes-20261124T085208Z/g1/attempt2/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/g1/attempt2/audit/B.md`, line 1, `AUDIT: MATCHED` |
| G2 | `freeze/g2/h-b537d067-20261124T105157Z` (harness `396f34ae`) | `mc/g2/campaign-76dcc20ae6967066/20261124T121023Z-db632642a58e7e177b76db92/verdict.json`, 2026-11-24 12:10:23Z–12:16:24Z: `MATCHED`, 13 of 13 forms matched | A: `mc-family-freezes-20261124T085208Z/g2/attempt2/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/g2/attempt2/audit/B.md`, line 1, `AUDIT: MATCHED` |
| E4, raw | `freeze/e4/h-c94add48-20261117T175403Z` (harness `40da7a24`) | `mc/e4/campaign-d69edbf40bb55abd/20261117T180755Z-f81e2c3b69b66d2b5a5635cd/verdict.json`, 2026-11-17 18:07:55Z–18:08:48Z: `MATCHED`, 42 of 42 forms matched | audit: `mc-e4-campaign-20261117T180750Z/audit/classification.txt`, line 3, re-judged `MATCHED` |
| E4, emitted | `freeze/e4-emitted/h-475f14b3-20261124T105157Z` (harness `396f34ae`) | `mc/e4-emitted/campaign-3a7ad268cbee6e1d/20261124T121841Z-0949028767707ab70111eda5/verdict.json`, 2026-11-24 12:18:41Z–12:25:52Z: `MATCHED`, 27 of 27 forms matched | A: `mc-family-freezes-20261124T085208Z/e4-emitted/attempt2/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/e4-emitted/attempt2/audit/B.md`, line 1, `AUDIT: MATCHED` |
| G3 | `freeze/g3/h-2db8d6fc-20261124T170101Z` (harness `20e8c344`) | `mc/g3/campaign-ba9ec1666ed54b1c/20261124T180315Z-1497d15d89e175a02c00bf70/verdict.json`, 2026-11-24 18:03:15Z–18:12:58Z: `MATCHED`, 16 of 16 forms matched | A: `mc-family-freezes-20261124T085208Z/g3/attempt4/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/g3/attempt4/audit/B.md`, line 1, `AUDIT: MATCHED` |
| G4 | `freeze/g4/h-927fbdc1-20261124T150722Z` (harness `20e8c344`) | `mc/g4/campaign-2c527c3666e30bef/20261124T171745Z-1235938afae72dad1a1ab62e/verdict.json`, 2026-11-24 17:17:45Z–17:27:28Z: `MATCHED`, 15 of 15 forms matched | A: `mc-family-freezes-20261124T085208Z/g4/attempt3/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/g4/attempt3/audit/B.md`, line 1, `AUDIT: MATCHED` |
| G5 | `freeze/g5/h-f85b168d-20261124T151322Z` (harness `20e8c344`) | `mc/g5/campaign-726b82198633203e/20261124T171745Z-ea65eccb213e1f701272c269/verdict.json`, 2026-11-24 17:17:45Z–17:31:40Z: `MATCHED`, 18 of 18 forms matched | A: `mc-family-freezes-20261124T085208Z/g5/attempt3/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/g5/attempt3/audit/B.md`, line 1, `AUDIT: MATCHED` |
| G6 | `freeze/g6/h-dcaacfca-20261124T153453Z` (harness `20e8c344`) | `mc/g6/campaign-f7c20d54808e2373/20261124T171745Z-14efce81007fb74da93dfa6e/verdict.json`, 2026-11-24 17:17:45Z–17:29:04Z: `MATCHED`, 17 of 17 forms matched | A: `mc-family-freezes-20261124T085208Z/g6/attempt3/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/g6/attempt3/audit/B.md`, line 1, `AUDIT: MATCHED` |
| G7 | `freeze/g7/h-67b544c7-20261124T153904Z` (harness `20e8c344`) | `mc/g7/campaign-62a807ffedbe1b49/20261124T172736Z-2d095c6b9f87f13283aef556/verdict.json`, 2026-11-24 17:27:36Z–17:35:29Z: `MATCHED`, 13 of 13 forms matched | A: `mc-family-freezes-20261124T085208Z/g7/attempt3/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/g7/attempt3/audit/B.md`, line 1, `AUDIT: MATCHED` |
| G8 | `freeze/g8/h-db448b9d-20261124T155735Z` (harness `20e8c344`) | `mc/g8/campaign-8f31f8862a80c35a/20261124T172905Z-c0cff1810c93748f2be91ee8/verdict.json`, 2026-11-24 17:29:05Z–17:37:12Z: `MATCHED`, 11 of 11 forms matched | A: `mc-family-freezes-20261124T085208Z/g8/attempt3/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/g8/attempt3/audit/B.md`, line 1, `AUDIT: MATCHED` |
| s03n | `freeze/s03n/h-da5ab553-20261126T171107Z` (harness `20e8c344`) | `mc/s03n/campaign-af5871619c7fc9c0/20261126T175918Z-c3d98b66f2fe6dec46dedf1c/verdict.json`, 2026-11-26 17:59:18Z–18:12:03Z: `MATCHED`, 12 of 12 forms matched | A: `mc-family-freezes-20261124T085208Z/s03n/t2-20261126/audit/A.md`, line 1, `AUDIT: MATCHED`; B: `mc-family-freezes-20261124T085208Z/s03n/t2-20261126/audit/B.md`, line 1, `AUDIT: MATCHED` |
| d19, first | `freeze/d19/h-a7452961-20261126T173820Z` (harness `20e8c344`) | `mc/d19/campaign-2cb3b25ce62b5d6e/20261126T181801Z-ce715751ba92d5d1dc2d3f81/verdict.json`, 2026-11-26 18:18:01Z–18:18:36Z: `MISMATCH`, none of its 32 forms matched | A: `mc-family-freezes-20261124T085208Z/d19/t2-20261126/audit/A.md`, line 1, `AUDIT: MISMATCH - harness cause`; B: `mc-family-freezes-20261124T085208Z/d19/t2-20261126/audit/B.md`, line 1, `AUDIT: MISMATCH - harness cause` |
| d19 | `freeze/d19/h-a7452961-20261126T201651Z` (harness `20e8c344`) | `mc/d19/campaign-298652c789e93f62/20261126T212915Z-b4797864f9c5a1b2c7a3701b/verdict.json`, 2026-11-26 21:29:15Z–21:30:27Z: `UNQUALIFIED_RECEIPT`, no form judged | A: `mc-family-freezes-20261124T085208Z/d19/t3-20261126/audit/A.md`, line 1, `AUDIT: UNQUALIFIED_RECEIPT - harness cause`; B: `mc-family-freezes-20261124T085208Z/d19/t3-20261126/audit/B.md`, line 1, `AUDIT: UNQUALIFIED_RECEIPT - harness cause` |
| d19p | `freeze/d19p/h-a7452961-20261126T171107Z` and `freeze/d19p/h-a7452961-20261126T203923Z` (harness `20e8c344`), neither launched | not run: its campaign was to follow a d19 campaign that matched and was audited, and D19's measurement ended without one (the lead's record of 2026-11-26 22:20Z) | none |

What each verdict and its audit reports establish:

| List | What the verdict and its audits established |
| --- | --- |
| G1, first | `MISMATCH` in I6 alone, 13 of 14 forms matched: on MySQL a `min` of an `INT` field read through the statement's WHERE stage was declared `my_int` and returned as `BIGINT`, and the public route failed it with `PIE-R3005`, with no wrong rows. Both audits found a real counterexample, and the second traced it to an existing defect of `main` in S02's cell, which PL.67 and PL.73 repaired before G1's second freeze. (PL.67 said 17 of 18 forms, as the route and the status page did until this audit; the verdict lists 14.) |
| G1 | `MATCHED` in the groups `bigint_nonnull`, `int` and `let`; both audits let it stand: 1,092 statements recomputed, every overflow cell `PIE-R3003` on both databases, the control N3 refused on MySQL with `PIE-B1004`. |
| G2 | `MATCHED` in `aggregates`, `keys` and `mixed`, all 26 labels; both audits let it stand: overflow `PIE-R3003` on both databases, the control A4 refused on MySQL. |
| E4, raw | `MATCHED` for `+`, `-`, `*` and unary `-`, bit for bit against the binary64 oracle, `*` with its guard (MC.05); the stage reads MySQL's own `DOUBLE` primitives, not the slice's SQL, and its freeze is on the integration candidate of the day. Its audit re-judged every cell `MATCHED`. |
| E4, emitted | `MATCHED` in `add`, `sub`, `neg`, `mul` and `mixed` on every route; both audits let it stand: overflow `PIE-R3003` in all 58 failing cells, the control EM1 refused on MySQL with `PIE-B1003`; no operator stays refused. |
| G3 | `MATCHED` in `distinct`, `having`, `limit`, `mixed` and `order`; both audits let it stand: auditor A re-judged all 2,016 cells, `PIE-R3003` on both databases in all 147 overflow pairs, the control L3 refused on MySQL with `PIE-B1004`, and on all 132 evaluation cells the databases agreed with each other and with the rules (a), (b), (b') and (c) of its preregistration, of which the [language reference](../language.md#aggregates-and-grouping) states (a) and (c), so the route's stop for databases that differ did not fire. |
| G4 | `MATCHED` in `aggregated`, `later`, `spelling` and `upstream`; both audits let it stand: `PIE-R3003` on both databases in all 102 overflow pairs, an out-of-range `sum` of an aggregating upstream failing the statement on every database and route, the control U2 refused on MySQL with `PIE-B1004`. Its `later` forms rest on G3's law, which G3's verdict kept. |
| G5 | `MATCHED` in `bind`, `later`, `mixed`, `read`, `source` and `unread`, all 36 labels; both audits let it stand: `PIE-R3003` in all 136 overflow cells of each database; G3's evaluation rules held with bound values in place of the literals, under prepared execution on both databases; auditor B checked the bound values of all 792 cells on every route against the preregistration and PostgreSQL's log of the 128 failing text-route `EXECUTE`s. G5's list has no control. |
| G6 | `MATCHED` in `carriers`, `keys`, `kinds`, `mixed` and `on`; both audits let it stand: both auditors recomputed all 1,734 run cells, `PIE-R3003` in all 101 overflow cells of each database, the control O2 refused on MySQL with `PIE-B1004`. |
| G7 | `MATCHED` in `beside`, `mixed` and `tests`; both audits let it stand: auditor A recomputed all 572 cells, 1,716 route observations, every overflow cell `PIE-R3003` on both databases, the control M1 refused on MySQL with `PIE-B1004`. |
| G8 | `MATCHED` in `depth` and `route`; both audits let it stand: auditor A recomputed all 1,386 run cells, `PIE-R3003` in all 86 overflow cells of each database, the control D1 refused on MySQL with three `PIE-B1004` blockers. |
| s03n | `MATCHED` in `conditional` and `levels`, Laws C and T; both audits let it stand: both auditors recomputed all 2,952 route cells, `PIE-R3003` in all 86 overflow pairs of each database, T-1's nine `filtered` witnesses returned only the rows that its WHERE keeps on both databases, and the control, T-1's form under `bind_safe_literals`, was refused on MySQL with two `PIE-B1004` blockers. |
| d19, first | `MISMATCH` in all 32 forms from one cause outside them: the list's public call made its R2 job workspace in the client's default temporary directory, a `tmpfs` on the rebuilt host, so the product refused every public cell before R2's first connection with `PIE-R1009` `WORKSPACE_PROFILE_FILESYSTEM`, as its job store admits only an `ext4` workspace; all 128 raw prepared and raw text cells matched. Both audits let the verdict stand and found a harness cause, the list's own call, and no counterexample or defect of `main`. Under MC.09 an erratum repaired the call, which now makes the workspace under the client's home directory and records a refusal before the call's start as a receipt gap; d19 refroze for the third and last of the freezes that d19 and d19p share, d19p refroze uncounted, and the campaign closed with its verdict (the lead's ruling of 2026-11-26 19:20Z). |
| d19 | `UNQUALIFIED_RECEIPT` on the third freeze: the repaired workspace held, but R2 refused the list's MySQL view at its source admission, before any first page, in every public cell, which the list's rule records as a receipt gap; all 128 raw prepared and raw text cells matched. Both audits let the verdict stand and found a harness cause, the list's fixture, which created the view without the `utf8mb4_0900_bin` collation that R2's MySQL source admission requires, and no counterexample or defect of `main`. The owner chose to end D19 by its rules, with no fourth freeze, so this third freeze ended D19's measurement without an extension (the d19 preregistration's item on freezes), and PL.40 D19 returns to the owner after the release (the lead's record of 2026-11-26 22:20Z). |
| d19p | not run: its campaign was to follow a d19 campaign that matched and whose audits let it start (the lead's ruling of 2026-11-26 19:20Z); neither d19 campaign matched, and D19's measurement ended, so neither of d19p's two freezes was launched. |

Two campaigns failed, G1's first and d19's first, and their records are
kept. G1's freeze is the first of the three freezes that MC.09 allows a
family; d19's campaign failed for a harness cause, its list was repaired,
and d19 and d19p refroze (the table above). One run was UNQUALIFIED, d19's
second campaign, and no other run was VOID or UNQUALIFIED; each campaign
ran one attempt. d19's second campaign was not retried: both audits found
its cause deterministic, and with it D19's measurement ended
([D19](#d19)).

**Receipts.** Changed production bytes need fresh full target receipts
(MC.16 (1)): PostgreSQL's runs once on the host on the release tree, before
the batch's Gate 2 and not during it, and MySQL's comes from the batch
head's natural CI `Target mysql` job. Both are recorded by the post-release
documentation commit.

## Forms still refused

Every form that MC did not open keeps `main`'s refusal and an approved
exception with no target, listed under J12 (3) in each release (MC.10):

- the MySQL project `sum` of an `Int` outside the forms of S01, S03 and
  G1–G8 and of the s03n list, among them G8's R6, R9 and R11 and every
  chain over a JOIN bottom, and a WHERE that reads a field column in T1's
  second level;
- every position of PostgreSQL's E4 on MySQL outside E4's narrow cell and
  [E4B's cells](#e4b), `Float` arithmetic in a JOIN `on` (PL.68) and a `*`
  beside a header parameter (PL.76) among them, and the other forms that
  [E4B keeps refused](#e4bs-forms-still-refused), but for PL.82's counts,
  which have a target before the Phase82 freeze.

The roadmap's [Phase82 freeze ledger](../roadmap.md#phase82-freeze-ledger)
holds MC.10's row for them.

## E4B

E4B is the part of C04's E4 that MC.04 left to the owner's plan, done
before the Phase82 freeze with its own Gate 1 (PL.58 (4), PL.75), the
lead's rulings on its parameter operands and its lists (PL.76–PL.83) and
its own ledger. All six of its lists had qualified when `0.2.2`'s final
assembly started, so its slices joined the release batch (PL.64 (2),
PL.85 (2)): S1–S4 and the decision commit S5, after MC's last code commit
and before this audit (lead).

### E4B's accepted scope

A position opens only in shapes in which the SQL text, not the plan, fixes
the rows on which the value is computed (PL.75 (2)), and only where its
finite results match on both databases and its overflow fails on both
(D77.78). The [language reference](../language.md#mysql-float-wider-cells)
states each cell, and each slice's release-note fragment lists its forms
and the neighbours that keep their refusal.

| Chain | Slice | Opens on MySQL | Lists (forms) |
| --- | --- | --- | --- |
| B | S1 | a narrow operation in one or two `let` values read by the select list, in a whole WHERE comparison with a `Float` literal or its `not`, and in ORDER BY keys that are `let` names (P1–P3) | `e4b` (206), `e4b-emitted` (37) |
| C | S2 | two `DOUBLE` fields and one level of nesting in a whole item, one `let`, a whole WHERE or one ORDER BY key (P4, P5), and the `count` of the sign of a nullable field with no WHERE (P6) | `e4b-c` (168), `e4b-c-emitted` (36) |
| C | S3 | a `Float` header parameter, read once, as the operand of `+` or `-` beside a field and as the inner operation of a unary `-`, such as `-(x + p)` (P7), and one or two computed `let` GROUP BY keys in an S07 form (P8) | the same two lists |
| J | S4 | a narrow item, or with no WHERE a `+` or `*` of two fields, as a whole SELECT item over one INNER or LEFT JOIN on an `Int`, `Text` or S06 `Float` key (P9) | `e4b-join` (42), `e4b-join-emitted` (14) |

E4B changes no PostgreSQL SQL, PIE code or detail, JSON shape, compiled
record or `VERSIONS`; every statement it does not open keeps `main`'s
blocker list under both literal policies. R2 `save_recoverable` and
`recover` refuse every newly opened form with PIE-R1004, with the detail
`PUBLIC_R2_UNQUALIFIED_FORM`, or the earlier detail that each fragment
names for an ORDER BY key or a computed key, as for MC's forms.

### E4B's qualification

E4B's six lists ran under MC's existing qualification and the lead's
rulings on them (PL.77–PL.83): three chains, each with a raw list of
hand-written SQL over MySQL `DOUBLE`, bound to the integration candidate
`c94add48`, and an emitted list of its slices' forms, bound to the slice
commit that completes the chain (PL.80).

- **Harness.** Every list froze on the twelfth harness freeze, placed on
  2026-11-24 at 15:00:38Z. Four lists first froze at about 15:57Z, and
  those freezes stand as records only: a scan found required witnesses
  that only overflowing cells carried, the oracle was repaired in three
  rounds, each checked independently, and every list froze after the
  repair, before any campaign ran, so no refreeze counted (PL.78 (1)).
  Each chain has used two of its three freezes.
- **Freeze reviews.** Each of the six freezes on which a campaign ran had
  five independent review lanes, record, steps, inputs, oracle and
  preconditions, and all thirty were clean, with low findings only
  (lead).
- **Campaigns.** One campaign per list on its freeze's engines, PostgreSQL
  18.6 and MySQL 8.4.12, each in its own containers with its own label and
  campaign lock (PL.14, MC.17 (2)). An emitted list's campaign started only
  after the verdicts of the lists it rests on had both their audits
  (lead), and `e4b-emitted`'s also after the midpoint record of `e4b`'s
  verdict. Each campaign ran once.
- **Audits.** Each of the six verdicts had two independent integrity
  audits, A and B, each recomputing the run's cells with an evaluator of
  its own, as the lead ruled for E4B's lists (lead); for `e4b-c`, a failed
  run, they are also the audit that MC.09 asks of a failed run, and two
  further reviewers found that its two reports, worded differently, agree
  in substance. Every audit let its verdict stand.
- **Admission.** Independent checks against the slices found that they
  emit on MySQL every shape that opened, each from its own slice on and
  built from bytes its lists ran, and no shape that did not (lead). A
  records check found one sentence of the language reference that read
  as refusing an opened computed GROUP BY key beside a field key; the
  restacked commit `4a01f58e` corrects it to "an ORDER BY key that reads a
  field beside a `let` key" (lead).

| List | Freeze | Campaign | Verdict and audits |
| --- | --- | --- | --- |
| `e4b`, chain B, raw | `h-c94add48-20261124T201317Z`, frozen 20:55:20Z | `8fcf4738679b8484`, 21:35:55Z–21:39:58Z | `MATCHED`: 206 forms, all 17 groups, `<op>-P1` to `<op>-P3`, `<op>-L` and `transport-L` for the four operators; both audits let it stand: 11,536 route cells recomputed, 610 failing cells per database, each forced-plan pair the same rows and failure, and each of the 98 raw statements that has a Pietto statement is `main`'s PostgreSQL SQL at `c94add48`. |
| `e4b-join`, chain J, raw | `h-c94add48-20261124T205520Z`, frozen 21:29:07Z | `e30a6a27724a033b`, 21:56:40Z–21:57:43Z | `MATCHED`: 42 forms, all 9 groups, `<op>-P9`, `<op>-L` and `transport-L`; both audits let it stand: 2,016 statements, 76 failing cells per database. |
| `e4b-c`, chain C, raw | `h-c94add48-20261124T212908Z`, frozen 22:10:45Z | `1ca7377d102517c3`, 22:35:47Z–22:40:56Z | `MISMATCH` in the witness group `CN` alone: 164 of 168 forms and 23 of 24 groups matched; `CNW1`–`CNW4`, a `count` of a non-null value, mismatched on 70 MySQL cells, where MySQL returned the count and PostgreSQL failed with SQLSTATE 22003. Both audits let it stand as the preregistered witness, never a real counterexample: it opens and ends nothing (PL.82). MySQL raised error 1690 on each of the other 1,542 expected failures, and on every route the parameter group's bound `Float` values were the oracle's, bit for bit. |
| `e4b-emitted`, chain B, emitted | `h-a8b1d000-20261124T201317Z`, on S1 `a8b1d000`, frozen 20:51:32Z | `7c146599e6aaa7a1`, 22:00:29Z–22:13:06Z | `MATCHED`: 37 forms on every route, all 12 groups; both audits let it stand: 3,108 route cells, overflow `PIE-R3003` on both databases in all 119 failing cells per database, the control `EB1A` refused on MySQL with `PIE-B1003`. |
| `e4b-join-emitted`, chain J, emitted | `h-230aa537-20261124T201317Z`, on S4 `230aa537`, frozen 20:50:59Z | `19fda9daa3279c69`, 22:15:37Z–22:20:50Z | `MATCHED`: 14 forms on every route, all 4 groups; both audits let it stand: overflow `PIE-R3003` in all 28 failing cells per database, the control `EJ6` refused on MySQL with `PIE-B1003`, the PostgreSQL SQL equal to the emission at the slice's bases `9b954b3e` and `475f14b3` (14 of 14). |
| `e4b-c-emitted`, chain C, emitted | `h-9b954b3e-20261124T201317Z`, on S3 `9b954b3e`, frozen 20:52:05Z | `aa872f7b60c702f2`, 23:12:36Z–23:26:54Z | `MATCHED`: 36 forms on every route, all 15 groups; both audits let it stand: overflow `PIE-R3003` in all 160 failing cells per database, the control `EC5A` refused on MySQL with `PIE-B1003`, the bound values and placeholders of the 378 parameter cells the oracle's, and the text route's `Float` literals, `-0.0`, `2^-1074` and `±DBL_MAX` among them, read back bit for bit. |

Freeze records are under the MC package's `freeze/<list>/`; campaign
records are under the recovery evidence's `mc/<list>/`, and each
verdict's two audit reports under its `e4b-freezes-20261124/<list>/audit/`,
beside the lane's freeze-attempt, review and launch records. All are
owner-held working records outside Git. No E4B run failed, was VOID or
was UNQUALIFIED but `e4b-c`'s preregistered witness; the superseded freeze
records of 15:57Z are kept.

**Opened.** 31 (operator, position) pairs in 93 (operator, position,
shape) triples, on both databases (PL.79):

- chain B: `+`, `-`, `*` and the sign at P1, P2 and P3, each in every
  shape of its position, 12 pairs in 36 triples;
- chain C: `+` and `-` at P4, P5, P7 and P8; `*` at P4, P5 and P8; the
  sign at P5, P7 and P8, and at P6 as the `count` of the sign of a
  nullable field with no WHERE; 15 pairs in 49 triples;
- chain J: the four operators at P9, as a whole item and beside a WHERE
  on an `Int` or `Text` JOIN, 4 pairs in 8 triples.

No list found a real counterexample, so no operator ended in any chain
(PL.78 (2)) and no emitted list refused an operator. Each slice's changed
production bytes need fresh full target receipts (MC.16 (1)), which the
batch's receipts provide ([Receipts](#qualification), as for MC's
forms). The emitted verdicts, judged on the slices' reviewed commits on E4
`475f14b3`, carry to the restacked commits `c79dce28`, `41950a90` and
`ddfd0db8` by D77.50: every document the compiler derives is
byte-identical there (PL.80).

### E4B's forms still refused

- A MySQL `count` of a `Float` `+`, `-` or `*`, and any E4B `count` under
  a WHERE, of a sign too: MySQL may count a row without computing an
  argument that it types non-nullable, as over a `NOT NULL` column under a
  nullable declaration, where PostgreSQL fails. One of two complete fixes,
  each with a chain C witness of such a column, lifts it before the
  Phase82 freeze, under the roadmap's deferred-owner rows (PL.82).
- Every other shape that did not open keeps `main`'s refusal and an
  approved exception with no target, listed under J12 (3) in each release
  (MC.10): a `*` beside a header parameter (PL.76); an E4 value in a JOIN
  `on` (PL.68); a `count` of a non-null value; the shapes whose computed
  rows depend on the plan (PL.75 (2)); two fields, a nesting or a
  parameter operation in the shapes outside the four in which they open,
  and a nesting or two fields beyond their pairs in a `count`, a computed
  key or a JOIN item; and the shapes that E4B's Gate 1 did not take, such
  as LIMIT, an upstream query, `/`, an aggregate other than `count` and
  two levels of nesting.

### E4B's Phase82 inputs

- MC.10's freeze ledger row names the E4 forms that neither E4's narrow
  cell nor E4B opens, PL.68's JOIN `on` and PL.76's `*` beside a header
  parameter among them.
- A row of its own carries the deferred item of E4B's Gate 1 question Q2:
  whether PostgreSQL fails a statement whose out-of-range `Float` value a
  plan-dependent shape may leave uncomputed, which the `Float` law does not
  state while the `Int` law does. It is an uncertainty of `main` that E4B
  neither brought nor observed; Phase82's Gate 1 decides the wording.

### E4B's budget

E4B's ledger is `C89/F280/D8,400/S7` with PL.15's automatic raise (PL.75
(3)). PL.15 raised D to 12,600 and 18,900 and F to 420 and 630 on
2026-11-21, raises booked on 2026-11-24 and reported to the owner on
2026-11-25, and D to 28,350 on 2026-11-24, reported to the owner the same
day. At the last booking, after the qualification checks and the restack
trial, E4B had used at most C37, F432, about D19,528 and S2: at most 42%,
69%, 69% and 29% of `C89/F630/D28,350/S7`. No ceiling was reached. The D
counts from 2026-11-24 on are the tool calls of each lane's agents, which
do not separate pytest starts, so F is undercounted for those days; some
lanes of 2026-11-18 were lost with the old disk and are not booked. The
lanes after that booking, the draft of these records, the final restack
with the repair of the language reference, its D77.50 promotions and its
review, and the P49 cross-check, were not booked when this audit was
written; the post-release documentation commit records E4B's final use.

### E4B's handoff

- **Opened.** 31 (operator, position) pairs in 93 (operator, position,
  shape) triples, as [E4B's qualification](#e4bs-qualification) lists
  them.
- **Target before the Phase82 freeze.** PL.82's two fixes, each with its
  chain C witness, under the roadmap's two deferred-owner rows.
- **Refused with no target.** The forms of [E4B's forms still
  refused](#e4bs-forms-still-refused) but PL.82's, which each release
  lists under J12 (3) and on which Phase82 rules (MC.10).
- **Phase82's Gate 1.** Q2's deferred item, by its freeze ledger row.

## D19

D19 was to measure, on MySQL 8.4.12, the first page of R2
`save_recoverable` and `recover` for the queries whose SQL R2 does not
read, `param_window` included, before extending D77.80's precheck to MySQL
(PL.40, D19). Its two lists hold 48 forms, whose predictions the test-only
commit `a7452961` pins: `d19` has 32 forms over literals and `d19p` 16
with header parameters, `param_window`'s among them, and the two share the
three freezes that MC.09 allows a family.

d19's first campaign was judged `MISMATCH`: the list's public call made
its job workspace on a `tmpfs`, which the product refuses before R2's
first connection. After an erratum repaired that call, d19's second
campaign, on the third and last freeze, was `UNQUALIFIED_RECEIPT`: the
list's fixture had created its MySQL view without the `utf8mb4_0900_bin`
collation that R2's MySQL source admission requires, so R2 refused the
view before any first page. Both audits of each campaign found a harness
cause and no counterexample or defect of `main`
([Verdict records](#verdict-records)). Neither campaign measured a first
page, and d19p, whose campaign was to follow a d19 campaign that matched,
never ran; neither of its two freezes was launched.

The owner chose to end D19 by its rules, with no fourth freeze (the lead's
record of 2026-11-26 22:20Z), so the d19 preregistration's item on freezes
applied: after the three freezes, a harness-caused `MISMATCH`, or a VOID
run that only a new freeze can repair, as the lead reads that item, ends
D19's measurement without an extension, and the lead takes PL.40 D19 back
to the owner. D19 extended nothing: D77.68's "The check is R2's last
before the workspace" and D77.80's "On MySQL this check is not made"
stand, and on MySQL an R2 first page whose SQL R2 does not read still ends
`FAILED` without a public reason. D19's product slice, prepared to extend
the precheck, does not ship, and its test-only commit has no release-note
fragment.

PL.40 D19 returns to the owner after the release, with three repairs for
any later measurement: a `SET NAMES` line with the `utf8mb4_0900_bin`
collation in the fixtures of `d19` and `d19p`, a `TMPDIR` line for the
client in the harness's next round, and a step before each campaign that
calls the list's own public call; and with two facts about the product
that the measurement found: the [execution reference](../execution.md)
does not state that a MySQL view that R2 retains must be created under
`utf8mb4` with the `utf8mb4_0900_bin` collation, and the public layer of
R2 reports that refusal as PIE-R3003 `SERVER_ERROR` with no detail rather
than PIE-R2007 `SOURCE_QUALIFICATION`.

## PL.49's two items

PL.49 left two items to MC (PL.49 (2), MC.16 (2)). One commit after D19's
test-only commit, `24da889a`, settles both, with no change of observable
behavior.

(1) The 57 surviving mutants of Phase77 S12's allowlisted guards, 55 in
`project_sql_emission_rows.py`, one in `project_completed_semantics.py`
and one in `project_sql_emission_verification.py`, were classified one by
one under MC.16 (2): none is a real defect or unexplained, and each is
equivalent or unreachable on public inputs. The 27 guards that a kept
guard, an invariant of the contract or of plan or compiled verification,
or a language refusal already implies are removed. Of the 30 that stay,
ten have new cases that kill their mutants, four become sole guards once
the 27 go and existing tests then kill them, and existing tests already
kill one; two are closed by the lead's ruling as structurally equivalent,
with no code change; eleven, for which no search found an edited bundle
that loads and tells the guard apart, stay by the lead's ruling that a
search alone removes no guard; and two, E04 and C10d, stay with no case
found that kills their mutants.

(2) The repeated MySQL cell derivation (W13(d)) is repaired on the
compiled side: `mysql_compiled_scalar_cells` returns before its pass over
the records when no value of the terminal row is an `lpad`, `now()` or
`date_of` operation, and `mysql_compiled_typed_cells` returns before its
walk when no parameter has a MySQL typed tag. The plan side stays as it is
by the lead's ruling, since its repeats are bounded and its verifier
derives emission again by design. A test that counts both laws' record
lookups on bundles of 4 and 16 chained `let`s fails on the code before the
repair (704 and 7,820 lookups).

The batch's dry run compared its release tree with the same tree without
that commit: the 57 mutants behave as classified, 2,843 compile and replay
probes differ in nothing, the plan-side law and the compiled law, over 837
bundles, disagree nowhere, and the compile record of each of the 14 MC
lists is unchanged. No SQL, emission status, blocker, diagnostic or
compiled reader outcome changed.

## Route items due at closure

| Item | Where |
| --- | --- |
| The families and E4 forms opened, each with its law and run | [Accepted scope](#accepted-scope), [Qualification](#qualification) |
| The forms still refused, with their decisions and the J12 (3) list | [Forms still refused](#forms-still-refused); the J12 (3) bullets of the `77-s03` and `77-e04` fragments |
| The shapes to which D19 extended the precheck, none: D19 did not extend it | [D19](#d19) |
| The Phase82 freeze ledger row of MC.10, with PL.68's JOIN `on` | the roadmap's [freeze ledger](../roadmap.md#phase82-freeze-ledger) |
| E4's wider positions and any ended family, for the owner's later plan | [Handoff](#handoff) |
| E4B's (operator, position) pairs opened, each with its two runs; its forms still refused with their decisions; its freeze ledger row and the deferred item of its Gate 1's Q2 | [E4B](#e4b) |
| PL.49's outcome | [PL.49's two items](#pl49s-two-items) |
| The ledger, the Gate 2 duration and the lessons | [Budget and Gate 2](#budget-and-gate-2), [Lessons](#lessons) |
| The capability page | the [capability page](../capabilities.md): each slice updated its MySQL cells, s03n's T1 `where lines > 0` under `preserve` among them, and every verdict matched, so each cell stands as its slice wrote it; no family ended, so no row changed for one |
| The phase-end acquisition review | [Acquisition review](#acquisition-review) |

The candidate-time sentences that each slice had to carry until its
campaign ran, one in each fragment and one in each of the G3, G4 and G5
paragraphs of the language reference, which said that the campaign was
still to come and that what followed was expected from the SQL, not
observed, now state the campaign that ran.

## Acquisition review

The batch's code commits were reviewed under the [phase-end acquisition
consolidation](../development.md#phase-end-acquisition-consolidation) for
the tests and helpers that they change from `65c22852`, the head every
slice was rebuilt on, up to `0fd28f69`, E4B's last commit, nineteen
commits: MC's slices with P49 `24da889a`, the unread typed MySQL header
repair, the repair `45ce8e55` of E4's cell and E4B's five commits, on
2026-11-27. Each test owner that they change ran whole at the head under
an acquisition probe that logs every in-process emission and every pass
through the readers by a digest of its inputs, and the nodes were counted
by collection at both ends and after P49, the unread-header repair and
the repair of E4's cell.

- **Coverage.** The commits add 4,702 nodes to ten owners and drop 151
  refusal pins of statements that they open (2,970 → 7,521 nodes): MC's
  slices +3,131/−150, the unread-header repair +525, the repair of E4's
  cell +134 and E4B +943/−32. They change three shared test helpers,
  `tests/_pietto_sql_emission.py` (+9,861/−995),
  `tests/_pietto_sql_emission_pure_boundary.py` (+1,975/−138) and
  `tests/_pietto_sql_query_parameters.py` (+14/−1), and add no test file,
  process acquisition or `ci_workload` declaration; the one fixture scope
  they add is the unread-header repair's module fixture `crossed_base` in
  `tests/test_sql_query_parameters.py`, one MySQL typed case per module
  whose files each node copies into its own project.
- **Repeated acquisition.** 12,675 in-process emissions of 8,275 distinct
  inputs and 1,398 passes through every reader. Each family's equivalence
  test passed its forms and spellings through the readers again, 222
  repeated passes of identical inputs, about a tenth of
  `test_sql_grouped.py`'s time; recorded as debt, owner the two test
  owners, latest the next whole-tree pass.
- **Kept.** The equivalence, law-edit and E4B form tests rebuild the
  outcome they compare or edit (2,036 repeats, under 0.1 s each; 590 of
  them are `tests/test_harness_target_conformance.py`'s own, which E4B
  changes in one assertion only), so each node stays self-contained; the
  forged-cell witnesses emit under a patched law by design; inputs shared
  across owners run on different loadfile workers. Fixtures are per node
  but `crossed_base`, and each serialization feeds a distinct reader.
- **Debt.** `tests/test_sql_grouped.py`,
  `tests/test_execution_compiled_bundle.py`, `tests/test_sql_rows.py` and
  `tests/test_sql_project_scalar_expressions.py` have no loadfile cost
  estimate in `ci/workloads.toml`; owner the lead, latest Phase81's Gate
  0, from a quiet four-worker session or CI health.
- **Profile.** The ten-node profile reads the natural CI health of the
  batch head after the push; the post-release documentation commit
  records it.

## Budget and Gate 2

MC's ledger is `C245/F735/D23,000/S13` with PL.15's automatic raise
(MC.07, MC.08). The last total recomputed from its rows, of 2026-11-18 at
14:15Z, was C≤48/F≈155/D≈8,434/S3, 20%, 21%, 37% and 23% of the ceilings.
On 2026-11-21 PL.15 raised D to 34,500, which the lead reported to the
owner at about 09:20Z that day, ordering a catch-up of the ledger from the
counted lanes. That catch-up had not been booked when this audit was
written: the ledger's later rows add about D345 without a new total, and
the lanes since 2026-11-22 have no rows, so the post-release documentation
commit records MC's use against each ceiling.

MC's slices had no Gate 2 of their own: none was pushed before the
release batch. The batch's one Python 3.13 Gate 2 runs on the release tree
after this audit is written, and the post-release documentation commit
records its duration.

## Lessons

- **MC-1 — Run a reference list's witnesses on the reference product.**
  The harness's weakening step ran S03's witnesses on each candidate's
  product, so once G7 legitimately opened S03's control C3, five lists
  could not freeze. A witness that a reference list defines belongs to the
  product that list froze on.
- **MC-2 — Close a freeze's open questions before the freeze.** Three
  freezes stood as records while their campaigns were held, because
  preconditions that named the lead's answers had none; the answers, the
  paper edits and the refreezes cost a round.
- **MC-3 — Put a narrowing of what opens to the owner before the run.**
  The lead's fail-closed default for T1's second-level WHERE narrowed
  MC.14's scope; when it was asked, the owner chose to open the form
  (PL.91), after the slice and its list had been built without it.
- **MC-4 — Give each concurrent agent its own scratch directory.** Two
  skeptics that shared a directory deleted each other's environment and
  invalidated a mutation run; directories named by agent and finding
  avoid it.
- **MC-5 — Keep run-dependent statements where the run is recorded.**
  Candidate-time roadmap and status prose left the slices for the closure,
  but each fragment and three language paragraphs still said that their
  campaign had not run, and the closure rewrote them. State such a fact
  once, in the record that the run completes.
- **MC-6 — Let one test own the readers pass of a body.** Each family
  added an equivalence test beside its forms test, and both ran every
  reader over the same bodies, a tenth of the largest owner's time.
- **MC-7 — Derive a record's counts and citations from the run records.**
  PL.67, the route and the status page said that G1's first campaign
  matched 17 of 18 forms, where its verdict lists 14, and a draft of this
  audit said that every verdict had two integrity audits, which E4's raw
  stage did not. The verdict records above are derived from the records
  by a script, which the lead reruns for each later verdict.

## Phase82 inputs

- MC.10's row: the MySQL project `sum(Int)` forms that MC did not open and
  the E4 forms outside E4's narrow cell and E4B's, PL.68's JOIN `on` among
  them.
- The R2 refusal of every form that MC opened (D77.67, D77.68, D77.73)
  stays under the existing R2 support-matrix row.

## Handoff

- **Opened.** The forms of G1–G8, the s03n list and E4's narrow cell, as
  [Accepted scope](#accepted-scope) lists them; PL.49's outcome.
- **Refused with no target.** The forms in [Forms still
  refused](#forms-still-refused), which each release lists under J12 (3)
  and on which Phase82 rules (MC.10).
- **The owner's later plan.** E4B, the owner's plan for E4's wider
  positions, opened them in its cells in `0.2.2` ([E4B](#e4b)); PL.82's
  two fixes keep their target before the Phase82 freeze, and E4B's other
  refused forms have none (MC.10).
- **Other owners.** The naming exception of
  `tests/_pietto_mysql_native_prepared.py`, S09's TLS identity check and
  the test-side `get_rows` stay with the line that next refreezes those
  packages (MC.13); the MySQL documentation gaps stay with the owner's
  later plan (MC.14); `verify_project_sql_plan`'s missing memo stays with
  Phase81 (PL.40, D15); the MySQL R2 first pages that end `FAILED` without
  a public reason stay with the owner, to whom PL.40 D19 returns after the
  release with the three repairs and two facts about the product that
  [D19](#d19) names.
- **Next.** After `0.2.2`: the post-release documentation commit, SQLite
  B2's second tier, Phase81, and the dependency batches (PL.89, PL.92,
  PL.93); no `0.2.3` is planned before Phase81 is done (PL.94).
