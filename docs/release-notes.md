# Pietto release notes

## Unreleased changes following 0.1.5

These notes cover changes after the published 0.1.5 release. They do not
assign a new version or replace the published 0.1.5 release notes.

### Refinement

- **R2 and a trailing `any`.** `save_recoverable` and `recover` accept a
  trailing `where any(...)` or `where not any(...)`, alone or AND-composed
  with other filters, including the migration of a last `semi join` or `anti
  join`. R2 refines it as the semi or anti JOIN it represents and qualifies
  the source columns that its predicate and another block's operands read.
  An `any` under `or`, in a `select` item, over a let with `capture` lines, or
  whose predicate reads another block is still `PIE-R1004`
  (`REFINEMENT_EXPRESSION_BLOCK_READ`). SQL, CLI and JSON shapes are unchanged.

### Checking and diagnostics

- **Phase71 nested-relation spellings (batch B1).** `name = collect let_name`
  in a `select:` block and `let o = unnest(binding.field)` read by a later
  CROSS, INNER or LEFT JOIN are recognized. In an EXPLICIT_MODULES project
  (`schema_version = 2`) they are typed, and every Collect read and Unnest let
  then reports `PIE-S2802` until later Phase71 work lowers them; single files,
  LEGACY_FLAT projects and package modules report `PIE-S2801`, which says how
  to make a `schema_version = 2` project. A user `def` named `collect` or
  `unnest` keeps its ordinary meaning, and syntax errors keep their code,
  order and position.
- The bounded D-11 unmatched-row and one-key-value proofs and D-12 typed-NULL
  numeric rules described in the language reference are now accepted. Cases
  outside those proofs remain refused; `min`, `max` and `count_distinct` do
  not gain a general fan-out exemption.

- `Text(Int)`, `round` and `date_trunc` are now closed scalar forms. `Text`
  accepts only Int; another input type is `PIE-S2105`. `round` accepts Decimal
  with an optional literal or `let`-expanded scale from -30 to 30, or one Float
  argument; `date_trunc` accepts literal units year/month/day for Date and
  additionally hour/minute for Timestamp. A `let`-expanded scale or unit is
  read also where the call is a project select item. A project Date is
  obtained with `date_of(Timestamp)`. Unsupported arity or scalar shapes are
  `PIE-S2104`.
- `string_agg(value, delimiter, order by key[, key ...])` is a PostgreSQL
  aggregate with explicit, preserved internal ordering. Without its internal
  ORDER BY it is `PIE-S2104` (`expected ORDER BY key`) in single files and
  projects. In a single file an argument of only `None` values, also a
  conditional whose branches are only `None`, is `PIE-S2104` too (`expected
  two Text arguments`); an explicit-module project refuses it with the bare
  `PIE-S2333`, or `PIE-S2315` with JOIN inputs. MySQL and window use fail
  closed. Over a source without a shape it is an aggregate projection like
  `max`: beside another projection, a window included, without GROUP BY it
  is `PIE-S2312`, and `emit-sql` refuses it with `PIE-B1000`, as it refuses
  every aggregate over such a source.
- An aggregate called with an extra argument of only `None` values, such as
  `sum(id, None)` or `max(id, coalesce(None, None))`, is `PIE-S2309`
  (`Aggregate function sum expects 1 arguments, got 2`) in single files and
  LEGACY_FLAT projects, as with an extra typed argument. 0.1.5 accepted it at
  `check`, and `emit-sql` refused it with `PIE-B1000`.

- Handwritten `on` equalities can prove the same at-most-one match as a
  relationship predicate. Single files use declared source keys. Projects also
  use a key that a query carries through only `select`, a `where` without
  `any(...)`, `order by` and `limit`; the key of a query with GROUP BY, an
  `any(...)` filter, a window, QUALIFY, `select distinct`, a JOIN or a FROM
  over a query block does not yet prove an `on` match (a grouped query's key
  still protects its own GROUP BY). Matching a nullable unique key in
  `on` is allowed, while using a key as GROUP BY protection still requires
  non-null fields. A key proof does not prove a match exists. Fan-out errors
  name the JOINs that can repeat the aggregate's input, and suggest matching
  only keys that `on` can prove.
- `PIE-S2383` warns when WHERE rejects the NULL-extended side of a LEFT JOIN;
  `PIE-S2384` warns about `not in` with a nullable left value. An explicit
  `None` list option retains the separate `PIE-S2107` warning.
- `PIE-S2385` warns about known single-file emission limits. PostgreSQL and
  MySQL both refuse RANGE offsets; effective `ignore nulls` or `from last`; a
  FULL JOIN `on` conjunct that is not an equality between Int fields of its
  two sides, such as a non-Int equality, a filter, `<`, `True` or an `or`;
  and a FULL JOIN after a pending `where any(...)` or `where not any(...)`.
  In a relation whose FROM does not end at a `mysql.table` source it also
  warns about untyped all-NULL outputs read by another relation or by the
  relation's own QUALIFY, which reads them through a derived table;
  operators over `None` only (`None + None`); a CASE, `coalesce` or `nullif`
  of only `None` values where text cannot stand, a QUALIFY condition
  included; a cast of a value not known to be Int that reads no field of
  unknown type; a `count` of a field typed by a shape; a `substr`, `ntile`,
  `lag`, `lead` or `nth_value` integer literal outside the 32-bit range; and
  a CTE that would hide a table read by the same statement. MySQL emits an
  untyped all-NULL output that another relation reads, except a field read
  after a FULL JOIN, which it refuses without this warning. A relation with
  an error gets none of the expression or CTE warnings. Warnings do not
  change the check exit status; existing errors remain errors.
- `check --project` in an explicit-module project reads a field of a shape,
  also through a `let` name, after a JOIN, in the WHERE, `let` and
  `any(...)` of a `select distinct` query and as a captured field, as that
  shape, as single files do: `home + 1`, `-work`, `len(work)` or
  `lower(o.ship)` over such fields are PIE-S2105 or PIE-S2104. 0.1.5
  accepted them in a WHERE, a `let` or an `any(...)` and refused a select
  item with the bare PIE-S2333; `lag(h)` or `h is None` for `let h = home`
  now pass where 0.1.5 reported PIE-S2333. Without JOIN inputs a select item
  that tests such a field directly, such as `b = home is None` or
  `b = home == work`, and a select item of a `select distinct` query, where
  a project types no select item yet (`x = name + 1` is the bare PIE-S2333
  there too), are still the bare PIE-S2333, as in 0.1.5. The ungrouped
  `order by` of a relation without JOIN inputs that is not `select distinct`
  reads such a field as that shape too (`order by home + 1` is PIE-S2105),
  but a project still types no other part of that `order by`, so
  `order by name + 1` for a Text `name` passes `check --project`; project
  emission refuses it.
- A one-line set-operation body such as `union all a, b` may be followed by
  blank lines, as a block body may; 0.1.5 reported PIE-P1000
  (`Unexpected end of line; expected end of block.`) at the blank line.
- A simple legacy `== null` or `!= null` comparison now suggests `is None` or
  `is not None` directly. `migrate` still refuses output that the modern
  parser cannot accept.
- In a single file, an `any(...)` predicate that reads a field of the FROM row
  of a source without a shape, such as `items.id` in
  `any(o.item_id == items.id for o in orders)`, is PIE-S2102
  (`Unknown or unavailable field in ANY predicate: items.id`). 0.1.5 accepted
  it at `check`, and `emit-sql` and `explain` stopped with PIE-I1000. So is
  a read of an output of no type, such as `o.x` in
  `any(o.x == items.id for o in t)` for `x = None` of `t`, which 0.1.5 also
  accepted at `check`.
- Some programs that 0.1.5 refused with a diagnostic that pointed at the wrong
  problem now report the problem itself. They are still refused, and no other
  program or SQL output changes:
  - A `let` that a later JOIN reads as its input, as in `let c = customers`
    before `inner join c on ...`, names a relation, as `from` does. When its
    value names no relation, such as a relation that the module does not
    import or a misspelled name, it is PIE-S2301 `Unknown relation: <name>` at
    the value, in single files and projects, and when it names a `let`
    declared after it, PIE-S2330
    (`Let binding cannot reference a later binding: <name>`). 0.1.5 reported
    PIE-S2604 (`A row-value let must follow FROM and every JOIN and precede
    WHERE`) at the `let`. A value that names a field visible there, a query
    header parameter or an earlier `let` keeps PIE-S2604.
  - In a single file, such a `let` of a set-operation query, such as
    `let b = both` for a `query both:` whose body is `union all a, a`,
    reports two PIE-S2334,
    at the set operation
    (`Set operations are available only when an EXPLICIT_MODULES project
    (schema version 2) completes them.`) and at the JOIN
    (`Set-operation inputs are available only when an EXPLICIT_MODULES project
    (schema version 2) completes them: both`), where 0.1.5 reported
    PIE-S2604. A `schema_version = 1` project no longer adds PIE-S2604 to its
    two PIE-S2334, and an explicit-module project still accepts the program.
  - The value of `lag`, `lead`, `first_value`, `last_value` or `nth_value`,
    and a `lag` or `lead` default, that names a `let` whose value is not a
    field, such as `let k = amount + 1` or `let k = 1`, is PIE-S2104 at the
    call: ``Invalid arguments for function lag: value must be a direct field
    or Bool, Text, Int, Float, or NULL literal, not the `let` name k``
    (`default must be` for a default). 0.1.5 reported PIE-S2102
    `Unknown field: k` at the argument, although `k` is defined. This holds in
    single files and in projects, except that an explicit-module project still
    reports the bare PIE-S2333 for `let k = None`. A `let` whose value is a
    field, such as `let k = amount`, still reads that field.
  - A JOIN `on` that calls an unknown function with JOIN inputs as its
    arguments, such as `inner join customer on nosuch(orders, customer)`,
    reports PIE-S2103 `Unknown function: nosuch` alone: the inputs are row
    arguments of the call, not ON references. 0.1.5 also reported a PIE-S2335
    `JOIN ON reference is unknown: <input>` for each such argument in a single
    file, and in an explicit-module project reported PIE-S2334 (`JOIN-local ON
    is available only when an EXPLICIT_MODULES project (schema version 2)
    completes it.`) and such a PIE-S2335 without the name instead of
    PIE-S2103. A `schema_version = 1` project, which has no JOIN, is unchanged.
    In an explicit-module project, when the name is a relationship that only
    other files declare, the message adds
    `order_customer is a relationship of models.pietto, which a module cannot
    import: declare it in this module`.
- In a single file, a SELECT item of a relation with GROUP BY that names a
  `let` binding (PIE-S2102 `Unknown field: <name>`, or PIE-S2329 for a binding
  selected by its own name) adds what to write: the field, for a binding of a
  field that a GROUP BY key groups by
  (``Unknown field: key; a query with GROUP BY cannot select a `let` name here
  yet: write status in place of key`` for `let key = status`); an
  explicit-module project, for a computed binding that is a GROUP BY key
  (``a query with GROUP BY cannot select a computed `let` value here yet:
  group by it and select it in an EXPLICIT_MODULES project (schema version
  2)``); otherwise `<name> is not a GROUP BY key`. A GROUP BY key that names a
  computed `let` adds ``a query cannot group by a computed `let` value here
  yet: group by it in an EXPLICIT_MODULES project (schema version 2)``. Codes
  and locations are unchanged.

- EXPLICIT_MODULES projects read a FROM input through its alias and its
  original name: after `let c = customers` and `from c`, `c.id`, which 0.1.5
  refused with PIE-S2102 `Unknown field: c.id`, and `customers.id` name the
  same input occurrence in every clause but HAVING and the ORDER BY of a
  grouped query, which read no qualified input field (the bare PIE-S2333, as
  in 0.1.5, also without an alias).
  0.1.5 accepted `customers.id` in WHERE, GROUP BY, an ungrouped ORDER BY and
  a grouped SELECT, refused it in a
  row-value `let` with PIE-S2102 (`Unknown field: customers.id`) and stopped
  with an internal error (`inconsistent_scope_relation`) on it in an
  ungrouped SELECT. The original name is read only in a query without a JOIN and
  outside `any(...)`; intermediate aliases and `any`, capture and JOIN scopes
  still refuse it, as 0.1.5 did.

- A legacy INNER, LEFT, RIGHT, FULL or CROSS JOIN written with `as` now has a
  PIE-P1000 suggestion for its own JOIN kind; a CROSS JOIN suggestion has no
  `on`. The `migrate` PIE-P1011 for a legacy `semi join` or `anti join` with
  `as` names its `where any(...)` or `where not any(...)` rewrite. These are
  corrections to 0.1.5's migration guidance; codes and locations are unchanged.
- A diagnostic inside an `any(...)` or `not any(...)` filter before a later
  JOIN names the authored binder, including unknown, ambiguous and nested
  reads, rather than a generated binding.

- An IN/NOT IN list of an enum value and its labels, such as
  `status in ("paid", "shipped")`, is accepted and emitted as written. Before,
  it was `PIE-S2105` while the same list with a `None` option passed. A Text
  literal operand likewise takes the type of a Date, Timestamp, UUID, Bytes or
  Json value, also as the left value of an EXPLICIT_MODULES `in` read of such
  a column or an enum column; a literal that is not a label, such as
  `status in ("paid", "gone")`, is still refused.
- Three new warnings, in every check mode, for spellings a Python reader
  misreads; programs still check and emit as before. `PIE-S2106`: `/` of two
  Int values truncates (`7 / 2` is 3); write `Float(x) / y`. `PIE-S2107`: a
  `None` option of an `in` list never matches (and makes `not in` never
  true); write `x == "a" or x is None`. `PIE-P1009`: `--` is two minus
  signs, not a comment (`100 -- 50` is 150); write `#`. The semantic two are
  reported in single files and LEGACY_FLAT projects, `PIE-P1009` wherever
  source is parsed except `migrate`. Programs that assert an empty
  diagnostic list or empty stderr for such source now see the warning.
- `pietto.semantic.analyze` refuses an AST that carries the legacy JOIN
  fields with PIE-S2378, and the legacy JOIN codes PIE-S2601 to PIE-S2603 are
  retired and not reused.

### SQL emission

- Single-file reads of a table or query now include its SQL as a dependency
  CTE. An unsupported dependency also prevents SQL for its reader; the old
  `PIE-S2382` warning is retired. Text output names each statement with a
  `-- name` line and terminates it with `;`; JSON artifact SQL is unchanged.
- Single-file `QUALIFY` now checks and emits for PostgreSQL and MySQL,
  including hidden windows. Its filter follows the window stage and precedes
  ORDER BY and LIMIT; ambiguous input/selected-output names are refused.
  Under GROUP BY it reads the GROUP BY keys and selected outputs only
  (PIE-S2102 otherwise, also for a `let` whose `any(...)` reads another
  field); with aggregates and no GROUP BY it reads selected outputs and `let`
  names that read no input field, and a hidden window there is PIE-S2103.
  These hold over a source without a shape too, whose fields it reads by
  name; over such a source a name that a SELECT output has reads that output,
  and any other name, a `let` value's fields included, reads the input
  through a private derived-table port. Under GROUP BY over such a source
  `check` accepts a selected or hidden window, as 0.1.5 accepted both, and
  `emit-sql` refuses the relation with PIE-I1000. A window under GROUP BY,
  hidden or selected, reads the selected keys and aggregates by their
  output names; a name that an output shares with an input field whose
  value it is not, such as `cat` for `cat = max(price)` grouped by `cat`, is
  PIE-S2102 (`Ambiguous field: cat is both the input field items.cat and a
  SELECT output; give the output another name`), where 0.1.5 read the
  output. An aggregate call
  in the QUALIFY condition is PIE-S2308; read the aggregate through its selected alias. Its ambiguity
  message offers the qualified input name only where QUALIFY can read it.
  PostgreSQL emission refuses, with PIE-B1000, a QUALIFY that reads an
  untyped all-None output or whose condition is a CASE, `coalesce` or
  `nullif` of only `None` values, which PostgreSQL reads as text through the
  derived table; check warns with PIE-S2385, and MySQL emits it.
  A MySQL statement that reads a QUALIFY relation ends its CTE, when it has
  no `limit`, with `LIMIT 18446744073709551615`, which keeps every row and
  makes MySQL compute its windows once, however often the statement reads it.
- Over a source without a shape, an ORDER BY key that reads an input field,
  named alone or through a `let`, is qualified with the name FROM gives the
  input where a SELECT item would capture it, as over a source with a shape:
  `order by price` beside `Price = 0 - price` emits
  ``ORDER BY `items`.`price` `` on MySQL, and `order by p` with `let p =
  price` beside `price = 0 - price` emits `ORDER BY "items"."price"`. 0.1.5
  emitted the bare name, which both targets read as the SELECT output.
- PostgreSQL single files support `sum`, `count`, `avg`, `min`, and `max` as
  window aggregates, with their ordinary argument and logical result
  contracts. An omitted frame keeps SQL's default: ordered peer-inclusive
  accumulation, or the whole partition without ORDER BY. GROUPS requires
  ORDER BY. A `let` name bound to `None` as the argument is PIE-S2315, and a
  `let` name whose value is no field as a partition or order key is PIE-S2103,
  as for other windows; over a source without a shape every aggregate window
  outside GROUP BY that reads a field, `count(x) window()` included, is
  PIE-S2103 (`count() window()` reads none and is accepted), and a `count`
  window of a field typed by a shape is PIE-S2104. Project aggregate-window
  support is not introduced; for MySQL see Single-file MySQL parity.
- Single-file PostgreSQL windows can read JOIN inputs, including named
  specifications and hidden QUALIFY windows, while retaining input identities
  and the visibility limits of existence filters.
- MySQL refuses, with PIE-B1000 at that statement, a reader whose CTEs have
  names that differ only by case, a statement that would define as a CTE a
  table or query with two outputs whose names differ only by case, and a
  QUALIFY whose derived table would hold two such outputs; a top-level SELECT
  keeps them. Each name Pietto generates into a statement (an `any(...)`
  alias, a hidden SEMI or ANTI JOIN alias, a QUALIFY output or derived
  table) now skips, on both backends, a name it would capture that differs
  from it only by case: 0.1.5 aliased the EXISTS of
  `any(o.price == _Pietto_Value_1.price for o in orders)` over
  `from _Pietto_Value_1` as `_pietto_value_1`, which MySQL with
  `lower_case_table_names` 1 or 2 reads as that outer row, so the EXISTS
  compared each order with itself.
- An ORDER BY key that reads a SELECT output by its name (a selected window
  result, or an output over a row of unknown type) is emitted as that
  output's SELECT list position beside an unaliased item, which PostgreSQL
  and MySQL each name by rules of their own, and on MySQL beside another
  output whose name differs from it only in case: `order by n` beside `" n"`
  and `n = row_number() window(order by id)` emits `ORDER BY 2`. 0.1.5
  emitted `` ORDER BY `n` ``, which MySQL sorts by the unaliased `' n'`, as it
  names that item `n`, and `ORDER BY "lower"` beside `lower(cat)`, which
  PostgreSQL rejects as ambiguous. Beside an unaliased item an input field
  key is now qualified on MySQL too, as PostgreSQL already qualified it:
  0.1.5 left `order by price` bare beside `" price"`, so MySQL sorted by that
  constant.
- A CTE gives each unaliased output (PIE-S2304) a private alias
  `__pietto_column_<n>`, which no name the statement selects or reads takes,
  in any case, so a read of another output never binds to the name the
  database would give the unaliased one, such as `lower` for `lower(cat)` or
  for a CASE whose ELSE is `lower(cat)` in PostgreSQL, or `price` for
  `" price"` in MySQL; the relation's own statement keeps the output
  unaliased.
- A statement that reads a table or query of the same file by a name that
  relation gives no output, such as `lower` for an unaliased `lower(email)`
  over a source without a shape, is refused by `emit-sql` with PIE-B1000 on
  PostgreSQL and MySQL, at the reading relation (``Its SQL reads lower from
  relation a, which names no output lower; if it means the unaliased output
  at line 6, column 9, which has no name a reader can use, write `lower = ...`
  there to name it``); `check` still accepts it, as its fields are of unknown
  type. An ORDER BY key such as `Z` beside an output `z`, or `z + 1`, reads
  the relation, not the output, and is refused the same way. 0.1.5 read the
  name the database gives the unaliased output, and emitted a read of a name
  no output has, which the database rejected.

### Single-file MySQL parity

Single-file `emit-sql --dialect mysql` now emits the following forms that
PostgreSQL emits, each with the same matches, duplicates and NULL-extended
rows under each target's own comparison rules. A form without such a MySQL
8.4 spelling is still refused with `PIE-B1000`, and PostgreSQL SQL is
unchanged. As in the MySQL SQL emitted before, the place of NULLs in an
ascending or descending order, Text comparison under the column's collation,
and the type and scale of an aggregate's result follow MySQL. Project MySQL
emission is unchanged.

- **JOINs.** INNER, LEFT, RIGHT and CROSS JOINs, every `on` form,
  relationship and `def` calls in `on`, self-JOINs, JOIN chains, a JOIN of a
  table or query of the same file (read as a CTE), `any` and `not any` filters
  before a later JOIN, `any` inside `on`, `where` or `select`, and the ordinary
  tail after a JOIN. The pending-filter rules are PostgreSQL's: the next RIGHT
  JOIN takes a pending filter into its `on`, else it leads the `where`.
- **Windows, QUALIFY, GROUP BY and aggregates over JOIN rows**, as
  PostgreSQL emits them.
- **FULL JOIN** within PostgreSQL's FULL JOIN limits (only `Int` field
  equalities across its two sides, no pending `any` filter). MySQL has no
  FULL JOIN, so the inputs through it become a derived table `__pietto_full`
  (`__pietto_full2`, ... beside an alias of that name in any case): the LEFT
  JOIN, then UNION ALL the RIGHT JOIN rows whose first earlier-input key is
  NULL. A field read after it whose type is not builtin or is `Any`, such as
  an enum, is refused, and so is a relation with more than 8 FULL JOINs, as
  each repeats the inputs before it. Other FULL JOINs keep PostgreSQL's two
  refusals, worded for MySQL, which come before these two for every FULL JOIN
  of the relation; the old `MySQL JOIN emission is not available yet` refusal
  is gone.
- **Aggregate windows.** `sum`, `count`, `avg`, `min` and `max` windows,
  direct, named, over grouped rows, in QUALIFY and over JOIN rows, with the
  grouped MySQL aggregate contract (`SUM` of Int is DECIMAL, `avg` of Int
  casts to DOUBLE). A sliding Float `sum` or `avg` frame assumes MySQL's
  default `windowing_use_high_precision = ON`. As with a grouped `sum`, an
  Int `/` of a `sum` that PostgreSQL holds as `numeric`, such as one over a
  `bigint` column, truncates on MySQL but not yet on PostgreSQL.
- **Window frames.** A GROUPS frame without an offset bound is written as the
  same RANGE frame, and an authored EXCLUDE NO OTHERS is left out. GROUPS with
  an offset bound (`MySQL does not support GROUPS frames with an offset`) and
  EXCLUDE CURRENT ROW, GROUP or TIES (`MySQL does not support EXCLUDE CURRENT
  ROW, GROUP or TIES`) stay refused.
- **`round(Float)` and `date_trunc`.** `round` of a Float rounds a tie away
  from zero with `TRUNCATE` arithmetic, as MySQL's own `ROUND` of a DOUBLE may
  not. It refuses Float arithmetic without a DOUBLE operand in its argument,
  such as `round(amount + 0.5 - 0.00000000000000001)` with an Int `amount`,
  which PostgreSQL computes as `numeric` and MySQL may not, and a read of a
  Float relation output, such as a CTE column, that is not such a DOUBLE;
  `date_trunc` of a Date or Timestamp is built from the value's parts, so a
  unit other than `day`, which repeats the value, refuses a value that holds
  another `date_trunc`.
- **Aliases that differ only in case.** A MySQL JOIN statement with two input
  or `any` aliases whose names differ only in case is refused, as MySQL may
  compare aliases without case: `Its SQL aliases inputs <first> and <second>,
  whose names MySQL may compare without case; rename one of them`. PostgreSQL
  emits them.
- `string_agg`, `matches`, `ignore nulls`, `from last` and RANGE offsets stay
  refused on MySQL.

### Command startup

- Help, version and single-file commands start faster. Running without a
  subcommand still prints help and exits 0.

### Python execution

- `pietto[execute-mysql]` now installs `mysql-connector-python==26.10.0`
  instead of `26.7.0`, and the `mysql_rows` route accepts only `26.10.0`: an
  environment that keeps `26.7.0` is refused with `PIE-R2002` before any
  connection. The connector's connection, protocol, cursor, network and
  authentication modules that `mysql_rows` uses are unchanged in `26.10.0`.
  Its parameter conversion changed only for character sets whose multibyte
  characters can contain `0x5c` (`big5`, `sjis`, `gbk`, and newly `cp932` and
  `gb18030`); the `utf8mb4` connection that `mysql_rows` opens quotes
  parameters as before.

## Modern-syntax public alpha release notes — 0.1.5

**Status:** These notes cover the `0.1.5` public alpha, published from
`6d0f6c6c` on the versioned GitHub pre-release and PyPI. Both channels carry the
accepted wheel and sdist byte for byte; this document neither creates those
channels nor substitutes for their byte verification.

