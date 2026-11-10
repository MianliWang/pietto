# S25 independent static semantic review

Scope: `/tmp/pietto-p77-s25` against `f8ccd2c4`; inspected only.  No test,
database, formatter, build, commit, or product edit was run by this reviewer.

## Terminal

`NOT_READY_FOR_TWO_DB` until F1 and F2 are repaired and independently
re-reviewed.  No static production lowering defect was established beyond
those closure gaps.  Even after them, native MySQL validity and the two-engine
bag differential remain mandatory; emitted SQL strings are not execution
evidence.

## Confirmed preservation path

The production diff deletes only the `not target.native_full` ASOF/FULL
refusal in `sql/joins.py::render_join_sql`.  PostgreSQL invokes the same
function with `native_full=True`, so the deleted branch was unreachable there;
no other production caller supplies the MySQL `JoinTarget`.  This is a static
reachability argument, not a byte-for-byte emission witness.

For MySQL, `render_mysql_relation` first validates the whole relation under
the existing FULL rule, then `_render_mysql_full_relation` constructs the
LEFT and RIGHT prefixes using `full_as=LEFT` and `full_as=RIGHT`, with the
existing `UNION ALL` and right-only `IS NULL` filter.  Its outer stage rewrites
fields through the FULL to derived-table ports before rendering later JOINs.
Consequently, with the existing one-ASOF-per-query semantic rule:

- ASOF before a FULL is independently rendered in both prefix branches; its
  correlated key/time reads retain their pre-FULL input aliases.
- ASOF after a FULL is rendered once over the derived ports, preserving the
  full bag before the LEFT/INNER lateral choice.
- Between two FULLs, it is in the second FULL's two prefix branches and reads
  the first FULL's ports.  The second right-only filter still reads the first
  earlier key through its port.

The implementation retains `ORDER BY joined_time DESC LIMIT 1`, the declared
key/time uniqueness premise, alias quoting, `UNION ALL`, and the right-only
winner predicate.  Nothing in the static tree proves that MySQL 8.4 accepts
every nested `LATERAL`/derived-table combination, or that its optimizer
preserves the intended occurrence bag.

## Findings

### F1 — current language contract still says the newly admitted form is refused (medium)

`docs/language.md:599`, the current feature matrix and complete language
reference, says MySQL single-file ASOF is emitted “except in a relation with a
FULL JOIN (PIE-B1000)”.  The candidate removes exactly that refusal.  It edits
the diagnostic catalog and adds a release-note fragment, but neither corrects
the language contract nor provides a narrower current statement.

Required repair: update the MySQL cell at that language row to state the
candidate's actual bounded surface (single-file only; existing backward ASOF
forms and MySQL FULL emulation; native qualification still pending).  Do not
edit `docs/decisions.md`, `docs/phases/.../completion-audit.md`, or assembled
historical `docs/release-notes.md`: those correctly record the prior published
state.  Recheck the release fragment against the repaired current contract.

### F2 — static controls omit INNER ASOF in two required null-extension placements (medium verification gap)

`tests/test_sql_join_emission.py` covers ASOF LEFT and INNER only when the
FULL is before the ASOF source in the authored JOIN list (ASOF before FULL),
then covers LEFT only for ASOF after one FULL and between two FULLs.  The
semantic rule permits `asof inner join` in all three placements, and INNER is
the form that must remove a FULL right-only row when its derived left-side
ports are NULL.  Current string counts do not exercise that behavior's SQL
shape for:

- `FULL -> asof inner`, where the lateral predicate must read the first FULL
  ports and `INNER JOIN LATERAL` must drop the null-extended right-only row;
- `FULL -> asof inner -> FULL`, where that drop happens before the second
  FULL's two branches and its right-only filter.

Required repair: extend the existing parameterized SQL owner with exactly those
two INNER cases.  Assert the existing port-qualified correlation and latest
row ordering, `INNER JOIN LATERAL ... ON TRUE`, per-branch occurrence count,
and both `p2`/`p3` right-only filters.  This is not a request for a new test
owner or a new lowering.  The native campaign must then seed a matching left
row, a first-FULL right-only row, duplicate candidate history rows/tie control,
and a second-FULL right-only row, and compare the complete row bag.

## Required native evidence after static repair

Run the qualified MySQL and PostgreSQL differential with the existing actual
rendered SQL, not a reconstructed hand SQL.  Cover LEFT and INNER ASOF in the
three placements; match/no-match, NULL extension, duplicate outer occurrences,
multiple eligible history rows, declared unique latest identity, and both
right-only FULL branches.  Capture result metadata, exact row bags and
`EXPLAIN`; confirm every emitted nested LATERAL/derived-table statement is
valid.  A successful static SQL-string assertion alone cannot demonstrate any
of these runtime facts.
