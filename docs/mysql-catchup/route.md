# MC route — MySQL catch-up work package

The owner answered the Gate 1 of the MySQL catch-up work package MC on
2026-11-16. The [decision
record](../decisions.md#mysql-catch-up-mc-gate-1--owner-answers-and-the-leads-rulings-2026-11-16)
keeps the answers as MC.01–MC.12 and the lead's rulings as MC.13–MC.18. MC
is the "MySQL catch-up phase" that D77.76, D77.78, PL.40's D1 and D19 and
PL.49 name. Under MC.01 it is a work package with no phase number, as the
editor core work package E-C is ([E-C route](../editor/ed03-route.md)): its
route and completion audit live under `docs/mysql-catchup/`, its decisions
live in `docs/decisions.md` with the prefix MC, and its costs go on its own
ledger (MC.07). It comes before Phase81 and ships in `0.2.2` (MC.01, PL.55).

Implementation is authorized from Gate 0. MC's batches before the `0.2.2`
release batch may be fast-forward pushed under D77.06's conditions
(MC.11). This route authorizes no tag, GitHub release or PyPI upload; the
`0.2.2` release and its push rest on PL.56.

## Gate 0

Gate 0 binds the head that published DuckDB B2's first tier: `main` at
`107df991a13096f4cc82c9966c509ac4faeff388` (tree
`a348295cafd6977a54429013f22316a2adafba06`), eleven commits on `851ad83f`
pushed under PL.52. Its [natural exact-head CI
`43888270979`](https://github.com/MianliWang/pietto/actions/runs/43888270979),
push/main attempt 1, completed with success at 15:04:04Z on 2026-11-16 and
passed all 21 jobs. At binding, `origin/main` was that commit, the working
tree was clean and no Git operation was in progress.

The CI health of that run was read under PL.07 from 15:22:41Z to 15:22:56Z
on 2026-11-16. All 15 health artifacts matched the head by digest and size,
and the health verifier passed. The status is INSUFFICIENT_EVIDENCE, with
the current screen WATCH. There are no comparable samples, because the
runners and the test set differ from the last history head `851ad83f` on
both runtimes. The workflow cost was incomplete when the report was written.
The suggested review actions are advisory: a shard imbalance to watch on
the 3.12 runtime, long indivisible nodes, and fewer units than workers in
the two portability groups. MC changes no CI placement.

Before Gate 0, only paper records were made (PL.02's precedent). The harness
freeze and its self-check, every campaign and every slice come after Gate 0.
A lane that opens later binds the newest published head and names its base
tree. Every lane rebases onto the latest integration head before delivery.

## Scope

Each family, and E4, opens on MySQL only after its own preregistered
two-database matrix (D74.09, MC.03, MC.06). A statement that MC does not
open keeps exactly `main`'s blocker list (rule two, D77.37).

**The other MySQL project `sum(Int)` forms (D77.76; MC.02, MC.03).** All
eight families are in scope. Each family widens one context dimension
around S01's guarded SUM (AD77.03), and the guarded SUM itself does not
change. Each family opens under one structural law, which a preregistered
matrix over the family's combinations witnesses. When a statement that the
law matches has any other blocker, the whole statement reports `main`'s
complete blocker list.

| Family | Widens, relative to S01's S02 cell and S03's nine forms |
| --- | --- |
| G1 Carrier | `sum` of a non-null `BIGINT` or an `INT` field; `sum(t)` where a `let` name points to one field |
| G2 Aggregates and grouping | `sum` beside `avg`, `max` and other aggregates; two or more `sum`s; a nullable grouping key, two or more grouping keys, a grouping key that is not an `Int` |
| G3 Later clauses | HAVING (including a condition that reads the `sum`), ORDER BY (including by the `sum`), LIMIT, DISTINCT |
| G4 Source organization | a relation alias `let`, a window declared and not read, an imported source, a read qualified by its source's name, an upstream query other than T1 and T2, and the byte-near neighbours that S03 refuses |
| G5 Parameters | header parameters, read or not; a bind-safe `?` |
| G6 JOIN extension | JOIN kinds, keys, carriers and ON orders beyond S03's J1–J3; two `sum`s over a JOIN; source tables with extra fields |
| G7 Conditional `sum` extension | compound tests, negative literals, C3 under `bind_safe_literals`, a conditional `sum` beside `count()` or a direct `sum`, parentheses and qualified reads in C1–C4 |
| G8 Several levels | a third level and beyond; the style page's two-level example with a non-null `amount` |

**E4's narrow cell (D77.78; MC.04, MC.05).** On MySQL, `+`, `-` and `*`
between a `Float` field and a literal, and unary `-` of a `Float` field. The
field is a nullable or non-null `DOUBLE` of a source in the selected module.
The expression is a whole-column SELECT item of a `query` or `table` with
one source and at most one WHERE, and with no `let`, JOIN, grouping, window,
ORDER BY, LIMIT or parameter. A form opens only where its finite results
match on both databases and its overflow fails on both. `*` is emitted with
an underflow guard in AD77.03's manner, which fails with 1690 (SQLSTATE
22003) where PostgreSQL reports 22003. If the guard's raw cells do not all
match on both databases, `*` stays refused and only `+`, `-` and unary `-`
can open.

**D19 (PL.40).** MySQL R2's first page that ends `FAILED` without a public
reason. MC first measures on a real MySQL the shapes that R2 does not read,
`param_window` included. It then extends D77.80's precheck to MySQL for the
measured shapes, with the existing PIE-R1004 `REFINEMENT_NATIVE_SQL` and no
new code or detail.

**PL.49's two items.** First, the 57 surviving mutants of Phase77 S12's
allowlisted guards in three modules under `src/pietto/_project`: 55 in
`project_sql_emission_rows.py`, 1 in `project_completed_semantics.py` and 1
in `project_sql_emission_verification.py`. Second, the repeated MySQL cell
derivation (W13(d), PL.49). Neither item may change observable behavior,
and the 57 are classified before any guard changes (MC.16).

Not included, each keeping its refusal under its own decision: new syntax,
new PIE codes or details; R2 for the newly opened forms, which R2 refuses
(D77.67, D77.68, D77.73); single-file MySQL, which already emits these
forms; MySQL nested results (D77.32); `stddev` of an `Int` (D77.34); the
MySQL `UUID` header parameter (D77.79); `sum(a + b)` and other `Int`
arithmetic outside S01's cell; a `sum` inside an expression or a window;
`Float` `/` (D77.38); `Float` `sum` and `avg`; E4's wider positions (`let`
carry, WHERE comparisons, ORDER BY keys), which go to the owner's later
plan (MC.04), before the Phase82 freeze with their own Gate 1 and ledger
(PL.58); and the items that MC.13 and MC.14 move out of MC.

## Gate 1 record

The sheet is the lead's MC Gate 1 decision sheet, brought to the current
state and reviewed once on 2026-11-16; like the lead's record of the
answers, it is an owner-held working record outside Git.

| Id | Rule in this route | Source |
| --- | --- | --- |
| MC.01 | An independent work package with no phase number; own Gate 1, ledger and completion audit; before Phase81, in `0.2.2` | Sheet Q1 A; PL.55 |
| MC.02 | All eight families G1–G8 in `0.2.2` | Sheet Q2 A (not the recommended B) |
| MC.03 | One structural law per family, witnessed by a preregistered two-database matrix; `main`'s complete list when another blocker is present | Sheet Q3 B |
| MC.04 | E4's narrow cell; the wider positions go to the owner's later plan, before the Phase82 freeze with their own Gate 1 (PL.58) | Sheet Q4 A |
| MC.05 | `*` with an underflow guard, falling back to refusal when its raw cells do not all match | Sheet Q5 B |
| MC.06 | One shared harness derived from S03's second freeze, frozen and self-checked first; one list per family, frozen and judged on its own | Sheet Q6 B |
| MC.07 | Ledger MC, `C245/F735/D23,000/S13`, about twelve slices | Sheet Q7 B |
| MC.08 | PL.15's automatic raise applies to the MC ledger | Sheet Q7b (a) (not the recommended (b)) |
| MC.09 | An integrity audit first; at most three freezes per family for harness causes; a real counterexample ends the family | Sheet Q8 B |
| MC.10 | Forms still refused at closure keep an approved exception with no target, and the Phase82 freeze ledger gets a row | Sheet Q9 B |
| MC.11 | Standing fast-forward push authorization for MC's batches before the `0.2.2` release batch, under D77.06's conditions | Sheet Q11 A |
| MC.12 | Five independent review lanes in each review round for a slice that opens MySQL shapes (D77.18) | Sheet Q12 A |
| MC.13 | The naming exception, S09's TLS identity check and the test-side `get_rows` leave MC | Lead |
| MC.14 | S03's byte-near neighbours fall inside G4, G6, G7 and MC.03; the MySQL documentation gaps leave MC | Lead |
| MC.15 | The slice order, the single writers, the midpoint and the stop points of this route | Lead |
| MC.16 | Full target receipts, the classification of PL.49's 57 mutants, and the ledger figure under MC.04 | Lead |
| MC.17 | The harness's raw text route, a container label and campaign lock for each family, MC.09's count of freezes, and no MC form in the conformance corpus's generation inputs by default | Lead |
| MC.18 | The harness's third round (H1–H4), a value the client cannot read judged `UNQUALIFIED_RECEIPT`, G1's law edge, G2's carriers and E4's rule for a difference on the text route alone | Lead |

The sheet's Q10, whether to take neighbouring MySQL refusals into MC, was
withdrawn before the owner answered: those items keep their refusals under
their own decisions and wait for the owner's later plan.

These existing decisions also bind MC: D74.09 (two-database qualification),
D76.17 (how D is counted), D77.18 (review lanes), D77.19 (the Docker
Engine), D77.37 (rule two), D77.50 (native runs carried to a rebased
commit), D77.51 (reviews with only low findings), D77.63 (a defect of
`main` found by a run is repaired on its own), D77.67, D77.68 and D77.73 (R2
refuses the newly opened forms), D77.70 (no second review after fixing
findings that are not real bugs), D77.76, D77.78, D77.80, AD77.03, PL.14
(engine slot locks), PL.15, PL.40's D1 and D19, PL.49 and PL.51.

## Slices and order

One slice is one commit. Each family slice changes the emitter, the live
verification, the compiled replay and the pure reader so that each derives
the family's law on its own; puts its tests in the existing owners; adds
the new forms to R2's refusal tests (D77.73); and updates the capability
page, the `language.md` cell description, the J12 (3) list and its
release-note fragment. MC's fragments take the number 77, as those of Wave
A, E-C and the Phase77 follow-up package did: `77-g01-<topic>.md` to
`77-g08-<topic>.md` for the families, `77-e04-<topic>.md` for E4,
`77-s03-<topic>.md` for the s03n list and `77-d19-<topic>.md` for D19,
which did not ship: D19 did not extend the precheck, and its test-only
commit has no fragment (DERIVED_MECHANICAL).

| Slice | Delivers | Depends on |
| --- | --- | --- |
| G1 | Family G1 | The frozen harness |
| G2 | Family G2 | G1 |
| E4 | E4's narrow cell, raw primitive stage first, then the emitted SQL | The frozen harness |
| G3 | Family G3 | G2; E4; the midpoint report |
| G4 | Family G4 | G3 |
| G5 | Family G5 | G4 |
| G6 | Family G6 | G5 |
| G7 | Family G7 | G6 |
| G8 | Family G8 | G7 |
| s03n | The s03n list: S03's neighbours that G7 and G8 hand on (PL.74), T1's second-level WHERE included (PL.91) | G8 |
| D19 | The R2 measurement on MySQL, then the extended precheck | G8; a head that carries SQLite B2's S11 |
| P49 | PL.49's two items | D19 |
| Z | Closure: the phase-end acquisition review, the capability page and the completion audit | P49 |

The order is Gate 0 → harness freeze → G1 → G2 → E4 → midpoint → G3 → G4 →
G5 → G6 → G7 → G8 → D19 → PL.49's two items → closure. The sheet's route
named G3–G5 after the midpoint; MC.02 extends it to G6–G8 (MC.15).
Families are implemented one at a time in this order, because each law
builds on the laws before it. E4 is not a family: it depends only on the
frozen harness, so it may be implemented beside G1 and G2, and its commit
follows G2's. The qualification campaigns may be frozen in parallel and
run queued on the engine slot locks, each family with a container label
and a campaign lock of its own (MC.17): at most three
PostgreSQL and three MySQL containers at once, each campaign with at most
one container per engine and one slot lock per engine (PL.14). PL.49's two
items come after the families because both they and every family change
`project_sql_emission_rows.py`, and changing it first would void each
family's byte equivalence under D77.50 again.

PL.74 revises this order, which keeps its text above: G3–G8's slices are
implemented in parallel and their commits keep the order; a family freezes
once its slice and the harness are ready and the families before it have
frozen, without waiting for their campaigns to be MATCHED; and a refreeze
that an upstream repair forces counts under MC.09 only when a campaign ran
on the old freeze. The lead's rulings in PL.74 read MC.17's count the same
way for every refreeze; let G7 and G8 freeze first without restating their
laws, with the S03 neighbours that MC.14 places within G7 and the two-level
neighbours handed to G8 on a list of their own, closed before MC's closure;
and run D19's measurement early, once the sixth harness freeze passes
MC.12, while its precheck still follows G8. None of this widens a family,
changes a cell or criterion, or opens a form.

## Qualification

The harness is derived from the second freeze of S03's qualification
package, whose run judged all three families `MATCHED`; the two-stage
package of D77.77's experiment (M01b), carried into `0.2.1` under D77.50,
is the reference sample
(MC.06). Before the derivation the lead measures the headroom of the target
conformance receipt, fixes the deferred low findings of the S03 package,
and checks whether its MySQL client skips the server identity check as
S09's does, fixing it first if so (MC.13). Before its first freeze the
harness gains a raw text route, MySQL's `COM_QUERY` and PostgreSQL's simple
query, beside S01's public and raw prepared routes (MC.17). The harness is
frozen once on its own and self-checked on the real launch path before any
family freezes.

- **`sum` families.** Each runs only its emitted SQL, since R4, S01 and S03
  already witnessed the guarded SUM. Every family has cells for exact sums,
  sums that pass ±2^63 and return into range, groups of only NULLs, empty
  input, both overflow directions with no row and no partial delivery, and
  the public, raw text and raw prepared routes. Each has at least one
  statement refused for an unrelated reason, which must report `main`'s
  complete list on both databases. G3 also preregisters what happens when
  a group that is not returned overflows; if the two databases differ, G3
  does not open.
- **E4.** The raw primitive stage compares MySQL `DOUBLE` `+`, `-`, `*` and
  unary `-` with a Python binary64 oracle bit for bit: ordinary values,
  negative zero, overflow near `±DBL_MAX`, `*` underflowing to zero and to
  subnormal results, NULL operands, and nullable and non-null fields; the
  guarded `*` gets the same cells. A warning makes the run INCOMPLETE.
- **D19.** The measurement uses the harness's MySQL half and is
  preregistered, frozen and reviewed like a family.
- **Judgment.** A form opens only when both databases match; PostgreSQL
  alone is not enough. Failed and VOID runs are kept and never replaced.
  A family's first freeze counts toward MC.09's three; a rebind that stops
  before its freeze record, or that follows only a move of the candidate
  head with no campaign run on the old freeze, does not count (MC.17).
  G1's first campaign matched 13 of its 14 forms; its I6 counterexample is
  an existing defect of `main`, not of G1's law, so G1 does not end:
  `main` is repaired first and G1 runs again on its second freeze (PL.67,
  which revises MC.09 for I6 only). Under that repair every grouped MySQL
  `SMALLINT` or `INT` `min` or `max` is a cast `my_signed_int`, and each
  family's expectations follow it (PL.67, PL.73).
- **Receipts.** Changed production bytes require fresh full target receipts:
  PostgreSQL's runs once on the host, and MySQL's comes from the batch head's
  natural CI `Target mysql` job, as D77.71 did (MC.16). MC's forms do not
  join the generation inputs of the target conformance corpus by default,
  since the MC campaign is their qualification; if a family's slice must
  add inputs and the receipt passes its reserve, the reader reserve is
  raised after measurement as a mechanical update (MC.17).

## Budget

MC has its own cumulative ledger `C245/F735/D23,000/S13` (MC.07), counted as
D76.17 counts, and it draws on no Phase77, V021 or Phase81 ledger. PL.15
applies (MC.08): a figure that reaches 80% gains half of itself and the
lead reports the raise afterwards; reaching a ceiling still stops MC for
the owner. The ledger is an owner-held working record outside Git, like the
others.

The sheet's planning figures are not slice caps: about D1,500 and C15–20
for each family or E4, raised by a quarter for the five review lanes;
`C15/F45/D1,200/S1` for D19; `C10/F30/D500/S0` for PL.49's two items; about
D400 for Gate 0 and the midpoint, D300 for the harness, D600 for the
closure, and a replay reserve of D800. The figure was computed with E4's
wider positions as one more slice; the owner chose the narrow cell and kept
the figure, and the lead does not lower it (MC.16).

## Midpoint

When G1, G2 and E4 each have a conclusion, opened or ended under MC.09, the
lane workflows stop and the lead reports to the owner: the S/H/L/K/Q
review, the ledger's use and the estimate for G3–G8, D19 and PL.49's items,
and the CI health of the latest published head. G3 starts only after that
report. An owner answer that changes the scope or the order revises this
route: PL.74 has the report drafted before G1, G2 and E4 each have a
conclusion and delivered before G3 freezes, while G3's slice is implemented
beside the others.

## Stop points

The workflow scripts carry these stop points; none relies on a person
stopping a lane in a dialog (MC.15).

1. The midpoint above.
2. Any ledger figure reaches its ceiling after PL.15's raises: MC stops for
   the owner.
3. A run or the classification of PL.49's mutants shows a real defect of
   `main`: the lane stops, the lead reports to the owner, and the repair
   runs on its own, apart from any family (D77.63, MC.16), as G1's I6 did
   (PL.67).
4. A change would alter PostgreSQL SQL or another public PostgreSQL output,
   the blocker list of a statement that stays refused, `VERSIONS`, a
   compiled record or a public contract, or would add a PIE code or detail:
   the lane stops for the owner.
5. A family's third freeze ends VOID or UNQUALIFIED for a harness cause, or
   a real counterexample appears: that family ends under MC.09, keeps its
   refusal and is listed under J12 (3); the next family goes on.
6. A campaign's preflight does not observe the Docker Engine (D77.19): the
   campaign does not run, and no other engine replaces it.
7. The `0.2.2` release window: MC's lanes stop while it is open.

## Single writers and the other lines

The lead sets the order; a later arrival rebases (MC.15). At binding, at
about 15:30Z on 2026-11-16, the lines stood as follows.

- **DuckDB B2.** Its first tier is published at the Gate 0 head; its second
  tier goes to the owner's plan (PL.54). It shares no `src` file with MC.
- **SQLite B2.** Its first tier is an unpublished candidate on `851ad83f`
  (`ff0f5e20`, seven commits), pushed under PL.52 when ready. MC changes
  the plan modules `project_sql_plan_target_assessment.py` and
  `project_sql_plan_pure_boundary.py` only on a head that carries SQLite's
  S07: S07 changes them first, as the [DuckDB B2
  route](../phases/phase-79/route.md#b2-lanes-integration-and-single-writers)
  states, and MC.15 orders MC after it. MC's D19 changes R2's MySQL precheck
  only on a head that carries SQLite's S11, which adds R2's SQLite
  refusals.
- **The pure verifier fidelity repair.** An unpublished candidate on
  `107df991` (`7e526cae`, three commits), pushed under PL.20 and PL.13's
  conditions. It rewrites `tests/_pietto_sql_emission_pure_boundary.py`,
  which every MC family changes. The pure repair goes first: an MC slice
  that changes that file starts on, or rebases onto, the head that
  publishes the repair and checks byte equivalence again (D77.50). The 30
  surviving mutants in the pure reader stay with the repair (PL.49).
- **E-C's closure.** An unpublished candidate on `107df991` (`1046e98d`,
  one commit) under ED.05. It shares only `docs/roadmap.md` and
  `docs/status.md` with MC.
- **Phase81.** Stopped until the owner's plan (PL.54). No Phase81 commit is
  pushed before the `0.2.2` release commit (PL.57). Later that day the
  owner put Phase81 on the new route of the draft plan, to start after the
  draft's next revision, and restored PL.52's standing push authorization
  for Phase81's batches from that push on (PL.58). MC does
  not add the memo of `project_sql_plan_verification.py`, which stays
  Phase81's (PL.40, D15).
- **Shared pages.** `docs/language.md`, `docs/capabilities.md`,
  `docs/execution.md`, `docs/development.md`, `docs/roadmap.md`,
  `docs/status.md` and `README.md` have one writer at a time at
  integration. `docs/decisions.md` has one writer, the lead; MC rows keep
  their prefix and are only appended.
- **Every push moves `main`.** The other waiting lines rebase and run their
  Gate 2 again.

## Closure and handoff

MC closes with its [completion audit](completion-audit.md), after the
phase-end acquisition review. The audit hands off:

- the families and E4 forms opened, each with its law and qualification run;
- the forms still refused, each with its decision (MC.09, MC.10), and the
  J12 (3) list that the next release carries;
- the shapes to which D19 extended the precheck;
- the Phase82 freeze ledger row of MC.10, which also lists E4B's `Float`
  arithmetic in a JOIN `on` (PL.68);
- E4's wider positions, which come before the Phase82 freeze under their
  own Gate 1 (PL.58), and any ended family, for the owner's later plan;
- PL.49's outcome: the classification of the 57 mutants and the cell
  derivation repair;
- the ledger's use, the Gate 2 duration, and the lessons for the
  engineering lessons page.
