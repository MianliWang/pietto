### Decimal and Int arithmetic and signs in fourteen MySQL project forms

A MySQL project now emits a `Decimal` plus or minus an `Int` in either
order, a `Decimal` plus or minus a `Decimal` of another scale, a `Decimal`
times an `Int` in either order and a unary `+` or `-` of a `Decimal` in a
statement that is, byte for byte, one of the fourteen forms that the
Phase77 qualification pack pairs across PostgreSQL 18.6 and MySQL 8.4.12,
with only its names changed. One of them is:

```pietto
shape Row:
    id: Int
    flag: Bool | None
    text: Text
    money: Decimal(9, 2)
    ratio: Float

source rows: Row = mysql.table("app.rows")

table result:
    from rows
    select:
        added = money + id
        subtracted = money - id
```

- Nine other forms hold the same shape and source and a `table result`
  from `rows` that selects `added = id + money` and
  `subtracted = id - money`, or one item `result = money * id`,
  `result = id * money`, `result = money * 2`, `result = -money`,
  `result = +money` or `result = -(money * id)`; or the shape with
  `ratio: Decimal(8, 3)`, selecting `added = money + ratio` and
  `subtracted = money - ratio`; or the shape with `money: Decimal(46, 30)`,
  selecting `result = money * id`. As in the pack, such an item's label is
  the definition's own name. The last four forms hold the first shape and
  source and a `query result(factor: Int)` from `rows` that selects
  `total = money + factor`, `total = factor - money`,
  `total = money * factor` or `total = factor * money`; the pack runs each
  with the arguments 7, 9223372036854775807 and -9223372036854775808.
- MySQL writes each operation without a result cast, as `(a + b)`,
  `(a * CAST(2 AS SIGNED))` or `(-a)`, and the header parameter as the
  server parameter `CAST(? AS SIGNED)`. Each result takes the carrier a
  PostgreSQL project takes ([project guide](../project-package.md#emission-rules)):
  `my_decimal(22, 2)` for a sum or difference with an `Int`,
  `my_decimal(28, 2)` for a product with an `Int`, `my_decimal(11, 3)` for
  the two scales and `my_decimal(65, 30)` for the wide product; a sign
  keeps its operand's carrier, `my_decimal(9, 2)` for a field and
  `my_decimal(28, 2)` for `-(money * id)`. MySQL itself declares the result
  column of the four forms with a header parameter one digit wider, as
  `DECIMAL(23, 2)` or `DECIMAL(29, 2)`; every value fits the stated
  carrier. A binary operation's column is `nullable` `unknown`, and a sign
  keeps its operand's. Compiled bundles and live templates replay the same
  SQL. PostgreSQL SQL is unchanged.
- The rest must match too. The project has that one module, which holds
  only the shape, the source and that one definition (empty lines aside),
  and the literal policy is `preserve`. The emission contract is the pack's:
  target `mysql` `8.4.12`; the statement premises `client_encoding`
  `utf8mb4`, `operator_environment` `builtin_only` and `identifier_case`
  `lower_case_table_names=0`, and for the four forms with a header
  parameter then `parameter_protocol` `mysql_prepared`, in that order; one
  source entry with the pack's field representations (`my_bigint`,
  `my_bool01`, `my_varchar` of length 64 in `utf8mb4_0900_bin`, the
  shape's `my_decimal` and `my_double` or `my_decimal(8, 3)`) and the
  premises `row_domain_matches` and `read_only_object`. A name (of the
  module file, the shape, a field, the source, the definition, the header
  parameter, a label, the physical namespace, the table or a column) is an
  ASCII identifier of at most 63 bytes that does not start with `__pietto`
  in any case; a `mysql.table` locator is two such names joined by a dot.
  Two names that are both columns, both tables, both namespaces, both
  locators or both Pietto names are equal, also ignoring case, exactly
  where the form's are. A word the forms use as a keyword, such as `table`,
  `select` or `Decimal`, is no name there, and a name the SQL quotes may
  not be one the SQL also generates, such as `s0`.
- Every other MySQL project statement with such an operation keeps its
  whole `0.1.11` output, and so does a paired statement whose emission does
  not give its form's SQL, names aside. `load_bundle` keeps its `0.1.11`
  refusal, PIE-R1004 `COMPILED_PHYSICAL_DOMAIN`, or `COMPILED_UNARY_DOMAIN`
  for a sign of a field, of every other bundle with such a MySQL operation,
  also of one whose records are a form's but whose SQL is not. R2
  `save_recoverable` and `recover` refuse a paired query with PIE-R1004
  `PUBLIC_R2_PAIRED_FORM`, as for the other paired forms.
- The native qualification passed on 2026-11-14. The PostgreSQL half of
  the pack ran once on 2026-11-13 and was accepted: run
  `20261113T214055Z-72eabeeffb3e386dc9825de4` (verdict `pass` true, no
  reason) bound this change as first committed on the S14, S11, S10 and
  S16 changes (tree `d455776d`). The MySQL half's first run, on the same
  tree, failed only on the native length of the four header-parameter
  forms' total column, which its package had derived from the public
  carrier, while MySQL 8.4.12 takes `CAST(? AS SIGNED)` into `Decimal`
  arithmetic as 20 integer digits; the SQL and every value matched. That
  run is kept and carries nothing. The MySQL half was frozen again as a
  changed experiment with MySQL's own lengths and ran once: run
  `wave-a-mysql-20261114T005229Z` (acceptance `pass` true, no reason)
  bound this change rebased onto the S14, S11 and S08 changes (tree
  `c059e5c4`), where D77.50 carried the PostgreSQL run, and the two runs
  pair all 22 pairs of the pack's S17 to S19 scope. D77.50 carries both to
  the commit that integrates this change: the records both halves' compile
  steps export, the 83 forms of the PostgreSQL pack and the 27 MySQL forms
  and controls, are identical there apart from the harness's install
  identity and the MySQL record's clock (the sha256 of each record as
  sorted-key JSON without its `identity` field and, for MySQL, its
  `started` and `finished` times, first 16 digits, the same on both sides:
  `b523f386dfc68ddd` and `1545fd52f5781fbf`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the fourteen forms above with only its names changed | for each SELECT item, `arithmetic_requires_signed_int_operands` for a sum or difference with an `Int`, `decimal_scale_mismatch` for the two scales, `binary_operator_not_admitted` for a product, also under a sign, and `unary_sign_requires_int_operand` for a sign of a field | none: the definition emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |
