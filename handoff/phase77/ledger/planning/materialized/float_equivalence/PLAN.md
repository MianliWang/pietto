# Phase77 S06/S07: MySQL Float equality/equivalence raw plan

## Status and boundary

This is a non-canonical planning artifact only.  It authorizes no database
run, compiler edit, document change, release, or claim of PASS.

The fixed value contract is `finite binary64`: `-0.0 == 0.0`, while their
bits remain distinct in transport and UNION ALL.  GROUP BY, DISTINCT,
equality, sets, and `count_distinct` use that one equality law.  A merged
GROUP/DISTINCT/set row must carry the complete tuple of some class member;
which member is unspecified.  In particular, a rewrite must not normalize a
zero, manufacture a tuple by choosing each Float column independently, or
alter a NULL rule, projection origin, bag multiplicity, or UNION ALL bits.

Current evidence is deliberately negative for MySQL 8.4.12:

- GROUP BY, DISTINCT, and UNION DISTINCT split the two zero encodings when a
  Float shares a `VARCHAR(1000)` (or wider) key.  A `VARCHAR(64)` observation
  merged them, but is not a general qualification.
- INTERSECT and EXCEPT compare the encodings as different.
- Phase72 B10 records a materialized semijoin over a wide key that returned an
  outer occurrence twice.  Joins and narrow-key cases matching zero do not
  qualify this different plan shape.

### Recovered evidence and remaining B10 gap

The actual Phase72 raw source is
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/claude-closeout-017-20261103/phase72/b72-0/DB-MATRIX.md`:

- §0 records the MySQL 8.4.12 image, default and Pietto-target session modes,
  raw SQL/output locations, and native client procedure.
- §C defines `z_n = {-0}` and `z_p = {+0}`, using `-0e0` for MySQL, and gives
  the actual set SQL/results plus the `Intersect materialize with
  deduplication` observation.
- Phase72 Lane E's `design-contract.md`, Stage 0 M1/M2, is an unexecuted
  extension design: M1 specifies `VARCHAR(1000)`/`VARCHAR(16383)` dedup
  witnesses and M2 spells `SELECT ... FROM z_n WHERE v IN (SELECT v FROM z_p)`.
  It is not evidence that this SQL reproduced B10.

I searched the retained Phase72 `b72-0`, Lane E, campaign, and `w5` receipt
paths for the B10 phrase, a semijoin/materialization plan, and a wide-key raw
statement.  They retain the documented conclusion but not the exact B10 SQL,
optimizer switches/hints, EXPLAIN, seed vector, or output.  Therefore no
artifact here claims a historical B10 replay.  Before any candidate is judged,
recover that exact record from its external ledger; copy its *exact* statement,
engine version, session settings, seed readback and `EXPLAIN` into the run
receipt.  Do not replace it with guessed optimizer controls.

## Shared raw fixture and observation record

Each engine owns an isolated table set with parameterized inserts; no Float
literal is evidence of negative zero.  Seed via the DBAPI with Python floats,
then immediately read the rows back.  Record every seeded/read Float with
`float.hex()` (including `-0x0.0p+0` and `0x0.0p+0`), rather than using an SQL
hash, a string key, or a driver display format as an equality key.

```
eq_wide(id BIGINT NOT NULL, f1 DOUBLE NULL, text_key VARCHAR(1000) NULL,
        f2 DOUBLE NULL, payload BIGINT NOT NULL)
eq_narrow(id BIGINT NOT NULL, f1 DOUBLE NULL, text_key VARCHAR(64) NULL,
          f2 DOUBLE NULL, payload BIGINT NOT NULL)
eq_left(id BIGINT NOT NULL, f1 DOUBLE NULL, text_key VARCHAR(1000) NULL,
        f2 DOUBLE NULL)
eq_right(id BIGINT NOT NULL, f1 DOUBLE NULL, text_key VARCHAR(1000) NULL,
         f2 DOUBLE NULL)