`0.1.5` is the first release whose compiler reads the modern source syntax. It
also contains the single-file JOIN support and the
[fix batch 7](#fix-batch-7-following-014-included-in-015) changes; the fix
batch 7 section keeps the 0.1.4 spelling in its examples. The sections from
0.1.4 down describe published files.

### Highlights

- **Modern source syntax.** `None`, `True` and `False`; `T` for a value that
  is never None and `T | None` for one that may be; `source name: Shape = ...`;
  single-line clauses without a colon; one `let` per name; shape-typed
  relationship predicates; and `any(predicate for row in relation)`.
- **`pietto migrate`** writes the modern form of a 0.1.4 file to stdout, or
  names each place that needs a manual decision.
- **Single-file JOINs.** `check` and PostgreSQL `emit-sql` accept INNER, LEFT,
  RIGHT, FULL and CROSS JOINs and `any`/`not any` filters over the sources,
  tables and queries of one file, within the
  [single-file JOIN limits](language.md#single-file-joins).
- **Diagnostics teach the modern spelling.** Each retired spelling is
  PIE-P1000 with its exact rewrite in the message.

### Upgrading a 0.1.4 file

Each spelling that the modern syntax retires is a syntax error (PIE-P1000)
whose message ends with the rewrite, such as
`This spelling is not accepted by the modern syntax. Write 'is None' or 'is not None'.`;
JSON output carries the rewrite as the diagnostic's `suggestion`. A
`pietto NUMBER` header does not select a syntax, and no flag restores the old
one. To convert a file, write the result to a new file and check it:

```bash
pietto migrate old.pietto > migrated.pietto
pietto check migrated.pietto
```

`migrate` never edits its input. It writes one complete source to stdout only
when the result passes the modern parser; otherwise it exits 1, writes nothing
to stdout and reports PIE-P1011 at every place that needs a decision, in
source order. It keeps comments, strings, line endings and a leading BOM, and
it neither checks SQL backend capability nor connects to a database. It
changes only what it must, so its output keeps the old layout around each
rewrite (for example an indented empty line where a `let:` header was);
`check` the result and tidy it by hand. Compiled bundles and saved-job records
are not source and are not migrated.

For example, this 0.1.4 file:

```text
shape Order:
    id: Int not null
    customer_id: Int not null
    amount: Int not null
    note: Text nullable

source orders: Order is postgres.table("orders")

query customer_totals:
    from orders
    where: amount between 100 and 500 and note is not null
    group by: customer_id
    select:
        customer_id
        total = sum(amount)
        n = count()
    satisfying: n > 1
    order by: customer_id
```

migrates to:

```pietto
shape Order:
    id: Int
    customer_id: Int
    amount: Int
    note: Text | None

source orders: Order = postgres.table("orders")

query customer_totals:
    from orders
    where 100 <= amount <= 500 and note is not None
    group by customer_id
    select:
        customer_id
        total = sum(amount)
        n = count()
    having n > 1
    order by customer_id
```

`migrate` also turns `null`, `true` and `false` into `None`, `True` and
`False`, a `let:` block into one `let` per name and `cast(x as Float)` into
`Float(x)`. It needs a manual decision (PIE-P1011) for a 0.1.4 JOIN written
with `as`, including `semi join` and `anti join`, and for a source-bound
`relationship` with endpoints: write `let name = relation`, a JOIN with `on`
or a [relationship predicate](language.md#named-inputs-and-reusable-relationship-predicates)
instead. A `schema_version = 1` project with such JOINs also needs
`schema_version = 2` (see
[legacy-flat projects](#legacy-flat-projects-and-relationship-joins)).
[Migrating old source](language.md#migrating-old-source) lists every rule.

### Syntax changes

Each example shows 0.1.4 source, then the source this release reads, except
where it says otherwise.

#### A bare type is never None

0.1.4 had three nullability states: `T not null`, `T nullable` and a bare `T`
of unknown nullability. Now `T` is never None and `T | None` may be None;
`not null` and `nullable` are PIE-P1000. `migrate` rewrites `T not null` to `T`
and both `T nullable` and a bare `T` to `T | None`, so it never adds a claim
that a value is not None: drop each `| None` it added to a bare type where the
column is in fact never NULL. A `type` alias names a type that is never None:
write `Email | None` where a field is declared. A `nullable` alias base needs
manual migration (PIE-P1011), and so does a bare type in a source that the
modern syntax also accepts, whose meaning changed, or that mixes 0.1.4
spelling with modern spelling that `migrate`'s reader of 0.1.4 source cannot
read, such as `T | None` (that reader also reads some modern spelling, such as
`source name: Shape = ...`, which does not count): `migrate` cannot tell which
syntax such a bare type was written for, so it never adds `| None` to it.

```text
shape User:
    id: Int not null
    nickname: Text
    email: Text nullable

source users: User is postgres.table("users")

table user_contacts:
    from users
    select:
        id
        nickname
        email
```

```pietto
shape User:
    id: Int
    nickname: Text | None
    email: Text | None

source users: User = postgres.table("users")

table user_contacts:
    from users
    select:
        id
        nickname
        email
```

#### Names after `select`

`select` may list a `let` name directly, and outside a grouped query an
`order by` key written as one name may name a SELECT output, as grouped
queries and `having` already could. A key that names both an input field and a
SELECT output of another value is now ambiguous (PIE-S2102) instead of
silently reading the input field: `migrate` qualifies such a 0.1.4 key
(`order by order_lines.quantity`) where the FROM input is a source of the same
file with that field in its shape, keeps it where that source has no shape or
its shape lacks the field, and asks for a decision (PIE-P1011) over JOIN
inputs or any other FROM input.
A single-file query with GROUP BY still cannot select a `let` name
(PIE-S2329). Without GROUP BY, project SQL cannot yet order by a SELECT output
other than a window result (PIE-B1003 at `emit-sql --project`, or PIE-S2102 at
`check --project` with JOIN inputs).

In 0.1.4 one value needed two names:

```text
query biggest_lines:
    from order_lines
    let:
        total_cents = price_cents * quantity
    select:
        id
        line_total = total_cents
    order by:
        total_cents desc
```

```pietto
shape OrderLine:
    id: Int
    price_cents: Int
    quantity: Int

source order_lines: OrderLine = postgres.table("order_lines")

query biggest_lines:
    from order_lines
    select id, total_cents = price_cents * quantity
    order by total_cents desc
```

`let total_cents = price_cents * quantity` with `select id, total_cents` is
the same query.

#### `any` and `not any` replace `semi join` and `anti join`

`semi join` and `anti join` are PIE-P1000. Write
`where any(predicate for row in relation)` or `where not any(...)`: before a
later JOIN the filter keeps the rows at that point, and after the last JOIN it
is the relation's WHERE. Both emit the same correlated `EXISTS` or
`NOT EXISTS`. 0.1.4 wrote every `semi join` and `anti join` with `as`: such a
JOIN is PIE-P1000 at its `as`, suggesting the `where any(...)` or
`where not any(...)` rewrite. `migrate` rewrites only `semi join x on p` and
`anti join x on p` themselves, written without `as`; one without `on`, and
each one written with `as`, is refused with PIE-P1011 (see
[migrating old source](language.md#migrating-old-source) for every case). The
explicit-module whole-relation read `exists name` is unchanged. See the R2
limitation under [known limitations](#known-limitations).

0.1.4 accepted this query only in an explicit-module project (a single file
reported PIE-S2334 at the JOIN); its modern form also checks as a single file:

```text
query customers_without_orders:
    from customers
    anti join orders as o:
        from customers
        on o.customer_id == customers.id
    select:
        id
        name
```

```pietto
shape Customer:
    id: Int
    name: Text

shape Order:
    id: Int
    customer_id: Int

source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")

query customers_without_orders:
    from customers
    where not any(o.customer_id == customers.id for o in orders)
    select id, name
```

#### Named windows come before `select`

A named window is a `let name = window(...)` among the lets after FROM and
every JOIN, before `where`, `group by` and `select`; one declared after
`select` is PIE-P1000 (`Move the window before 'select', ...`). Windows share
the `let` namespace: a window named like a value `let` or an input alias is
PIE-S2604, and a window may not take the name of an input relation or input
field (PIE-S2329). `migrate` moves a window declared after `select`, with its
comment lines, to the end of the lets, and asks for a decision (PIE-P1011)
when its name clashes.

```text
query ranked:
    from accounts
    select:
        id
        position = row_number() window ordered
    window ordered:
        order by:
            id
```

```pietto
shape Account:
    id: Int
    account_id: Int

source accounts: Account = postgres.table("accounts")

query ranked:
    from accounts
    let ordered = window(order by id)
    select:
        id
        position = row_number() window ordered
```

#### One-line forms

An `enum` may list its members on its header line after `:`; the indented
form remains, and an enum header without `:` is PIE-P1000. A `def`,
relationship predicate, `constraint` or `derive` body may follow its header on
the same line. A `qualify:` block joins its lines with `and`, as `where:` and
`having:` do.

```text
enum Status:
    active
    suspended
```

```pietto
enum Status: active, suspended

shape Item:
    id: Int
    status: Status
    price: Int

source items: Item = postgres.table("items")

query top_items:
    from items
    where status == "active"
    select id, price
    qualify:
        row_number() window(order by price desc) <= 3
        price > 0
```

Single-file QUALIFY is checked but not lowered: `explain` and `emit-sql` still
refuse it with PIE-I1000.

#### Diagnostics teach the modern spelling

Messages name only modern spelling and state the fix within the diagnostic's
one line of text output. The fan-out remedies of
PIE-S2381 and PIE-S2333 no longer suggest grouping by a unique key, which
compiles but changes the result's grain.

0.1.4 for `where email == null`:

```text
users.pietto:9:11 PIE-S2105 error: Invalid operands for operator ==: comparison with null is never true; write `is null` instead
```

This release for `where email == None`, then for `where email is null`:

```text
users.pietto:9:11 PIE-S2105 error: Invalid operands for operator ==: comparison with null is never true; write `is None` instead
users.pietto:9:20 PIE-P1000 error: This spelling is not accepted by the modern syntax. Write 'is None' or 'is not None'.
```

```pietto
shape User:
    id: Int
    email: Text | None

source users: User = postgres.table("users")

table missing_email:
    from users
    where email is None
    select id
```

#### Reading a table or query of the same file warns

Single-file SQL emits each table and query as its own statement, so a `from`,
a JOIN or an `any(...)` before a later JOIN that reads a table or query of the
same file reads it by name: that SQL runs only where the database already has
a relation of that name. Each such read is now a PIE-S2382 warning in every
check mode; an explicit-module project emits the relation it reads as a CTE.
Any other `any(...)`, such as one after the last JOIN, defines the relation it
reads as a CTE of the reader's SQL and has no such warning.
The text output of `emit-sql` is unchanged in this release (see
[deferred to the next release](#deferred-to-the-next-release)).

0.1.4 checked such a file, written in its spelling, without a diagnostic.
This example is in the spelling of this release:

```text
shape Order:
    id: Int
    amount: Int

source orders: Order = postgres.table("orders")

table large_orders:
    from orders
    where amount > 100
    select id, amount

query large_order_ids:
    from large_orders
    select id
```

now reports:

```text
orders.pietto:13:5 PIE-S2382 warning: `large_orders` is a table of this file; single-file SQL reads it by name, so the SQL runs only where the database already has a relation named large_orders (an EXPLICIT_MODULES project emits it as a CTE)
```

Reading the source directly needs no such relation:

```pietto
shape Order:
    id: Int
    amount: Int

source orders: Order = postgres.table("orders")

query large_order_ids:
    from orders
    where amount > 100
    select id
```

### Single-file JOINs

No published release emits a single-file JOIN: 0.1.4 refused JOIN forms in
single files (PIE-S2334 at `check`, or PIE-I1000 at `explain` and
`emit-sql`), and the support merged after 0.1.4 spelled JOINs the 0.1.4 way.
This release offers them in modern spelling. Name each JOIN input with `let` and give every
JOIN but CROSS an `on`:

```pietto
shape Customer:
    id: Int
    name: Text
    customer_key = unique(id)

shape Order:
    id: Int
    customer_id: Int
    amount: Int

source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")

relationship OrderCustomer(order: Order, customer: Customer): order.customer_id == customer.id

query orders_per_customer:
    from orders
    let customer = customers
    inner join customer on OrderCustomer(orders, customer)
    group by customer.name
    select:
        customer_name = customer.name
        order_count = count(orders.id)
```

PostgreSQL `emit-sql` writes one flat SELECT with every input aliased by its
name; `any` filters become correlated `EXISTS` or `NOT EXISTS`. MySQL
`emit-sql` refuses each JOIN relation (PIE-B1000) and keeps the file's other
SQL; `explain` refuses each JOIN relation (PIE-I1000), as its metadata
format has one input per relation. Windows over JOIN rows and ORDER BY after an
ungrouped aggregate are PIE-S2334, PostgreSQL FULL JOIN needs Int equalities
in `on`, and a JOIN of a source without a shape is PIE-S2334.

An aggregate other than `count()` must not read rows that a JOIN may repeat
(PIE-S2381). The relationship call above proves that each order matches at
most one customer, because its equality matches the declared key
`customer_key`. The same equality written by hand in `on` proves nothing yet:

```text
orders.pietto:23:23 PIE-S2381 error: An aggregate may read rows that a JOIN repeats; match a declared unique key of customer whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first
```

[Single-file JOINs](language.md#single-file-joins) and
[Aggregates and grouping](language.md#aggregates-and-grouping) give the
complete rules.

### Legacy-flat projects and relationship JOINs

0.1.4 checked relationship JOINs in a legacy-flat project
(`schema_version = 1`): a JOIN such as `inner join customers as customer`
matched through a declared relationship, a JOIN `via` a relationship, and the
other forms written with `as`. They are no longer available. This release
names each JOIN input with `let` and states its condition with `on`, and a
legacy-flat project checks no JOIN and no `any(...)` of this syntax. Each
JOIN, of any kind and whatever its target, is one PIE-S2334 at its `on`, a
relationship call included, or at the JOIN when it has no `on`, with the text
``JOIN customer: a schema_version = 1 project has no JOIN in the current syntax; set schema_version = 2 to check it.``;
each `any(...)`, before a JOIN or after it, nested or not, in any clause, is
one PIE-S2334 at the `any(...)`, with the text
``any(...): a schema_version = 1 project has no any(...) in the current syntax; set schema_version = 2 to check it.``;
they come in source order. 0.1.4 refused this spelling of JOIN and `any(...)`
with PIE-P1000, so this refusal removes nothing that 0.1.4 accepted. A
legacy-flat project never emitted SQL, so no SQL changes. To check such a
project again:

1. Rewrite each JOIN and each relationship with endpoints in the current
   spelling; `migrate` reports each of them with PIE-P1011 and writes no
   source for the file.
2. Set `schema_version = 2` in `pietto.toml`.
3. In a project of several files, make each module import what it reads from
   another module, which exports it, and declare each relationship in the
   module whose JOINs call it, as a relationship is not imported (see
   [project and package](project-package.md#schema-compatibility)).

For example, this file of a 0.1.4 `schema_version = 1` project:

```text
shape Order:
    id: Int not null
    customer_id: Int not null

shape Customer:
    id: Int not null
    name: Text not null

source orders: Order is postgres.table("orders")
source customers: Customer is postgres.table("customers")

relationship order_customer: orders.customer_id == customers.id

query order_names:
    from orders
    inner join customers as customer
    select:
        order_id = orders.id
        customer_name = customer.name
```

is written as follows in a `schema_version = 2` project, where it also checks
as a single file:

```pietto
shape Order:
    id: Int
    customer_id: Int

shape Customer:
    id: Int
    name: Text

source orders: Order = postgres.table("orders")
source customers: Customer = postgres.table("customers")

relationship OrderCustomer(order: Order, customer: Customer): order.customer_id == customer.id

query order_names:
    from orders
    let customer = customers
    inner join customer on OrderCustomer(orders, customer)
    select:
        order_id = orders.id
        customer_name = customer.name
```

### Explicit-module JOIN diagnostics

In an explicit-module project, a JOIN whose `on` has an error of its own, such
as the invalid operand of `on orders.customer_id == -customer.name`
(PIE-S2105), or whose relationship call fails now reports only that error,
once. For that example 0.1.4 also reported PIE-S2334 at the `on`
(`JOIN-local ON is available only when an EXPLICIT_MODULES project (schema
version 2) completes it.`). A JOIN after one that failed keeps that PIE-S2334.

### Fixes

- **Comparison chains.** `check --project` no longer stops with an internal
  error on a comparison chain such as `0 < low + 1 <= high < 10`, where it
  reports what a single-file check reports, or on one over a window in
  QUALIFY, such as `0 < row_number() window(order by id) < 3`.
  `emit-sql --project` emits a chain as it emits the same comparisons joined
  with `and`, and so does single-file `emit-sql` for a chain over an
  `any(...)`, such as `False == any(z.id > 0 for z in b) == True`. An error in
  an operand that two comparisons of a chain share is reported once by
  `check --project` of a `schema_version = 2` project, as the next item
  states, and, in the cases this release fixes, in a single file and in a
  `schema_version = 1` project.
- **Repeated diagnostics in an explicit-module project.** `check --project`
  of a `schema_version = 2` project reports a diagnostic equal to an earlier
  one in code, severity, message, location and suggestion once, at its first
  position, as the
  [project JSON v2 contract](spec/project-cli-json-v2.md#ordering) states.
  0.1.4 reported an error in a call written inside another def's body as
  often as the called def's expansion made it, and a query header parameter
  passed to a `def` and read in a position that refuses it (PIE-S2355) at
  each use of the argument. A single file still reports such an error in a
  def body as often as the expansion makes it, except anywhere in an operand
  that a comparison chain copies, such as `x` in `0 < x < 10`, where it is
  reported once. The value of an inclusive chain `lower <= value <= upper` is
  not itself copied, so its error still follows the expansion unless the error
  lies in copied operand text, either around that chain or nested in its
  value.
- **Aggregates in a project `any`.** An explicit-module project refuses an
  aggregate in an `any(...)` predicate, such as
  `any(count() > 0 for o in orders)`, with PIE-S2335
  `Aggregate expressions are unavailable in ANY predicates.`, as a single file
  does; it accepted it.
- **A nested `any` before a later JOIN.** An enclosing binder hides the
  relations of its name from a nested `any(...)` also when the outer `any`
  filters before a later JOIN:
  `where any(any(True for nested_row in candidate) for candidate in rows)`
  followed by a JOIN was accepted, and its SQL read the table `candidate`; it
  is now PIE-S2301, as the same filter after the last JOIN is. A binder hides
  only the name as written, so a nested `any(...)` over a `let` alias of a
  relation with the binder's name, such as
  `any(any(True for other in buyers) for customers in orders)` after
  `let buyers = customers`, is now accepted, also after the last JOIN, where
  it was refused.
- **A nested `any` in a project.** An explicit-module project applies the same
  rule, also before a later JOIN:
  `any(any(True for nested_row in rows) for rows in rows)`, or the same
  through a `let` alias of `rows`, is PIE-S2301 and PIE-S2334 where it was
  accepted; before a later JOIN, that JOIN also reports PIE-S2335.
- **A CTE that hides a table.** Single-file SQL emission refuses a scalar
  `any(...)` reader with PIE-B1000 when a CTE that it defines would hide a
  table that the same SQL reads without a schema (MySQL compares the names
  case-insensitively); the SQL read the CTE in place of the table. Rename the
  relation, or read the table with its schema.
- **Private combined IR verification.** The verifier refuses a document whose
  scalar `any` read of an outer FROM or JOIN input names another relation, or
  other field names or another nullability than that input has; it accepted
  it.
- **A JOIN without `on` over a table or query.** In a single file, a JOIN
  without `on` whose FROM input or target is a table or query of the same file
  reports PIE-S2335 ``JOIN <binding>: write `on` with the condition that
  matches <input> to <relation>``, as every other JOIN without `on` does; it
  reported a PIE-S2334 text about relationship JOINs through a table or query.
- **A failed relationship call beside a window.** When a relationship call in
  `on` or in `any(...)` passes a table of the same file to a shape parameter
  and the file selects a window function, `check`, `explain` and `emit-sql`
  report PIE-S2604 as they do without the window; they stopped with an
  internal error.
- **`let` in a legacy-flat project.** A `schema_version = 1` project resolves
  each `let name = value` as a single file does, so a selected `let` name, a
  `let` alias read by `from` and an aggregate over a `let` are checked; they
  were PIE-S2102 `Unknown field`, PIE-S2301 or an empty row schema.
- **JOINs and `any(...)` in a legacy-flat project.** A `schema_version = 1`
  project reports one PIE-S2334 per JOIN and one per `any(...)`, in source
  order, each naming the way out (`set schema_version = 2 to check it`, see
  [legacy-flat projects](#legacy-flat-projects-and-relationship-joins)). A
  JOIN `on` said `JOIN-local ON is available only when an EXPLICIT_MODULES
  project (schema version 2) completes it.`; a CROSS, RIGHT or FULL JOIN
  reported its JOIN-kind text, such as `CROSS JOIN is available only when an
  EXPLICIT_MODULES project (schema version 2) completes it.`, and a RIGHT or
  FULL JOIN with `on` reported both. An INNER or LEFT JOIN without `on`, also
  one whose target names no relation in a relation that reads a field of its
  binding, and an `any(...)` in a `where`, `select` or `let` after the last
  JOIN, which such a project accepted without a diagnostic, are now refused
  the same way.
- **Deeply nested expressions.** A long chain of unary operators in a `derive`
  body and nested conditional expressions in a QUALIFY window argument parse
  to the depths 0.1.4 parsed; they stopped earlier with PIE-P1000
  `Parser recursion limit exceeded while processing source.`
- **Package check.** `scripts/package_smoke.py` writes its project sources in
  the modern spelling and accepts the approved PIE-S2382 warning of the MySQL
  ordering fixture; the installed package is unchanged by it.

### Known limitations

- **R2 and a trailing `any`.** A `where any(...)` or `where not any(...)` after
  the last JOIN, the rewrite of a last `semi join` or `anti join`, is an
  existence read, so R2's `save_recoverable` and `recover`
  refuse it with `PIE-R1004` (`REFINEMENT_EXPRESSION_BLOCK_READ`) where they
  accepted that last JOIN. A filter before a later JOIN, ordinary execution,
  an ordinary `save` and bundles are unaffected. A later release adds R2
  support for a trailing correlated `EXISTS`
  ([execution](execution.md#known-limitations)).
- **D-11 and D-12.** The conservative fan-out and typed-NULL refusals of
  [fix batch 7](#fix-batch-7-following-014-included-in-015) remain, including
  programs whose old SQL ran correctly.
- **Bundles and saved jobs.** As with every release, the changed code identity
  refuses bundles and saved-job records made by 0.1.4 or earlier; keep their
  matching environment.
- **The rewrite suggested for an old JOIN written with `as`.** The PIE-P1000
  of a 0.1.4 JOIN written with `as` suggests
  `let alias = relation` and then `left join alias on predicate` for every
  kind, also for an INNER, RIGHT, FULL or CROSS JOIN; keep the JOIN's own kind
  when rewriting it (a CROSS JOIN takes no `on`).
- **`migrate` and an old `semi join` or `anti join`.** Its PIE-P1011 for one
  written with `as` says to introduce `let` and `on`; rewrite it as
  `where any(predicate for o in orders)` or `where not any(...)`, as the
  PIE-P1000 of `check` suggests.
- **`migrate` and a parenthesized row argument.** A `semi join` or `anti join`
  whose relationship call passes the JOIN's own name in parentheses, such as
  `OrderCustomer((orders), customers)`, needs a manual rewrite (PIE-P1011),
  although the same call without the parentheses migrates.
- **A compiler-generated name in a diagnostic.** A bare binder as the
  predicate of an `any(...)` or `not any(...)` before a later JOIN, such as
  `where not any(o for o in orders)`, is PIE-S2335
  `JOIN ON reference is unknown: _pietto_any_1`, naming a binding that the
  compiler generated; after the last JOIN the same filter is PIE-S2102
  `Unknown or unavailable field in ANY predicate: o`.
- **MySQL and relation names that differ only in case.** When MySQL SQL
  defines two relations as CTEs whose names differ only in letter case, such
  as `chosen` and `CHOSEN`, a server with `lower_case_table_names` set to 1 or
  2 refuses the statement for a duplicate name; it returns no wrong rows.
- **Private combined IR verification.** The verifier does not check the type
  or the definition of a field that a scalar `any` reads from an outer input,
  as the document does not record them.
- **Very deeply nested comparison chains.** Checking a comparison chain nested
  in other chains many levels deep, such as
  `True == (True == (...) == True) == True`, is slower than in 0.1.4.
- **A diagnostic printed twice.** Apart from `check --project` of a
  `schema_version = 2` project, which reports an equal diagnostic once, an
  identical diagnostic printed twice at one position is a known issue to
  report, except for an error in a def body, which a single file reports as
  often as the def's expansion makes it, except anywhere in an operand that a
  comparison chain copies (including a nested operand). The value of an
  inclusive chain `lower <= value <= upper` is not itself copied; an error is
  reported once only when it lies in copied operand text, either around that
  chain or nested in its value.

### Deferred to the next release

These decided changes are not in this release:

- A hand-written `on` equality to a declared unique key whose fields are never
  None earns the same fan-out proof as a relationship call, in single files
  and projects.
- Warnings in every check mode for `Int / Int` truncation, `None` inside an
  `in` list (with the enum `in`-list fix) and `--` in an expression.
- Two warnings: a test in WHERE that rejects NULL on the NULL-extended side
  of a LEFT JOIN, and `not in` with a nullable left value.
- A style page for Python users.
- Relaxing the conservative fan-out (D-11) and typed-NULL (D-12) refusals of
  [fix batch 7](#fix-batch-7-following-014-included-in-015), so that the outer-JOIN
  aggregates and NULL arithmetic that the database runs correctly are accepted
  again (deferred, not dropped).
- R2 recovery through a trailing correlated `EXISTS`.
- Emitting a same-file table or query read as a CTE, and with it naming each
  statement and ending it with `;` in `emit-sql` text output, so that the SQL
  text changes once; this release's text output is unchanged.
- Reporting a swapped argument pair as one diagnostic.

## Fix batch 7 following 0.1.4 (included in 0.1.5)

This addendum covers the compiler fixes following 0.1.4, which `0.1.5` includes.
It does not replace the published 0.1.4 release notes.

### Checking and supported results

- Known function results are checked even when an argument's type is unknown.
  Decimal quotients and arithmetic with a NULL operand retain their numeric
  information, so incompatible scalar calls, comparisons and conditions receive
  specific diagnostics.
- The existing accepted NULL-containing IN/NOT IN compatibility branch now has
  type Bool nullable, including its supported numeric, Date/Text-literal and
  enum-label cases. Calls such as LOWER or ABS apply the existing Bool rules.
  Some previously accepted MySQL uses relying on implicit conversion are newly
  refused; the owner explicitly approved that compatibility change. Operand
  compatibility rules and unrelated Unknown operators are unchanged.
- A specific scalar error is retained inside an aggregate when the failing
  argument contains qualifying typed NULL arithmetic. For example,
  `count(trim(null % n))` reports the TRIM type error rather than only an
  unsupported-aggregate-expression error. Existing arity, bounds, def-argument
  and independent-error precedence remains.
- ABS accepts Int and Float as well as Decimal. Int-to-Float casts can use newly
  known Int results. Supported non-null def bodies and value windows with a
  provably nullable result can also be accepted in cases that previously lacked
  enough type information.
- Invalid qualifiers, grouped projections, aggregate forms and ORDER BY uses
  over sources without a shape are checked earlier. The unpublished aggregate
  emission expansion was removed: shapeless aggregate SQL, grouped-window
  lowering and downstream output-schema/lineage remain at the 0.1.4 boundary.

### JOIN proofs and metadata

RIGHT/FULL unmatched rows no longer receive an unconditional grain dependency
that can hide repeated aggregate inputs. Some programs that 0.1.4 accepted now
receive `PIE-S2333` with a more accurate repeating-JOIN explanation and remedy.

Correct existing COUNT cases retain narrowly justified proofs: an exact reverse
INNER/SEMI match can remove the original unmatched rows, and a grouped nullable
key can serve only the specific bounded unmatched-row proof whose full final
non-null and cardinality premises hold. It does not become a generic group key
for unrelated or unbounded JOINs.

INNER relationship equalities retain their actual matched-field non-null facts
even with an additional ON. Self-relationship directions use exact endpoint
roles, and compiled field ancestry preserves the original introducing input
through internal JOINs. Current and compiled key, FD and grain evidence follow
the same identity rules. These metadata corrections are not limited to queries
containing RIGHT/FULL.

Composed WHERE/LET proof traversal avoids adding the two expression depths while
preserving the values actually visited and existing short-circuit behavior.
Project source selection and cyclic-import inspection also retain diagnostics
instead of their documented recursion/inspection crashes.

### SQL and compatibility

MySQL integer division uses `DIV` where the dividend is now known Int, and
ORDER BY fields are qualified when an unaliased TRUE/FALSE/NULL output would
capture them. PostgreSQL's supported NULL temporal calls use a typed NULL
instead of an unresolved EXTRACT. These are generated-SQL changes, not claims
of new native database execution.

A semantic error still prevents emission of a single file or every relation of
an EXPLICIT_MODULES project. Newly detected errors can therefore remove partial
or otherwise-valid sibling output.

The documented conservative **D-11** fanout refusals and **D-12** typed-NULL
refusals remain for this release, including specified programs whose old SQL was
database-correct. Their relaxation is required after the JOIN demo; it has been
deferred, not dropped. The restored COUNT and composed-depth cases are not
additional exceptions under those decisions.

The detailed compatibility changes follow.

### Compatibility with 0.1.4: fix batch 7

This is the compatibility text for the fixes following 0.1.4 (included in 0.1.5).
Examples describe compiler checks, metadata and generated SQL. They do not claim
new execution against PostgreSQL or MySQL. This batch does not introduce the
single-file JOIN MVP or new aggregate emission over sources without a shape.

#### Effect of an error on emission

A new semantic error prevents SQL emission for the whole single file. Where
0.1.4 refused one relation but still printed another relation's SQL or returned
partial artifacts with `ok: false`, that partial output is no longer produced
once the program fails checking.

In an EXPLICIT_MODULES project, an error in any relation blocks
`emit-sql --project` for every relation, including otherwise valid siblings.
For example, rejecting `id in (1, "x", null)` in one query also blocks a sibling
table that 0.1.4 could emit. This follows the existing project policy; it is an
intentional compatibility effect, not a new project execution policy.

LEGACY_FLAT projects still do not emit SQL. Their checking changes are described
below.

#### Comparisons, membership and COALESCE

The same semantic type rules apply to both dialects. Programs relying on MySQL
implicit conversion can therefore be newly refused even when their old SQL ran.

- Enum values and enum aliases cannot be compared with Int, Float or Bool, a
  different enum family, an invalid or differently cased label, or a non-literal
  Text expression. Examples include `st == 1`, `st == other_enum`,
  `st == "bogus"`, `st == name` and `st > upper(name)`. These report
  `PIE-S2105`. Valid labels such as `st == "active"` and valid enum-label
  BETWEEN bounds remain accepted; a Text conditional is not a literal label.
- Date, Timestamp, UUID, Bytes and Json cannot be compared with non-literal Text
  fields, calls or bindings, including BETWEEN bounds. Literal forms such as
  `d == "2020-01-01"` retain their existing admission rules.
- Bytes and Json comparisons with unrelated families, and shape values compared
  with a different family or shape, report `PIE-S2105`. The existing permitted
  Text-literal comparisons, same-shape comparisons and gradual `Any` cases remain.
- A NULL option no longer hides an incompatible IN/NOT IN option:
  `id in (1, "x", null)` and `id not in ("x", null, null)` report
  `PIE-S2105`, “expected same canonical membership operands.”
  Numeric-looking or Bool-looking Text is not automatically converted:
  `id in ("5", null)` and `b in ("true", null)` are also refused.
  Existing compatible lists such as `amount in (2.5, null)`,
  `id in (2.5, null)`, `d in ("2020-01-01", null)` and valid enum-label
  lists retain their admission rules.
- In the existing NULL-containing membership compatibility branch, once the
  remaining operands are accepted by the existing pairing rules, IN and NOT IN
  now have type **Bool nullable**, rather than Unknown. This covers the accepted
  numeric, Date/Text-literal and enum-label cases. Direct expression metadata,
  and direct outputs on the supported typed-row path, reflect that type.
  Surrounding calls apply the existing Bool
  rules: `lower(d in ("2020-01-01", null))` and
  `abs(1.5 in (null, n))` report `PIE-S2104`. This includes newly refused
  MySQL uses that previously relied on implicit conversion, as explicitly
  approved by the owner. Unsupported operand pairings are not admitted, and
  unrelated Unknown operators are not retyped by this change.
- On an unknown row, known incompatible COALESCE arguments are checked even
  beside an unknown argument: `coalesce(t, 1, "x")` and
  `coalesce(t, true, 1)` report `PIE-S2104`. The existing gradual case
  `coalesce(t, 1, 2.5)` remains accepted.
- EXPLICIT_MODULES projects apply the comparison rules to query header
  parameters, JOIN predicates and joined result predicates as well as ordinary
  scalar expressions. A Text header parameter is not an enum label or temporal
  literal. Supported header parameter families remain Bool, Int, Float and Text;
  other families retain `PIE-S2353`.
- A def that compares a Date, Timestamp or UUID parameter with a Text parameter
  is checked at its declaration even if every call passes a Text literal.
  A def-body error still prevents the later call analysis.

The owner retained the documented dialect-independent comparison and
typed-result refusals for this release, including cases for which a database
would supply a conversion.

#### Fixed-signature results and numeric expressions

A fixed-signature call can have a known result even when its argument's type is
unknown: `len(t)`, `year(t)` and `count(t)` have Int results, and
`lower(t)` has a Text result. This affects expression checking; it does not
introduce type propagation through an unsupported shapeless relation output.

Consequently, `lower(t) + 1`, `-lower(t)`, `len(t) like "a%"`,
`lower(len(t))` and mismatched known parameters of `matches`, `contains` or
`replace` are refused with `PIE-S2104` or `PIE-S2105`.
A numeric result used as WHERE reports `PIE-S2202`. These checks also apply
when the argument is an all-NULL expression or a Decimal quotient on a shaped
row.

Known result types also receive Pietto's existing stricter rules:
`year(t) == "2020"`, `len(t) in (1.5, 2.5)`,
`coalesce(len(t), 1.5)` and `nullif(year(t), 2.5)` can now be refused.
A def expecting Text rejects `len(t)` with `PIE-S2395`. Unknown
nullability alone remains gradual; it is not treated as proven NULL.

Some refusals move earlier from emission to checking. These include a Text-to-
Float cast whose argument is now known to be Text, invalid arity for `nullif`,
unsupported aggregate expressions, and invalid uses of a COUNT result in
`satisfying`. Their original unsupported emission capability is not added.

A Decimal quotient is recognized as numeric even where its concrete numeric type
is unknown. The rule follows direct expressions, LET bindings, COALESCE, NULLIF
and conditionals:

- A quotient in WHERE, satisfying, a shape check or an index predicate must
  satisfy the Bool rule. Quotients used with `and`, `or`, `not` or as a
  conditional condition are likewise checked.
- Mixing a quotient with Text, Bool, an enum or another incompatible family in
  arithmetic, comparison, LIKE, membership, BETWEEN or a conditional reports the
  corresponding `PIE-S2104` or `PIE-S2105`.
  Numeric-looking Text literals do not receive an implicit conversion.
- Text and temporal functions reject a numeric quotient at the offending
  parameter: for example `lower(a / 2)` and `year(a / 2)`.
  Existing supported numeric uses of `abs`, `sign` and COALESCE remain.
  `substr(t, a / 2, 1)` remains refused because its start is not a positive
  Int literal; this is not a new refusal.
- The same checks apply inside def expansions and to a field's `derive`.
  A def call can report the expanded body's scalar errors at the call, rather
  than one `PIE-S2395`; this existing diagnostic distinction is retained.
- A branch known only to be numeric, with unknown concrete numeric type, can
  no longer be combined with Text merely because the condition has silent
  Unknown type. This includes an unknown-argument ABS result or a Decimal quotient.
  `abs(t) if b else "x"` reports `PIE-S2105` in that situation.
  Compatible numeric branches retain Unknown when the condition remains Unknown.
  Ordinary cases such as `1 if b else "x"` with silent Unknown `b` retain
  their existing gradual behavior; this is not a general conditional migration.

`abs` accepts Int and Float in addition to Decimal and preserves a concrete
argument's type and nullability. An unknown argument or Decimal quotient can
remain numeric with unknown concrete type, so numeric contexts continue to work
while Text and temporal calls reject it. The intermediate typing-lane refusals of
`abs(len(t))`, `abs(t) % 2 == 1`, `abs(t) + 1.5`,
`nn(abs(t))` and `nn(abs(amount / n))` are not retained.

#### NULL-only values and typed NULL arithmetic

A conditional, COALESCE or NULLIF made only of NULL values behaves like NULL
when combined with a known typed value. For example, a Text branch beside an
all-NULL branch yields nullable Text, and a not-null def parameter can reject
that nullable result with `PIE-S2395`. A known incompatible type is no longer
hidden by the all-NULL expression.

PostgreSQL emission refuses an all-NULL output when another relation reads its
relation, including a plain read, an IS NULL test or a reader that does not use
that column, as it already did for a literal NULL output. It also refuses all-NULL
CASE/COALESCE/NULLIF values in unsupported numeric, Bool or temporal uses within
one relation. The diagnostic is `PIE-B1000` and explains the text typing.
Text uses and the MySQL emission boundary retain their existing behavior;
`nullif(null, 1)` is typed and is not an all-NULL expression.

Arithmetic with one NULL operand and a known numeric operand is now typed as the
operator's typed twin and is nullable. This includes `+`, `-`, `*`, `/`
and `%`, and a NULL supplied by an allowed LET or inlined def value.
Thus `null + n` is nullable Int, `null + fl` nullable Float and
`null + d` nullable Decimal; division beside Decimal retains the existing
numeric-but-concrete-type-unknown rule.

The resulting compatibility changes include:

- `lower(null + n)`, `trim(null % n)`, `len(null + n)`,
  `year(null + n)` and `lower(null / d)` now report the scalar
  `PIE-S2104` type error. Mixing those results with Text in COALESCE also
  reports `PIE-S2104`.
- Arithmetic, comparison, LIKE, IN, BETWEEN or a conditional with an
  incompatible partner reports `PIE-S2105`. A numeric NULL expression as
  WHERE reports `PIE-S2202`.
- The typed twin's existing rules also reject some SQL that a database would
  evaluate: Decimal/Float or Decimal/Int combinations outside Pietto's supported
  rule, numeric-looking Text, incompatible canonical COALESCE/NULLIF arguments,
  and nonmatching def parameters. Def argument messages now name the inferred
  nullable numeric type where it is available.
- A declared def result can now be checked against the typed NULL arithmetic
  body. For example, an Int body declared as Text reports `PIE-S2402`.
  Conversely, nullable-Int bodies such as `coalesce(x + null, x)`,
  `(x + null) if x > 0 else x` and `x if x > 0 else x + null` can be
  accepted where their result was previously unknown.
- When a valid-arity scalar call has an actual type error caused by NULL
  arithmetic in its failing argument, an enclosing aggregate retains that
  specific error. `count(trim(null % n))` reports `PIE-S2104` at
  `trim` instead of the generic aggregate-form `PIE-S2315`.
  `count(null + n)` still reports `PIE-S2315`;
  `count(nn(n + null))` retains its def-argument error.
  Arity errors, substr bounds, prior independent errors, ordinary quotients and
  unrelated NULL siblings keep their existing precedence and multiplicity.
- The rules apply to readers of supported typed outputs and to known JOIN
  fields. In projects, a newly exposed semantic error also blocks otherwise
  valid siblings under the normal project policy.

**D-12 is retained for this release.** It includes the documented newly refused
uses whose old PostgreSQL or MySQL SQL was database-correct, including MySQL
implicit conversions. The owner requires those specified database-correct
classes to be accepted again after the JOIN demo; that work is deferred, not
dropped.

In the documented project LET/JOIN cases, typing can instead remove a check-time
`PIE-S2333` while emission still refuses the affected relation with
`PIE-B1003 expression_evidence_unavailable`. This covers a grouped
null-arithmetic LET key, an ungrouped SELECT reading such a LET or LET chain,
and null arithmetic over either a joined binding's field or the FROM binding's
field in an ON JOIN. Valid sibling relations can then emit again.
The direct no-LET/no-JOIN SELECT form retains its separate `PIE-S2333` boundary.

`null + null` and `-null` retain their unknown-type boundary.
PostgreSQL still refuses their unsupported emission; fix7 does not make every
NULL-valued expression lowerable.

#### Sources without a shape

The retained change is earlier checking, while the released aggregate emission
and output-schema boundaries remain.

- A qualifier other than the FROM binding, or a field path with three or more
  parts, reports `PIE-S2102` in WHERE, SELECT, ORDER BY and read LET values,
  including a stale upstream qualifier used by a downstream relation.
- An invalid reference in an unread LET is also reported. Dropping that LET from
  emitted SQL no longer hides its error.
- Grouped unknown rows are checked for a missing aggregate, a non-key projection,
  unsupported scalar projection and duplicate keys, using the existing
  `PIE-S2318`, `PIE-S2319`, `PIE-S2320` and `PIE-S2317` families.
  A GROUP BY is no longer silently discarded while row-level SQL is emitted.
- Aggregate arity, form and known argument types are checked even on an unknown
  row. This can move a failure from `PIE-B1000` emission to checking:
  examples include `count(x, y)`, `min(x + 1)`, `count(x + "a")`,
  non-grouped fields beside an aggregate, and an aggregate ORDER BY input.
  Unsupported computed LET arguments retain name/form errors. A known Bool
  min/max error remains visible beside independent unread-name errors, with
  their original locations, order and repeated occurrences.
- Aggregate modulo cases such as `count(x % 2.5)` and
  `count((x * 1.5) % 2)` remain subject to the aggregate form/type boundary;
  a plain unknown-field `x % 2.5` is not newly refused solely for being unknown.
- Grouped ORDER BY retains the released whole-clause `PIE-S2321` boundary.
  Grouped windows do not gain a new lowering path.
- Reading a single-file JOIN binding still requires the separate single-file
  JOIN capability; this batch retains its refusal.

The unpublished emission expansion was removed, including its later
count-only/grouped subset. There is no new shapeless COUNT/COUNT DISTINCT,
MIN/MAX/SUM/AVG, HAVING, grouped ORDER BY or grouped-window emission in this
batch. Unknown-input ungrouped relation outputs remain unknown; grouped
unknown-input outputs and downstream explain/lineage remain at their released
empty/unknown boundary. Restoring these boundaries is not a new refusal
relative to 0.1.4.

#### JOIN aggregation and relation identity

In projects, a RIGHT or FULL JOIN with an at-most-one match no longer supplies
an unconditional left-to-right grain dependency over its unmatched right rows.
An aggregate with an argument is refused with `PIE-S2333` when it can read
repeated rows that the available key/grain proofs do not protect. A unique key
on the NULL-extended left input alone does not fix its NULL group.

Affected forms include a subsequent LEFT/CROSS JOIN from the preserved side;
an argument such as `orders.rush or true` that is not NULL on unmatched rows;
WHERE conditions such as `orders.amount > 0 or c.vip` or
`orders.id is null`; and ANTI or unrelated SEMI conditions that retain those
rows. Empty-list conditions keep their actual TRUE/FALSE behavior, including
through LETs and NOT.

Accepted proofs include an argument that is NULL on those rows, a WHERE or
later INNER/SEMI/RIGHT match that excludes them, and the existing narrowly
qualified later-input proof. In addition:

- For the initial RIGHT/FULL over direct sources with no extra ON, a later
  INNER/SEMI reverse match over the exact same source domain can eliminate all
  original unmatched rows. Complete paired equalities are compared without
  treating authored conjunct order as meaning, while their multiplicity and
  field pairing are retained. A stricter later ON is allowed. ANTI, an extra
  earlier ON, a different source declaration sharing a physical table name, or
  a filtered source does not establish this proof.
- Generic group protection remains **source STRICT-key only**. A grouped nullable
  unique key can be used only for the exact later input that supplies the
  existing bounded RIGHT/FULL unmatched-row proof, when every key determinant
  is non-null in the final rows and the original pinning/cardinality premises
  hold. It restores only that original dependency; it adds no general group
  seed. An unrelated unbounded JOIN cannot borrow this capability.
  Missing composite-key evidence and later outer NULL extension defeat it.
- INNER relationship equalities contribute complete non-NULL facts even with an
  extra ON. These facts refer to the actual matched field occurrences, not an
  unwritten equivalent sibling; source declarations remain unchanged. A later
  outer JOIN can NULL-extend them again.
- A self-relationship's reverse guarantee is selected by its exact opposite
  endpoint roles, not by the shared output object. Current and compiled keys,
  FDs and grain retain the legitimate inverse dependencies. Compiled field
  ancestry follows internal JOIN outputs to the original introducing use while
  respecting named-producer boundaries.

The last two corrections also affect metadata outside a RIGHT/FULL aggregate,
including the applicable INNER/LEFT relationship paths.

**D-11 is retained for this release.** Some safe programs remain conservatively
refused because the proof does not simplify values, constants, contradictions,
vacuous conditions or every correlation. Examples include the documented
`where r.id is null` on a non-null CROSS input, contradictory comparisons,
and value-dependent COALESCE/conditional/NULLIF or empty-membership forms.
Some previously had correct VERIFIED SQL; other examples already failed
emission. Correlated ANTI/LEFT emptiness is distinct from a value-only proof.

`min`, `max` and `count_distinct` receive no general fanout exemption,
even when repetition would leave their value unchanged. The documented
database-correct D-11 classes remain scheduled for relaxation after the JOIN
demo, not silently reclassified as wrong SQL.

For already refused programs, `PIE-S2333` can name different repeating JOINs
or a different remedy while keeping its code and declaration location.
`count()` without an argument counts the joined rows and retains its separate
rule.

Composed WHERE/LET NULL proofs no longer stack the two expression depths or
evaluate unrelated LETs speculatively. Existing short-circuit visitation is
preserved. Very deep programs still have the existing `PIE-S2006` boundary;
historical recursion thresholds and timing samples are not public guarantees.

#### Windows and project checks

- RANGE offsets must be nonnegative Int literals no greater than
  `9223372036854775807` after permitted LET inlining. Unknown names, Text,
  Float, NULL, fields, computed offsets and out-of-range literals report
  `PIE-S2104`. Zero, the maximum literal and an allowed literal LET remain
  accepted. The check applies to named/selected windows and project JOIN and
  QUALIFY contexts.
- Value windows can accept a known value type with unknown nullability when the
  result is nevertheless known nullable: first/last/nth value and the admitted
  lag/lead cases. The existing limits for offset zero or a non-null default
  remain. Project emission still requires its target contract.
- Project windows over supported shape-valued inputs/aliases can pass checking
  without gaining shape SQL emission. JOIN/hidden-QUALIFY shape windows,
  shape partition/order keys, unsupported shape LET reads and the documented
  unknown-result-nullability cases retain their refusal boundaries.
- An unrelated unknown-typed LET no longer blocks a project window whose actual
  reads are supported. Some such relations still fail emission with
  `expression_evidence_unavailable`, while valid siblings can emit.
- LEGACY_FLAT checking reports the single-file semantic diagnostics after its
  model diagnostics. This includes type, predicate, field, aggregate, window,
  constraint/derive and relationship errors. SELECT-output ORDER BY keys outside
  grouped queries receive the existing `PIE-S2102` hint to restate the
  expression or bind it with LET. LEGACY_FLAT still refuses `def` with
  `PIE-S2379` and emits no SQL.
- Relationship JOIN routes through supported DISTINCT endpoints in
  EXPLICIT_MODULES projects can plan and emit again, including inferred/explicit
  routes and their readers, rather than failing with unavailable planning roots.

#### SQL, diagnostics and metadata changes

For programs accepted before and after, these generated SQL changes are
intentional:

- MySQL uses `DIV` rather than `/` where the dividend is now known Int:
  `len(t) / 2`, admitted temporal/sign calls, a typed branch beside all-NULL
  values, and `(null + n) / 2`. This does not introduce missing type
  propagation through an upstream relation.
- MySQL qualifies an ORDER BY field that an unaliased TRUE, FALSE or NULL SELECT
  item would otherwise capture.
- PostgreSQL emits a typed NULL for `year(null)` and the corresponding
  month/day/hour/minute forms, including permitted LET/def NULL values, instead
  of an unresolved EXTRACT over NULL.

Other supported outcomes include Int-to-Float casts of newly known Int results,
such as `cast(len(t) as Float)` and `cast(null + n as Float)`.
Float-to-Float casts remain unsupported and can now fail at check rather than
emission. Proven non-null def bodies over the supported operators can be
accepted; `/`, `%`, `and`, `or`, `nullif` and `matches` remain
outside that non-null proof. An all-NULL branch can establish a compatible
nullable def result without making PostgreSQL's unsupported all-NULL emission
valid.

Project Int/Float ABS uses retain physical range requirements. A range that
cannot establish safety blocks emission; public details include
`abs_result_outside_physical_range` and `int_range_proof_missing`.
A query header parameter is not newly admitted as an ABS argument.

Diagnostics become more specific in several already refused cases:

- Computed window partition/order LETs report the window-computation
  `PIE-S2103` rather than a spurious unknown name. Value-window offsets,
  defaults, unknown fields and unsupported shape equivalence keep their
  specific existing diagnostic families.
- Unsupported min/max LET arguments on known rows receive their actual
  argument/type/binding diagnostic rather than an unconditional unknown name.
- Known function results expose their own outer type errors; prior independent
  errors and duplicate authored occurrences are retained.
- Projects report scalar/name/duplicate-projection errors in place of a bare
  `PIE-S2333` where those facts are available. Redundant relation-level
  cascades and repeated reporting of the same JOIN issue are removed.
  Identical BLOCKED entries are deduplicated in text, JSON and `compile_query`.
- QUALIFY's single-file refusal and project configuration errors have clearer
  suggestions. Clause-header hints are no longer added in inapplicable parser
  contexts. ABS and def-result messages describe the supported types/proof
  limits more accurately.

Metadata reflects known fixed-signature expression results, typed nullable NULL
arithmetic, the accepted membership branch's Bool nullable result, and the
corrected JOIN nullability/identity facts. This does not restore the removed
shapeless output-schema or lineage expansion.

#### Retained limitations and stability

Unknown types alone remain gradual. These changes do not introduce arbitrary
casts, implicit canonical-type conversion, general computed aggregate arguments
or unrestricted window/shape lowering.

A value known only as numeric with unknown concrete type can still lose that
numeric marker at an existing relation-output boundary. The batch does not
introduce general propagation through those boundaries. The documented
known-row unknown-field aggregate forms remain separately limited; removing the
unpublished shapeless capability does not make those forms newly lowerable.

Project selection with deeply nested include/exclude patterns or paths no longer
ends in RecursionError, and ambiguous declarations in an import cycle retain
their diagnostics instead of crashing inspection. The new NULL analysis
preserves established LET-cycle diagnostics and shared-DAG behavior.

Development-tool and CI pin updates do not define new SQL, diagnostic, JSON or
golden behavior.

---

## Post-Phase70 public alpha release notes — 0.1.4

**Status:** These notes describe `0.1.4`, published and byte-verified on the
versioned GitHub pre-release and PyPI channels.

This release makes Pietto source read more like Python, adds one-line
relationships, inferred JOIN sources and inline `def` functions, and fixes
compiler and CLI defects found after 0.1.3. Source that 0.1.3 parsed keeps
parsing as before, with one exception: a file whose first code line is
indented is now PIE-P1000.
Some programs that 0.1.3 accepted are now refused because their SQL would fail
or mean something else; see
[Compatibility and retained data](#compatibility-and-retained-data). Pietto
remains an alpha; the CLI does not execute database queries.

### Highlights

- **Python-style layout.** `select:`, `select distinct:`, `group by:`,
  `order by:`, `partition by:`, the row `let:` and `enum NAME:` take their
  items after `:` on the header line, separated by commas, or in an indented
  block whose lines each hold one item or a comma-separated list, for example
  `order by: ordered_at desc, id desc`. `where:`, `satisfying:` and a shape's
  `check NAME:` take one condition after `:` or one condition per line of an
  indented block; the lines are joined with `and`, each as if written in
  parentheses. Inside parentheses an expression can continue over several
  lines; there is no backslash continuation, and an unclosed `(` is PIE-P1008.
  These forms parse to the same tree as the one-item-per-line form or the
  `and` chain, so checks and SQL are unchanged.
- **Soft keywords as names.** 26 words, among them `type`, `source`, `from`,
  `where`, `select`, `query`, `limit` and `check`, may also name a shape field,
  a `select` output, a row `let:` binding, a parameter or a typed VALUES
  column, as in `where type == "click"`. They do not name declarations or
  relations. `and`, `or`, `not`, `null`, `true`, `false`, `between`, `like`,
  `nullable` and `window` stay reserved.
- **One-line relationships.** `relationship r: a.x == b.y`, with one or more
  `and`-joined equalities between fields of two different relations, declares
  the endpoints `a` and `b`, so its roles are the relation names. A
  relationship of a relation to itself keeps the block form.
- **Shorter relationship JOINs.** A JOIN that follows a declared relationship
  needs only its header; its `from` line and VIA roles are optional, and the
  header may carry one step: `: from b`, `: via r` or `: via r: s -> t`. In an
  explicit-module project (`schema_version = 2`) a JOIN without `from` uses the
  one earlier binding that has a relationship to its target, in exactly one
  usable direction. No candidate is preferred: otherwise PIE-S2333 at the JOIN
  names every candidate. A JOIN with `on` and a CROSS JOIN still name their
  source with `from` (PIE-S2378). Single-file and schema version 1 project
  checks do not infer.
- **Inline `def` functions.** `def f(p: T not null) -> R nullable: return e`
  names a reusable scalar expression over `Bool`, `Int`, `Float`, `Decimal`,
  `Text`, `Date`, `Timestamp` or `UUID` parameters with explicit nullability.
  It is checked once where it is declared, and each call is replaced by its
  body before the call site is checked, so a call emits exactly the SQL of the
  same expression written by hand; no database function is created. A def
  belongs to its module (no import or export), recursion is refused, and an
  error inside a call is reported once however often the body uses the
  argument, except in a call written inside another def's body, where an
  error other than an argument mismatch (PIE-S2395) is reported as often as
  its expansion makes it, and in two project cases (see
  [Known limitations](#known-limitations)). An error in a def body stops the
  check before semantic analysis: of its file, and in a project of every
  module. Available in single files and explicit-module projects.
- **New diagnostics:** PIE-P1008 (an unclosed `(`), PIE-S2378 (a JOIN with
  `on` or a CROSS JOIN without `from`), PIE-S2379 (`def` in a schema version 1
  project), PIE-S2395 to PIE-S2399 (`def` arguments, recursion, forms, names
  and expansion size), PIE-S2380 (an ORDER BY key a target would misread) and
  PIE-S2604 (a relationship `on` operand error).

### Compatibility and retained data

- Bundles and saved jobs made by 0.1.3 or earlier are rejected by the 0.1.4
  code identity. Pietto neither migrates nor rewrites those bytes; use their
  matching old environment, then compile again for 0.1.4. Format markers are
  unchanged. The VS Code extension 0.1.0 accepts only the 0.1.2 wheel or its
  baseline fingerprint and refuses 0.1.4. This release adds no stable editor
  API.
- Explicit-module projects:
  - A field of an enum, or of an alias of one, is typed as that enum, as in a
    single file, and a `def` parameter the field does not fit is PIE-S2395.
    Programs 0.1.3 accepted are refused: `where status` (PIE-S2202),
    `status in ("active")` and `status not like "a%"` (PIE-S2105), and
    `lower(status)` and `coalesce(status, "x")` (PIE-S2104). Programs 0.1.3
    refused pass `check --project`: with JOIN inputs, a selected `let:` name
    bound to an enum field (0.1.3: PIE-S2333), a JOIN `on` that compares enum
    fields (PIE-S2334 and PIE-S2335) and a JOIN over a relation `let` that
    outputs one (PIE-S2333); without them, `select distinct` of an enum field
    and a grouped `satisfying` that compares one (PIE-S2333), a window or
    QUALIFY partitioned or ordered by one (PIE-S2103 `Unknown function`), and
    `lag`, `lead`, `first_value`, `last_value` and `nth_value` of one
    (PIE-S2104 `value type must be concrete`). The other JOINs over a source
    with an enum field, on which 0.1.3 crashed with a ValueError traceback
    (see Included repairs), pass when they select, group, order, compare or
    window the field, and `count(c.status)` there is PIE-S2314.
    `emit-sql --project` still blocks every table or query that reads a
    source with an enum field (PIE-B1003). Some enum reads still fail closed
    with PIE-S2333 (see Known limitations).
  - A LIKE pattern read through a `let:` name of a relation with JOIN inputs
    and ending in an unpaired `!` is PIE-S2105, where 0.1.3 emitted a
    VERIFIED `LIKE ... ESCAPE '!'` that PostgreSQL rejects.
  - The WHERE of a relation with a `let:` binding of unknown type, such as
    `k = null`, or with an error in a binding is checked as in a single file,
    except in a `select distinct` relation or one with QUALIFY (see Known
    limitations): `where n == k` is PIE-S2105, where 0.1.3 passed `check` and
    `emit-sql --project` blocked the relation with PIE-B1003, and a `def`
    argument there that does not fit is PIE-S2395.
  - A relation reports the errors of each `let:` binding, of its WHERE and of
    its SELECT items, in source order, where 0.1.3 reported only the first
    part that failed: the first failing SELECT item hid the others, an error
    in any relation's `let:` hid its WHERE, and an error in a JOIN relation's
    `let:` hid its WHERE and SELECT errors. After such an error in a JOIN
    relation's `let:`, its WHERE and, without GROUP BY or aggregates, each
    SELECT item that is no window report their own errors when they read no
    relation (`exists`, `scalar` or `in`), no binding with an error of its
    own and no field that does not resolve; any other SELECT item, such as a
    grouped or aggregate one, still reports none. Without JOIN inputs, the
    SELECT items of a `select distinct` relation and an aggregate argument a
    project refuses still report no error of their own (see Known
    limitations).
  - Beside a binding of unknown type or with an error, the other bindings keep
    their types: with `k = null`, `f = id` and `h = f`, `v = h` passes, where
    0.1.3 reported PIE-S2102 `Unknown field: h`, and a window that reads no
    binding, also through the named window it uses, is analyzed, where 0.1.3
    reported PIE-S2103 `Unknown function` for every window there. A selected
    read of `k` itself takes its type from where it stands, as in a single
    file, so `v = coalesce(k, 1)` and `v = 1 if k else 2` pass
    `check --project` where 0.1.3 reported PIE-S2102 `Unknown field: k`;
    `emit-sql --project` still blocks such a relation (PIE-B1003). A window
    that reads a binding there fails closed with the binding's error or
    PIE-S2333.
  - With JOIN inputs, a `let:` binding of unknown type is written into a later
    binding's `def` argument and null test, as without them: with `k = null`,
    `w = coalesce(k, o.id)` and `v = tnn(w)` for a `Text not null` parameter,
    `v` is PIE-S2395. A read of such a binding is typed as without JOIN inputs
    too, so a later binding, SELECT item or WHERE that is ill-typed only then
    reports its error: with `j = coalesce(k, 1)`, `d = len(j)` is PIE-S2104
    where 0.1.3 reported a bare PIE-S2333; with nothing ill-typed, such a
    relation still fails closed with PIE-S2333. A `let` that renames a field,
    such as `g = r.n` with `group by: g`, selects that field's group key, so
    `k = g` passes and emits where 0.1.3 reported PIE-S2102; another `let:`
    name selected from the groups is PIE-S2333 instead of PIE-S2102.
  - In a relation with JOIN inputs, a null literal compared or combined in
    `satisfying:`, also as a nullable `def` argument, is PIE-S2327 at the
    literal, and any other predicate of unknown type is PIE-S2333, where 0.1.3
    crashed with a ValueError traceback.
  - `emit-sql --project` reports an ORDER BY key with a part of unknown type,
    such as `(null is null)`, BLOCKED with PIE-B1003 `order`, where 0.1.3
    reported INPUT_REJECTED `Invalid current planning roots.` (exit `2`). A
    plan whose `let:` stages carry more columns than half the generated-node
    limit is BLOCKED with PIE-B1007 `generated_structure_limit` once the
    contract is read, before it is assessed and realized, beside no other
    blocker than a premise conflict: a 300-binding chain is refused in
    seconds instead of about a minute.
  - A GROUP BY over a table or query that is one global aggregate row, such
    as a table that selects only `c = count()`, passes `check --project` and
    emits, where 0.1.3 crashed with a TypeError traceback in `check --project`
    and in `emit-sql --project` of either relation.
  - A SEMI or ANTI JOIN over some inputs, such as a table that selects the
    fields of a source with a unique key in another order than the source
    declares them, emits, where 0.1.3 reported every table and query of the
    project INPUT_REJECTED `Project planning roots are unavailable.` (exit
    `2`) although `check --project` passed.
- LEGACY_FLAT projects (`schema_version = 1`): a table or query whose `from`
  reads a set operation reports PIE-S2334 at that `from`, as a single file
  does, where 0.1.3 stopped `check --project` with an internal
  AssertionError.
- Programs that 0.1.3 accepted and 0.1.4 refuses:
  - a file whose first code line is indented (PIE-P1000);
  - a comparison with the null literal, or with a `let:` name bound to it,
    a `between` whose value or both bounds are null, and an `in`/`not in`
    list whose value or every option is null, all never true (PIE-S2105;
    write `is null` or `is not null`);
  - a single file with an expression nested more than 450 levels anywhere,
    a relationship `on`, a type `ensure` and a window frame offset included
    (PIE-S2006 in every command; projects are not held to this bound);
  - checks that do not depend on an argument's type now also run over rows of
    unknown type, such as a source without a shape: an unknown function or
    connector, a window function without `window`, the argument count of
    `sign`, `year`, `month`, `day` and a connector, `substr` bounds, and a
    cast to any type but `Float` (PIE-S2103, PIE-S2104, PIE-S2105,
    PIE-S2306);
  - a condition that is not a `Bool` beside values of unknown type, for which
    0.1.3 emitted SQL that PostgreSQL rejects and MySQL converts: over a
    source without a shape, a `where`, shape `check` or index `when`
    condition that is a built-in call whose signature fixes another result
    type, such as `where len(t)` or `where lower(t)`, also through a `let:`
    name bound to one (PIE-S2202), and an operand of `and`, `or` or `not` or
    the condition of a conditional that is such a call, or of a known type
    that is not `Bool` beside an operand or branch of unknown type, such as
    `not lower(t)`, `t and 5` or `1 if len(t) else 2` (PIE-S2105). The same
    holds where an always-null argument leaves such a call's type unknown,
    as in `where lower(coalesce(null, null))`, also with a shape and in an
    explicit-module relation, which 0.1.3 passed and blocked at emission with
    PIE-B1003 or reported as a bare PIE-S2333 (a WHERE of such a relation
    with JOIN inputs still fails closed with PIE-S2333 unless a `let:`
    binding there has an error of its own). Over a source without a shape a
    `count()` output read alone, as an `and` operand or compared with a value
    that is not a number in `satisfying:` is PIE-S2202 or PIE-S2105, which
    0.1.3 refused only at emission;
  - an ORDER BY key that is a bare constant once `let:` names are inlined, and
    in a query with aggregates and no GROUP BY a key that reads an input field
    outside an aggregate (PIE-S2380);
  - a ROWS or GROUPS frame offset that is not a nonnegative `Int` literal up
    to 9223372036854775807, a larger window count literal (PIE-S2104),
    `cast(null as T)` and a literal LIKE pattern ending in an unpaired `!`
    (PIE-S2105);
  - a division with a known operand that is not `Int`, `Float` or `Decimal`
    (PIE-S2105); `Int / Int` is now an `Int` and a `Float` operand gives a
    `Float`, so a division result is checked where it is used;
  - `count` of a field typed by an alias of `Any` or of an enum, which 0.1.3
    passed at check and refused at emission (PIE-B1000), is PIE-S2314 at
    check;
  - in single files: a connector argument that is not a string literal
    (PIE-S2306), a repeated enum member (PIE-S2001), an aliased bare name that
    names no field (PIE-S2102), an INNER or LEFT JOIN whose target, `from`
    binding, relationship or role is unknown or whose VIA path does not
    connect (PIE-S2301, PIE-S2335), and a `let:` chain whose inlined
    expansion exceeds 768 weighted levels or 100,000 nodes (PIE-S2328);
  - in explicit-module projects: relationship declaration errors
    (PIE-S2601 to PIE-S2603), shape item errors (PIE-S2501 to PIE-S2503) and
    repeated enum members (PIE-S2001), as single files report them, and a
    relationship `on` operand error (PIE-S2604, in both modes), whether or
    not a query uses the relationship;
  - PostgreSQL emission of an identifier longer than 63 bytes, which
    PostgreSQL would truncate, and of a window integer argument outside int32
    (PIE-B1000);
  - single-file PostgreSQL emission of an arithmetic whose every operand is
    `null`, such as `null + null`, `-null` or `coalesce(-null, n)`, which
    PostgreSQL cannot type, and of a table or query that another relation of
    the file reads when one of its outputs is `null` itself, such as
    `v = null` or a `let:` name bound to `null`, which PostgreSQL gives the
    reader as a `text` column (PIE-B1000); MySQL emission is unchanged;
  - a `between` with one null bound, which is now a `Bool` whose other bound
    is checked against the value: `n between null and "z"` with an `Int`
    field and a conditional such as `n if flag else n between null and 1`
    are PIE-S2105, where 0.1.3 passed `check` and emitted SQL that
    PostgreSQL rejects;
  - an operand of `+`, `-`, `*`, `/` or `%` that the operator does not take
    beside a `null` operand, also a `let:` name bound to one, such as
    `label + null` for a `Text` field, `lower(label) - null` or `0.5 % null`
    (PIE-S2105), as `label + label` and `0.5 % 0.5` are, where 0.1.3 emitted
    SQL that PostgreSQL rejects for a `Text` operand;
  - a `let:` value, or an expression that reads a `let:` name, that is
    ill-typed once the name has the type of its value written in its place:
    a name whose value is `null` takes its type from where it is read, as
    `null` does, and over a source without a shape a name has its binding's
    type. With `k = null` and `j = coalesce(k, 1)`, `d = len(j)` is PIE-S2104
    in the binding and `v = lower(j)` PIE-S2104 at `lower`, where 0.1.3
    emitted `lower(COALESCE(NULL, 1))`; over a source without a shape, with
    `w = n is null`, `-w` is PIE-S2105 and `coalesce(w, 0)` PIE-S2104. An
    explicit-module project reports such an error too: in a binding of a
    relation without JOIN inputs, as `d = len(j)`, which 0.1.3 passed; in a
    SELECT item of such a relation, as `v = lower(j)`, where 0.1.3 reported
    PIE-S2102 `Unknown field: j`; and with JOIN inputs, where 0.1.3 reported
    a bare PIE-S2333 (see Explicit-module projects above). A column that a
    relation computes from such a name has that type in later relations: with
    `z = coalesce(k, n)` for an `Int nullable` field `n`, a later relation's
    `v = lower(z)` is PIE-S2104, where 0.1.3 emitted `lower("z")` (and in a
    project reported PIE-S2102 `Unknown field: k` and PIE-S2333).
- SQL that differs for programs 0.1.3 already emitted:
  - MySQL `Int / Int` emits `a DIV b` instead of `a / b`, so the result is an
    integer, not a DECIMAL; PostgreSQL bytes are unchanged. This includes a
    `let:` name read as above: with `k = null` and `j = coalesce(k, id)`,
    `j / 2` emits ``COALESCE(NULL, `id`) DIV 2``, and over a source without
    a shape, with `u = 7`, `u / 2` emits `7 DIV 2`, as the values written in
    place do; a later relation's `z / 2` of the column `z` above emits
    `` `z` DIV 2 ``.
  - Single-file `cast(j as Float)` of a `let:` name whose value reads `null`,
    such as `j` above, or of a column an earlier relation computes from one,
    such as `z` above, emits `CAST(... AS double precision)` (PostgreSQL) or
    `CAST(... AS DOUBLE)` (MySQL) as the value written in place does, where
    0.1.3 refused it with PIE-B1000.
  - Single-file `avg` of an `Int` emits `AVG(CAST(x AS double precision))` on
    PostgreSQL and `AVG(CAST(x AS DOUBLE))` on MySQL, as project SQL does.
  - PostgreSQL `sign(x)` of an `Int` emits `CAST(sign(x) AS bigint)`.
  - Single-file PostgreSQL `lag`, `lead`, `first_value`, `last_value` and
    `nth_value` of a string literal without a `lag`/`lead` default write the
    literal as `CAST('b' AS text)`, where 0.1.3 wrote `LAG('b')`, which
    PostgreSQL rejects; MySQL bytes are unchanged.
  - An ORDER BY input field that has the same name as a different output alias
    is qualified with its FROM item's reference name.
- Single-file `explain` reports the type an output has when it is computed
  from a `let:` name whose value reads `null`, also as the column of a later
  relation, where 0.1.3 reported `unknown`: with `j = coalesce(k, id)`,
  `v = j + 1` is `Int`.
- Diagnostics: many messages name their cause more precisely. Invalid source
  gets different PIE-P1000 wording, counts and positions: at most one parser
  error per top-level declaration, naming the unexpected token and what was
  expected. A lone CR now ends a line in every reported position, and
  PIE-P1004 counts lines only at LF, CRLF and CR. A project reports a restated
  diagnostic once.
- CLI: a failed write to stdout, and a refused `--output` (no SQL to write,
  an existing output the user may not write or that belongs to another user,
  or in single-file mode an existing FIFO, socket or device), exit `2`; a
  failing stderr is ignored and the command keeps its own exit code.
  Repeated or abbreviated `--format` and `--project` options are resolved as
  argparse resolves them, so `--form json` is no longer ignored.

### Included repairs

Compiler:

- Division follows SQL: `Int / Int` truncates toward zero (PostgreSQL `/`,
  MySQL `DIV`), a `Float` operand gives a bare `/`, and Pietto never inserts a
  cast; write `a * 1.0 / b` or `cast(a as Float) / b` to keep the fraction.
- Type aliases, alias chains included, are read as their builtin type by
  arithmetic, `not`/`and`/`or`, comparisons, `between`, `in`, `like`, the
  fixed-signature scalar functions, Bool conditions, the aggregates and the
  window value functions, so an alias program checks and emits like its
  base-typed twin.
- `sum` and `avg` of a `Decimal * Decimal` argument emit single-file SQL
  instead of PIE-B1000. `amount in (1, 2)` with a `Decimal` field is accepted
  wherever `amount == 1` is; project emission refuses that pair with
  PIE-B1003 (`membership_type_pair_not_admitted`), as it refuses the
  comparison.
- The `let:` inline limit (PIE-S2328) measures the recursion emission needs
  instead of crashing with RecursionError; `let:` bodies are checked with the
  earlier bindings, and a binding's own error no longer cascades into unknown
  fields or extra window errors.
- Single-file analysis of a long chain of tables takes linear time.
- Gradual typing is kept: an aliased read of a field of any type is a
  computed output, aggregates and `satisfying` over fields of unknown type are
  not refused at check, and a `satisfying` predicate of unknown type fails at
  emission with PIE-B1000 instead of an internal error.
- In a grouped query, `first_value`, `last_value` and `nth_value` over an
  aggregate output emit SQL instead of crashing.
- In single files, a `lag` or `lead` result of an enum keeps the enum's
  declaration, as a `first_value` result does, so a later relation may
  combine the column with a field of that enum, as in
  `coalesce(previous, status)`, which 0.1.3 refused with PIE-S2104 (and a
  conditional with PIE-S2105).
- Projects: a project relation may read a declaration written later in its
  module; a relationship JOIN over an input completed in the same run, such
  as a named `select distinct` query, and a SEMI or ANTI JOIN over a table
  that reorders a keyed source's fields emit instead of INPUT_REJECTED;
  repeated `on` operands, a VIA through a grouped endpoint, an unknown grain, a
  grouped query listing a window before an aggregate, a JOIN over a source
  with enum or shape fields, an ORDER BY of an enum group key, a GROUP BY over
  a global aggregate and a LEGACY_FLAT read of a set operation no longer
  crash; deeply nested project expressions are PIE-S2006 instead of a
  RecursionError traceback, and a configuration or package manifest nested
  too deeply is a `project_resource` error; a `let:` binding read in a
  SELECT item no longer reports a false unknown field; a bare PIE-S2333 for a
  relationship JOIN over an input it cannot read yet names the reason; the
  JOIN fan-out remedy lists each key once; and query block IR verification
  checks every use against the output its owner names.
- The execution API reports a recursion overflow while preparing a query as
  PIE-R1004.

CLI:

- Every command writes its results through one stdout writer. A full device,
  closed stream or other write failure exits `2` with a fixed notice instead
  of a traceback, exit `120` or a silent exit `0`, and a reader that closes the
  pipe early ends the run quietly. `--help`, `--version` and usage errors use
  the same writers.
- Operating-system errors are reported by path with a fixed English reason
  and errno or winerror codes, without temporary names or localized text.
- `--output` writes UTF-8 with LF line endings on every platform. A new file
  gets the mode `open(path, "w")` gives (`0o666` less the umask, or what a
  default ACL grants). A replacement never gets wider permission bits than
  the file it replaces: it keeps them only on Linux when both files have the
  same owner and group and are shown to carry no ACL, and otherwise keeps at
  most the owner bits. Temporary files use short `.pietto-*.tmp` names.
- C1 controls, line and paragraph separators and bidirectional controls are
  written as `\uNNNN` in CLI diagnostics, paths and project text records; SQL
  text (stdout and `--output`) and JSON values keep them raw.
- Windows: trusted project reads no longer refuse unchanged files because of
  ctime, and directory junctions are refused like symbolic links.

### Known limitations

- The release target is compiler and package coverage on CPython 3.12 and
  3.13 for Linux x86-64; the support boundary is established by formal
  acceptance of the actual distribution bytes. Native-route evidence is
  limited to CPython 3.13.13 on the qualified integration host with the
  lock's exact artifacts. Other platforms, Python versions, database releases
  and driver closures are not claimed. No signing or attestation.
- A successful `check` is not an emission proof. Single-file `explain` and
  `emit-sql` refuse an authored `qualify:` block and a relationship JOIN with
  PIE-I1000; JOINs, set operations, DISTINCT and relation lets need
  `emit-sql --project`.
- An error in a call written inside another def's body is reported at that
  def as often as the called def's expansion makes it, in single files and
  projects: with
  `def low(x: Int nullable) -> Bool nullable: return x < 3 or x < 4`, a def
  body that calls `low(null)` gets two PIE-S2105. An argument mismatch
  (PIE-S2395) there is reported once.
- A project check still repeats the errors of a JOIN `on` condition, written
  by hand or made by a `def` call, and reports a query header parameter passed
  to a `def` and read in a position that refuses it (PIE-S2355) at each use of
  the argument.
- In single files, `lag`, `lead`, `first_value`, `last_value` and
  `nth_value` over a field typed by an alias of an enum are PIE-S2104, while
  the enum itself is accepted; an explicit-module project types such a field
  as the enum and accepts both.
- In an explicit-module project, some reads of an enum value fail closed with
  PIE-S2333 at the table or query, where a single file passes or reports
  another code: without JOIN inputs, an aggregate of an enum field
  (PIE-S2314 in a single file and after a JOIN), a selected `let:` name
  bound to an enum value and a computed output of enum type other than a
  window value, such as `coalesce(new_status, status)`; with or without them,
  an output such as `status in ("active", null)`, and a window value function
  over an enum field of a row that also has a field of another module's enum
  of the same name. A project check does not type the ungrouped `order by` of
  a relation without JOIN inputs that is not `select distinct`, so
  `order by: lower(status)` passes `check --project` there.
- In an explicit-module project, a relation without JOIN inputs reports no
  error of its SELECT items when it is `select distinct`, nor of an aggregate
  argument that a project refuses (PIE-S2314 or PIE-S2315 in a single file,
  such as `max(t + 1)`): it reports PIE-S2333 at its table or query, or,
  beside another error such as one in its WHERE, only that error.
- In an explicit-module project, after an error in the `let:` of a relation
  with JOIN inputs, a SELECT item reports no error of its own when the
  relation has a GROUP BY or aggregates, when it is a window, or when it
  reads a relation, a binding with an error of its own or a field that does
  not resolve.
- Over a source without a shape, a built-in call with an argument of unknown
  type has an unknown type outside a condition, also where its result type
  does not depend on the argument: `lower(t) + 1` passes `check` and emits
  SQL that PostgreSQL rejects, `len(t) / 2` emits `/` on MySQL, which keeps
  the fraction that PostgreSQL drops, and a condition built on such a call,
  such as `where len(t) + 1`, passes. Over such a source a `count` output
  with an argument has an unknown type to `satisfying` too.
- In an explicit-module project, a relationship JOIN without `on` whose input
  is a `select distinct` query completes on its own, but reports PIE-S2333 at
  its table or query when that table or query is itself `select distinct` or
  once a later table or query reads its result with a JOIN `on`, a CROSS JOIN
  or `select distinct`. In some shapes, for example when such a query is
  joined through a relationship with the relation it reads, `check --project`
  passes but `emit-sql --project` reports INPUT_REJECTED (exit `2`).
- A function argument of known type is not checked when another argument has
  an unknown type: over a source without a shape, `matches(a, 1)` passes
  `check` and PostgreSQL emission writes `"a" ~ 1`.
- A `def` argument of unknown type is not checked against its parameter.
  Inside a built-in call, `coalesce`, conditional or `in` list only `null`
  itself takes a type from where it stands, and `null` takes none inside
  `and`/`or` or in a built-in whose parameter admits
  more than one type (`year`, `month`, `day`, `sign`), so the arguments
  `null and true`, `year(null)` and `coalesce(-null, n)` pass a `not null`
  parameter unchecked, written by hand or through a `let:` name.
- In a relation without JOIN inputs that is not `select distinct`, a project
  check does not type a `def` argument in the ungrouped `order by`, as it
  does not type the same expression written by hand there. An argument of
  known type that does not fit its parameter therefore passes
  `check --project` there: with a field `text: Text not null` and
  `def nn(x: Int not null) -> Int not null: return x`, `order by: nn(text)`
  passes. `emit-sql --project` blocks it with PIE-B1003 without naming the
  argument.
- In an explicit-module project, a relation with a `let:` binding of unknown
  type, such as `k = null`, fails closed: with JOIN inputs, a GROUP BY,
  `select distinct` or QUALIFY it reports PIE-S2333 at its table or query
  even when nothing in it is ill-typed (a single file passes such a GROUP BY,
  QUALIFY or relationship JOIN without `on`), and otherwise
  `emit-sql --project` blocks it with PIE-B1003 once it passes
  `check --project`. A `select distinct` relation or one with QUALIFY does
  not check its WHERE beside such a binding or a binding with an error of its
  own: it reports that PIE-S2333, or the binding's error, in place of the
  WHERE's errors.
- A `substr` start and count must be `Int` literals written in the call: a
  `let:` name bound to one, such as `start = 1` in `substr(t, start, 1)`, is
  PIE-S2104, also in a `def` argument, although single-file emission would
  write the literal in its place.
- Division with a `Decimal` operand is not specified yet: it has no result
  type and emits a bare `/`. Division by zero follows the target (PostgreSQL
  raises an error, MySQL returns NULL), and dividing the smallest `Int` by -1
  is not specified.
- `def` takes only the eight builtin types (or a same-file alias of one) and
  positional arguments; a call is refused where the written form must be a
  literal, a field or a window call that Pietto checks by its own rule, such
  as inside a window specification, LIMIT, a VALUES row or a relationship
  condition (PIE-S2397). A comparison, `between` or arithmetic is not proven
  non-null, so such defs declare a `nullable` result. An argument appears in
  the SQL as often as the body uses its parameter. `constraint` and `derive`
  still cannot be called.
- `--output` does not copy a replaced file's owner, group, set-id or sticky
  bits or its ACL entries; the write check uses the real user, so root can
  still replace a read-only output.

### Support and release boundary

The [language guide](language.md) is the reference for the forms above; its
[Layout](language.md#layout) and
[Inline functions](language.md#inline-functions-def) sections describe the new
syntax. Published bytes are never overwritten. A later defect
is addressed in a later version; any PyPI yank remains an owner action.

---

## Phase70 public alpha release notes — 0.1.3

**Status:** These notes describe `0.1.3`, published and byte-verified on the
versioned GitHub pre-release and PyPI channels.

`0.1.3` extends query authoring and checked execution in explicit-module
projects (`schema_version = 2`). Pietto remains an alpha; the CLI still has no
database-execution command.

### New capabilities

- **Relation lets.** `let NAME:` at the start of a table or query body declares
  a local relation whose body is FROM-based, a set operation or a typed VALUES
  body. The other lets and the body of its declaration read it by name with
  `from`, a JOIN target, a set operand or an `exists`, `scalar` or `in` read,
  any number of times and whether it is written before or after them (a let
  with `capture` lines, below, is read exactly once). Project
  SQL emits each let once as one named CTE, after the lets it reads and exactly
  like the equivalent module-level declaration, and every read refers to that
  CTE; a let keeps its own LIMIT, so a filter written where it is read stays
  outside that LIMIT. A source read only inside a let is a source of the query
  for the emission contract, the compiled query, source qualification and R2
  source requirements. A let is never a module declaration: it cannot be
  exported, imported, selected by `emit-sql --project` or compiled on its own.
  A declaration has at most 64 lets (`PIE-S2357`); a let named like a module
  relation, an import binding, another let or a JOIN binding is `PIE-S2001`,
  and no name hides another. A let that no block of its declaration reads is
  `PIE-S2359`, reads that form a cycle, a let reading itself included, are
  `PIE-S2302`, and a let nested deeper than 16 query blocks is `PIE-S2360`.
  The row-level `let:` clause keeps its meaning.
- **Named query parameters.** An entry `query` header declares at most 64
  `Bool`, `Int`, `Float` or `Text` parameters, each `not null` or `nullable`,
  for example `query since(low: Int not null, note: Text nullable):`. A read is
  available in `let:` bindings, `where`, JOIN `on`, ungrouped SELECT items,
  `satisfying`, `qualify`, ORDER BY keys through a `let:` binding or a restated
  selected expression, a computed group key of a query without JOIN inputs,
  `count`, `avg`, `min` or `max` of one `let:` name, and as a window value,
  `lag`/`lead` default or structural count (`lag`/`lead` offset, `ntile` bucket
  count, `nth_value` position; an `Int not null` parameter, `PIE-S2358`).
  LIMIT, window frames, window PARTITION BY and ORDER BY keys and other
  positions refuse a read (`PIE-S2355`). A header is available on an entry
  query whose own FROM reads a relation, with or without relation lets. Every
  FROM-based let of that query reads the header like its body, under the same
  position rules, a let with `capture` lines included (its reads render where
  the let renders); no other declaration reads it. A parameter named like a
  let of the query or like an input field, `let:` name, relation, JOIN
  binding, SELECT output or named window of the query or of one of its lets is
  `PIE-S2354`, and a query with parameters is never the input of another
  relation nor read by `exists`, `scalar` or `in` (`PIE-S2356`). On a VALUES,
  set-operation or table-function body, and beside a let whose FROM is a table
  function (whether or not that let reads a parameter), a header stays
  `PIE-S2346` at each parameter.
  `emit-sql --project` writes the unbound template as `pietto.sql-emission.v2`
  with a typed placeholder for each read under both literal policies:
  PostgreSQL reuses one `$n` per parameter across every CTE, subquery and
  LATERAL derived table, and MySQL writes one `?` per read in rendering order.
  One statement renders at most 65,535 placeholders, reads and bind-safe slot
  uses together (`PIE-B1007`, `parameter_occurrence_limit`). A check that
  needs a value is a binding obligation (`int_range_representable`,
  `text_result_width` or `structural_count_interval`) naming every parameter
  it depends on, including one read in a let with `capture` lines, and
  re-derived at every binding. `compile_query` and
  `export_bundle` keep the unbound template (bundle format marker
  `pietto.compiled-execution.v2`), and `execute(..., parameters={...})` binds
  it by name on `postgres_rows`, `mysql_rows` and `postgres_adbc`; a missing
  or extra name, a value of the wrong type, NULL for a `not null` parameter
  and a failed obligation are refused before any connection. `save`,
  `save_recoverable` and `relay_live` bind new values the same way before the
  workspace opens; `open_saved_read`, `release_saved_read`,
  `publish_saved_generation`, `verified_export` and `recover` restate the
  saved binding, and any difference is `PIE-R1009` (`BINDING_VECTOR`).
  `values=` slots are unchanged and independent.
- **Computed group keys and `let:` extrema.** In an explicit-module query,
  `group by` may name a computed `let:` binding; the emitted SQL groups by that
  value's LET-stage column, never by a repeated expression. Such a key never
  supplies source-row grain, and R2 refuses it before any workspace access
  (`PUBLIC_R2_COMPUTED_GROUP_KEY`). With JOIN inputs the key records every JOIN
  side its value reads but never proves a side unique per group, so it never
  removes a fan-out refusal; only direct field keys protect a JOIN side. `min`
  and `max` accept one `let:` name and keep its proven range while admitting
  NULL; with JOIN inputs the argument reads its JOIN-side fields under the
  fan-out rule of a direct field argument.
- **Typed VALUES.** A table, query or relation-let body may be a typed
  `values(name: Type not null, ...)` header followed by one row of fixed
  literals per line, or the header alone for a zero-row relation. Each column
  is `Bool`, `Int`, `Float` or `Text`, `not null` or `nullable`; rows keep
  their order and duplicates, and the row schema comes only from the header. A
  column type, a row width, a cell that is not a fixed literal, a cell that
  does not match its column, and more than 1,000 rows or 64 columns are
  `PIE-S2361` to `PIE-S2365`; a body within those limits whose emission
  exceeds the compiler's generated-structure or document limit is BLOCKED with
  `PIE-B1007`. Project SQL writes every column alias and every cell inside a
  CAST to its declared type, and a cell is never a bound parameter. A VALUES
  body read beside a physical source emits and compiles for PostgreSQL and
  MySQL. A statement whose only inputs are VALUES bodies runs on PostgreSQL
  under a session-context qualification whose premise includes `pg_catalog`
  and that records no relation root and no relation catalog check; MySQL
  refuses it (`PIE-B1003` at emission and compilation, `PIE-R1003` before
  connecting). R2 refuses a query with a VALUES body before any workspace
  access (`PIE-R1004`, `PUBLIC_R2_VALUES_COORDINATE_BASIS`). Grouping over a
  VALUES input is not available yet (`PIE-S2333`).
- **Closed relation reads.** In a table or query body `exists r` and `not
  exists r` test whether `r` has a row, `scalar r.c` reads the column `c` of
  `r`, and `value in r` and `value not in r` compare a value with the one
  column of `r`; `r` is a source, a module table or query, or a let of the
  declaration. A read is available in WHERE and in the SELECT of an ungrouped
  query, let bodies included; anywhere else it is `PIE-S2349`, `PIE-S2348` or
  `PIE-S2350` at the read. `exists` is a `Bool not null`. `scalar` is always
  nullable: a read of no row is NULL, and a read of more than one row is the
  database's own runtime error, `PIE-R3003` with SQLSTATE `21000`; no LIMIT is
  added. `in` and `not in` keep SQL three-valued logic, are a nullable `Bool`
  and are never rewritten to an ANTI JOIN, a literal list or a COALESCE; over
  an empty `r`, `NULL in r` is false and `NULL not in r` is true. `scalar`
  cannot yet read a set, an authored JOIN, a table function or a relation that
  reads one of them or a VALUES body (`PIE-S2348`), while a VALUES body itself
  is read like any relation; for such a block `emit-sql --project` and
  `compile_query` check the one column of an `in` read (`PIE-B1003`). Project
  SQL emits each read block once as its own named CTE and each read as a
  subquery over it, so the read block's `order by` and `limit` stay inside its
  CTE. A source read only through relation reads is a source of the query. R2
  refuses a query with a relation read before any workspace access
  (`PIE-R1004`, `REFINEMENT_EXPRESSION_BLOCK_READ`).
- **Correlated lets and LATERAL joins.** A relation let may start with
  `capture NAME` lines, one per line, naming the FROM input or a JOIN binding
  of its declaration body; inside the let `NAME.field` reads that field of the
  current outer row, while bare names keep naming the let's own input. Only
  FROM and JOIN row fields are captured. A captured field keeps the outer
  field's type and is nullable when that field is or when an earlier LEFT,
  RIGHT or FULL JOIN may null-extend its binding; an outer JOIN ON condition
  never narrows it. Such a let is read exactly once: by `exists`, `not
  exists`, `scalar`, `in` or `not in` in the WHERE or in the SELECT of an
  ungrouped declaration body, or as the target of a `cross join`, `inner join`
  or `left join`, which reads it LATERAL with no new keyword. Every outer row,
  duplicates included, gets its own result: a correlated read is never
  rewritten to a JOIN, deduplicated or decorrelated, a correlated `scalar`
  keeps the runtime error for more than one row (`PIE-R3003`, SQLSTATE
  `21000`), `in` and `not in` stay three-valued, and a `left join` keeps each
  left row without a row of the let once, with the let's fields NULL. The let
  body is a FROM relation with an optional WHERE and an ungrouped, window-free
  SELECT; a let joined LATERAL or read by `scalar`, `in` or `not in` may end
  in ORDER BY and a static LIMIT, a top-k per outer row in which the database
  chooses among rows that tie on every key. Project SQL emits the let inside
  its read as nested derived tables, or as the JOIN's `CROSS JOIN LATERAL`,
  `INNER JOIN LATERAL ... ON` or `LEFT JOIN LATERAL` derived relation, never
  as a CTE. A `scalar`, `in` or `not in` read of a let that ends in ORDER BY
  and LIMIT is PostgreSQL only: PostgreSQL wraps the let in the read's own
  derived table, while MySQL `emit-sql --project` and `compile_query` refuse
  each such read, in source order, with `PIE-B1003`
  (`mysql_correlated_order_or_limit_read_not_admitted`) before any connection,
  and `load_bundle` refuses a MySQL bundle that claims one (`PIE-R1008`); a
  let joined LATERAL keeps its ORDER BY and LIMIT on both targets. The binding of a table
  function cannot be captured (`PIE-S2366`), though its body's JOIN bindings
  can; otherwise, a capture line naming no single FROM or JOIN
  row input is `PIE-S2366`, a repeated
  capture name `PIE-S2367`, a capture of an input of the let itself
  (self-correlation) `PIE-S2368`, a captured field the input does not have
  `PIE-S2369`, a direct table-function FROM in a capture let (read it through
  another let), another let body or ORDER BY that correlation does not support,
  and every read of the let after its first `PIE-S2370`, a capture of an input
  that is not left of the LATERAL JOIN `PIE-S2371`, and a RIGHT, FULL, SEMI or
  ANTI JOIN of such a let `PIE-S2372`. A field read of a captured input whose
  columns are not known before completion (a set, an authored JOIN, a typed
  VALUES body, a table function, a relation reading one of them, or a relation
  whose own errors leave its columns unknown) is `PIE-S2369` at `check
  --project`, whatever field it names. When the captured outer input's fields
  are known, the let's own FROM may read a set, an authored JOIN, a typed
  VALUES body or a let reading a table function. R2 refuses a query with a
  correlated read
  (`REFINEMENT_EXPRESSION_BLOCK_READ`) or a LATERAL JOIN
  (`REFINEMENT_LATERAL_JOIN`) before any workspace access; ordinary execution
  on every route, `save` and bundles accept them.
- **Bounded `generate_series`.** A table, query or let body may read
  `from generate_series(start, stop, step) as n`, a zero-input relation whose
  rows and only column `n` are `Int not null`. `generate_series` with exactly
  three fixed integer literals in the signed 64-bit range is the only admitted
  table function: another function is `PIE-S2373`, another argument count
  `PIE-S2374`, an argument that is not such a literal (`null`, another literal
  type, a name, a parameter or an expression) `PIE-S2375`, a zero step
  `PIE-S2376` and more than 1,048,576 rows `PIE-S2377`. Its closed catalog
  entry carries the determinism and side-effect evidence admission consumes.
  Grouping or aggregating directly over a table-function input is `PIE-S2333`
  for now (read it through a let first), and `scalar` cannot read it
  (`PIE-S2348`). Project SQL writes each input as a CTE over
  `pg_catalog.generate_series` with each fixed argument CAST to
  `pg_catalog.int8`, never as a bound parameter; a binding longer than 63
  UTF-8 bytes is `PIE-B1002` (`table_function_binding_unrepresentable`). It is
  PostgreSQL only: MySQL `emit-sql --project` and `compile_query` block each
  input with `PIE-B1003` (`table_function_not_admitted_on_target`), and
  `load_bundle` refuses a MySQL bundle that claims one (`PIE-R1008`).
  PostgreSQL runs a statement whose only inputs are table functions or VALUES
  bodies under the session-context qualification of a VALUES-only statement,
  with no runtime catalog check of the function. R2 refuses a query with a
  table function before any workspace access (`PIE-R1004`,
  `PUBLIC_R2_TABLE_FUNCTION_COORDINATE_BASIS`).

### Refusals and limits

The new forms are available only in EXPLICIT_MODULES projects. Single-file
analysis and LEGACY_FLAT projects keep refusing them with the temporary
`PIE-S2345..PIE-S2352` diagnostics, and PACKAGE_ROOT `explain --project` does
not read relation bodies, so explaining a package that uses them does not make
its relations available. In an explicit-module project each file reports its
pre-admission diagnostics first, in source order (the capture forms
`PIE-S2366`, `PIE-S2367`, `PIE-S2368` and `PIE-S2370..PIE-S2372` among them),
and then the header checks of its entry queries; after either, semantic
analysis does not run. In an explicit-module project a header on a VALUES,
set-operation or table-function body or beside a let that reads a table
function (`PIE-S2346`) is still refused this way. This release adds
`PIE-S2345` to `PIE-S2377`.

Known limitations of this release:

- A typed VALUES body of 1,000 rows and 64 columns passes `PIE-S2365` but is
  always BLOCKED at emission by the compiler's generated-structure or document
  limit (`PIE-B1007`).
- The width and type pair of an `in` read of a set, an authored JOIN, a
  typed VALUES body or a table function is checked only at emission
  (`PIE-B1003`), not by `check --project`.
- An INNER JOIN whose ON has a nullable `Bool` field as an AND conjunct of its
  own (`on o.flag`) checks, but `emit-sql --project` and `compile_query` block
  it with `PIE-B1002` (`join_output_nullability_drift`) on both targets;
  `o.flag == true` is not admitted either (`PIE-B1003`). Write the test in
  WHERE instead (`where o.flag`).
- In a let with `capture` lines, an ORDER BY key that is not a field of the
  let's input, such as one of the let's own SELECT outputs, is reported only
  as `PIE-S2333` at the declaration (`Project relation semantic completion is
  unavailable`), with no diagnostic at the key.
- While a module import cycle exists (`PIE-S2703`), a project check reports
  besides it only parse, semantic analysis and source connector diagnostics;
  the checks made while completing relations appear once every cycle is
  fixed.
- An unknown field in a SELECT item of an explicit-module query can be
  reported twice as `PIE-S2102` at the same position.
- In a single-relation explicit-module query, a reference or shape error in a
  grouped `satisfying` is reported only as `PIE-S2333` at the declaration.
- LEGACY_FLAT project checks report neither `satisfying` errors nor a WHERE
  condition that is not `Bool`, which single-file `check` reports, and a
  LEGACY_FLAT query that reads a set operation stops `check --project` with an
  internal `AssertionError`.
- A selected query that reads a table declared later in the same module checks,
  but `emit-sql --project` refuses it as
  INPUT_REJECTED (`Project planning roots are unavailable.`) and
  `compile_query` raises `CompileRejected`; declare the read relation first.
- `compile_query` refuses (`PIE-R1004`, `COMPILED_EXPORT_SOURCE_BINDING`) an
  emission contract that also describes a source the query does not read,
  which `emit-sql --project` accepts; describe only the query's sources.

### Included repairs

- A module import cycle in an explicit-module project no longer crashes the
  project check, `emit-sql --project` or `compile_query`; it is reported as
  `PIE-S2703`.
- `import pietto.execution` no longer imports the saved-result job subsystem;
  the first use of a saved-result name imports it.
- In an explicit-module project, `satisfying` on a query without GROUP BY no
  longer crashes `check --project`, `emit-sql --project` or `compile_query`:
  it is `PIE-S2323` (`PIE-S2308` when the predicate holds an aggregate), as in
  single-file analysis. A single-relation aggregate query with `satisfying`,
  which reported `PIE-S2333` in `0.1.2`, now also reports `PIE-S2323`, the
  documented code.
- On `postgres_adbc` a server error raised while the result is read keeps its
  SQLSTATE: a `scalar` read of more than one row is `PIE-R3003` with
  `sqlstate` `21000`, as on the other routes, instead of an error without a
  `sqlstate` (cause `ArrowInvalid`), and the 10 second statement limit reached
  while reading is `PIE-R3002` (`STATEMENT_TIMEOUT`) instead of `PIE-R3003`.
  [Execution](execution.md) now states the terminal facts of a server error
  per route: `postgres_adbc` reports cleanup `LOCAL_CLOSED_REMOTE_UNOBSERVED`
  with no cleanup failure, and on `mysql_rows` a statement error does not end
  the transaction, which is then rolled back (`ROLLBACK_ACK`).
- `save_recoverable` and `recover` now reject a query whose largest
  continuation page binds more placeholders than the `parameters` resource
  limit with `PIE-R1004` (`REFINEMENT_RESOURCE_LIMIT`) before workspace access
  or a connection.

### Compatibility and retained data

Bundles and saved jobs produced by `0.1.2` are refused under `0.1.3` by code
identity. Pietto neither migrates nor rewrites them; keep the matching old
environment to use retained state, and compile again for this release.
`pietto.sql-emission.v1` and project JSON v2 keep their formats, and relation
lets, VALUES bodies and relation reads add nothing to project JSON; only a
verified document of a query with header parameters is
`pietto.sql-emission.v2`, which a v1 reader refuses by its tag. Such a query
bundles as `pietto.compiled-execution.v2`, which a v1 reader refuses, and a
saved binding with parameters is recorded as `pietto.binding-vector.v2`; a
binding without parameters is recorded as before.
The VS Code extension `0.1.0` accepts only the `0.1.2` wheel or the `9e74aa68`
baseline fingerprint and refuses `0.1.3`; updating it belongs to the
extension's owner, and this release adds no stable editor API.

Target-conformance receipt v3 stores each public emission document once. It is
test and CI evidence only, not a query, bundle or saved-job format.

### Support and release boundary

The release target is compiler and package coverage on CPython 3.12 and 3.13
for Linux x86-64. That support boundary is established only by acceptance of
the formal distribution bytes. Native route evidence is limited to CPython
3.13.13 on the qualified integration host with the lock's exact artifacts;
other native platforms, Python versions, database releases and driver closures
are not claimed. Published bytes are never overwritten. A defect found after
release is fixed in `0.1.4`; any PyPI yank is the owner's action, noted on the
GitHub pre-release.

---

## Phase69 public alpha release notes — 0.1.2

These notes describe `0.1.2`. Its versioned GitHub pre-release and PyPI listing
determine release availability. The historical `0.1.1` wheel and `v0.1.1`
assets are not replaced.

### Public alpha API

- `pietto.execution` exposes explicit `postgres_rows` for PostgreSQL 18.6,
  `mysql_rows` for MySQL 8.4.12, and `postgres_adbc` for PostgreSQL 18.6.
  Each route uses its selected pinned dependency closure and never falls back to
  another route.
- Results use caller-owned Arrow batches and terminal outcome facts.
  `UNKNOWN`, `REMOTE_QUIESCENCE_UNCONFIRMED`, and remote-unobserved cleanup are
  not acknowledgements. `ResultHandle.cancel()` may be requested by a
  controller thread; it returns `None`, while the outcome retains the observed
  cancellation, transaction, and cleanup facts.
- Query bundles carry caller-held content, producer, and compatibility records.
  They are snapshots: source edits need a new compilation. Bundle loading and
  every execution attempt check current code identity. Bundle trust records
  are checked at load time; each execution needs fresh access and deployment
  premises.
- v7 saved workspaces provide ordinary save, R1 source-free re-read,
  fixed-snapshot verified export, R2 same-source recovery, local publication,
  narrow caller-owned unpublished-generation retirement, and relay to the
  local reference cooperative sink. `inspect_job()` is read-only recorded
  metadata and grants none of those authorities.
- The API remains alpha. Names, fields, error codes, and behavior may change
  in later alpha releases; existing compiler and CLI contracts remain separate.
  The CLI still has no database-execution command.

### Compatibility and retained data

The installed Pietto and ANTLR code identity is checked for compile, bundle
load, and execution. The `0.1.2` version update changes the CLI fallback version,
and the wider source tree can also change that identity. A bundle or saved-job
record made under `0.1.1` can therefore be refused under `0.1.2`. Pietto
preserves the original bytes and does not migrate them; use the matching old
environment when the old state must remain usable.

### Support and durability limits

Only CPython 3.13.13 on Linux x86-64, with the lock's exact artifacts on the
qualified integration host, has native evidence for all three routes. Windows
native execution is `NOTRUN`; offline Windows compiler-project checks do not
establish job, database, or platform support.

Public save creates v7 only, with no migration. A workspace permits one
coordinator at a time and refuses concurrent capture, recovery, or relay with
`RUNTIME_BUSY`. There is no public scheduler, general garbage collector,
age-based deletion, or general directory cleanup. `retire_generation` removes
only the caller-owned unpublished generation's latest-checkpoint root; it does
not delete files. Publication-owned retention is permanent.

R1 and verified export are source-free reads with compatible code, fresh
caller-held scalar trust, integrity, and reader protections. R2 is live
same-source recovery: it requalifies one caller-supplied compiled-source
requirement for every source in compiled order, including guarded and refined
sources. A saved close only resumes or awaits bounded cleanup; until it
settles, remote state is `UNKNOWN` and no acknowledgement is claimed.

### Included compiler and CLI repairs

- A single leading UTF-8 BOM is ignored without changing parsed AST or source
  locations; a second or non-leading BOM remains invalid, and the original
  UTF-8 byte budget still applies.
- When the terminal cannot encode CLI output, Pietto preserves the terminal's
  configured encoding and returns the established clear output-encoding error
  instead of silently replacing source or diagnostic text.
- A single-file relation name may be `table` or `schema.table` (MySQL uses the
  database position); each component is quoted independently. Empty components
  and names with more than one dot fail closed with `PIE-S2306`.
- Cross-family comparison operands fail closed with `PIE-S2105`; there is no
  implicit conversion. This does not change the existing SQL three-valued
  behavior for comparisons with `null`.

### Attribution and release boundary

`THIRD_PARTY_NOTICES.md` records unbundled runtime and execution dependencies
and separates wheel/sdist material from the GitHub source archive.
`LICENSES/SOURCES.md` records the retained original-text provenance. This is
an attribution record, not a legal conclusion.

Before publication, the release stage must inspect the exact accepted wheel,
sdist, and source archive against those per-channel notices. Independent
rebuilds may verify the accepted bytes but never replace them.
