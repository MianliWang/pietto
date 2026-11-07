# Phase76 route — 12 slices

Phase76 owns the Phase 76 row of the
[roadmap](../../roadmap.md#future-roadmap-v6), PostgreSQL deep adaptation.
Its Gate 1 narrows the row to the PostgreSQL gaps that users meet today
(D76.01): PostgreSQL emission of more project forms that `check --project`
already accepts, `%` of `Float` operands, `Decimal` times `Int`, two
relaxations of the D8 rules and a caller-supplied CA for PostgreSQL
connections, with the MySQL forms whose two-database runs already passed or
ride the same runs. Its Gate 0 binds `main` at the `0.1.10` release commit
`8e7c43f1852b2c26318b3217268a1f7416f44965` (tag `v0.1.10`), the last commit
of Phase75 batch 2, whose natural exact-head CI `42343772631` attempt 1
accepted all 21 jobs. Its Gate 1 is D76.01–D76.18 and the ten technical
reminders in the
[decision record](../../decisions.md#phase76--owner-decisions-2026-11-07).
Its batches publish to `main` with no tag or PyPI upload in between. Phase76
and Phase77 ship together as Pietto core `0.1.11`; the tag, GitHub release and
owner-operated PyPI upload remain separately approved (D76.14).

Gate 0 takes the Phase75 [completion audit](../phase-75/completion-audit.md),
its [Phase76 handoff](../phase-75/phase76-handoff.md), the Phase75
[engineering lessons](../../references/engineering-lessons.md#phase75) and the
latest qualified CI health as inputs. It also records two baselines before
any design is bound: an evidence matrix with the exact `check`,
`check --project`, `emit-sql` and `emit-sql --project` result of each
candidate form on both dialects, and a byte corpus of every VERIFIED document
of the receipt corpus and of the documentation examples on both dialects.
Each slice shows against that corpus that only formerly refused outputs
change. Lines that ran before `0.1.10` worked only in worktrees and evidence
folders, and they replay onto the release commit. This route is
published by an unnumbered documentation-only commit, the first Phase76
commit on `main`, which also records the `0.1.10` publication. Each slice
binds its exact inputs, write set, checks and acceptance when it is
integrated; this table fixes coverage, dependencies and batches only.

## Lines

| Line | Delivers | Not included |
| --- | --- | --- |
| 76-E | PostgreSQL project emission, semantics unchanged (D76.02): a FULL or CROSS JOIN beside an unread `Timestamp` or `UUID` field (E1); a joined query whose WHERE calls a def that inlines to a conditional, and a scalar call inside an aggregate argument over JOIN rows (E2, E3); `Float` field arithmetic and negation, and `Float` window, FULL JOIN and distribution-result keys (E4, E6); `/` of `Int` and `Float` operands and `%` of `Int` operands, and a `Text` default of `lag` and `lead` (E5, E7); a `Decimal` compared with a literal, `Decimal` with `Int` under `+` and `-`, `Decimal` values of different scales, and `Decimal` `sum` (E8–E10). One new meaning rides S04: `%` of `Float` operands, simulated, in single files and projects on each target where the S04 run proves an exact lowering (D76.02) | a `Float` `%` on a target without a proven exact lowering, which stays refused with its code; the forms of D76.03: `Decimal` division and `avg`, project `matches(...)`, a `Float` beside an `Int` literal, `Int` arithmetic wholly outside signed 64 bits, `Float` `median` and `quantile`, UUID `min` and `max` |
| 76-N | `Decimal` times `Int` on either side and a sign on a `Decimal`, in single files and PostgreSQL projects (D76.04) | `Decimal` with `Float`; scale rules for `Decimal` division and `avg`; MySQL projects |
| 76-D | In single files, `group by` and `select` of a computed `let`, by the rule projects use (D8 (a)); in single files and PostgreSQL projects, a scalar function or arithmetic around direct aggregates, group keys and literals in one query, such as `coalesce(sum(qty), 0)`, and in a single file `round(avg(amount), 2)` for a `Decimal` amount (D8 (b)) (D76.05) | a project `Decimal` `avg`, which stays refused (D76.03); `round` of a `Float` with digits (a Phase80 Gate 1 candidate); retiring the two-query route (J16); a check that the contract relation matches the source table string (D76.06) |
| 76-T | An optional `ca_file` on `PostgresAccess` that makes both PostgreSQL routes verify the certificate chain and the host name, or refuse with a typed error before connecting (D76.07); `ExecutionLimits` as the bounded-read contract (D76.08) | a required `ca_file`; a CA from an environment variable or a default file; another TLS profile |
| 76-M | MySQL single-file constants and `--set`, and `now()`, after a byte replay of their passed runs; the MySQL single-file forms of 76-N and 76-D and the MySQL CROSS JOIN of E1, each after the same two-database run; the capability page rows for `string_agg` and the typed project parameters (D76.09) | MySQL FULL JOIN; every other MySQL refusal (Phase77) |
| 76-H | The `Header.mode` read on a hand-built AST deleted, and the header grammar rule removed only if `migrate` and the per-line PIE-P1000 hints stay byte-identical (D76.12); `fmt --project` writes hardened against a directory race; PostgreSQL witnesses for the `-0.0`, UUID, `Timestamp` and `Date` members of `count_distinct(a, b, ...)`, and MySQL statements of their own for the open forms that read a reopened `Timestamp` or `Date` `min` or `max` (a `let`, `order by`, a window `order by`, `select distinct`) | whole-project write atomicity of `fmt --project` |

A form opens on PostgreSQL only with a real-database run against an oracle
written before the run, and on MySQL only after a passing two-database run on
the same data (D74.09). A form whose run does not pass keeps its refusal with
its code, and the release notes list it. Semantics and IR stay
dialect-neutral; a MySQL difference is a plan or emitter blocker with a fixed
PIE code. The large PostgreSQL-only subjects leave Phase76 (D76.11):
extension functions and the function/plugin SPI are unscheduled, and
database-native array and JSON columns and the `postgres_adbc` nested route
are Phase80 Gate 1 candidates; the Phase82 freeze is the latest point for
all four.

## Slices

| Batch | Slice | Content | Depends on | Database run |
| --- | --- | --- | --- | --- |
| B1 | route | Route publication, the Gate 1 record, the `0.1.10` publication record and the `AGENTS.md` contract list (documentation only) | the `0.1.10` release commit | none |
| B1 | roadmap | Roadmap cleanup: the roadmap keeps its forward-looking parts, its stale statements are fixed, and it gains the editor work package, the Phase82 freeze ledger, the content of `0.2.0`, the rules after 1.0 and the tentative rows 98–106; README and the project guide state that batch `--output DIR` is not supported on Windows (documentation only, D76.18) | route | none |
| B1 | S01 | E1: an outer or CROSS JOIN checks only the JOIN ports the relation reads; the `count_distinct` member witnesses and the MySQL `min`/`max` composition witnesses of 76-H | route | PostgreSQL; MySQL CROSS and the MySQL witnesses in the same run |
| B1 | S02 | E2, E3: JOIN expression admission | S01 (JOIN emission files) | PostgreSQL |
| B1 | S03 | E4, E6: `Float` arithmetic and `Float` keys | S01 (merge order) | PostgreSQL, with overflow and underflow controls |
| B2 | S04 | E5, E7: `/` of `Int` and `Float`, `%` of `Int`, and the `Text` default of `lag` and `lead`; `language.md` states the sign rule of `%`; `%` of `Float` operands, simulated, with its meaning in `language.md` and a lowering proven exact on each target it opens (D76.02) | S03 (`resolved_binary_realization`) | PostgreSQL: zero divisor of `/` and `%`, smallest `Int` divided by -1 and its remainder by -1, negative dividends and divisors of `/` and `%`, `Float` `/`; `Float` `%` with negative, zero, tiny and large operands on each target it opens (MySQL only with a two-database run) |
| B2 | S05 | E8–E10: `Decimal` in PostgreSQL projects; E8 only if Gate 0 confirms that the check reads a literal beside a `Decimal` as its exact decimal digits | S04 (same realization) | PostgreSQL, with a wide-precision control |
| B1 | S06 | T1, T2: the PostgreSQL CA and the bounded-read record | route | PostgreSQL 18.6 with TLS: `verify-full` success; wrong host name, wrong CA and missing CA failures |
| B1 | S07 | M1, M2: MySQL constants, `--set` and `now()`; the two capability page rows; the stale comments of `src/pietto/sql/mysql_expressions.py` | route | MySQL byte replay; reruns only for changed bytes |
| — | midpoint | exit criteria below | B1 head CI | |
| B2 | S08 | N1: `Decimal` times `Int` and a sign on a `Decimal` | S05 | PostgreSQL and MySQL single file; PostgreSQL project |
| B2 | S09 | D1: computed `let` keys in single files | route | PostgreSQL and MySQL single file |
| B2 | S10 | D2: scalars around direct aggregates, with the two-query route as its oracle (in a PostgreSQL project with forms such as `coalesce(sum(qty), 0)`, since a project `Decimal` `avg` stays refused), and a worked-example part that combines the Phase76 forms (lesson 74-5) | S08, S09 | PostgreSQL project; PostgreSQL and MySQL single file |
| B2 | S11 | Closeout code: the phase-end acquisition consolidation, H1 and the `fmt --project` hardening | S01–S10 | generated checks if H1 removes the rule |
| B2 | S12 | Audit only: completion audit with its Phase77 handoff section, Phase82 freeze-ledger entries and lessons | S11 | none |

B1 contains the route, roadmap and two Lean Gate v3 documentation steps,
then S01, S02, S03, S06 and S07. S04 and S05 carry into B2 under the
authorized handoff fallback; S03 → S04 → S05 → S08 remains the
shared numeric integration order. S08–S12 expand after the B1 natural CI.
S01 to S05 merge in that order, S06 and S07 are independent, S03, S04, S05
and S08 share `project_sql_emission_rows.py::resolved_binary_realization` and
`semantic/expressions.py`, and S09 and S10 share the group and aggregate
analysis. Lean Gate v3 batch rules apply: one commit per slice; one
authoritative validation, one fast-forward push and natural exact-head CI per
batch; a failed head is kept and repaired by a child, never rerun. The first
slice that changes a compiled record, if any does, moves `VERSIONS` from
`(7, 1, 7, 1)` once, and later slices ride it until the next release
(D76.13). A slice that changes the grammar or the built-in catalog carries
the sync of the owner's VS Code extension (D76.12). Follow-ups that touch a
slice's files ride it only when the Gate 0 matrix shows them
semantics-preserving and the caps allow; the Phase77 handoff section of the
completion audit keeps the rest:
a project `max(a, b)` or `min(a, b)` of two `Date` values (S02), the
`let`-map differences of `first` and `last` order keys, `count_distinct` and
`stddev` beside a refused `let`, and the lost diagnostics of a `let` relation
beside a failing generator (S10), and a single-file PIE-I1000 that names
`explain --project` (S11, a text change the release notes list).

Each slice applies the technical reminders of the Gate 1 record that name
it: the E items state their semantics one by one, zero divisors and ±0
included; each `Decimal` digit bound is proven for its own operation; the
S10 examples state their types; Gate 0 checks whether S01 or S02 reads the
JOIN key and grain facts on which compiled replay and live analysis differ,
and if one does, that decision comes first; and the slices build a
composition matrix of real queries, not every permutation, which S12 checks.

**Midpoint (after the B1 head CI).** The route publication, the roadmap
cleanup, Lean Gate v3 and S01, S02, S03, S06 and S07 are on `main`
with green natural exact-head CI. Each B1
form is open after its run or refused with its code. The measured rate
projects within the caps, and CI health is read. B2 seals only after the
midpoint passes.

**Unfreeze conditions.** A slice beyond S12, a new refusal, or a change of a
public text outside the rows a slice lists needs the owner. A failed database
cell is first a question about its judge (lesson 74-1).

**Closure.** Phase76 closes when each 76-E, 76-N, 76-D, 76-T and 76-M form is
open with a passing run or refused with its code and listed in the release
notes, 76-H is done or its fallback is recorded, and the S12 commit is on
`main` with green natural exact-head CI. Phase77 then joins it in the `0.1.11`
core release, with separate approval (D76.14).

## Database runs

Each run uses the pinned local images (PostgreSQL 18.6, MySQL 8.4.12) with no
network and an engine-specific campaign lock, at most two hours each
(D76.16). At most one PostgreSQL and one MySQL container run at once, under
`/tmp/claude-1000/pietto-docker-campaign-postgres.lock` and
`/tmp/claude-1000/pietto-docker-campaign-mysql.lock`; every container uses
its fixed image ID, `--pull=never --network none`, an owned name and
`docker rm -f -v` cleanup. Its oracle is written before the run, its verdict is built only
from saved outputs, a fabricated-output self-test fails every fail-open shape,
and an independent integrity audit reads it. The S06 container runs PostgreSQL
with TLS on; its test CA and server certificate are generated locally with no
network and mounted read-only, and the private keys stay in the run
directory. After a rebase, a run's statements are emitted again and compared
byte for byte; only changed statements run again.

## Budget

Cumulative repair caps (stop and ask at any cap): C150/F450/D4400/S12
(D76.17). D counts one per diagnostic command, and a loop inside one command
counts once. Database runs, and the probe and design lines before this route,
count. Each batch push is pre-approved once Gate 2 passes on its exact tree
and `main` has not moved since the rebind: fast-forward only, with no tag,
release or PyPI upload (D76.15). While the owner is away, Gate 2 may use up to
18 pytest workers on CPUs 0–19; it returns to 12 workers on CPUs 0–11 when the
owner resumes use. Nothing is cut without asking.