```

`W` is one exactly 1000-character value and `N` one 64-character value.
Use the same values in every row for a class; a second wide value separates a
nonzero control class.  The minimal discriminating zero rows are
`(-0.0, W, +0.0)` and `(+0.0, W, -0.0)`.  They are one equality class but no
source row has `(-0.0, W, -0.0)` or `(+0.0, W, +0.0)`, so an independent
per-column representative is detectable.  Add exact duplicates of both,
one `NULL`-containing tuple, one all-NULL Float pair, and finite nonzero rows.
Run 0, 1, and many-member variants, plus the same data in a different insert
order.  Keep the seed vectors, native column metadata, warnings, exact SQL,
parameters, rows/bag, `float.hex()` bits, terminal error (if any), and
EXPLAIN output in every raw record.

The independent oracle is in memory only:

- equality canonicalizes only the sign of a zero; NULL is handled by the
  particular operation's existing three-valued/null-safe rule;
- it computes each output bag/class cardinality from source occurrences;
- for a merged visible row, it accepts its complete Float/non-Float tuple
  only when that exact bits tuple is a source member of the corresponding
  equality class (and rejects a column-wise synthetic tuple);
- UNION ALL compares output occurrence bits exactly, with no equality
  canonicalization.

Metadata and seed readback are mandatory: a row count alone cannot establish
the carrier or a negative-zero result.

`raw_hook.py --selfcheck` validates the static, finite raw-request manifest
without a connection.  `raw_hook.py --request` prints the M1/M2-inspired
wide-key SEMI/ANTI request for the engine parent to bind to an already-approved
endpoint/resource lease.  It never imports a DBAPI or starts a container.  Its
request is explicitly a new discriminating witness, not the unrecovered B10
statement.

## Raw shape matrix

| Slice/form | Pietto-source shape to compile after raw SQL qualification | Native SQL/probe shape | Oracle assertions |
| --- | --- | --- | --- |
| S06 row equality | `where left.f1 == right.f1`; same-row `f1 == f2`; `!=`; `not (f1 != f2)` | inner JOIN and same-row WHERE with two row reads | true/false/NULL per occurrence; both zero signs equal; no changed sign in transported selected Float |
| S06 null-safe equality | `same_value(left.f1, right.f1)` and same-row form | MySQL `<=>`, separately from `=` | NULL/NULL true; NULL/non-NULL false; non-NULL zero equality; Bool is non-null |
| S06 semijoin/anti | correlated `exists`/`any` and its anti form with Float + wide Text correlation | exact recovered B10 materialized SEMI/ANTI statement and plan, with right duplicates and both zeros | every outer occurrence appears once or zero times as specified; no duplicate outer id; ordinary JOIN/narrow control reported but never substitutes |
| S07 GROUP | `group by f1, text_key, f2; select f1, text_key, f2, count()` | `GROUP BY f1, text_key, f2` for wide, narrow, Float-only, and multi-Float key cases | equality-class group count; NULL group; one whole-row key representative; 0/1/many and insert-order variants |
| S07 DISTINCT | `select distinct: f1, text_key, f2` | `SELECT DISTINCT f1, text_key, f2` | one row per equality class, whole-row representative, no invented sign combination |
| S07 scalar count | `count_distinct(f1)` globally and within a wide-key GROUP | `COUNT(DISTINCT f1)` in both scopes | zero counts once; NULL excluded; wide outer grouping is tested separately from the global aggregate |
| S07 tuple count (preparation only) | `count_distinct(f1, text_key, f2)` | `COUNT(DISTINCT f1, text_key, f2)` | tuples containing any NULL excluded; Float equality per position; no S11 project admission follows from a raw result |
| S07 sets | `union all`, `union distinct`, `intersect all/distinct`, `except all/distinct` over `(f1, text_key, f2)` | corresponding explicitly parenthesized native set statements | UNION ALL bit-exact bag; other forms use union presence, min(left,right), or max(left-right,0) per equality class; every merged tuple is an actual contributing member |
| downstream check | a GROUP/DISTINCT/set output read by a later SEMI/ANTI or a second relation | two-layer native SQL using the exact output shape | same bag/representative test after the second layer; no source-order or plan-sensitive assumption |

For every line run both engines against the same parameterized fixture.  A
PostgreSQL result is a differential reference, not the sole oracle.  Capture
the target's native metadata and warnings before decoding, and classify each
cell as observation, terminal error, or failed invariant--not a blanket family
PASS.

## Candidate lowering disposition

No candidate is selected yet.

1. Keep native `=`/`<>` and `<=>` as the only S06 expression spelling under
   test.  `CASE`, `COALESCE`, string/bit conversion, and zero normalization
   are not candidates: they change NULL or zero/transport semantics.  Current
   B10 evidence means a broad `rows_both_sides=False` relaxation is unsound.
2. Native MySQL GROUP/DISTINCT/UNION DISTINCT is a known counterexample.  A
   rewrite that groups normalized Float keys and uses `MIN`/`MAX` per selected
   Float field is rejected in advance: the crossed-zero fixture can make an
   absent whole row.  A window partition/row-number rewrite is also unselected
   until its own wide-key partition behavior and complete-row representative
   proof exist; it would be new relational machinery, not a local guard flip.
3. Native INTERSECT/EXCEPT is a known counterexample.  A target-only emulation
   would need occurrence identity, whole-row representatives, NULL semantics,
   left-fold nesting, and ALL multiplicities.  No such lowering may be added
   as a generic backend framework or a hash/string-concatenated tuple key.
4. The existing MySQL UNION ALL path stays untouched and bit-preserving.
   The direct `COUNT(DISTINCT Float)` spelling is a separately testable narrow
   candidate only; its global observation cannot admit grouped, joined, wide
   key, or tuple forms.  Tuple count remains S11-gated.

Consequently the minimal outcome after an unsuccessful or incomplete campaign
is *no code change*: retain existing MySQL blockers and the successful native
transport/order/UNION ALL paths.  Opening any subset requires the owner to
state the merged-row representative rule is exactly the existing contract,
then a lowering/shape-specific proof that all rows, bits, NULLs and bags above
survive.

## Integration closure if evidence supports a bounded opening

Do not implement from the renderer alone.  Rebind these existing owners on the
actual integration tree, and edit only owners required by the approved shape:

- S06 admission: `project_sql_emission_rows.py` comparison and `same_value`
  realization, plus renderer only if a reviewed expression changes.  Preserve
  `rows_both_sides` through plan, live, compiled, and independent verification.
- S07 GROUP/count: `project_sql_emission_aggregation.py` group-key and MySQL
  Float aggregate gates.
- S07 DISTINCT: `project_sql_emission_results.py::distinct_problem` and its
  result-boundary verifier.
- S07 set: `project_sql_emission_sets.py`, set rendering, independent
  set-column realization, and the pure/compiled/portable set readers if and
  only if a retained equivalence representation changes.
- Test owners, extended in place: `tests/test_sql_rows.py`,
  `tests/test_sql_joins.py`, `tests/test_sql_grouped.py`,
  `tests/test_sql_result_bounds.py`, `tests/test_sql_set_forms.py`,
  `tests/test_project_numeric_carriers.py`, and
  `tests/test_execution_compiled_families.py`.  Native qualification belongs
  in the existing execution/qualification owner, not a phase-named test.

PostgreSQL outputs/bytes and every current MySQL refusal outside the explicit
approved shape are compatibility controls.  Raw native SQL success is not
compiler, emitted-SQL, compiled, reader, Gate2, or CI evidence.

## Unresolved items requiring owner/evidence closure

- The exact Phase72 B10 raw record is required to reproduce and assess the
  materialized-semijoin trigger; no guessed optimizer forcing is acceptable.
- The owner must decide whether any MySQL merged-zero shape can meet the
  existing whole-row representative obligation.  This is
  `USER_DECISION_REQUIRED`, not an emitter choice.
- No threshold can be inferred from `VARCHAR(64)` versus `VARCHAR(1000)`.
  The observations delimit witnesses, not a static safe-width policy.
- `count_distinct` tuple admission is outside S06/S07's implementation scope
  unless S11 authority changes; raw tuple evidence does not alter that fact.
