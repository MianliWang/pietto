# Phase70 planning notes: external references

This file records the external references reviewed during the Phase70 phase
start. It is published with the documentation-only route publication commit and
holds only upon successful natural exact-head CI on that commit; before that it
is a candidate. The owner adopted the recommendations below; the
[decision record](../../decisions.md) holds them as D70.01–D70.11.
External behavior informs Pietto decisions but never becomes repository authority
([phase initiation gate](../../architecture/phase-initiation-gate-v1.md#external-reference-review-record);
[product design lessons](../../references/product-design-lessons-v1.md)).

Slice numbers refer to the [route](slices.md) (20 rows). The reference
identifiers R1–R4 below name external references only; they are unrelated to
the saved-result flows R1 (re-read) and R2 (same-source recovery) in the
[execution guide](../../execution.md). The roadmap
row for this phase is [Phase 70](../../roadmap.md).

## Scope and freshness

- Reviewed references: PostgreSQL 18.6, MySQL 8.4.12, the DuckDB article on
  correlated subqueries, and Neumann and Kemper, "Unnesting Arbitrary Queries".
  No other external reference informed this phase start.
- Documentation was read on 2026-10-14. The fetched pages were not archived.
  Quoted documentation text below is therefore a reading note, not a retained
  copy.
- Native observations were run on 2026-10-14 from 08:27:43Z to 08:27:51Z. The
  owner authorized them. Each target ran once in a disposable container with no
  network and tmpfs storage, and the SQL was read-only. Both containers were
  removed afterwards. The images are the
  [pinned targets](../../../tests/phase66_target_pins.json): PostgreSQL config
  digest `sha256:f372eda9…` (package `18.6-1.pgdg12+2`) and MySQL config digest
  `sha256:c9570e7b…` (`8.4.12`). The servers reported `PostgreSQL 18.6 (Debian
  18.6-1.pgdg12+2)` and `8.4.12`.
- The probes used each server's command-line client and the text protocol. They
  did not use the Pietto execution routes. PostgreSQL ran with only `TIME ZONE
  'UTC'`. MySQL ran with Pietto's `sql_mode`, `+00:00`, and
  `utf8mb4_0900_bin`. The results show target behavior only. They are not slice
  acceptance, conformance rows, or proof of Pietto semantics.
- Target pins did not drift. Emission accepts only the exact releases 18.6 and
  8.4.12, and Phase70 does not change the pins.

## R1 PostgreSQL 18.6

1. **Snapshot/date**: PostgreSQL 18 documentation read on 2026-10-14: §9.24
   subquery expressions, §4.2.11 and §4.2.14 (scalar subqueries and evaluation
   rules), Table 9.69 (series-generating functions), and §7.2.1.3–5 (table
   functions and LATERAL). Native observation on the pinned 18.6 image on
   2026-10-14.
2. **Problem/constraints**: PostgreSQL is a real execution target. Phase70 needs
   its semantic boundaries for scalar, EXISTS, IN, LATERAL, VALUES, and
   `generate_series`. Performance is out of scope.
3. **Semantic/identity model**:
   - **Scalar subquery.** Zero rows give NULL. More than one row is a data-dependent error,
     observed as `21000 more than one row returned by a subquery used as an
     expression`. Outer references act as constants during one evaluation.
   - **EXISTS.** The result depends only on whether a row exists.
   - **IN and NOT IN.** Both are three-valued. `NULL IN (empty)` is `false` and
     `NULL NOT IN (empty)` is `true`. `1 IN (SELECT NULL)` and
     `2 NOT IN (1, NULL)` are NULL, and so is `NULL IN (SELECT 1)`. The
     documentation is internally inconsistent about the NULL-left/empty-right
     case, so the native result decides it.
   - **Default column names.** A table function returning a base type gets one
     column named after the function. With the alias `AS n` that column is `n`.
     VALUES columns default to `column1…`.
4. **Layering/dependency direction**: LATERAL may reference only FROM items to
   its left. The keyword is optional for function calls. Both
   `LEFT JOIN LATERAL … ON true` and `CROSS JOIN LATERAL` were observed. The LEFT
   form extends with NULL when nothing matches.
5. **Algorithms/data structures/complexity**:
   - LATERAL is evaluated once for each row that supplies it.
   - EXISTS evaluation stops once a row is found.
   - The order of subexpression evaluation is undefined, and some subexpressions
     may never be evaluated. CASE does not guard against constant folding or
     against an aggregate being evaluated first.
   - Correlated `EXISTS` and `NOT EXISTS` were planned natively as `Hash Semi
     Join` and `Hash Anti Join`.
6. **Interface/version/capability model**:
   - **Release.** Pietto pins the exact release 18.6. At runtime it requires
     `server_version` 180006.
   - **`generate_series` overloads.** It has integer, bigint and numeric
     overloads. `generate_series(1, 2, 1)` resolves to `integer`. Explicit
     bigint arguments resolve to `bigint`.
   - **Step and NULL arguments.** A step of zero fails with `22023 step size
     cannot equal zero`. A NULL argument returns zero rows, and so does an
     argument pair in the wrong direction.
   - **Upper limits.** A series of 1,048,576 rows and a two-row series that
     reaches bigint max both completed.
   - **Not read.** The exact type-resolution rule text.
7. **Testing/operational lifecycle**: Evidence for a supported shape comes from
   the existing isolated target conformance facility and natural CI. Each Phase70
   feature slice adds rows to the per-shape PostgreSQL matrix. The phase-start
   probes stay advisory.
8. **Pitfalls/migration costs**:
   - A VALUES column that is all NULL is inferred as `text`.
   - The default VALUES names differ from MySQL's.
   - `generate_series` returns zero rows on NULL input without an error.
   - The multi-row error is data-dependent.
   - Not verified here: whether RIGHT JOIN LATERAL and FULL JOIN LATERAL are
     prohibited, and whether a server-side parameter works in LIMIT.
   - Each new emitted variant adds to the target conformance receipt.
9. **Disposition**: `ADAPT`. This is the source of target behavior and of
   counterexamples for the PostgreSQL route. Pietto's own contract still decides
   semantics.
10. **WHAT_NOT_TO_COPY**:
    - implicit LATERAL;
    - `ROWS FROM`, `WITH ORDINALITY`, and set-returning functions in the select
      list;
    - type inference for unknown literals or all-NULL VALUES columns;
    - relying on default column names;
    - relying on CASE or AND ordering to avoid errors;
    - side-effecting functions;
    - planner strategy;
    - accepting a NULL `generate_series` argument as silently empty;
    - `statement_timeout` as a substitute for a static row bound.
11. **Pietto owner affected**:
    - S06: VALUES column aliases and types.
    - S07: scalar.
    - S08: EXISTS.
    - S09: IN and NOT IN.
    - S12 and S13: LATERAL.
    - S14: correlated combinations.
    - S15: `generate_series`.
    - S16: documentation and diagnostics catalog.
    - S17: joint acceptance.
    - Deep adaptation: Phase76.

## R2 MySQL 8.4.12

1. **Snapshot/date**: MySQL 8.4 Reference Manual read on 2026-10-14: §15.2.15.10
   (subquery errors), §15.2.15.12 (subquery restrictions), §15.2.15.1 (scalar
   subqueries), §15.2.15.9 (lateral derived tables), §15.2.19 (VALUES), and
   §10.2.2.3 (EXISTS optimization). Native observation on the pinned 8.4.12 image
   on 2026-10-14.
2. **Problem/constraints**: MySQL is a real execution target. Its shape
   restrictions mean that "valid in the language" and "emittable for the target"
   have to be decided separately.
3. **Semantic/identity model**:
   - **Scalar subquery.** Zero rows give NULL. More than one row fails with
     `ERROR 1242 (21000) Subquery returns more than 1 row`, which is
     data-dependent.
   - **IN and NOT IN.** `NULL IN (empty)` is `0` and `NULL NOT IN (empty)` is
     `1`. `1 IN (SELECT NULL)` and `2 NOT IN (1, NULL)` are NULL. These match
     PostgreSQL.
   - **Default column names.** VALUES uses `ROW(…)` and its columns default to
     `column_0…`.
4. **Layering/dependency direction**:
   - LATERAL appears only in FROM.
   - A table on the right may reference one on the left only through INNER,
     CROSS or LEFT joins. MySQL also allows left-to-right references in RIGHT
     JOIN, and Pietto does not support that direction.
   - `JSON_TABLE()` is always implicitly lateral.
   - Both `LEFT JOIN LATERAL … ON TRUE` and `CROSS JOIN LATERAL` were observed,
     with the same results as PostgreSQL.
5. **Algorithms/data structures/complexity**:
   - A lateral derived table is brought up to date for each preceding row.
   - IN uses guarded conditions for NULL correctness, which may cost a full scan.
   - Correlated `EXISTS` and `NOT EXISTS` were planned natively as `Nested loop
     semijoin` and `Nested loop antijoin`.
6. **Interface/version/capability model**:
   - **LIMIT in IN subqueries.** `LIMIT` written directly inside an `IN` or
     `NOT IN` subquery fails with `ERROR 1235 (42000) This version of MySQL
     doesn't yet support 'LIMIT & IN/ALL/ANY/SOME subquery'`. `IN` over a CTE
     or a derived table that contains `LIMIT` is accepted, and so are `EXISTS`
     and a scalar subquery with `LIMIT`. All of these observations used
     non-correlated shapes. A correlated relation refers to the outer row, so it
     cannot be hoisted into a top-level CTE, and its `IN` form was not observed.
   - **Column aliases.** The alias lists `AS v(x, y)` and `AS t(a, b)` are
     accepted.
   - **LIMIT placeholders.** A SQL-level `PREPARE … LIMIT ?` worked. That result
     is informational only, because Phase70 parameters never reach LIMIT.
7. **Testing/operational lifecycle**: Pietto runs MySQL with server-side
   prepare under a fixed `sql_mode`. Supported shapes are proven by the target
   conformance facility and natural CI. The phase-start probes stay advisory.
8. **Pitfalls/migration costs**:
   - Error 1235 appears only when the statement is prepared, so Pietto must never
     emit the direct shape.
   - A correlated `IN` or `NOT IN` over a relation with `LIMIT` has no CTE shape.
     Phase70 refuses it on MySQL instead of wrapping it.
   - The default VALUES names differ from PostgreSQL's.
   - Mixed-type VALUES is permissive.
   - Not verified here: the type MySQL infers for an all-NULL VALUES column,
     whether EXISTS can be NULL on MySQL, whether other correlated shapes are
     rewritten by the optimizer, and how many times stored functions with side
     effects run.
9. **Disposition**: `ADAPT`. This is the source of evidence for target
   restrictions and NULL semantics. It does not widen Pietto semantics.
10. **WHAT_NOT_TO_COPY**:
    - mixed-type VALUES or implicit conversion;
    - `column_0` as a user-visible name;
    - the implicit lateral of `JSON_TABLE`;
    - optimizer switches;
    - wrapping the direct LIMIT shape to get around 1235;
    - treating "doesn't yet support" as a promise of future support.
11. **Pietto owner affected**:
    - S06: VALUES aliases; queries with no physical source are rejected on MySQL.
    - S07: scalar.
    - S09: closed IN with LIMIT, emitted only as a top-level CTE.
    - S14: correlated IN or NOT IN over a relation with LIMIT is refused on MySQL
      and allowed on PostgreSQL.
    - S12 and S13: LATERAL.
    - S14: correlated combinations.
    - S16: support matrix.
    - S17: joint acceptance.
    - Deep adaptation, including wrappers and `JSON_TABLE`: Phase77.

## R3 DuckDB, "Correlated Subqueries in SQL"

1. **Snapshot/date**: duckdb.org blog article, read on 2026-10-14. Attributed
   date and author: 2023-05-26, Raasveldt. No DuckDB version is pinned or
   observed.
2. **Problem/constraints**: Correlated subqueries executed naively cost O(n²).
   DuckDB decorrelates every subquery automatically. Pietto is not an optimizer
   and makes no speed promise.
3. **Semantic/identity model**: The dependent join is the semantic primitive.
   The engine may introduce join types that do not exist in SQL.
4. **Layering/dependency direction**: Rewriting happens inside the engine's plan
   algebra, below the SQL surface.
5. **Algorithms/data structures/complexity**: Generalized unnesting is presented
   as reaching about O(n) in the ideal case.
6. **Interface/version/capability model**: DuckDB is not a Pietto target. It is
   absent from the dependency closure. DuckDB adaptation belongs to Phase79.
7. **Testing/operational lifecycle**: Pietto does not run DuckDB. Its own oracle
   for any rewrite would be an independent BAG oracle together with a check that
   no outer reference remains in the generated SQL.
8. **Pitfalls/migration costs**: The reviewed material does not cover NULL-aware
   rejoin, MARK join, or the COUNT bug. Neither PostgreSQL nor MySQL has SEMI
   JOIN syntax. Any rewrite changes which rows are evaluated, so it would depend
   on effects and totality evidence that Phase70 opens only for one table
   function.
9. **Disposition**: `ADAPT`, as background only. It supports the view that
   general decorrelation is an engine or optimizer concern. Nothing from it is
   consumed as a Pietto mechanism in the route.
10. **WHAT_NOT_TO_COPY**:
    - general or automatic decorrelation;
    - mark, single, or dependent joins as public operators;
    - performance figures;
    - DuckDB as a target in this phase.
11. **Pietto owner affected**:
    - S16 documents that narrow decorrelation is moved out.
    - DuckDB target work: Phase79.
    - Rewrites: Phase88 (logical optimizer) and Phase93 (formal rewrite
      certification).

## R4 Neumann and Kemper, "Unnesting Arbitrary Queries"

1. **Snapshot/date**: Read on 2026-10-14. The source was the authors' BTW 2015
   presentation slides (PDF metadata: Thomas Neumann and Alfons Kemper,
   2015-03-05, 21 pages). The paper's bibliographic record was seen as search
   metadata only (LNI P-241, pp. 383–402). The full paper text was not read.
2. **Problem/constraints**: Unnest correlated subqueries of any shape so that
   they avoid quadratic execution. Pietto borrows only a correctness argument.
3. **Semantic/identity model**:
   - Dependent join: `{t1∘t2 | t1∈T1 ∧ t2∈T2(t1) ∧ p(t1∘t2)}`.
   - General rewrite: `T1 ⋈dep T2 ≡ T1 ⋈_{p∧T1=_{A(D)}D} (D ⋈dep T2)`, where
     `D := Π_{F(T2)∩A(T1)}(T1)`.
   - D is a set, so the outer bindings are deduplicated. Outer multiplicity is
     preserved by the final join back to `T1`.
   - Equality EXISTS reduces to a semijoin once its predicates are pulled up.
4. **Layering/dependency direction**: Works on the relational algebra, not on
   SQL text.
5. **Algorithms/data structures/complexity**: D is pushed down until the inner
   side no longer depends on the outer side. `|D| ≤ |T1|`.
6. **Interface/version/capability model**: Pietto consumes no interface from
   this work, and no version applies.
7. **Testing/operational lifecycle**: A future rewrite would need an independent
   BAG oracle, a check that no outer reference remains, and effects evidence.
8. **Pitfalls/migration costs**: Deduplicating outer rows instead of bindings
   loses multiplicity. The reviewed material does not cover NULL-aware rejoin or
   the COUNT bug. Rewrites change the evaluated rows.
9. **Disposition**: `ADAPT`, narrowly. Two parts are taken: the equivalence of
   the simple semijoin, and the law that bindings are deduplicated while outer
   rows are not. General unnesting is not adopted.
10. **WHAT_NOT_TO_COPY**:
    - generalized unnesting;
    - public dependent, mark, or single join operators;
    - cost-based derivation of D;
    - complexity claims.
11. **Pietto owner affected**:
    - S14 must preserve outer duplicate rows in correlated combinations, which
      matches this law.
    - Rewrites are deferred to Phase88 and Phase93 (D70.06). A future rewrite
      owner consumes this record.

## Impact on Phase70 decisions

| Owner decision | Basis | Disposition |
| --- | --- | --- |
| A scalar subquery gives NULL for zero rows and its value for one row. More than one row is a runtime database error, and Pietto adds no `LIMIT 1`. The public form keeps [`PIE-R3003`](../../spec/diagnostics.md) with SQLSTATE `21000` (D70.04). | R1, R2: both targets report `21000` | ADAPT |
| IN and NOT IN over a subquery use three-valued logic and match the existing literal-list `in` ([language](../../language.md)). `NOT IN` is not rewritten to ANTI. | R1, R2: `NULL IN (empty)` is false on both targets | ADAPT |
| EXISTS is never NULL. Pietto does not promise which written expressions the database evaluates, or in what order runtime errors arise. Every written expression is still checked statically. | R1: evaluation order undefined | ADAPT |
| IN may read a closed local relation (one without `capture`) that has `LIMIT`. Pietto emits that relation as a top-level CTE, and the direct `IN (… LIMIT …)` shape is never generated. A correlated relation with `LIMIT` read by IN or NOT IN is refused on MySQL and allowed on PostgreSQL (D70.05). | R2: 1235 for the direct shape; non-correlated CTE and derived shapes accepted | ADAPT (no wrapping workaround) |
| VALUES requires a typed header, and emitted SQL always carries a column alias list. Pietto never relies on `column1` or `column_0`. | R1, R2 | ADAPT |
| LATERAL uses explicit `capture` and an explicit keyword in emitted SQL, and references only from left to right. CROSS, INNER and LEFT `ON true` are supported. | R1, R2 | ADAPT |
| Table functions are limited to PostgreSQL `generate_series`. Pietto emits `pg_catalog.generate_series` with explicit bigint arguments. Arguments must be static, non-NULL literals, a step of zero is rejected at compile time, and rows have an upper bound. There is no runtime catalog check (D70.05). MySQL is unsupported, and `JSON_TABLE` is not a substitute. | R1: integer overload is the default, `22023` for step zero, NULL gives zero rows | ADAPT |
| Narrow decorrelation is moved out of Phase70 and handed to Phase88 and Phase93. The owner approved this roadmap scope change (D70.06). | R1, R2: small probes show native semi and anti join plans; the execution benefit of a rewrite was not measured, and the decision rests on semantic scope and optimizer ownership, not performance; R3 | REJECT for Phase70 (D70.06) |
| Correlated combinations preserve outer duplicate rows. Any future rewrite deduplicates bindings only. | R4 | ADAPT |
| The target pins stay at PostgreSQL 18.6 and MySQL 8.4.12 ([execution](../../execution.md)). | R1, R2 | unchanged |
