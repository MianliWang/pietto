# Phase74 route — 12 slices

Phase74 owns the Phase 74 row of the [roadmap](../../roadmap.md#future-roadmap-v6):
cross-module reuse of `def` and relationships, relationship parameters that
take the rows of a table or query, and the MySQL catch-up. It also holds two
owner additions: the backward asof JOIN on MySQL, a candidate from the start,
and new aggregates (2026-11-05), whose spelling table the owner approved on
2026-11-06. Its Gate 0 binds `main` at the Phase73 completion commit
`37143dcb` (tree `d93f9393`), whose natural exact-head CI `42277807557`
attempt 1 accepted all 21 jobs. It is the repair child of the Phase73
batch-3 head `b148fdee`, whose natural CI `42272513354` failed only one
Windows 3.12 test (a forced comparable `ctime`, now POSIX-only); that head
is kept and was not rerun. Its Gate 1 is D74.01–D74.16 in the
[decision record](../../decisions.md#phase74--owner-decisions-2026-11-05-and-2026-11-06).
Phase74 ships in `0.1.10` together with Phase73 and Phase75, after Phase75
closes, with separate approval; its batches publish to `main` with no tag or
PyPI upload in between (D74.14).

The owner let the Phase74 lines start on 2026-11-05, beside Phase73. Their
work was built on the Phase73 heads and replays onto `main`. This route is
published by an unnumbered documentation-only commit, the first Phase74 commit
on `main`. Each slice binds its exact inputs, write set, checks and acceptance
when it is integrated; this table fixes coverage, dependencies and batches
only.

## Lines

| Line | Delivers | Not included |
| --- | --- | --- |
| 74-A | `def NAME` and `relationship NAME` as items of the bare and the parenthesized import and export lists in `schema_version = 2` projects; their bindings through the existing exporter and binder; collisions refused with no winner; PIE-S2103 hints that name the export or import to write | wildcard imports, `constraint` and `derive` exports, qualified calls such as `a.pos(x)`, items in PACKAGE_ROOT package modules |
| 74-B | Relationship parameters that take the rows of a table or query, matched by field name and type; PIE-S2604 names the field that does not match; PostgreSQL and MySQL | field-name matching for source rows, positional matching, inferred paths |
| 74-M | The MySQL catch-up: project UUID ordering and `max(a, b)` and `min(a, b)` of two UUIDs, the project aggregate forms Phase73 opened on PostgreSQL, `order by` a `Float`, single-file `max(a, b)` and `min(a, b)` of two `Bool` values, and the backward asof JOIN | MySQL nested values (Phase77, D71.05); project `sum(Int)` and `stddev` of an `Int` (Phase77) |
| 74-G | `variance`, `pvariance` and `pstdev`; `all` and `any` over a group; `first` and `last` with an `order by` that ends in a unique key; `count_distinct(a, b, ...)`, as the approved spelling table writes them (D74.11) | MySQL `first` and `last` in the first version; window forms of these aggregates; `all`, `any`, `first` and `last` in a grouped query with a JOIN |

Every 74-A and 74-B form needs emission, compiled-bundle and live-template
witnesses on PostgreSQL and MySQL. Moving a def or relationship to another
module leaves the SQL bytes unchanged; that is the 74-A oracle. A project
without def or relationship items keeps byte-equal check output.

A MySQL form opens only after a passing two-database differential
(PostgreSQL 18.6, MySQL 8.4.12). A form whose differential did not pass keeps
its refusal and is listed in the release notes. `Timestamp` and `Date` `min`
and `max`, and checked signed 64-bit `Int` arithmetic, stay refused on MySQL
for this reason. A passing rerun may reopen one of them in batch 2 as a
follow-up of S04.

## Slices

| Batch | Slice | Content | Depends on |
| --- | --- | --- | --- |
| B1 | S01 | `def` import and export: the two grammar items, def bindings, inlining in import-dependency order, collisions, reserved built-in names, the PIE-P1000 texts, the PACKAGE_ROOT refusal | route publication |
| B1 | S02 | `relationship` import and export; PIE-S2103 hints for a def or relationship that another module declares, and for a qualified call | S01 |
| B1 | S03 | Relationship parameters take table and query rows, on PostgreSQL and MySQL; an imported relationship checks rows by its own module's field types | S02 |
| B1 | S04 | MySQL catch-up part 1: UUID comparison, BETWEEN, `order by` keys and `max(a, b)` and `min(a, b)` of two UUIDs in projects | route publication |
| B1 | S05 | MySQL catch-up part 2: project aggregates of `Text`, `Bool`, `Float` and `Decimal` values and over row expressions, relation `order by` a finite `Float`, single-file `max` and `min` of two `Bool` values | S04 (shared MySQL emission owners) |
| B1 | S06 | Backward asof JOIN on MySQL, in single files and projects | route publication |
| — | midpoint | exit criteria below | B1 head CI |
| B2 | S09 | `variance`, `pvariance`, `pstdev` | the approved spelling table |
| B2 | S10 | `count_distinct(a, b, ...)` | S09 (merge order) |
| B2 | S11 | `all` and `any` over a group | S10 |
| B2 | S12 | `first` and `last`, with hints for arg_max and arg_min | S11 |
| B2 | S07 | Closeout code: a two-module example in the style guide's canonical forms with its witnesses, and the acquisition consolidation | S01–S06, S09–S12 |
| B2 | S08 | Audit only: completion audit, Phase75 handoff, lessons | S07 |

S09–S12 merge in that order. Lean Gate v2 batch rules apply: one commit per
slice; one authoritative validation, one fast-forward push and natural
exact-head CI per batch; a failed head is kept and repaired by a child. The
root integrates the lanes and lands each slice's canonical forms in
[style](../../style.md) with its batch. Phase74 does not change the compiled
`VERSIONS`: the new aggregate values ride the unreleased `(7, 1, 7, 1)`
(D74.15).

**Midpoint (after the B1 head CI).** 74-A and 74-B are on `main` with their
emission, compiled and live witnesses on both databases; each B1 MySQL form is
open with a passing differential or still refused with its code; the measured
rate projects within the caps, including the reserve; CI health is read. B2
seals only after the midpoint passes.

**Closure.** Phase74 closes when 74-A and 74-B are delivered, each 74-M form
is open with a passing differential or refused with its code and listed in
the release notes, each 74-G slice is delivered, and the S08 commit is on
`main` with green natural exact-head CI.

## Budget

Cumulative repair caps (stop and ask at any cap): C170/F550/D2000/S12 for
S01–S08 (D74.16), plus C36/F110/D650 for the approved S09–S12:
C206/F660/D2650/S12 in all. Live database runs count in D. 74-A and 74-B are
never cut.
