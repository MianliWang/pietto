# Pietto release notes

## Unreleased changes following 0.1.9

These changes are on `main` after `0.1.9` and are in no published release
yet. They are Phase73 batch 1. Each subsection lists the changes against
`0.1.9` that a program can observe, its compatibility rows and the new
refusals.

### JOIN fan-out: the two-level route

- The PIE-S2381 message now ends, after the remedies it already names, with
  the two-level route, in every check mode, in a single file and in the
  PIE-S2381 that an EXPLICIT_MODULES project reports beside PIE-S2312 (a
  JOIN aggregate mixed with another projection without GROUP BY):
  ``; two-level route: group a first query by a unique key of each input the
  aggregate reads and by every other field that query selects, select an
  aggregate such as `count()` in it too, then aggregate in a second query
  that reads `from` it``.
  For example:
  ``An aggregate may read rows repeated by JOIN customer; match a unique key
  of customer in `on`, use `any(...)` for an input that only filters rows, or
  aggregate in a separate query first; two-level route: group a first query
  by a unique key of each input the aggregate reads and by every other field
  that query selects, select an aggregate such as `count()` in it too, then
  aggregate in a second query that reads `from` it``.
  Compatibility: only the message text changes. The code, severity, location,
  count and order of PIE-S2381 are unchanged, and so are a project's
  PIE-S2333 cause texts (`... (an aggregate may read rows repeated by JOIN
  x; ...)`), which do not add the route, although the same route closes
  them. A tool that matches the whole PIE-S2381 message must accept the new
  ending.
- No refusal changes. An average over items grouped by `orders.id` that also
  LEFT JOINs the order's payments (Phase72 case D11-04) stays PIE-S2381 in a
  single file, now with the route, and PIE-S2333 in a project, without it;
  the same query grouped by `orders.customer_id` (D11-05), whose result
  would be weighted by payment counts, stays refused the same way. Pietto
  has no rule that a group key fixes how often each row repeats.
- The two-level route is documented ([language](language.md), [style](style.md)):
  a first query grouped by the declared key of the repeated input (for
  example one row per order with `lines = count(item.id)`), and a second
  query that reads `from` it and sums or averages its rows. It is two
  ordinary grouped relations: single files emit it for PostgreSQL and MySQL;
  an EXPLICIT_MODULES project emits it for PostgreSQL VERIFIED and compiles
  and binds it as a template; project MySQL emission blocks each Int `sum`
  with PIE-B1004 `sum_int_aggregate_range_proof_missing`, as for any project
  MySQL Int `sum`. A two-database differential (PostgreSQL 18.6, MySQL
  8.4.12) of the single-file route, counting per order and summing per
  customer, and averaging over items in two levels, matched the expected rows
  on both databases.

### LIMIT 1 in a let with capture lines (documentation only)

- No behaviour changes. The docs now state what `limit 1` does when rows tie:
  a let with capture lines that ends in `limit 1`, read by a JOIN or by
  `scalar`, with an ORDER BY whose keys several rows share, or without ORDER
  BY, gets the row the database picks, with no warning and no refusal, and
  the pick may differ between runs and databases; end the ORDER BY with a
  unique field to fix it. `limit 1` is not a proof of at most one row: an
  aggregate of the left rows over a JOIN of such a let stays PIE-S2333.

### Conditional count and sum: `sum(1 for o in group if ...)`

- A single file now counts and adds the rows of a group that pass a test,
  written as Python's generator: `sum(1 for o in group if o.paid)` is the
  number of rows of this group whose test is True, and
  `sum(o.amount for o in group if o.paid)` adds their non-None `amount`, an
  `Int` field (an alias of `Int` included). Both are an `Int` that is never
  None: 0 when no row matches. A None test is no match. `group` is the rows of
  the current group after `from` and `where`, with their multiplicity (the
  rows `count()` counts); a query with aggregates and no GROUP BY reads its
  whole input as one group. The test reads the member's fields as `o.f` and,
  besides them, only the GROUP BY key fields. A generator is a whole aliased
  SELECT item, as every other non-window aggregate; `having` and `order by`
  read its output name.
- PostgreSQL emits `COUNT(CASE WHEN <test> THEN 1 END)` and
  `COALESCE(CAST(SUM(CASE WHEN <test> THEN CAST(<f> AS pg_catalog.int8) END)
  AS pg_catalog.int8), 0)` (a sum outside signed 64 bits fails with SQLSTATE
  22003, as `sum(Int)` does). MySQL refuses both (below).
- `where any(p for o in orders)` and `not any(...)` are unchanged, with the
  same SQL bytes: `for o in orders` always means every row of `orders`, never
  the current group.
- `pietto fmt` needs no new rule: a generator is tokens inside a call's
  parentheses. Its canonical layout is the whole call on its item's line,
  one space around `for`, `in` and `if`.

New refusals (programs that were PIE-P1000 before; the hint follows `; ` at
the end of the message and is also the JSON `suggestion`):

- MySQL single file, conditional count: PIE-B1000 `MySQL SQL emission is
  not implemented for RelationIR: <name>. MySQL has no conditional count
  yet; emit with --dialect postgres` (no JSON `suggestion`; the Phase74
  MySQL catch-up takes it up).
- MySQL single file, conditional sum: PIE-B1000 `MySQL SQL emission is not
  implemented for RelationIR: <name>. MySQL conditional sum of an Int argument
  is not supported` (MySQL sums integers in DECIMAL; the Phase74 MySQL
  catch-up takes it up).
- A project, of any schema version: PIE-S2334 at the call, before semantic
  analysis, ``sum(... for ...) is not available in a project yet; a single
  file checks and emits the conditional count and sum of a group`` (the
  callee's name in place of `sum`).
- PIE-S2334 at the call: ``count takes no generator; count matching rows with
  `sum(1 for o in group if ...)` `` (`len` likewise: ``len takes no generator;
  ...``); ``max takes no generator; a conditional max is not available; only
  `sum(... for o in group if ...)` takes a generator`` (also `min`, `avg`,
  `stddev`, `count_distinct`, `string_agg`); `A generator is only the argument
  of sum or any` for another known callee, such as a builtin or a `def`;
  ``any takes its test in the body; write `any(p and q for o in r)` `` for an
  `any(...)` with an `if` (``write `any(q for o in r)` `` when its body is
  `True`).
- At the source: PIE-S2301 ``Unknown or unavailable generator source: grp;
  for this group's rows write `for o in group` ``; PIE-S2334 ``Generator over
  orders in sum: orders is the whole relation, not this group; for this
  group's rows write `for o in group` `` (in a relation with a non-aggregate
  SELECT item and no GROUP BY: ``...; count per key in a grouped query and
  join it on the key``); a relation named `group`: ``Generator over group in
  sum: group is the relation group, not this group; rename the relation group
  to read this group's rows`` (a `let group`: `the let group`, `rename the let
  group`); a dotted source: ``A generator over c.items is not available yet;
  `len`, `sum` and `any` over a row's collected list are a coming feature``.
- PIE-S2308 at the call for a group generator in a `where`, `let`, JOIN
  `on`, `having`, `order by` or `def` body: ``Aggregate sum() is not allowed
  in where clause; use it only as a direct aliased select projection; a
  group's rows exist only after `group by`; test a row's own fields
  directly`` (`let binding`, `JOIN ON`, `this position`; in `having clause`
  and `order by` without the part after the second `; `); PIE-S2313 without
  an alias; PIE-S2310 inside an expression.
- PIE-S2334 at the call for JOIN inputs: ``sum(... for o in group ...) over
  JOIN rows is not available yet; join in one query, then group it in another
  that reads it with `from` ``.
- PIE-S2334 at the call for a body without `if`: ``sum(1 for o in group)
  counts every row of the group; write `count()` ``; ``sum(o.amount for o in
  group) adds every row of the group; write `sum(amount)` ``.
- PIE-S2315 at the call for another body: `Aggregate function sum of a
  generator adds 1 or one field of o; expression bodies are not supported
  yet`, with ``; filter with `if` after the source: `sum(o.f for o in group
  if ...)` `` for a conditional body and ``; read the member as `o.amount` ``
  for a bare field.
- PIE-S2314 at the call for the summed field's type: ``Aggregate function sum
  of a generator adds an Int field of o, got Bool; count with `sum(1 for o in
  group if o.paid)` `` (`..., got Text` for another type); `Aggregate function
  sum of a generator adds an Int field of o; a Float or Decimal sum is not
  available yet`.
- In the test or body, at the read: ``Generator reads paid outside its
  member; write `o.paid` `` (PIE-S2334, also for `orders.paid`); ``Generator
  reads its member o as a value; read a field of it: `o.f` `` (PIE-S2334);
  PIE-S2102 `Unknown or unavailable field in generator: o.a.b` (also `o.f`
  where `f` names a `let`); PIE-S2102 `Unknown field: nosuch` at `o.nosuch`;
  PIE-S2311 for a nested aggregate; PIE-S2334 `A generator test reads one
  member row: no window, any(...), generator, relation read or captured field`;
  PIE-S2202 `Expected Bool expression in generator test` at a non-Bool test.
- PIE-S2334 at the call over an input without known fields (a source without
  a shape): `sum(... for o in group ...) reads an input whose fields are not
  known; give its source a shape`.
- PIE-P1000 stays for a second `for`, a second `if` (`Missing ')' before
  'if'.`), a second argument (`Missing ')' before ','.`), `[o for o in ...]`
  and SQL `FILTER (WHERE ...)`, and for a generator in a table-function
  `from` argument or a QUALIFY call (texts unchanged, `Unexpected 'for'; expected
  ')' or ','.` / `Unexpected 'for'.`).

Changed diagnostics of programs refused before (no accepted program is
refused; compatibility):

- Every generator call other than the exact `any(p for o in r)` was PIE-P1000
  (`Unexpected 'for'; expected ')' or ','.`, `Unexpected 'for'.` or, with an
  `if` in `any`, `Missing ')' before 'if'.`); it is now admitted or one of the
  refusals above.
- A generator in a SELECT window call, `r = sum(1 for o in group)
  window(order by id)`, was `Unexpected 'for'.` at the `for`; it is now
  ``Unexpected 'window'; expected ',' or end of line. A window call is a whole
  `select:` item on a line of its own.`` at the `window`.
- `any(p for o in group)` where no relation or `let` is named `group` keeps
  PIE-S2301 `Unknown or unavailable ANY relation: group`, its span and order
  (after PIE-S2319 in a grouped SELECT); its JSON `suggestion`, null before,
  is ``a group test is not available yet: select `n = sum(1 for o in group if
  ...)` and test `n > 0` in `having` or a later query``. In a `having`, the
  same `any(...)` keeps PIE-S2334 `ANY is not supported in this context`, its
  span and order, and gains the same suggestion. A single file only: a
  project's diagnostics are unchanged.
- PIE-S2315 of `sum(amount if paid else 0)` and `count(1 if paid else None)`
  (a conditional argument, outside a window) gains ``; write `sum(o.v for o in
  group if ...)` `` (`sum`) or ``; write `sum(1 for o in group if ...)` ``
  (`count`) at the end of its message; its JSON `suggestion`, null before, is
  the text after that `; `.
- PIE-S2314 of `sum(paid)` over a Bool field gains ``; count with `sum(1 for o
  in group if o.paid)` `` (the field's name in place of `paid`); its JSON
  `suggestion`, null before, is the text after that `; `.
- PIE-S2103 of `count_if`, `countif`, `sum_if` and `sumif`, in any letter
  case, gains ``; write `sum(1 for o in group if ...)` or `sum(o.v for o in
  group if ...)` ``, also its JSON `suggestion` (null before); the PIE-S2319
  that a grouped SELECT reports after it at the same span is unchanged.
- The parser's nesting limits are unchanged: an expression nested inside a
  call or window-call argument parses to the same depth as before.

New warning (compatibility: a program that checked clean now reports a
warning; its exit code and SQL are unchanged):

- PIE-S2388 (WARNING, single-file check, every check mode, at the call):
  ``count(paid)` counts every row whose paid is not None, False included; to
  count the rows where it is True, write `sum(1 for o in group if o.paid)` ``
  for `count` of one field, bare or qualified (`count(orders.paid)` names it
  as written), of `Bool` type or an alias of `Bool`. Not reported at a call
  with an error of its own, at a window call (`count(paid) window(...)`),
  which takes no generator, nor in a project. No JSON `suggestion`, as for
  the other habit warnings.

## Equality, nullability and asof JOIN public alpha release notes — 0.1.9

<a id="unreleased-changes-following-018"></a>
<!-- The id above keeps links written before these notes were released pointing here. -->

**Status:** These notes cover `0.1.9`, the public alpha prepared from its
release commit, the last commit of Phase72 batch 2. It is published only when
the tag `v0.1.9`, the versioned GitHub pre-release and PyPI carry its
accepted wheel and sdist; this document neither creates those channels nor
substitutes for their byte verification. As for earlier releases, the
compiler and package are covered on CPython 3.12 and 3.13 for Linux x86-64;
other platforms and Python versions are not.

`0.1.9` retires no source spelling of `0.1.8`. It is the Phase72 release:
both Phase72 batches, the formatter step `pietto fmt` and a warning on the
header lines that Phase75 removes. It adds `pietto fmt`, the builtins
`concat`, `same_value` and `stddev`, project typing of always-null numbers,
fewer false JOIN fan-out refusals, one `Float` value contract and the backward
asof JOIN. Each subsection below lists the changes against `0.1.8` that a
program can observe and the new refusals; the last one lists the known
limitations. The Python execution extras keep the pins of `0.1.8`. The
sections from 0.1.8 down describe published files.

### Highlights

- **`pietto fmt`.** One command lays out a file in the one canonical form:
  `pietto fmt PATH` prints it, `--check` tells whether a file is formatted,
  `--write` replaces it. Only whitespace between tokens changes.
- **New builtins.** `concat(a, b, ...)` joins `Text`; `same_value(a, b)` is
  equality that treats two `None` as equal and is never `None`; `stddev(x)` is
  the sample standard deviation, as Python's `statistics.stdev`.
- **Backward asof JOIN on PostgreSQL.** `asof left join` and
  `asof inner join` keep, for each row, the latest matching row at or before
  its time, as pandas `merge_asof` does.
- **`Float` has one meaning.** A finite binary64 value whose equality is
  Python's, so `-0.0 == 0.0`; PostgreSQL project SQL now groups, orders and
  removes duplicates of `Float` values.
- **Fewer false refusals.** Sound JOIN aggregates, a JOIN on all the GROUP BY
  keys of a grouped query, and project arithmetic with an always-`None`
  operand now check, and an always-null project output no longer hides later
  errors.

### Upgrading from 0.1.8

- `0.1.9` retires no source spelling, so a `0.1.8` file needs no
  `pietto migrate` step. Each header line now warns with PIE-P1012, and
  `pietto migrate FILE > FILE.new` deletes the ones without effect; for
  `mode loose` or `mode strict`, delete the line and pass `--check-mode`.
- `same_value` and `stddev` are reserved: a `def` with either name is
  PIE-S2398. A file's own `concat` keeps its meaning.
- Tools that compare exact diagnostics, SQL text or JSON must expect the
  changes listed below: the new PIE-P1012 and PIE-S2385 warnings, new and
  changed hint texts, the typed NULL casts in single-file SQL, and additive
  JSON vocabulary that strict readers must accept.
- As with every release, compiled bundles and saved jobs made under `0.1.8`
  or earlier are refused by code identity.
- The output of `pietto fmt` may still change before the Phase82 freeze;
  each change is listed in these release notes.
- The VS Code extension `0.1.0` accepts only the `0.1.2` wheel and refuses
  `0.1.9`; the extension is set aside until the work before Phase75 is done.

### Formatter: `pietto fmt`

- `pietto fmt PATH` writes the formatted source of one file to stdout and
  never changes the file. `pietto fmt --check PATH` never writes: it exits 0
  when the file is formatted, and 1 with `would reformat: PATH` on stderr when
  it is not. `pietto fmt --write PATH` replaces the file atomically, only when
  formatting changes it, and keeps its permission bits. `--check` with
  `--write`, a directory, `--project` and `--format` are usage errors
  (exit 2). There is no configuration.
- `fmt` changes only the whitespace around tokens, never a token, its order
  or the spaces between two tokens of a line (`a -- b` still reports
  PIE-P1009): four-space blocks; a continuation line inside parentheses keeps
  its indentation relative to the line it continues; a comment line takes the
  indentation of the line that follows it in its block; two spaces before an
  end-of-line comment; one blank line between top-level declarations, none
  between consecutive imports and exports; the comment lines at the left
  margin over a declaration belong to it; comment lines that no declaration
  follows keep their written blank lines, one at most in a row; no trailing
  whitespace; every line ends with the file's first line ending and a
  non-empty file ends with one; a leading BOM and the header lines (`pietto`,
  `mode`, `dialect`, `encoding`) are kept as written.
- The result is lexed again and must give the input's tokens, blocks, logical
  lines, code and comments; otherwise, or when it would exceed the source size
  limit, `fmt` prints and writes nothing and exits 1. A file with parser
  errors is refused with the diagnostics `check` reports and exit 1, also with
  `--check` and `--write`. `--write` refuses with exit 2 a symbolic link or a
  file that is not regular, before reading it, and, when the file needs
  changing, a read-only file, a file owned by another user, a file whose bytes
  changed after it was read, or a failed replace.
- No diagnostic code, JSON shape, SQL output or existing command changes. The
  `pietto` code blocks of `README.md`, `docs/language.md` and `docs/style.md`
  are now in this layout, and `tests/test_repo_docs_examples.py` keeps them
  so.

### `concat` joins Text

- `concat(a, b, ...)` takes two or more `Text` values (a `Text` alias
  included, also one imported from another module) and is `None` when any
  argument is, in `check`, single-file `explain`, `emit-sql` and
  `emit-sql --project`. One argument or a non-Text argument is PIE-S2104
  (`Invalid arguments for function concat: expected at least 2, got N`,
  `Invalid argument type for function concat at position P: expected Text,
  got X`); write `Text(n)` for an `Int`.
- PostgreSQL SQL, single file and project, is `(a || b)`; in a single file an
  argument not known to be `Text`, such as a field of a source without a
  shape, is `CAST(x AS text)`. Single-file MySQL SQL is `CONCAT(a, b)`.
- Project SQL refuses, on PostgreSQL, `concat` of only `None` (PIE-B1003
  `scalar_call_signature_not_admitted`) and of a binding-width `Text` (new
  detail PIE-B1004 `text_concat_result_bound_missing`), and on MySQL every
  `concat` (PIE-B1003 `scalar_call_signature_not_admitted`, at the statement
  part that holds the call, also through a `def`).
- **Diagnostic text changes.** The PIE-P1000 hint for `||` is now ``Write
  `concat(a, b)` to join Text, or `or` for a condition.``; PIE-S2103 for
  `CONCAT(...)`, `Concat(...)` and other non-lowercase spellings now hints
  ``write `concat(...)` in lowercase``; PIE-S2105 for `+` with a `Text`
  operand now ends ``; use `concat(...)` to join Text values`` beside a
  `Text`, the null literal or a number of unknown type, ``; use `concat(...)`
  with `Text(n)` to join Text values`` beside an `Int`, and at `expected
  numeric operands` beside another type.
- **A file's own `concat` keeps its meaning.** A `def concat` (still
  accepted, not PIE-S2398), or a `constraint`, `derive` or relationship
  template named `concat`, keeps its `0.1.8` meaning in its own file, and in
  every file of a `schema_version = 1` project; there the messages above keep
  their `0.1.8` text. A callable that only another module declares does not
  hide the builtin, so a module's `concat(a, b)` that `0.1.8` reported as
  PIE-S2103 is now the builtin.

### `same_value`: NULL-safe equality

- `same_value(a, b)` is a `Bool` that is never `None`: true when both
  operands are `None` or equal, false when only one is `None`. Its operands
  compare as for `==`. PostgreSQL SQL is `(a IS NOT DISTINCT FROM b)`, MySQL
  SQL `(a <=> b)`, in `select`, `where`, `let`, conditions and JOIN `on` in
  single files, and in explicit-module project checks. Project SQL admits it
  in a relation's select items, WHERE and `let`, and in select items after a
  JOIN, on both targets.
- **Compatibility.** `same_value` is now a reserved builtin name: a
  `def same_value(...)` is PIE-S2398 (``Def same_value has the name of a
  built-in function; a def cannot shadow one``), so its project `emit-sql`
  documents go from VERIFIED to BLOCKED and `emit-sql --all` fails the batch
  with no items. A call is no longer PIE-S2103.
- **New refusals.** A `None` argument, also through a `let` name or a `def`
  argument, is PIE-S2104 ``Invalid argument type for function same_value at
  position N: expected a non-None value, got None; write `x is None`
  instead`` (no hint when both are `None`); operands that `==` refuses are
  PIE-S2104 `Invalid argument types for function same_value: expected
  comparable operands`; a wrong count is PIE-S2104 `expected 2, got N`. On
  PostgreSQL a single-file `same_value` beside a CASE/`coalesce`/`nullif` of
  only `None` warns PIE-S2385 at check and is refused at emission, as `==`
  is. Project SQL admits `Float` operands exactly where `==` admits them
  (on MySQL only beside an operand that reads no row) and refuses `Bool`
  operands and `same_value` in a JOIN `on` or in a WHERE or `let` after a
  JOIN (also as a GROUP BY key there) with the existing PIE-B1003 details.

### Always-null numbers in projects (D-12)

- In an explicit-module project an always-null number (`amount + None`,
  `None * 2`, `None - 3.0`) is typed as in a single file, the widest-type
  rule included (`(None + d) + 1.5` is a `Float`), so its relation completes
  where `0.1.8` reported the bare PIE-S2333, and the relations that read it
  report their own errors. A `schema_version = 1` project takes the same
  widest-type rule: such programs that failed with PIE-S2104 or PIE-S2105
  there now pass.
- A relation without a JOIN input of its own and without `select distinct`
  that selects an untyped NULL (`o = None`, `-None`, `None + None`), or a typed
  output that reads one (`coalesce(None, None) == amount`, `n is None` after
  `let n = None`), now completes with a PIE-S2385 warning at that output,
  which every emission document of the project also carries; project SQL
  refuses it with PIE-B1003 `expression_evidence_unavailable`.
- **SQL changes.** Single-file SQL writes a `None` operand of `+`, `-`, `*`,
  `/` or `%` as a typed NULL (PostgreSQL `CAST(NULL AS bigint|numeric|double
  precision)`, MySQL `CAST(NULL AS SIGNED|DECIMAL|DOUBLE)`), also in WHERE,
  `sign`/`abs`, comparisons, `coalesce`/`nullif`, conditionals, a `let` name
  bound to `None` and a `None` argument inlined from a `def`; it casts an
  always-null `Int` or `Decimal` operand beside a `Float` result to `double
  precision` / `DOUBLE`; MySQL divides `amount / None` with `DIV`. This
  changes the SQL text of every program with such an expression: `0.1.8`
  typed PostgreSQL `NULL * 2` as `integer` and `NULL - 3.0` as `numeric`, and
  MySQL `amount + NULL` as `DOUBLE`.
- Project SQL now emits `Int` arithmetic with a `None` operand on PostgreSQL
  and MySQL (`("s0"."amount" + CAST(NULL AS pg_catalog.int8))`), in the
  target's `Int` carrier with `int_range` 0..0, wherever it is read: a `let`
  value and a GROUP BY key over it, a JOIN output, a WHERE condition,
  `sign`/`abs`, comparisons, `coalesce`, conditionals, an `in` list, a grouped
  aggregate (MySQL `sum` keeps PIE-B1004
  `sum_int_aggregate_range_proof_missing`) and a `union all` branch. Its
  compiled bundle now emits and builds a live template, where `0.1.8` raised
  `COMPILED_NULL_CONTEXT`. Emission observations gain the additive `ranges`
  roles `expression_range` `null_cast` and `syntax` `null_cast_open`,
  `null_cast_close`. `Float` and `Decimal` arithmetic with a `None` operand
  and arithmetic over a `let` name bound to `None` stay refused.
- **Fixed crash.** Project SQL of `o = abs(None)` crashed with
  `KeyError: 'precision'` on both targets (also in `0.1.7`). A visible output
  whose value or window result is that precision-less `Decimal` typed NULL is
  now BLOCKED PIE-B1003 `scalar_call_signature_not_admitted` at the output
  item, also through a `let` name, ORDER BY, LIMIT, a named relation or a
  `def`. Every reader of it that `0.1.8` emitted (`abs(None) is None`,
  `coalesce(abs(None), price)`, `sign(abs(None))`, ...) emits the same
  document, and every form `0.1.8` refused keeps its blockers, with that
  PIE-B1003 added in source order when the relation also has such an output.
- Unchanged: comparisons with `None` and `label + None` stay PIE-S2105, and
  `sum(None + amount)` stays PIE-S2315.

### JOIN aggregates: fewer false fan-out refusals

- Single files (PIE-S2381) and explicit-module projects (PIE-S2333) now
  accept, and emit as one grouped JOIN: `min`, `max` and `count_distinct` over
  any JOIN; `count`, `sum`, `avg` and `stddev` of a field of the many side
  of a LEFT JOIN (or the same RIGHT JOIN) whose `on` matches the other side's
  unique key, and of a further LEFT JOIN on that side; the anti-join
  `where orders.id is None` after such a JOIN when the tested field is never
  `None`; and a JOIN on all the GROUP BY keys of a named grouped query.
- Real fan-out stays refused: `sum`/`count`/`avg`/`stddev` over a JOIN that
  repeats rows, an anti-join on a field that may be `None` or under `or`,
  `is not None`, a JOIN on only part of a grouped query's keys, and a
  hand-written WHERE equality.
- The PIE-S2381 message no longer asks to match a unique key that the `on`
  already matches: for a LEFT or RIGHT JOIN it says ``read no row that JOIN
  NAME keeps without a match``, and where only a FULL JOIN's `on` matches it
  names only the other remedies. MySQL project SQL keeps refusing `sum(Int)`
  with PIE-B1004.

### `Float` value contract

- `Float` has one meaning in both modes: a finite IEEE-754 binary64 value
  whose equality is Python's float equality, so `-0.0 == 0.0`. Single-file SQL
  bytes are unchanged.
- `check --project` accepts `select distinct` over `Float` values and UNION
  DISTINCT, INTERSECT and EXCEPT over `Float` columns; PIE-S2339 and PIE-S2344
  no longer report them, and their message tail "Float equality is not
  supported yet" is retired.
- PostgreSQL project SQL admits same-carrier finite `Float` comparisons in
  WHERE, SELECT, `let`, HAVING, QUALIFY, INNER and LEFT JOIN `on` and
  correlated predicates, and `Float` GROUP BY, DISTINCT, ORDER BY and every
  set form, a window `percent_rank`/`cume_dist` result included in
  comparisons. Each merged row carries the value of some member of its class,
  so a key whose class holds both zeros may show either sign.
- MySQL project SQL admits `Float` comparisons with a literal or a header
  parameter and every ordering inequality. `Float` GROUP BY
  (`group_key_type_outside_reviewed_comparison_domain`), relation ORDER
  (`order_comparison_domain_unsupported`) and `==`/`!=` between two row reads
  (`comparison_type_pair_not_admitted`) keep their PIE-B1003 blockers;
  `Float` DISTINCT, UNION DISTINCT,
  INTERSECT and EXCEPT are BLOCKED at emission with
  `distinct_field_comparison_domain_unsupported` or
  `set_row_equivalence_domain_unsupported` (real MySQL 8.4.12 kept `-0.0` and
  `0.0` apart beside a wide key).
- **Compatibility.** No VERIFIED `0.1.8` document changes bytes. Some
  refusals move: a MySQL `Float` DISTINCT or equivalence set form, and those
  forms over a window distribution result on both targets, pass the check and
  are BLOCKED by emission with one PIE-B1003 and no diagnostics (two on MySQL
  when the only inputs are typed VALUES bodies, the second
  `zero_physical_source_not_admitted_on_target`); a FULL JOIN whose `on`
  compares a `Float` is now refused by the FULL JOIN rule (subject reference
  `join`: PostgreSQL `full_join_equality_outside_reviewed_int_domain` or a
  shape detail, MySQL `mysql_full_join_approved_non_support`, except MySQL
  `==`/`!=` between two row reads, which keeps
  `comparison_type_pair_not_admitted`); and every FULL JOIN rule refusal now
  carries the location of the JOIN's `on` clause, for every type, on both
  targets. The suggestion of `set_row_equivalence_domain_unsupported` names
  the per-target limits.
- Still refused: `Float` beside `Int` (`price > 1`; write `1.0`), `Float`
  field arithmetic, unary minus on a field, `/` and `%`, `Float` `sum`, `avg`,
  `count`, `count_distinct`, `min` and `max`, a window PARTITION or ORDER BY a
  `Float`, a FULL JOIN on a `Float` equality, and DISTINCT, GROUP BY, ORDER and
  equivalence set forms over a window distribution result.

### `stddev` aggregate

- `stddev(x)` is the sample standard deviation (Python `statistics.stdev`)
  of a direct `Int` or `Float` field: a nullable `Float`, `None` below two
  values. PostgreSQL SQL is `SQRT(CAST(VAR_SAMP(x) AS double precision))`
  (project: `pg_catalog.float8`), VERIFIED in projects for `Int` and, with the
  new evidence token `target_checked_binary64_overflow`, for `Float`.
  Single-file MySQL SQL is `STDDEV_SAMP(x)` for a `Float`.
- **New refusals.** MySQL `stddev` of an `Int` is refused in both modes
  (single file PIE-B1000, project PIE-B1003
  `stddev_int_not_admitted_on_target`); MySQL project `Float` `stddev` is
  PIE-B1004. Over a JOIN that repeats rows it is PIE-S2381, as `sum` is, and
  where `sum` is accepted after a JOIN it is too.
- **Compatibility.** `def stddev` is now PIE-S2398 (``Def stddev has the name
  of a built-in function; a def cannot shadow one``) with the suggestion
  ``Rename this def: `stddev` is now the built-in sample standard deviation
  aggregate, and a call to stddev always means it.``; a `constraint stddev` or
  `derive stddev` called as `stddev(...)`, which was PIE-S2103, now means the
  aggregate. In a single file, the refusal of a non-window aggregate with a
  `window`, `count_distinct` included, gains the suffix `; window aggregates
  are sum, count, avg, min and max`, unless the relation admits no such
  window; a project keeps the text without a suffix.
- PIE-S2103 hints (the lookup ignores letter case): `stdev`, `stddev_samp` and
  `statistics.stdev` hint ``write `stddev`, the sample standard deviation
  (Python `statistics.stdev`)``; `std`, `pstdev`, `stddev_pop`,
  `statistics.pstdev` and `stddev` in a letter case other than lowercase say
  that the population deviation is not available; the aggregate list of the
  other hints now names `stddev`.
- PIE-S2103 hints: `in_range` hints ``write the half-open range
  `a <= ts < b` `` and `ranges_overlap` hints ``write `a_start < b_stop and
  b_start < a_stop` ``.
- Project JSON v2 gains the additive syntax roles `aggregate_root_open` and
  `aggregate_root_close`, the aggregate spelling `VAR_SAMP` and the evidence
  token `target_checked_binary64_overflow`; a strict reader of those
  vocabularies must accept them. Semantic metadata artifact v1 records no
  `stddev` call.

### Backward asof JOIN (PostgreSQL)

- `asof left join price on orders.product_id == price.product_id and
  orders.ordered_at >= price.valid_from` keeps, for each order, the latest
  price at or before its time (pandas `merge_asof`: backward, exact matches
  allowed); `asof inner join` drops the orders without one. The `on` is zero
  or more `==` keys, then one `>=` time test, each written earlier input
  first, on one line without parentheses; both times are `Date` or both
  `Timestamp`, and no key is a `Float`. The joined input is a source whose
  shape declares a `unique(...)` within the keys and the time, so the latest
  row is one row; Pietto never picks one of several tied rows. A `None` key
  or time matches nothing. Single files and explicit-module projects check it
  with the same rules and messages, except that a project reports a JOIN
  without `on` as PIE-S2333 and refuses an asof JOIN beside nested fields
  (below).
- **SQL.** Single-file PostgreSQL SQL is `LEFT JOIN LATERAL (SELECT * FROM
  <source> AS <b> WHERE <on> ORDER BY <b>.<time> DESC LIMIT 1) AS <b> ON
  TRUE` (`INNER JOIN LATERAL` for `asof inner join`). Project SQL is the JOIN
  with `AND (NOT EXISTS (...))` of a later matching row in its `ON`, in a
  table or query without a relation `let NAME:` block whose FROM is not a
  table function; compiled bundles and live templates replay that SQL. On
  PostgreSQL 18.6, 34 single-file and 30 project statements returned the rows
  of a reference implementation, and 7 of 7 mutated statements were caught.
- The JOIN repeats no earlier row: in a single file `sum(orders.x)` after an
  asof JOIN is accepted, and an aggregate of a joined field stays PIE-S2381.
  A project accepts an aggregate after an asof JOIN only where the `on` keys
  match a unique key of the joined source, as for any JOIN.
- **New refusals.** New PIE-S2386, at the JOIN, when the joined input cannot
  have one latest row: ``asof JOIN joins only a source: one latest row is
  proved by the source shape's unique(...).`` for a table, query or
  `let NAME:` block, and ``Several rows of price may be the latest for one
  orders row; Pietto does not pick one.`` followed by the `unique(...)` to
  declare or the key to match. An asof JOIN without `on` is PIE-S2335 in a
  single file and the cause of PIE-S2333 in a project, with a new text:
  `` JOIN price: write `on` with the keys, then one time test: `on
  orders.k == price.k and orders.t >= price.t` ``. PIE-S2336 refuses another
  kind (``ASOF JOIN is `asof left join` or `asof inner join`.``), a second
  asof JOIN in one query
  (``One asof JOIN per query: move the first into its own query and `from`
  it.``), a missing, strict, reversed, forward, misplaced or second time
  test, a repeated key, a chain, time arithmetic, a validity range, any other
  condition, a bare field name, mixed `Date` and `Timestamp` and a `Float`
  key, with a rewrite where one exists. A project also refuses, with
  PIE-S2336, an asof JOIN in a query with `collect` or `unnest` or whose
  earlier input has a nested-relation field (``Do the asof JOIN in a query
  with only flat fields first.``). PIE-P1000
  refuses `left asof join`, `asof join`, an `as` alias, `by` keys and an `on` that is
  broken over lines or in parentheses, with the asof form as its hint. MySQL
  refuses every asof JOIN: single file PIE-B1000 (``... MySQL has no ASOF
  JOIN yet; emit with --dialect postgres``), project PIE-B1003
  `asof_join_not_admitted_on_target`.
- **Compatibility.** `asof` is a new soft keyword of the generated parser; it
  stays a valid name elsewhere (`select asof = orders.id`). A relation-body
  line that starts with `Asof` now ends its PIE-P1000 with ``Keywords are
  lowercase: write `asof`.``, as for the other keywords. After an
  `asof left join`, PIE-S2383 names the asof remedies (test the chosen row
  in `select`, or write `asof inner join`). When only asof JOINs repeat the
  rows an aggregate reads, PIE-S2381 offers only `any(...)` or a separate
  query, not a key match in `on`.

### Header lines warn (PIE-P1012)

- **Compatibility.** Each leading `pietto <number>`, `mode ...`, `dialect ...`
  or `encoding ...` line now reports a new WARNING, PIE-P1012
  (``The header line `<line>` is deprecated and will be removed.`` followed
  by its hint), in every check mode, once the source parses, in every command
  and project that parses source, dependency packages included, except
  `migrate` (`emit-sql --project` only in a document refused before semantic
  analysis, as for PIE-P1009). Exit codes, `ok` and every other diagnostic are
  unchanged, but tools that compare exact diagnostics must expect it. Phase75
  removes the header syntax.
- `pietto migrate FILE > FILE.new` now deletes each header line without
  effect (`pietto <number>`, `mode checked`, `dialect`, `encoding`; a comment
  on the line stays), also from a source that it returned byte for byte in
  `0.1.8`, and refuses `mode loose` and `mode strict` with PIE-P1011
  (``The header line `mode <mode>` needs manual migration, as it sets the
  check mode.``): delete the line and pass `--check-mode` instead.

### Known limitations of 0.1.9

- MySQL project SQL refuses `concat`: real MySQL 8.4.12 types a `CONCAT`
  result from its arguments' storage lengths and counts the literal anchor
  that project SQL writes by its UTF-8 bytes, so the declared width does not
  hold. MySQL project `REPLACE` and the other Text calls whose result can grow
  have the same typing and are still emitted as in `0.1.8`; a MySQL project
  `replace` wider than the 16383-character bound stays the generic PIE-B1003.
  Single-file MySQL `CONCAT` returns NULL above `max_allowed_packet`.
- MySQL project SQL of `union distinct`, `intersect distinct` and
  `except distinct` over a `same_value` column is VERIFIED but was not run on a
  database. `same_value` is not emitted in a project JOIN `on` or in a WHERE
  or `let` after a JOIN (also as a GROUP BY key there), `having:` admits no
  call, a header parameter cannot be its operand (PIE-S2355), and on MySQL a
  `Text` operand relies on the `utf8mb4_0900_bin` collation premise. Project
  SQL admits a `Float` `same_value` exactly where it admits a `Float` `==`:
  on PostgreSQL, and on MySQL only beside an operand that reads no row
  (`same_value(ratio, 1.5)` is emitted with `<=>`; a MySQL `same_value` of
  two row `Float` operands is PIE-B1003 `comparison_type_pair_not_admitted`,
  as their `==` is).
- Project typing of untyped NULL values still fails with the bare PIE-S2333
  in a relation with a JOIN input of its own whose output has no type or reads
  one through a `let` name, a `select distinct` relation whose output has no
  type, a relation that computes with, groups by, aggregates or JOINs an
  untyped output it reads, a SELECT output with no type that is not always
  NULL (`abs(amount + (-None))`), and a relation with a `Decimal` quotient
  output; a relation that passes an untyped output through and has an invalid
  LIMIT still reports PIE-S2333 in place of PIE-S2307. A project places
  PIE-S2385 at the output, a single file at the value. Single-file SQL writes
  a `Decimal` typed NULL without precision.
- MySQL single-file GROUP BY of a `Float` beside a wide `Text` key can put
  `-0.0` and `0.0` in different groups.
- The asof JOIN is PostgreSQL only; MySQL refuses it in both modes. One asof
  JOIN per query, and no lower bound, tolerance, forward or nearest
  direction, strict `>` or validity range. A project emits it only in a table
  or query without a relation `let NAME:` block whose FROM is not a table
  function; elsewhere (a set or VALUES input in a `let NAME:` block, an
  asof JOIN inside a `let NAME:` block, a query with any other relation
  `let NAME:` block, a table-function FROM) the JOIN gets its own checks and
  then `asof JOIN is not available in projects yet.` (PIE-S2336); a
  `let NAME:` block as the joined input is PIE-S2386, as it is no source. A project
  refuses an aggregate after an asof JOIN (PIE-S2333) unless the `on` keys
  match a unique key of the joined source, where a single file accepts an
  aggregate of earlier fields: aggregate in a query that reads it with
  `from`. The project SQL pairs each earlier row with every joined row of its
  keys at or before its time and tests each pair with `NOT EXISTS`, so on a
  long history it costs more than the single-file SQL; an index on the joined
  table's keys and time makes each test one index lookup. The `unique(...)`
  that proves one latest row is trusted, not checked
  at run time: on data that breaks it, single-file SQL returns one of the
  tied rows and project SQL returns each of them.

## Project-mode quality public alpha release notes — 0.1.8

<a id="unreleased-changes-following-017"></a>
<!-- The id above keeps the links of the 0.1.7 notes below, written before these notes were released, pointing here. -->

**Status:** `0.1.8` was published from `61b05586` (tag `v0.1.8`) on the
versioned GitHub pre-release and PyPI channels. These historical release notes
neither publish a successor nor substitute for channel byte verification.
As for earlier releases, the compiler and package are covered on CPython 3.12
and 3.13 for Linux x86-64; other platforms and Python versions are not.

`0.1.8` retires no source spelling of `0.1.7`. It is `main` at `d654738f`
with only version and documentation changes: the project-mode quality
interlude that the [0.1.7 notes](#rescheduled) scheduled, that is, its first
batch `8cebe779` and PMS-2 `d654738f`. It changes the diagnostics that a
project reports and what `explain --project` lists, with one exit status of
`explain --project`, and it checks large projects faster, as described below.
On the programs whose SQL was compared with `0.1.7`, named under F5 and under
Measured output below, the SQL of the first batch is byte-identical to that
of `0.1.7`, and PMS-2 changed no exit status, stdout or stderr on the project
command invocations compared with the first batch. Every change but PMS-2
came in the interlude's first batch. The Python execution extras keep
the pins of `0.1.7`. The sections from 0.1.7 down describe published files.

### Highlights

- **Project diagnostics closer to a single file.** In an explicit-module
  project, a JOIN relation that a single file refuses with PIE-S2312 because
  it mixes an aggregate with another projection and has no GROUP BY (for
  example a JOIN query whose `select:` has `customer_id` and `n = count()`
  but no `group by`) now also reports what a single file reports beside it,
  unless its `let:` clause or WHERE is refused, and a repeated SELECT output
  name reports more as a single file does. Only relations that already report
  an error change, so a program that checks still checks.
- **`explain --project` lists the dependencies' diagnostics after a root
  parse failure.** When the root's pin check passes and a root module then
  fails to parse, the dependencies' diagnostics follow the root's, and in one
  case it now exits 2 instead of 1 (see
  [Upgrading from 0.1.7](#upgrading-from-017)).
- **Faster project checks.** With the first batch, one module with 600 tables
  checks in about 5.2 s where `0.1.7` took 13 s, and one query with 120 JOINs
  in about 11 s where `0.1.7` took 31 s. With the import-cycle change
  (PMS-2), a 160-module import cycle is reported in about 2.7 s and 108 MiB,
  against 103 s and 3,075 MiB on the first batch (the first batch was
  measured again beside PMS-2 on a shared machine; the `0.1.7` notes give
  71 s for 160 modules from an earlier measurement). The [Performance](#performance) section gives how these
  times were measured; they are no performance promise.
- **Documented rules.** An exactly repeated environment premise of an
  emission contract is now a documented rule, and the language
  reference no longer describes the PostgreSQL `sum` of a `bigint` column as
  `numeric`. Both change documentation only.

### Upgrading from 0.1.7

- 0.1.8 retires no source spelling, so a 0.1.7 file needs no `pietto migrate`
  step.
- Some project diagnostics change, only for relations that already report an
  error: in an explicit-module project, a mixed aggregate JOIN relation
  refused with PIE-S2312 and a repeated SELECT output name report more of
  what a single file reports (for such a JOIN relation `0.1.7` reported
  PIE-S2312 alone, or a bare PIE-S2333 when the only other projection was a
  window), and an unknown QUALIFY name in such a mixed
  aggregate JOIN relation is PIE-S2102; in an explicit-module or LEGACY_FLAT
  project, a repeated unknown bare name outside a JOIN reports PIE-S2102 only
  at its first item. A tool that compares the exact diagnostics of such a
  project with those of `0.1.7` must expect these changes; see
  [Project diagnostics](#project-diagnostics).
- `explain --project` now lists the dependencies' diagnostics after a root
  module that fails to parse once the root's pin check passes. When the
  root's only failures are error diagnostics found as its modules are parsed
  and a dependency reports a project error, it exits 2 where `0.1.7` exited 1.
  The `pietto.project-explain.v1` shape is unchanged.
- The private module inspection document that a project builds before it
  reports an import cycle (PMS-2) now lists a blocked module's cycle members
  once. It is private, built and checked in-process only, and keeps its
  marker `pietto.module-inspection.v1`; on the invocations compared for PMS-2
  with the interlude's first batch, the stdout, stderr and exit status of the
  project commands are unchanged.
- Bundles and saved-job records made by 0.1.7 or earlier are refused by the
  changed code identity; keep their matching old environment. Pietto supplies
  no migration or rewrite.
- The execution extras install the same driver versions as `0.1.7`.
- `0.1.8` is a normal version number: once it is published,
  `pip install -U pietto` upgrades to it, and so do the pins `pietto~=0.1`
  and `pietto<0.2`.

### Project diagnostics

These changes apply to explicit-module projects, and the change for a repeated
bare name outside a JOIN (F7) applies to LEGACY_FLAT (`schema_version = 1`)
projects too. They change only the diagnostics of relations that already
report an error, so a program that checks still checks. Each statement
describes the queries probed for these changes, apart from the differences
that the [known limitations](#known-limitations-of-018) list.

- **A mixed aggregate JOIN reports what a single file reports (F5).** A
  relation with JOIN inputs that a single file refuses with PIE-S2312, for
  mixing an aggregate with another projection without GROUP BY, now reports
  beside that PIE-S2312 what a single file reports, unless its `let:` clause
  or WHERE is refused: the errors of its other SELECT items, of the reads in
  its windows, of its QUALIFY (an unknown name there is PIE-S2102, where
  QUALIFY elsewhere in an explicit-module project still reports PIE-S2332) and
  of its ORDER BY keys, and PIE-S2381 at each aggregate that may read rows
  that a JOIN repeats. `0.1.7` reported PIE-S2312 alone, beside the PIE-S2305
  of a repeated output name, or, when the only other projection was a window,
  a bare PIE-S2333. The
  [PIE-S2312 row](spec/diagnostics.md#semantic-diagnostics) lists the codes.
  Compared with `0.1.7` on 44 JOIN programs and 68 grouped JOIN emissions with
  a window, for PostgreSQL and MySQL, the SQL and the `check --project` output
  of the programs that check are unchanged, and so are the single-file
  diagnostics of 674 cases.
- **A repeated SELECT output name reports more as a single file does (F7).**
  Under owner decision Q1-A, which aligns project diagnostics with single-file
  behaviour:
  - A repeated unknown bare name, such as `nosuch` in
    `select: id, nosuch, nosuch` or `x = nosuch` written twice, reports
    PIE-S2102 `Unknown field: nosuch` at the first item and only PIE-S2305 at
    the repeat. Outside a JOIN, `0.1.7` also reported PIE-S2102 at the repeat;
    in a JOIN query without GROUP BY or aggregates it reported it at neither
    item, or, after a JOIN `where` or `let:` that fails, at both.
  - In a JOIN query, a repeated item and the item that it repeats now report
    their other errors beside the PIE-S2305, as a single file does: an unknown
    field (PIE-S2102 at both items of `x = rows.nosuch` written twice), a name
    that two inputs have (PIE-S2335, `x = id`), or invalid operands or
    arguments (PIE-S2105, `x = rows.id + 'a'`; PIE-S2104,
    `z = abs(rows.nosuch, 1)`). Without GROUP BY, aggregates or a failing
    `where` or `let:`, `0.1.7` reported PIE-S2305 alone, and with GROUP BY it
    omitted the repeated item's errors.
  - A grouped JOIN query whose `where` or `let:` fails now also reports the
    errors of its SELECT items without an aggregate or a window, such as
    PIE-S2102, PIE-S2318 `Grouped projection is not a GROUP BY key` and
    PIE-S2319 at a computed output; `0.1.7` reported none of them.

  A LEGACY_FLAT (`schema_version = 1`) project checks no JOIN, so a JOIN query
  there still reports only PIE-S2334 at the JOIN.

On the 1392 generated JOIN queries probed for the first batch, these changes add
no project diagnostic that a single file does not report and `0.1.7` did not
report, remove none that `0.1.7` and a single file both report, and change no
single-file output; 504 of them now report exactly what a single file reports,
against 116 in `0.1.7`. The 286 queries probed for F7 show no regression from
`0.1.7`.

### `explain --project`

- **A root module that fails to parse no longer hides the dependencies' errors
  (EXD-5).** Explain reads the root package's manifest and every asset file
  and checks their content against the root's pin before it parses any module.
  When that check passes and a root module then fails to parse, explain now
  loads the dependencies that the verified manifest declares and lists their
  diagnostics after the root's, as it lists them once the root loads: the same
  codes, messages, locations, `In dependency package ...` prefix and order,
  and the same cycle, conflict and diamond rejections. A module fails to parse
  when its bytes, which match the pin, are not UTF-8 (`source_read`) or when
  it reports an error diagnostic as it is parsed: a syntax error, `PIE-S2801`
  for `collect` or `unnest`, or any other. A root that fails before the pin
  check still reports only its own diagnostics, because its dependency
  declarations are not verified: when its manifest or typed-asset validation
  fails, an asset read fails (`source_read` for a module file that is missing
  or not accessible), or the content does not match the pin, for example a
  stale pin. The `pietto.project-explain.v1` shape is unchanged. See the
  [project guide](project-package.md).
- **One exit status changes.** The exit status of such a failure now follows
  the whole list, as it does once the root loads: 2 when the root or a
  dependency reports a project error, such as `project_resource` for a missing
  dependency directory, and 1 otherwise. So when the root's only failures are
  error diagnostics found as its modules are parsed, such as a syntax error,
  and a dependency reports a project error, explain now exits 2 where `0.1.7`
  exited 1.

### Emission contracts

- **Repeated premises are documented (PE-09).**
  [Emission contract values](project-package.md#emission-contract-values) now
  states the rule that `0.1.7` already follows. PE-09 changes documentation
  and tests only, so acceptance, exit codes and output bytes are those of
  `0.1.7`. A premise declared again with the same bound scope, key and
  canonical value is an exact repeat, accepted in any number of copies, within
  `environment`, within one source's `premises` or across both; the SQL is
  unchanged, `request.contract` and `target.environment` echo every copy, and
  a requirement that uses the premise cites each copy. Each copy is still
  checked on its own, so a field premise that disagrees with the field's
  `domain` is BLOCKED with `PIE-B1005` however many copies there are. Two
  declarations of one key in one bound scope with different canonical values
  are BLOCKED with `PIE-B1005`, also on a source the statement does not read,
  and a source described twice is INPUT_REJECTED.

### Documentation

- The [language reference](language.md) no longer says that PostgreSQL holds
  the `sum` of a `bigint` column as `numeric`, so that `s / 2` with `s = 3` is
  `1.5000000000000000`. Since `0.1.7` Pietto casts the PostgreSQL `sum` of an
  `Int` back to `int8` and emits `s / 2`, for such a sum `s`, as an `int8`
  division, an integer division like `DIV` on MySQL. This changes
  documentation only.

### Performance

- **Faster checks of many relations (PMS-3).** In an explicit-module project,
  `check --project`, `emit-sql --project` and `compile_query` no longer build
  the private Project IR analysis bundle, which nothing on these paths read.
  Relational properties now take the verified Project IR result directly;
  private Project IR inspection still builds the bundle. With the first batch,
  one module with 600 tables checks in about 5.2 s and 90 MiB at peak, where
  `0.1.7` took 13 s and 361 MiB; 300 tables take 2.1 s instead of 4.2 s, and
  200 modules of one source, table and query each take 3.7 s instead of 11 s.
- **Faster JOIN functional dependencies (PMS-6, in part).** At each JOIN step,
  duplicate functional dependencies are merged through an index instead of
  being compared with every one merged so far, imaged classes are ordered by a
  position lookup, and strict-rule incidence lists are built from the set bits
  of each rule's determinant mask. With the first batch, one query with 60
  JOINs checks in about 1.6 s instead of 2.3 s, with 90 JOINs in 4.3 s instead
  of 9.4 s, and with 120 JOINs in 11 s and 567 MiB instead of 31 s and
  585 MiB. Every JOIN step still images the functional dependencies of its
  inputs into its own output, so the cost still grows faster than the JOIN
  count.
- **Measured output.** Both trees were measured again for this comparison, the
  first batch against `0.1.7`, so the times do not separate PMS-3 from PMS-6,
  on generated explicit-module projects, on the same machine with CPython
  3.13.13 on Linux x86-64; the `0.1.7` figures in its own notes come from an
  earlier measurement. The machine was shared with other work, so a run counts
  only when a reference CPU loop just before it took at most 1.40 s (the clean
  reference runs took 1.07 to 1.39 s); this rule was set after the runs had
  been made, because a planned fastest-of-five rule left the 300-table check
  without a clean run, and the 90- and 120-JOIN checks had been rerun, up to
  four times a run, until a reference loop just before them ran at normal
  speed. Each time is the fastest such run of one command on one tree: for the
  check times given here, 3 to 9 runs counted, out of 8 to 12. Peak memory, in
  MiB, is the median of all runs. The times show the change and are no
  performance promise. On these projects the stdout, stderr and exit status of
  `check --project`, and of `emit-sql --project` for PostgreSQL for the
  300-table module and the 60-JOIN query, are byte-identical to those of
  `0.1.7` in every run; other programs were not compared byte for byte for
  this measurement.
- **An import cycle is reported sooner (PMS-2).** Before `check --project` or
  `emit-sql --project` reports an import cycle (PIE-S2703), the project builds
  and self-checks its private module inspection. That inspection now lists a
  blocked module's cycle members once, under its first readiness cycle record,
  instead of once for each issue that blocks the module. For a cycle of N
  modules from which modules outside it make R relation imports, its readiness
  records now grow as N² + N·R instead of N³ + N²·R. Measured with
  `check --project` against the first batch on generated projects, on the same
  machine with CPython 3.13.13 on Linux x86-64: a 40-module cycle takes 0.92 s
  instead of 2.1 s; an 80-module cycle 1.2 s and 66 MiB instead of 10 s and
  446 MiB; a 160-module cycle 2.7 s and 108 MiB instead of 103 s and 3,075
  MiB; a 40-module cycle with 40 outside modules that each import a table from
  every member (R = 1,600) 4.8 s and 125 MiB instead of 55 s and 2,038 MiB.
  Each figure is the median of three runs per tree, the two trees alternating,
  and a pair of runs counted only when a reference CPU loop just before and
  just after it took at most 1.40 s. The machine was shared with other work,
  so the times show the change and are no performance promise; stdout, stderr
  and exit status were the same on both trees in every run.
  `emit-sql --project` was not timed. On 715 project command invocations
  compared with the first batch, 51 of them `emit-sql --project` for
  PostgreSQL and MySQL, the exit status, stdout and stderr are byte-identical;
  the 26 that produced SQL are all on projects without an import cycle,
  because PIE-S2703 blocks every emission from a project that has one. The
  private document keeps its marker `pietto.module-inspection.v1`, since it is
  built and checked in-process only. Its portable self-check still compares a
  blocked module's cycle count with its cycle records and its member list with
  the module's graph component. A forged document whose positive cycle member
  count disagrees with its member list or with the module's graph component is
  now refused when the module closes, as `inconsistent_scope_relation` instead
  of `child_count_mismatch`, so another fault later in the same module is
  reported first.

### Release notes

- The 0.1.7 notes below were corrected after publication: see
  [Corrections after publication](#corrections-after-publication).

### Known limitations of 0.1.8

These [known limitations of 0.1.7](#known-limitations) change in `0.1.8`; the
others stay as listed there, with the timings measured for `0.1.7`.

- `explain --project` no longer stops at the root package when a root module
  fails to parse after the root's pin check passes, and a repeated environment
  premise is a documented rule (both above). The 0.1.7 entries for many
  relations or many JOINs, a mixed aggregate JOIN and a repeated unknown
  SELECT item are replaced by the entries below, and an unknown QUALIFY name
  in a mixed aggregate JOIN relation is now PIE-S2102 (see F5). The 0.1.7
  entry for an import cycle is replaced by PMS-2 above: a ring's readiness
  records now grow with the square of its size, not its cube, when no module
  outside it imports from it, and in general as N² + N·R.
- **Many relations or many JOINs are still slower to check than in a single
  file.** In an explicit-module project, one module with 300 tables checks in
  about 2.1 s (a single file of them in 0.55 s, as the `0.1.7` notes give),
  and one with 600 tables in about 5.2 s; 200 modules of one source, table and
  query each take about 3.7 s. The JOIN properties of one query still grow
  faster than its JOIN count: one query with 60 JOINs checks in about 1.6 s,
  with 90 JOINs in about 4.3 s (a single file in 0.4 s, as the `0.1.7` notes
  give) and with 120 JOINs in about 11 s and 567 MiB.
- **A mixed aggregate JOIN relation whose `let:` clause or WHERE is refused.**
  In a project such a relation still stops before its aggregates, as in
  `0.1.7`: it reports only that refusal, and the PIE-S2305 of a repeated
  output name, where a single file also reports PIE-S2312 and what F5 above
  lists. For example, beside a JOIN `o` of `items` with `let p = items.price`,
  `where id > 1` with `select k = items.id, n = sum(items.price)` reports only
  its PIE-S2335. The [PIE-S2312 row](spec/diagnostics.md#semantic-diagnostics)
  lists the 20 cases measured for F5.
- **Other differences from a single file.** The probes for the first batch
  show these differences in explicit-module projects too; each is as in
  `0.1.7` or closer to a single file, and the list is not complete:
  - When a SELECT item reports an error, such as an unknown field or the
    PIE-S2305 of a repeated output name, a JOIN query or a query without GROUP
    BY reports no error of its ORDER BY keys, unless it is a JOIN relation
    that reports PIE-S2312 (F5 above): beside `select: id, y = nosuch + 1`,
    `order by k` reports no PIE-S2102. A relation without JOIN inputs that
    reports PIE-S2312 checks no key either, where a single file reports
    PIE-S2380.
  - With GROUP BY, a computed output can report PIE-S2319 without its own
    errors (`x = rows.nosuch + 1`).
  - After a failing `where` or `let:`, an aggregate or a window item can
    report fewer errors than in a single file, PIE-S2320 or PIE-S2329 can be
    missing, and after a failing `let:` an ambiguous name can miss its
    PIE-S2335.
  - A JOIN relation whose projections are all aggregates and which a single
    file refuses with PIE-S2381, or with ORDER BY PIE-S2334, is a PIE-S2333 in
    a project, with its fan-out cause when an aggregate may read rows that a
    JOIN repeats; so is a grouped JOIN relation whose aggregate may read such
    rows, where a single file reports PIE-S2381 or another error of the
    relation. A SELECT error, such as the PIE-S2305 of a repeated output name,
    or a refused `where` or `let:` can be reported instead.
  - An unnamed computed item in a JOIN query, such as `rows.id + 1`, is a
    PIE-S2304 error in a project and a warning in a single file, and the other
    items' errors can then be missing.
  - Some diagnostics come in another order: a call such as
    `abs(rows.nosuch, 1)` can report PIE-S2102 before PIE-S2104, and without a
    JOIN the diagnostics of a repeated dotted or computed output are not
    sorted by position.

A later architecture item, project joined aggregation analysis beside a
refused WHERE or `let:` binding, which lets the joined aggregation stage
analyse over a row filter that is not concrete, is to remove the differences
above that follow a refused or failing `where` or `let:`; it has no scheduled
phase yet (see the [roadmap](roadmap.md#project-mode-follow-up)). The other
differences have no scheduled home yet. Sharing JOIN functional dependencies
across JOIN steps is a separate design decision.

## Nested results and project emission public alpha release notes — 0.1.7

<a id="unreleased-changes-following-016"></a>
<!-- The id above keeps the links of the 0.1.6 notes below and of docs/phases/phase-71/slice-23.md, written before these notes were released, pointing here. -->

**Status:** `0.1.7` was published from `4c8348a4` (tag `v0.1.7`) on the
versioned GitHub pre-release and PyPI channels. These historical release notes
neither publish a successor nor substitute for channel byte verification.
As for earlier releases, the compiler and package are covered on CPython 3.12
and 3.13 for Linux x86-64; other platforms and Python versions are not.

`0.1.7` retires no source spelling of `0.1.6`. It completes Phase71: in an
explicit-module project (`schema_version = 2`), `collect` and `unnest` now
check, emit PostgreSQL SQL and run through the alpha Python API on
PostgreSQL. It also widens project SQL emission, adds batch project emission,
emits PostgreSQL `sum(Int)` with checked casts in single files as in projects,
and refuses a relation-name qualifier through a `let` alias in a project, as a
single file does. The Python execution extras keep the pins of `0.1.6`. The
sections from 0.1.6 down describe published files.

### Highlights

- **Nested PostgreSQL results.** In an explicit-module project,
  `name = collect r` reads an ordered relation let `r` as one nested value, and
  `let o = unnest(p.field)` followed by one `cross join o`,
  `inner join o on ...` or `left join o on ...` (for example `on True`)
  expands it again.
  `check --project` types and checks both, and `PIE-S2802` is retired. On
  PostgreSQL, `emit-sql --project` emits each Collect read as a
  `LEFT JOIN LATERAL` count-and-arrays aggregate and an admitted Unnest as
  `LATERAL ROWS FROM` over `pg_catalog.unnest`; MySQL reports `PIE-B1003` for
  every Collect read and Unnest. Single files, LEGACY_FLAT projects and
  package modules still report `PIE-S2801`.
- **Nested results in Python.** `compile_query`, `load_bundle` and
  `execute(..., route="postgres_rows")` run bounded Collect queries with Int,
  Bool, finite Text, finite Float, Decimal, Date, Timestamp and UUID children,
  several collections side by side, and one Unnest that may keep a sibling
  collection. Ordinary `save`, source-free R1 and `verified_export` keep the
  complete child lists. `postgres_adbc`, `mysql_rows` and guarded or refined
  requests refuse nested results before any connection, and R2 and recovery,
  relay and sink effects refuse them too.
- **Batch project SQL emission.** `emit-sql --project ROOT --all` emits every
  matching top-level table or query in one `pietto.sql-emission.batch.v1`
  document, each item the document of its single-owner call; when every item
  is VERIFIED, `--output DIR` writes them as files on supported Linux
  filesystems.
- **Wider project SQL emission.** On PostgreSQL, narrow Int arithmetic is
  computed in `bigint`, `bigint` arithmetic and `sum(Int)` use PostgreSQL's
  checked `bigint`, and UUID values compare and order. `Date` source fields
  and Timestamp and Date comparisons and ordering are emitted on both targets,
  and so are JOIN SELECT projections with the reviewed scalar calls, casts and
  conditionals, and Timestamp UNION ALL and UNION DISTINCT. Every blocker of a
  BLOCKED `emit-sql --project` document now carries a `suggestion`.
- **Exact `sum(Int)` in single-file PostgreSQL SQL.** Single-file `emit-sql`
  writes PostgreSQL `sum(Int)` as
  `CAST(SUM(CAST(x AS pg_catalog.int8)) AS pg_catalog.int8)` (an aggregate
  window as `CAST(SUM(CAST(x AS pg_catalog.int8)) OVER (...) AS pg_catalog.int8)`),
  as project emission does: a sum outside signed 64 bits fails with SQLSTATE
  22003 instead of returning an exact `numeric`.
- **Project-mode corrections.** A relation-name qualifier through a `let`
  alias (`customers.price` after `let c = customers` and `from c`) is refused
  in a project as in a single file. The import hint of an unknown name is now
  also the JSON `suggestion`; when no module exports the name, it names the
  modules that declare it without exporting it, and it never suggests an
  import that would close an import cycle. `explain --project` names the
  commands that read schema 1 and 2 projects.
- **Known limitations and rescheduled work.** The project-mode limits that
  remain, with fresh timings, are listed under
  [Known limitations](#known-limitations), and the
  [Rescheduled](#rescheduled) section gives the home that the owner decided
  for each debt reviewed for this release and not fixed in it.

### Upgrading from 0.1.6

- 0.1.7 retires no source spelling, so a 0.1.6 file needs no `pietto migrate`
  step.
- In an explicit-module project, a program that reads a relation-name
  qualifier through a `let` alias, which 0.1.6 accepted, now fails
  `check --project` and is BLOCKED by `emit-sql --project`: write `c.price`
  instead of `customers.price` after `let c = customers` and `from c`.
- `collect` and `unnest` in an explicit-module project, which 0.1.6 refused
  with `PIE-S2802`, now check, and on PostgreSQL emit; MySQL reports
  `PIE-B1003` for every Collect read and Unnest, and the new `PIE-S2803` to
  `PIE-S2807` say why a form is not admitted.
- Single-file PostgreSQL SQL for `sum(Int)` changes: its result is a nullable
  signed 64-bit `bigint` for every Int input, and a sum of a `bigint` column
  outside that range fails with SQLSTATE 22003 instead of returning an exact
  `numeric`. Single-file MySQL SQL is unchanged.
- Strict readers of the JSON documents must upgrade: every blocker of a
  BLOCKED `pietto.sql-emission.v1` document (a failure document is always
  v1) gains a nonempty `suggestion`; Collect documents add `collection`
  columns, R27 requirements and `collect_*` range roles; the import hint of
  PIE-S2002, PIE-S2303, PIE-S2604, PIE-S2301 and PIE-S2103 fills the
  diagnostic's `suggestion`, which was null; and the batch document is a new
  format. VERIFIED documents gain no `suggestion` field.
- Some messages change: PIE-S2370 in every project now names `collect` among
  the one read of a let with `capture` lines, and the `config_schema` refusal
  of `explain --project` for a schema 1 or 2 project names the commands to use.
- Bundles and saved-job records made by 0.1.6 or earlier are refused by the
  changed code identity; keep their matching old environment.
- Nested saves add no workspace version: `0.1.7` saves nested results in the
  v7 workspace format of `0.1.6`. A saved-job record, nested or flat, is
  usable only under the code identity it names, so `0.1.7` refuses the
  records that `0.1.6` saved and `0.1.6` refuses those that `0.1.7` saves,
  nested results included. Pietto supplies no migration or rewrite.
- Pietto's own PostgreSQL sessions now set and verify `extra_float_digits=1`
  and `DateStyle=ISO,MDY` on every request, flat ones included.
- The execution extras install the same driver versions as `0.1.6`.
- `0.1.7` is a normal version number: once it is published,
  `pip install -U pietto` upgrades to it, and so do the pins `pietto~=0.1`
  and `pietto<0.2`.

### Nested relations: checking

- **Phase71 nested-relation spellings are checked.** In an EXPLICIT_MODULES
  project (`schema_version = 2`), `name = collect let_name` and
  `let o = unnest(binding.field)` are typed and checked as the next two
  entries describe; `PIE-S2802`, which 0.1.6 reported at each of them, is
  retired. Single files, LEGACY_FLAT projects and package modules still
  report `PIE-S2801`, which says how to make a `schema_version = 2` project.
- **Collect reads in explicit-module projects.** A relation with a
  `name = collect r` SELECT item completes like any other: the Collect
  output is a nested relation that is never None, and its relation stays
  readable with `from`, a JOIN, `exists` and its scalar columns. Such a
  project checks.
  New errors say why a read is not admitted: `PIE-S2803` for a Collect in a
  grouped SELECT or a relation let, of a source, table or query instead of a
  relation let of the same body, of a let whose columns are not known before
  completion, or of a let with a field that is not one of the eight collected
  leaf types (`Bool`, `Date`, `Decimal`, `Float`, `Int`, `Text`, `Timestamp`
  and `UUID`), has no known nullability yet (one computed with a binary
  arithmetic or comparison operator, such as `id + 1`, with `and` or `or`, or
  with `not`, `-` or `+` over one of those) or is itself collected;
  `PIE-S2804` for a let without `order by`; and `PIE-S2805` for a read of a
  nested field that needs a value (a comparison, ordering, grouping, a scalar,
  `in` or ANY read, `select distinct` or a set operation), or a nested field
  selected beside a RIGHT or FULL JOIN, a window or QUALIFY, GROUP BY or an
  aggregate, or in a relation let. As in a `select distinct` relation, a
  SELECT item that reads a shape-typed field, or a `let` bound to one, makes a
  relation with a Collect read report `PIE-S2333`.
  A let with `capture` lines counts `collect` as its one read, so a second
  read is `PIE-S2370`, whose read-once message now reads ``... can be read
  only once, by exists, scalar, in, collect or a join in the body of q.`` in
  every project, including those that use no `collect`.
- **Unnest binding in explicit-module projects.** `let o = unnest(p.field)`
  followed by one `cross join o`, `inner join o on ...` or
  `left join o on ...` (for example `on True`) reads the rows of a nested
  field that a `collect` SELECT item outputs: `o` has the collected let's
  fields, and its JOIN reports what any JOIN reports. Such a project checks.
  New errors say why an Unnest is not admitted: `PIE-S2806` for an argument
  that is not a nested field of the FROM input or a CROSS, INNER or LEFT JOIN
  written before the let, and `PIE-S2807` for a RIGHT or FULL JOIN of it, a
  second JOIN, another read of its name, an Unnest in a relation let, or one
  beside grouping, aggregates, windows, `select distinct`, `any(...)`, a
  Collect read, another Unnest or a RIGHT or FULL JOIN that may null-extend
  its binding.

### Nested relations: SQL emission

- **PostgreSQL Collect emission.** `emit-sql --project --dialect postgres`
  emits a Collect read (`name = collect r`) of the selected table or
  query. Each read is one `LEFT JOIN LATERAL` single-row aggregate: `COUNT(*)`
  under the field's label, then one `ARRAY_AGG` per child field under the
  child's label, in child order. Every array of a read is ordered by one
  private `ROW_NUMBER()` over `r`'s own ORDER BY items, so the arrays of one
  parent row stay aligned; a LIMIT on `r` applies per parent row, and sibling
  Collect reads are independent laterals. An empty collection is a count of 0
  with NULL arrays; a child row whose fields are all None counts 1, and a
  missing outer-JOIN container has a NULL count and NULL arrays.
- **Collections in later relations.** A table or query that reads such a
  relation, by name or through an import, may read its scalar columns, test it
  with `exists`, expand one collection with an Unnest, and keep a collection
  as an output beside an ordinary JOIN or the Unnest of another collection.
  Grouped child producers, query parameters and scalar filters keep that
  collection intact. On PostgreSQL the admitted Unnest is a JOIN whose right
  side is one `LATERAL ROWS FROM` that zips one `pg_catalog.unnest` per child
  array in child-field order; the final columns stay scalar, except a retained
  collection.
- **JSON documents.** A document (`pietto.sql-emission.v1`, or v2 with header
  parameters) describes a nested column as `logical_type.kind` `collection`
  with `element` entries and a `pg_column_arrays_v1` representation that lists
  the count and array columns by statement position, with `result_origin`
  added when the relation ends in ORDER BY or LIMIT. Every
  `correspondence.sql_symbol` stays a logical position, so a flat column after
  a nested field with F fields is F statement columns further right than its
  `sql_symbol`. The `collection` requirements and the generated kinds
  `collect_lateral`, `collect_count`, `collect_array` and `collect_ordinal` use
  rule R27. Each `collect_lateral.evidence` holds exactly one object with the
  `use`, `producer`, `terminal` and ordered `children` of the read, which the
  public reader checks against the parsed SQL; it is consistency evidence, not
  an authentication of altered documents. SQL ranges add the `collect_*`,
  `ordinal_*`, `distinct_wrapper_*` and `unnest_*` roles. These additions
  leave a document without a nested field unchanged. A generated SELECT counts
  its physical columns against the column limit (`PIE-B1007`).
- **Refused forms.** MySQL reports `PIE-B1003` (`collect_not_admitted_on_target`
  or `unnest_not_admitted_on_target`) at each Collect read and Unnest let. A
  nested UNION, an ordinary RIGHT or FULL JOIN carrying a nested value, and a
  nested window value stay refused on PostgreSQL too.

### Nested relations: Python execution

- **Bounded Collect and Unnest.** `compile_query` and `load_bundle` prepare
  the admitted PostgreSQL collection shapes without connecting, and
  `execute(..., route="postgres_rows")` runs them through the live compiled
  graph or a loaded source-free bundle. Collect fields may have Int, Bool,
  finite Text, finite Float, Decimal, Date, Timestamp and UUID children, and
  one CROSS, INNER or LEFT Unnest can expand one collection while the result
  keeps another. Named and imported producers, ordinary JOIN carry, scalar
  filtering, grouped child producers and header parameters keep the whole
  nested field.
- **Values.** Each collection keeps its child's authored ordering, without a
  tie-break guarantee. A missing outer-JOIN container is `None`, distinct from
  an empty `[]` and from a real child row whose fields are None. Float keeps
  its binary64 bits; Decimal keeps its precision and scale, in decimal128 or
  decimal256 as needed; Date stays within 1000-01-01..9999-12-31; Timestamp is
  timezone-free civil microseconds; UUID keeps its 16 bytes. Pietto's own
  PostgreSQL sessions set and verify `extra_float_digits=1` and
  `DateStyle=ISO,MDY`, flat requests included.
- **Bounds.** Before the main SQL, in the same read-only snapshot, an attempt
  checks `server_encoding = UTF8`, bounded physical root counts (at most 64
  rows for a parent root and 16 for a root that a collected child reads) and
  actual Text lengths (at most 256 UTF-8 bytes). Preflight bounds every
  emitted field, batch and total bytes and retained child occurrences, counting
  each JOIN edge and each retained occurrence; an unknown or unsupported bound
  is refused, and no protective LIMIT is added. `batch_rows` and `max_rows`
  count top-level rows, the rows that an Unnest expands included, and a
  parent's collection is never split across batches.
- **Saves, R1 and export.** Ordinary `save(..., route="postgres_rows")` keeps
  admitted nested results, final-flat Unnest included, in the existing v7
  workspace. Source-free R1 and independent read-only `verified_export` read
  the fixed saved checkpoint with the original nested schema and complete child
  lists. Parent occurrences are the checkpoint, batch and ACK unit; children
  have no cursor or ACK of their own, and rebatching keeps each child list
  whole. Export verifies each member before its first returned slice, caches at
  most one verified member and rechecks acceptance and reader lifetime before
  each slice.
- **Refused routes.** `postgres_adbc`, `mysql_rows` and guarded or refined
  nested requests are refused before any connection; R2 and recovery, relay
  and nested sink effects remain refused. Nested IPC is an internal checked
  transport, not a public IPC API.

### Batch project SQL emission

`emit-sql --project ROOT --all` emits every matching top-level table or query,
with optional exact `--module`, `--kind` and `--name` filters, in one
`pietto.sql-emission.batch.v1` document. Each batch item contains the same
document as its single-owner call. The exit status is 0 only when every item is
VERIFIED, 1 when one or more is BLOCKED and none is INPUT_REJECTED, and 2 for
any INPUT_REJECTED. The complete batch JSON has a 64 MiB limit; overflow
rejects the whole batch with exit 2 and no output directory. On supported Linux
filesystems, `--output DIR` writes a new directory, only when every item is
VERIFIED, with complete JSON artifacts and a manifest installed last; an
interrupted run can leave a directory without its manifest, which is
incomplete. Other platforms retain batch stdout. Existing paths are never
overwritten, and calls without `--all` retain their prior output and behavior.
`pietto emit-sql --help` does not list `--all`;
`pietto emit-sql --project ROOT --all --help` prints the batch usage, and the
[project guide](project-package.md) and
[project CLI JSON v2](spec/project-cli-json-v2.md) describe it.

### JOIN projections, Timestamp UNION and blocker suggestions

- In `emit-sql --project`, JOIN SELECT projections now accept the existing
  reviewed scalar calls, casts, conditionals, membership and comparison
  chains. ON, joined LET/WHERE, JOIN kinds and source/key domains keep their
  previous limits.
- In `emit-sql --project`, Timestamp UNION ALL and UNION DISTINCT preserve the
  existing exact carrier, civil-microsecond meaning and NULL behavior. No
  Timestamp INTERSECT/EXCEPT or additional set carrier is enabled.
- Every blocker of an `emit-sql --project` document gains a nonempty
  `suggestion` shared with text `hint:`. This changes BLOCKED JSON bytes while
  retaining the current format names; old strict readers must upgrade.
  VERIFIED documents and CLI error records gain no field, and batch items
  remain byte-identical to current single-owner output.

### Project SQL emission: numeric and temporal operations

- **Narrow Int arithmetic in bigint on PostgreSQL.** `emit-sql --project`
  computes a `+`, `-`, `*`, unary `-` or `abs` over `pg_int2`/`pg_int4`
  operands whose exact range leaves that type in `bigint`, writing
  `CAST(x AS pg_catalog.int8)` around its first operand, so `id + id`,
  `id * id`, `-id` and `abs(id)` over an `int4` field are now emitted instead
  of `PIE-B1002`. The proof is static (a narrow operation always fits 64
  bits), so a parameterized template such as `-nullif(id, low)` now carries no
  `int_range_representable` obligation and binds; before, it kept an `int4`
  carrier that no binding could satisfy. An operation that already fits its
  narrow type, an operation with a `bigint` operand (`id + 1` with its literal
  anchored to `bigint` included) and every MySQL statement are unchanged, and
  arithmetic that may leave 64 bits stays `PIE-B1002` except on PostgreSQL
  `bigint` operands (see the checked bigint rule below). For a still-BLOCKED
  PostgreSQL operation, the blocker hint says every result lies outside signed
  64 bits and PostgreSQL's checked operation could only fail; the MySQL hint
  keeps the signed-64-bit fit requirement. A public consumer of the
  emission observation accepts the new `int8_widen` overlay only where this
  rule requires it.
- **Date source fields.** An emission contract may map a `Date` field to
  PostgreSQL `pg_date` or MySQL `my_date` with the `date` domain. Such a field,
  like a derived Date, supports carrying, `==`/`!=`, `count`,
  `count_distinct`, DISTINCT, GROUP BY and `year`/`month`/`day`, and unlike a
  derived Date it is an equality JOIN key (INNER, LEFT, RIGHT); a FULL JOIN on
  a Date key stays refused.
- **Timestamp and Date ordering.** Timestamp and Date values of one carrier
  compare with `<`, `<=`, `>`, `>=` and inclusive comparison chains, in WHERE
  and in a JOIN ON condition alike (`on a.id == b.id and a.ts <= b.ts`),
  order a result or a window, and on PostgreSQL are `min`/`max` arguments,
  whose result keeps the carrier and, for a Timestamp, its result-contract
  meaning (MySQL keeps `PIE-B1003` for these `min`/`max`). Timestamp, Date and
  UUID values may partition a window; UUID ordering follows below. `min`/`max`
  of a UUID stays refused, and a Timestamp never compares with a Date.
- **Exact `sum(Int)` on PostgreSQL.** Both single-file `emit-sql` and
  `emit-sql --project` emit PostgreSQL `sum(Int)` as
  `CAST(SUM(CAST(x AS pg_catalog.int8)) AS pg_catalog.int8)`. In project mode
  this replaces `PIE-B1004` (`sum_int_aggregate_range_proof_missing`): the sum
  accumulates exactly, and its result is a nullable `Int` with storage
  `pg_int8` over the whole signed 64-bit range. A sum outside that range,
  including one over a physical `bigint` input, is never returned as a wrong
  value: PostgreSQL may report SQLSTATE 22003 (`bigint out of range`) while
  planning or running the statement, with no timing guarantee. In single
  files, where it applies to global, grouped and HAVING aggregates and to
  aggregate windows (written
  `CAST(SUM(CAST(x AS pg_catalog.int8)) OVER (...) AS pg_catalog.int8)`), it
  replaces the bare `SUM(x)`, which returned `bigint` for a `smallint` or
  `integer` column and an exact `numeric`, possibly outside signed 64 bits,
  for a `bigint` column. Project emission's generated R13 requirement carries
  the new evidence
  `{"overflow": "target_checked_signed64_narrowing"}`. This revises Phase66
  R13, which admitted no final aggregate CAST. Project MySQL keeps `PIE-B1004`,
  as its `CAST(DECIMAL AS SIGNED)` would clamp such a sum; single-file MySQL,
  and `Decimal` or `Float` `sum` or `avg`, are unchanged.
- **Checked bigint arithmetic on PostgreSQL.** An `Int` sign, `+`, `-`, `*`
  or `abs` over `bigint` operands whose exact range leaves signed 64 bits but
  meets them, such as `qty + 1`, `-qty` or `abs(qty)` over a `pg_int8` field,
  is now emitted unchanged instead of `PIE-B1002`: PostgreSQL's `bigint`
  operators are checked, so an out-of-range value is the same run-time
  SQLSTATE 22003 and never a wrapped one. The result keeps the part of the
  exact range inside signed 64 bits, and the operation's generated R05
  requirement carries the same evidence. PostgreSQL may also raise the
  error while planning, wherever it reduces the operands to constants, such
  as `(9223372036854775807 if True else 0) + 1` or a bound value, even over
  no rows or in a branch no row takes. A range wholly outside signed 64 bits,
  such as that of a constant, stays `PIE-B1002`, as such an operation could
  only fail. A parameterized template keeps its
  `int_range_representable` obligation, and on PostgreSQL a binding now
  discharges it under the same rule when the bound range meets signed 64
  bits. Likewise a slot value under a sign or inside arithmetic whose result
  only meets signed 64 bits now binds on PostgreSQL instead of `PIE-R1004`
  (`BINDING_INVALID`), so `execute()` may then fail after connecting, with
  `PIE-R3003` and SQLSTATE 22003, where it refused the value before. MySQL
  keeps `PIE-B1002` until a real-database differential reviews its `BIGINT`
  overflow error.
- **UUID ordering on PostgreSQL.** UUID values of one carrier now compare
  with `<`, `<=`, `>`, `>=` and inclusive comparison chains, order a result
  and order a window on PostgreSQL, by their 16 bytes compared as unsigned
  big-endian values, the order of PostgreSQL `uuid_cmp` and of Python
  `uuid.UUID`. MySQL keeps them BLOCKED (`PIE-B1003` for a comparison or
  result ORDER, `PIE-B1002` for a window ORDER key) until a real-database
  differential reviews its `BINARY(16)` byte order; `min` and `max` of a UUID
  stay `PIE-S2314`.
- **Observation and evidence.** The private emission observation records
  each generated requirement's evidence tokens and each aggregate's
  `result_cast`, and a public consumer admits `SUM`, its two casts and
  `target_checked_signed64_narrowing` only where the rules above produce
  them.

### Project mode

- **A relation-name qualifier through a `let` alias is refused, as in a
  single file.** After `let c = customers` and `from c`, `0.1.6` projects
  accepted a read such as `customers.price` in a query without a JOIN,
  outside `any(...)`, in every clause but HAVING and the ORDER BY of a
  grouped query, and `emit-sql --project` read the field of `c`. An
  explicit-module project now refuses it as it refuses any name that is no
  input, so such a program fails `check --project` and is blocked by
  `emit-sql --project`. Rewrite the read with the alias: `c.price`. A query
  with a JOIN, or a read inside `any(...)`, already refused it. At the read
  a project reports what a single file reports, such as PIE-S2102
  `Unknown field: customers.price`, with the differences for any unknown name
  that the [known limitations](#known-limitations) below list.
- **An import hint is also the JSON suggestion, names a declaration that is
  not exported, and never closes a cycle.** The hint that `0.1.6` added to
  PIE-S2002, PIE-S2303, PIE-S2604 and PIE-S2301 when another module exports
  the unknown name, and to PIE-S2103 for a `def` of another module, is now
  also the diagnostic's JSON `suggestion`, which was null; the message is
  unchanged. A module that imports the module of the diagnostic, directly
  or through others, is no longer named, since that import would close a
  module import cycle (PIE-S2703). When no other module exports the name,
  the modules that declare it without asking to export it are named the
  same way, with the export to add, where `0.1.6` gave no hint:
  `Unknown relationship parameter shape: Order; Order is a shape declared but not exported by types.pietto: export it there with export (shape Order), then import it with from "types.pietto" import (shape Order)`.
  The unknown relation of a Collect read gets no hint, since `collect`
  reads only a relation let of its own table or query (PIE-S2803), which
  no import gives.
- **`explain --project` names the commands for schema 1 and 2 projects.**
  Its `config_schema` refusal of a `schema_version = 2` project now reads
  `Project Explain runtime requires project schema version 4. Use check --project and emit-sql --project for this schema version 2 project.`,
  and of a `schema_version = 1` project
  `Project Explain runtime requires project schema version 4. Use check --project for this schema version 1 project.`;
  `0.1.6` gave only the first sentence. Its suggestion, for every schema
  version below 4, is now
  `explain --project reads only a schema version 4 package-root project, and changing schema_version alone does not convert a project.`,
  followed for schema 3 by the one-step conversion as before; it no longer
  names the commands, which the message of a schema 1 or 2 project now
  does. The code, location and exit status are unchanged.

### Command line

- `pietto emit-sql --help` ends its project-mode usage line with
  `In project mode --output writes the JSON artifact in either --format.`,
  as the [project guide](project-package.md) and the project-mode help of
  `--output` already say. The behaviour is unchanged.

### Release notes

- The 0.1.6 notes below were corrected after publication: see
  [Corrections after publication](#corrections-after-publication).

### Known limitations

None of these limits produces wrong SQL. The timings were measured on the
code of this release with CPython 3.13.13 on Linux x86-64; they show how the
cost grows and are no performance promise.

- **Layered JOIN DAGs are slow to check.** When each relation JOINs the
  relation before it and the one before that, `check --project` takes about
  1.7 to 2.7 times as long for every two more layers: about 1.8 s at 16
  layers, 3.1 s at 18, 7.3 s at 20, 18 s at 22 and 48 s at 24, where a single
  file of 16 or 18 such layers checks in about 0.3 s. `emit-sql --project` was
  not timed for this release. The grain that a project keeps for each JOIN
  still copies the factors of every path to its inputs.
- **An import cycle is slow to report.** A ring of modules that import each
  other is reported with one PIE-S2703, but only after the project builds
  readiness records whose number grows with the cube of the ring's size:
  `check --project` takes about 2.3 s for 40 modules, 9.4 s and 458 MB for
  80, and 71 s and 3.1 GB for 160. The change after `0.1.7` that records
  each blocked module's cycle members once is described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **Many relations or many JOINs are slow to check.** A project check builds
  an assessment for every pair of relations: one module with 300 tables
  checks in about 4.7 s (a single file of them in 0.55 s), and one with 600
  tables in about 14 s and 378 MB (a single file in 0.8 s); 200 modules of
  one source, table and query each take about 8.9 s. The JOIN properties of
  one query grow about with the cube of its JOIN count: one query with 60
  JOINs checks in about 3.0 s, with 90 JOINs in about 10 s (a single file in
  0.4 s), and with 120 JOINs in about 32 s and 609 MB. The changes after
  `0.1.7` make these checks faster; see
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A bare PIE-S2333 can hide later errors.** Some relations that a single
  file accepts, or refuses with another code, are still the bare PIE-S2333
  `Project relation semantic completion is unavailable: <r>` in a project,
  for example one whose SELECT output is an always-null number such as
  `o0 = None - 3.0`. The relations that read it report nothing of their own,
  such as an invalid LIMIT, until it is fixed. The
  [diagnostics reference](spec/diagnostics.md#semantic-diagnostics) lists
  these cases.
- **A cross-module shape error can add a bare PIE-S2333.** A source whose
  shape, imported from another module, fails for an error inside its
  declaration other than an unknown type, such as a duplicate field
  (PIE-S2501), still adds the bare PIE-S2333 at the source beside that
  error, where a shape in the source's own module reports only the error.
  So does a source whose field type is an alias, declared in another
  module, of a name that module imports with a relation kind (PIE-S2705).
- **A source without a shape is quiet beside some other errors.** In a module
  that reports some other errors, such as a duplicate shape field (PIE-S2501)
  or an unknown field (PIE-S2102), a source without a shape gets no
  PIE-S2333, and so no `(source items has no shape, ...)` advice, until that
  error is fixed; beside others, such as an invalid LIMIT (PIE-S2307), it
  still gets it.
- **An exported duplicate declaration.** A module that declares a source or
  shape twice and exports it reports PIE-S2704
  `Ambiguous local export declaration: source s` at the export; a single
  file, or the module without that export, reports PIE-S2001 at the second
  declaration.
- **An import after the target's own import fails.** When the target module
  re-exports a name whose own import of it fails, or imports a name and
  exports it with another kind, an import of the name from that module
  still adds PIE-S2705 (`Imported declaration is unavailable: ...` or
  `Imported declaration is private or not exported: ...`) beside the
  target's own error. An import of the very kind and name whose export the
  target refuses (PIE-S2704) adds nothing.
- **An unknown name.** A QUALIFY predicate that reads an unknown name outside
  a window reports PIE-S2332 `Unknown QUALIFY reference: <name>` in a project,
  where a single file reports PIE-S2102. When a relation name is read through
  a `let` alias after a JOIN (`customers.price` after `let c = customers`), a
  single file adds `; customers names a relation, not a binding: write c.price`
  and a project does not.
  When a query has several unknown names, a project can list a SELECT item's
  diagnostic before a WHERE test's or a GROUP BY key's, where a single file
  follows the source order. The change after `0.1.7` that reports the
  unknown QUALIFY name as PIE-S2102 in a mixed aggregate JOIN relation is
  described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A mixed aggregate JOIN.** A relation with JOIN inputs that mixes an
  aggregate with another projection reports only PIE-S2312 in a project, with
  or without ORDER BY, beside the PIE-S2305 of a repeated output name; a
  relation whose aggregate has an error of its own reports that error and no
  PIE-S2312, as a single file does. When its `let:` clause or WHERE is
  refused, it reports only that refusal, and the PIE-S2305 of a repeated
  output name, without PIE-S2312, and when its only other projection is a
  window, it is a bare PIE-S2333. A single file reports PIE-S2312 in the other
  cases, the errors of the other SELECT items and QUALIFY beside it, PIE-S2381
  when an aggregate may read rows repeated by a JOIN and, with ORDER BY, the
  PIE-S2380 of an ORDER BY key that reads an input field outside an aggregate.
  A project relation whose projections are all aggregates still reports that
  fan-out, as a PIE-S2333 with its cause. The change after `0.1.7` that aligns
  most of these cases is described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A repeated unknown SELECT item.** A SELECT item of an unknown name written
  twice, such as `nosuch`, reports PIE-S2102 at both items in a project
  outside a JOIN, and in a JOIN query at neither, at the first or at both,
  depending on GROUP BY and on whether a `where` or `let:` fails; for such a
  bare name a single file reports it at the first, with the PIE-S2305 that
  both report. The change after `0.1.7` that aligns it is described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **`explain --project` stops at the root package.** When the root package
  of a schema 4 project fails to load, for example for a syntax error in one
  of its modules, `explain --project` reports only the root's diagnostics;
  the errors of its dependencies appear once the root is fixed. The change
  after `0.1.7` that lists them when the root's pin check passes is
  described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A repeated environment premise.** An emission contract whose
  `environment` lists one premise twice with the same value is VERIFIED, and
  the artifact's `target.environment` lists it twice, while a repeated source
  description is INPUT_REJECTED. After `0.1.7` this is a documented rule; see
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A collection selected without a JOIN.** A table or query that reads a
  relation with a Collect read and selects its collection, without a JOIN or
  an Unnest, checks, but `emit-sql --project` reports it BLOCKED with
  `PIE-B1003` (`expression_evidence_unavailable`) at that SELECT item. Keep the
  collection in the relation that collects it, or select it beside a JOIN.
- **Collect ordering by an output name.** Completion does not yet order a
  collection by a key of `r` that is one name alone naming a SELECT output
  other than a window's (`order by oid` over `oid = id`); order by the input
  value (`order by id`) instead, or the table or query reports PIE-S2333.
- **A non-UTF-8 unrecognized argument to `emit-sql --project`.** With JSON
  output, an unrecognized argument that holds a byte that is not valid
  UTF-8 prints `pietto: error: terminal output could not be encoded` on
  stderr and no `INPUT_REJECTED` usage document (exit `2`);
  `--format text` prints the usage error.
- **`--all` is missing from `pietto emit-sql --help`.** That help does not
  list the batch option; `pietto emit-sql --project ROOT --all --help` prints
  the batch usage and `--all`.
- **A swapped argument pair.** A relationship call whose arguments are given
  in the wrong order, such as `PlacedBy(customers, order)` for
  `relationship PlacedBy(order: Order, customer: Customer)`, still reports
  PIE-S2604 at each argument instead of one diagnostic, as since 0.1.5.

### Rescheduled

These items are not fixed in `0.1.7`. By the owner decision of 2026-11-03
(see the [decision record](decisions.md)), each has the following home; the
[roadmap](roadmap.md#project-mode-follow-up) records them.

- **A project-mode quality interlude after `0.1.7`**, which may run beside the
  formatter step, takes: the import-cycle readiness records behind the slow
  PIE-S2703 (PMS-2); building the pairwise relation assessments only when
  private inspection asks for them (PMS-3); an incremental JOIN
  functional-dependency closure (PMS-6); `explain --project` diagnostics of
  the dependencies after a root failure (EXD-5); a rule for an exactly
  repeated environment premise (PE-09); the mixed aggregate JOIN diagnostics
  (F5); and the repeated unknown SELECT item (F7).
- **A later phase** takes linear analysis of layered JOIN DAGs, which needs an
  ARCHITECTURE_DECISION on the semantic identity of grain facts.
- **Phase72 Gate 1 candidates**, which that Gate 1 may accept or not, are:
  the rest of the D-11 and D-12 restoration that the post-0.1.4 stability
  repair deferred, that is, sound outer-JOIN aggregates that `check` still
  refuses with PIE-S2381, such as `min`, `max` or `count_distinct` over a JOIN
  that may repeat rows, or a LEFT JOIN anti-test `where o.id is None`, and the
  typed-NULL arithmetic of a project SELECT; the bare PIE-S2333 of a project
  relation whose SELECT output is an always-null number, which hides the
  errors of the relations that read it (F2); the `concat` and `stddev`
  functions, which the owner placed after Phase71 on 2026-10-30; and `now()`,
  which needs a semantic design first. None of them is available in `0.1.7`:
  `concat`, `stddev` and `now()` are unknown functions (PIE-S2103).

This decision covers the debts reviewed for this release. The other known
limitations above are carried over from `0.1.6` or come with the changes of
this release; no decision has scheduled them yet, and they stay documented
here until one does.

### Corrections after publication

These notes were corrected after `0.1.7` was published; the release itself
is unchanged.

- The status above now says that `0.1.7` is published.
- The known limitation of a mixed aggregate JOIN said that a project reports
  only PIE-S2312. It now also names the two cases where `0.1.7` does not: a
  relation whose `let:` clause or WHERE is refused reports only that
  refusal, and one whose only other projection is a window is a bare
  PIE-S2333. It also names the errors of the other SELECT items and QUALIFY
  that a single file reports beside PIE-S2312.
- The known limitations that changes after `0.1.7` lift or reduce now point
  to [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- The known limitation of a mixed aggregate JOIN now also names the
  PIE-S2305 of a repeated output name and a relation whose aggregate has an
  error of its own.
- The known limitation of a repeated unknown SELECT item said that a project
  reports PIE-S2102 at both items. It now says that this holds outside a
  JOIN, and that a JOIN query reports it at neither, at the first or at both
  items.

## Corrections and MySQL parity public alpha release notes — 0.1.6

**Status:** `0.1.6` was published from `bdb3f567` (tag `v0.1.6`) on the
versioned GitHub pre-release and PyPI channels. These historical release notes
neither publish a successor nor substitute for channel byte verification.

`0.1.6` retires no source spelling of `0.1.5`. It corrects single-file SQL and
checking, brings single-file MySQL `emit-sql` close to PostgreSQL for JOINs,
FULL JOINs and windows, corrects project mode, and moves the driver pins of
two Python execution extras. Of Phase71 it contains only
batch B1: the nested-relation spellings are recognized and refused. The
sections from 0.1.5 down describe published files.

### Highlights

- **Same-file reads are CTEs.** A single-file read of a table or query of the
  same file includes its SQL as a dependency CTE, in text and JSON output
  alike, and the `PIE-S2382` warning of 0.1.5 is retired. `emit-sql` text
  output also names each statement with a `-- name` line and ends it with `;`;
  JSON artifact SQL has no name line and no `;`.
- **Single-file QUALIFY and aggregate windows.** `QUALIFY` checks and emits
  for PostgreSQL and MySQL; `sum`, `count`, `avg`, `min` and `max` windows
  emit in single files; and single-file windows read JOIN inputs.
- **Single-file MySQL parity.** `emit-sql --dialect mysql` emits INNER, LEFT,
  RIGHT and CROSS JOINs, most FULL JOINs within PostgreSQL's FULL JOIN limits
  (as a derived table), windows, QUALIFY and aggregates over JOIN rows,
  aggregate windows, `round(Float)` and `date_trunc`, with the same matches,
  duplicates and NULL-extended rows as PostgreSQL under each target's own
  comparison rules. Some forms that PostgreSQL emits stay `PIE-B1000` on
  MySQL, among them GROUPS frames with an offset bound, EXCLUDE CURRENT ROW,
  GROUP or TIES, a read of an enum or other non-builtin field after a FULL
  JOIN, and more than 8 FULL JOINs in one relation. Project MySQL emission
  gains none of these forms.
- **Fewer conservative fan-out refusals.** A hand-written `on` equality to a
  unique key proves an at-most-one match as a relationship call does, and the
  bounded D-11 and D-12 proofs accept some outer-JOIN aggregates and typed-NULL
  arithmetic that 0.1.5 refused.
- **Warnings for what a Python reader may misread.** `PIE-S2106` (`/` of two
  Int values truncates), `PIE-S2107` (a `None` option of an `in` list never
  matches), `PIE-P1009` (`--` is not a comment), `PIE-S2383` (a WHERE test
  that rejects the NULL-extended side of a LEFT JOIN), `PIE-S2384` (`not in`
  with a nullable left value) and `PIE-S2385` (a single-file relation that
  emission will refuse). Warnings do not change the exit status of `check`.
- **Checking corrections.** An explicit-module project reads a shape-typed
  field as that shape in more places, as a single file does, and reads a FROM
  input through its alias; several diagnostics that pointed at the wrong
  problem now name it.
- **Project mode.** After an external review of 0.1.5 project mode,
  `check --project` and `emit-sql --project` report what a single file
  reports in many more places. An ambiguous or unknown read and a grouping
  or aggregate error in a relation without JOIN inputs keep their
  single-file code, message and position instead of a bare `PIE-S2333`; a
  failed import is no longer masked, and the relations that read it add no
  bare `PIE-S2333`; follow-on diagnostics of an error already reported are
  dropped; each module gets the single-file declaration checks; and import
  or export statements outside a `schema_version = 2` project are
  `PIE-S2708`. A wrong-kind import is `PIE-S2705`, re-exports resolve
  through any number of modules, and an unresolved import or an unknown name
  suggests the path or import it may mean. JSON v2 counts a file with only a
  semantic error as a file with errors, configuration, selector and contract
  errors name their fault, emission blockers point at their item, and the
  project guide and contracts match the code. The SQL that project emission
  still produces is unchanged. The known limitations under Project mode below
  list what remains, among them slow checks of layered JOIN DAGs, some bare
  `PIE-S2333`, a mixed aggregate JOIN that reports only `PIE-S2312`, a
  relation-name qualifier through a `let` alias that is still accepted, and
  a repeated unknown SELECT item reported twice.
- **R2 and a trailing `any`.** `save_recoverable` and `recover` accept a
  trailing `where any(...)` or `where not any(...)`.
- **Python execution dependencies.** `pietto[execute-mysql]` installs
  `mysql-connector-python==26.10.0` and `pietto[execute-postgres-adbc]` installs
  `1.13.0` of both ADBC packages; each route refuses the previous driver
  version with `PIE-R2002` before any connection.
- **Phase71 nested-relation spellings, recognized and refused.**
  `name = collect let_name` and `let o = unnest(binding.field)` are recognized:
  an explicit-module project types them and reports `PIE-S2802`, and every
  other mode reports `PIE-S2801`.
- **A style page.** [Pietto style](style.md) shows one way to write each thing
  for readers who know Python and a little SQL.

### Upgrading from 0.1.5

- 0.1.6 retires no source spelling, so a 0.1.5 file needs no `pietto migrate`
  step.
- Some programs that 0.1.5 accepted are refused or warned about, and some
  emit different SQL; the entries below describe each change. Programs that
  assert an empty diagnostic list or empty stderr see the new warnings.
- Bundles and saved-job records made by 0.1.5 or earlier are refused by the
  changed code identity; keep their matching old environment.
- In project mode, `check --project` refuses more programs that a single file
  refuses and `emit-sql --project` blocks them, a `schema_version = 1`
  project with import or export statements fails `check --project`
  (`PIE-S2708`), and many project diagnostics, the project JSON v2
  `files_with_errors` count, related locations and some error kinds change;
  Project mode below lists each change.
- An environment that keeps `mysql-connector-python==26.7.0` or the `1.12.0`
  ADBC packages is refused on that route; install the extra of this release.
- `0.1.6` is a normal version number: `pip install -U pietto` upgrades to it,
  and so do the pins `pietto~=0.1` and `pietto<0.2`.

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
  then reports `PIE-S2802`, as this release cannot lower or return them;
  single files, LEGACY_FLAT projects and package modules report `PIE-S2801`,
  which says how to make a `schema_version = 2` project. A user `def` named `collect` or
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
  CTE, in the text output and in the JSON `sql` of the reading artifact alike.
  An unsupported dependency also prevents SQL for its reader; the old
  `PIE-S2382` warning is retired. Text output names each statement with a
  `-- name` line and terminates it with `;`; JSON artifact SQL has no name
  line and no `;`.
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
8.4 spelling is still refused with `PIE-B1000`, and MySQL parity does not
change PostgreSQL SQL. As in the MySQL SQL emitted before, the place of NULLs in an
ascending or descending order, Text comparison under the column's collation,
and the type and scale of an aggregate's result follow MySQL. Project MySQL
emission gains none of these forms.

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
- `pietto[execute-postgres-adbc]` now installs `adbc-driver-postgresql==1.13.0`
  and `adbc-driver-manager==1.13.0` instead of `1.12.0`, and the
  `postgres_adbc` route accepts only `1.13.0`: an environment that keeps
  `1.12.0` is refused with `PIE-R2002` before any connection.
  `adbc-driver-postgresql` `1.13.0` no longer depends on `importlib-resources`,
  so the extra no longer installs it. The `1.13.0` driver returns a PostgreSQL
  `uuid` result column as the canonical `arrow.uuid` type instead of an opaque
  binary value; `postgres_adbc` checks that type and still delivers the same
  `UUID` values. The driver now classifies server errors by SQLSTATE, so the
  exception class in `failure.cause` can differ from `1.12.0`, which reported
  `ProgrammingError` for most of them: a multi-row scalar read (`21000`) now
  reports `OperationalError` and a data exception (class `22`) `DataError`.
  `code` and `sqlstate` are unchanged.

### Project mode

These entries correct `check --project`, `emit-sql --project` and
`explain --project` after a review of 0.1.5 project mode. An entry that also
changes single files says so.

#### Project diagnostics match single files

- Some explicit-module project programs that 0.1.5 refused with a diagnostic
  that hid the problem now report the problem itself, with the single-file
  code, message and position. They are still refused, and no SQL output
  changes:
  - A read after the JOINs of a field that more than one input has, such as
    `id` over `orders` and `customer`, in a SELECT item, an expression,
    a `let` value, WHERE, ORDER BY, a window's PARTITION BY or ORDER BY or a
    GROUP BY key, is PIE-S2335
    `Ambiguous field: id; write orders.id or customer.id` at the read. 0.1.5
    reported the bare PIE-S2333
    `Project relation semantic completion is unavailable: <relation>` at the
    relation, or PIE-S2102 `Unknown field: id` for a GROUP BY key, its
    SELECT item or a window.
  - A JOIN whose input names no relation, such as
    `inner join nosuch on nosuch.id == items.id`, is PIE-S2301
    `Unknown relation: nosuch` at the JOIN. 0.1.5 reported
    `JOIN pre-match input or relationship authority is unavailable.` and
    `JOIN ON reference is unavailable.` (PIE-S2335) instead.
  - A JOIN `on` read reports
    `JOIN ON reference is ambiguous: <f>; write <alternatives>`,
    `JOIN ON reference is unknown: <text>` or
    `JOIN ON reference is forward: <text>` at the read. 0.1.5 reported the
    same code without the read (`JOIN ON reference is unknown.`), after a
    PIE-S2334 `JOIN-local ON is available only when an EXPLICIT_MODULES
    project (schema version 2) completes it.`
  - A read in `any(...)` of a field its row does not have, such as
    `o.nosuch`, is PIE-S2102
    `Unknown or unavailable field in ANY predicate: o.nosuch`. 0.1.5
    reported PIE-S2334 `ANY predicate reference is unavailable.`, which
    remains for a bare name that only the generator row has: a project reads
    a generator field only qualified.
  - In a relation without JOIN inputs, an aggregate, grouping, grouped ORDER
    BY or `having` error is reported at its call or item with its
    single-file code and message: PIE-S2318
    (`Grouped projection is not a GROUP BY key: <f>`), PIE-S2319, PIE-S2320
    (`Grouped output without an aggregate is not supported yet`), PIE-S2312,
    PIE-S2311, PIE-S2314, PIE-S2315, PIE-S2104 for `string_agg` arguments,
    PIE-S2321, PIE-S2323 to PIE-S2327, and in `having` PIE-S2308 for an
    aggregate call (`Aggregate count() is not allowed in having clause; ...`),
    PIE-S2105 for operands and PIE-S2202 for a predicate that is no Bool.
    So are an unknown field (PIE-S2102) in an aggregate call, such as
    `sum(nosuch)`, or in a GROUP BY key, an aggregate's argument count
    (PIE-S2309, `Aggregate function sum expects 1 arguments, got 2`) and
    an invalid LIMIT (PIE-S2307), also beside another grouping error. An
    unknown GROUP BY key that is also selected is reported once, at the
    key, as in a single file. An
    aggregate argument of a field declared with a type alias names the
    alias (`got Whatever`), as in a single file.
    0.1.5 reported the bare PIE-S2333 at the relation. A grouped ORDER BY
    key that names a selected window result is not refused by this check. A relation over a row of unknown type, or one
    that reads a `let` name, a relation, a captured field, a query parameter
    or `any(...)` in those positions, still reports the bare PIE-S2333, and
    so does an aggregate of a shape-typed field. A relation that reports an
    error of its own, such as an unknown field in a grouped SELECT item, no
    longer adds a bare PIE-S2333 beside it.
    This replaces the bare PIE-S2333 that two entries under Checking and
    diagnostics above still name for a relation without JOIN inputs: a
    `string_agg` argument of only `None` values is now PIE-S2104
    (`Invalid arguments for aggregate string_agg: expected two Text arguments`),
    and a qualified input field such as `users.count`, also through a `let`
    alias, in HAVING is PIE-S2327
    (`Unsupported having expression form: qualified name`) and in a grouped
    ORDER BY PIE-S2321
    (`Unsupported grouped ORDER BY item; expected a supported select output name`),
    as in a single file.
  - In a relation without JOIN inputs that a project completes itself, such
    as one with `any(...)` or QUALIFY, an ORDER BY key that names a SELECT
    output is
    ``Unknown field: <name>; this project relation cannot order by a SELECT output yet (restate its expression, or bind it with `let` and order by that name)``,
    as with JOIN inputs. 0.1.5 reported `Unknown field: <name>` alone. An
    invalid LIMIT is PIE-S2307 whatever the ORDER BY key is, where 0.1.5
    reported that ORDER BY error instead.
- In a single file, a relation with JOIN inputs that mixes an aggregate with
  another projection and has ORDER BY reports PIE-S2312, with the PIE-S2380
  of a key that reads an input field outside an aggregate, as without the
  ORDER BY. 0.1.5 reported PIE-S2334
  ``ORDER BY is not available after an ungrouped aggregate over JOIN rows: the result has one row; remove `order by`.``,
  which is now reported only when every projection is an aggregate.
- A call's function is resolved before its arguments, in single files and
  projects. In WHERE, a row `let` and an `any(...)`, as already in a JOIN
  `on`, a call of an unknown function is PIE-S2103 `Unknown function: R`,
  also for a relationship that the module does not declare, and a bare name
  the call is given is no longer read as a field. 0.1.5 reported PIE-S2102
  `Unknown field: <row>` for each row argument instead, with no PIE-S2103;
  inside `any(...)` it reported
  `Unknown or unavailable field in ANY predicate: <row>` in a single file
  and PIE-S2334 `ANY predicate reference is unavailable.` in a project. An
  unknown function is now reported beside an argument's own error, for
  example both `foo` and `bar` in `foo(bar(x))`. In a project, a
  relationship of another module adds
  `; R is a relationship of a.pietto, which a module cannot import: declare it in this module`.
- An explicit-module project reports fewer diagnostics after an error it
  already reports. A relation stopped by an input whose failure is reported
  gets no PIE-S2333, and its JOIN no PIE-S2335
  `JOIN pre-match input or relationship authority is unavailable.` or
  `JOIN ON reference is unavailable.`. Such inputs are:
  - an import that does not resolve, is private or is ambiguous (PIE-S2701,
    PIE-S2705, PIE-S2706);
  - a source whose shape or field type does not resolve (PIE-S2303,
    PIE-S2002), also where another module reports it: an unknown type at a
    field of the shape it imports, or the export its import's target
    refuses (PIE-S2704); the cross-module cases under Known limitations
    below still add the bare PIE-S2333;
  - a name reported as unknown;
  - a relation or table-function body that fails with its own error;
  - an earlier JOIN of the same relation that fails;
  - a relation that a FROM, a JOIN, a set operand or an `any(...)`,
    `exists`, `scalar` or `in` read names and that fails, also one that
    only follows another failure.

  Such a read or operand also drops its own follow-on: PIE-S2334
  `ANY input relation is unavailable.` (and the PIE-S2202
  `ANY predicate requires a known Bool expression.` or PIE-S2335
  `JOIN ON expression type is unavailable.` of an expression around such an
  `any(...)`), PIE-S2348
  `... the columns of <r> are not known before completion.`, PIE-S2342
  `Set operand N has no concrete completed output.` and, in a JOIN's `on`,
  a relationship call's PIE-S2604
  `Unavailable row argument for relationship R parameter p` (a call in an
  `any(...)` over such an input keeps it, as a single file does for an
  unknown ANY relation).
  A read refused in its position (PIE-S2348, PIE-S2349, PIE-S2350) or one
  that closes a relation cycle (PIE-S2302) likewise stops its relation
  without a PIE-S2333 beside it.
  A relationship declaration's own errors now come before the calls that
  cannot use it, as in a single file, and a parameter shape that a failed
  import leaves unresolved reports only the import's error: the
  relationship's calls add no PIE-S2604
  `Relationship predicate R has no unambiguous checked declaration`. A
  relation that reports an error of its own from an earlier stage, such as
  an unknown field in a SELECT item, adds no PIE-S2333 without a cause
  beside it. A source
  without a shape, in a module that reports no other error, now says what it
  needs:
  ``Project relation semantic completion is unavailable: items (source items has no shape, which a project needs to type its rows: write `source items: <shape> = ...`)``.
  A relation stopped by an input whose failure is reported reports its own
  checks, also those that do not depend on the input, such as PIE-S2307 for
  an invalid LIMIT, once that failure is fixed. An
  explicit-module project also never reports the temporary texts
  `... is available only when an EXPLICIT_MODULES project (schema version 2) completes ...`
  of a JOIN kind, a JOIN-local `on` or a set operation; such an operation
  reports what stops it, such as PIE-S2341. 0.1.5 reported these follow-on
  diagnostics beside the root error. Each read of an unknown relation name
  is its own PIE-S2301, a set operand too: another relation's read of the
  same name does not stand in for it. 0.1.5 reported only PIE-S2334 at such
  a set operation.

#### Module diagnostics

- A failed import is no longer masked. In an explicit-module project, the
  module import and export errors (PIE-S2701, PIE-S2705, PIE-S2706,
  PIE-S2707) are reported even when a query has a query-local naming error,
  a `def` error (PIE-S2397), a query header error (such as PIE-S2001
  `Duplicate parameter name in query p: cutoff` or PIE-S2354) or a query
  parameter in a position that does not take one (PIE-S2355). They come
  first, ahead of the errors that stop the check before semantic analysis,
  for every module, in `check --project` and in `emit-sql --project`, once
  every module parses and its syntax is admitted. 0.1.5 dropped the module
  errors of every module.
  A `let` whose value is a relation that the module imports but cannot bind,
  as in `let c = customers` with `customers` not exported by its target, now
  reads that name as `inner join customers` would, and the import's own
  error reports it; 0.1.5 reported only PIE-S2604
  (`A row-value let must follow FROM and every JOIN and precede WHERE`) at
  the `let`. The PIE-S2301 `Unknown relation: <name>` of the `let` entry
  under Checking and diagnostics above is only for a name the module never
  imports.
- An import that names the wrong kind, such as `shape customers` for an
  exported `source customers`, is PIE-S2705 at the imported name:
  `Imported declaration has another kind: shape customers from "a.pietto" is a source; write source customers`.
  0.1.5 reported PIE-S2707
  `Inconsistent explicit-module target facade: "a.pietto"` at the target
  path, once per import statement. A relation read of such a name, as in
  `let c = customers`, follows that error as for a failed `source` import,
  and the other modules' errors are still reported; when the target also
  has the name as the requested kind or another kind of its namespace, such
  as a shape for `type customers`, privately or not, the module never
  imported the relation, and such a read is its own PIE-S2301. Likewise, a
  type use of a name that the import asks for with a relation kind, as in
  `source Customer` or `query Customer` for a shape, follows that error,
  unless the module declares a type of that name: no PIE-S2002 or PIE-S2303
  repeats its advice (a source in another module whose field type is an
  alias of such a name still adds the bare PIE-S2333; see Known
  limitations). When the target declares the requested
  kind but exports only another kind of that name, it is PIE-S2705
  `Imported declaration is private or not exported: ...`. An unknown export
  of a name that the module declares only with another kind names that
  kind: `Unknown export binding: type Customer; Customer is a shape`, and an
  export of a name that the module imports only with another kind names the
  imported kind:
  `Invalid imported export candidate: type Customer; Customer is a shape`.
  A wrong-kind import through a re-export points at the re-exporting
  module's import of the name, as a direct one points at the declaration.
- An import of a name that its target module only imports itself, with the
  same kind, no longer says the name is unknown. When the target does not
  export it, it is PIE-S2705
  `Imported declaration is private or not exported: shape Row from "b.pietto"`;
  when the target re-exports it but its own import of it fails, it is
  PIE-S2705
  `Imported declaration is unavailable: shape Row from "b.pietto", whose own import of Row fails`.
  Both point at the target's import of the name. 0.1.5 reported
  `Unknown imported declaration: shape Row from "b.pietto"`, with no
  related location.
- A re-export of a re-export now resolves through any number of modules, to
  the one original declaration. 0.1.5 rejected the third hop and beyond with
  PIE-S2705 `Unknown imported declaration`, plus a PIE-S2333 for each
  reader. Each further hop resolves the project's imports once more, so a
  chain of hundreds of re-exports takes tens of seconds to check.
- PIE-S2701 names up to three selected paths that an unresolved import
  target may have meant:
  `Unresolved module import target: "a.pietto"; did you mean "models/a.pietto"? An import path is the project-root-relative path of a selected source, with / separators`.
  0.1.5 reported `Unresolved module import target: "a.pietto"` alone.
  The target and the paths are quoted as Pietto strings, so a non-ASCII
  character stays as written; 0.1.5 echoed the target with `\u` escapes. A
  control character, which a file name rarely holds, is still shown as a
  `\u00XX` escape, which a Pietto string does not accept. A path that is not
  valid UTF-8, which no Pietto string spells, is never suggested.
  The language reference now states that an import target is the
  project-root-relative path of a selected source, with `/` separators.
- An unknown name that other selected modules export now says where and how
  to import it, for PIE-S2002 `Unknown type`, PIE-S2303
  `Unknown source shape`, PIE-S2604 `Unknown relationship parameter shape`
  and PIE-S2301 `Unknown relation`, for example
  `Unknown relationship parameter shape: Order; Order is a shape exported by types.pietto: import it with from "types.pietto" import (shape Order)`.
  Every exporter is listed in path order, at most three in full, and none is
  chosen. An exporter is an export that resolves: an export that is itself
  refused (PIE-S2704), a duplicate export request included, or a re-export
  whose own import fails, is not named, nor is a module whose path is not
  valid UTF-8, which no import can spell. A module that already declares or
  imports the name, in either namespace, such as a `source Customer` or an
  `import (source X as Customer)` beside a use of the shape `Customer`, gets
  no hint, since that import would collide with the declaration or binding
  (PIE-S2706).
  PIE-S2103 for a `def` that only other modules declare adds
  `; twice is a def of a.pietto, which a module cannot import: declare it in this module`.
  0.1.5 reported each of these messages without the hint.

#### Stricter checks

- `check --project` in an explicit-module (`schema_version = 2`) project now
  runs in each module the declaration checks a single file runs, with the
  same codes, messages and positions, reading each type name as the module
  declares or imports it. 0.1.5 printed `Project check OK` (exit 0) for
  these projects, and `emit-sql --project` emitted a VERIFIED artifact for
  their tables and queries. Now `check --project` reports these errors
  (exit 1), and `emit-sql --project` is BLOCKED with them. They follow each
  module's enum and shape declaration diagnostics, module by module, each
  module's in source order. While any import cycle (PIE-S2703) exists, these
  checks wait in every module, as the other completion checks do, and are
  reported once every cycle is fixed. The newly refused forms are:
  - Decimal type arguments out of range or misspelled, in shape fields, type
    aliases and constraint or derive signatures (PIE-S2004), such as
    `amount: Decimal(1, 2)`, `type M = Decimal(5, 9)`, `Decimal(66, 0)` or
    `Decimal(precision = 9, scale = 2)`. For such a field
    `emit-sql --project` reported the emission blocker PIE-B1004; it now
    reports PIE-S2004 at the field's type, and a project `select distinct`
    over such a field reports PIE-S2004 before PIE-S2339. A plain `Decimal`
    or `Decimal()` still passes `check --project`, and emission still blocks
    it with PIE-B1004;
  - a repeated constraint or derive name (PIE-S2001
    `Duplicate symbol name in callable namespace: N`) or parameter name
    (PIE-S2001 `Duplicate parameter name in ...`);
  - an unknown type in a constraint or derive signature (PIE-S2002); a name
    already blocked by an import collision, a duplicate type declaration, or
    a failed import of a type or of a name its target has only as a type,
    reports only that error, as at a shape field;
  - a constraint whose declared type is not Bool (PIE-S2401);
  - a constraint, derive or field `derive` body whose type does not match
    its declaration (PIE-S2402);
  - errors inside constraint and derive bodies, shape `check(...)`,
    `index ... when` predicates and field `derive` bodies, such as an unknown
    name (PIE-S2102), invalid operands (PIE-S2105), a check that is not Bool
    (PIE-S2202), an aggregate (PIE-S2308) or a `def` argument that does not
    fit its parameter (PIE-S2395);
  - a derived-field cycle (PIE-S2504).
- A bare name in `any(...)` that both the outer row and the generator row
  have, such as `price` in `where any(o.price == price for o in orders)`
  over `items`, is PIE-S2102 `Ambiguous field in ANY predicate: price` in
  WHERE, SELECT and `let` of an explicit-module project, as in a single
  file. 0.1.5 accepted it at `check --project`, and `emit-sql --project`
  read the outer row's `price`.
- In an explicit-module relation without JOIN inputs or GROUP BY, an ORDER BY
  key that reads a field the relation does not have, also through a field of
  a shape (`home.nosuch`), is PIE-S2102 `Unknown field: <name>`, a call of an
  unknown function is PIE-S2103 `Unknown function: <name>` (with the
  `def of <module>` hint for a `def` of another module), and a key written
  as a bare constant (`"x"`, `-1`) is PIE-S2380, as in a single file. A
  SELECT output is a key only as the whole key, so `-total` with an output
  `total` that is no input field is PIE-S2102. 0.1.5 accepted all of these at
  `check --project`, and `emit-sql --project` blocked them with PIE-B1003. A
  constant that a `let` name binds is still ordered by as a value, and such
  keys are still not typed: `order by lower(status)` passes
  `check --project`.
- Import and export statements outside a `schema_version = 2` project are no
  longer silently ignored (new PIE-S2708). 0.1.5 ignored them in single
  files and in `schema_version = 1` projects, so an unresolved import, or an
  export of an undeclared name, passed `check`, and single-file `emit-sql`
  emitted SQL.
  - A single-file command now warns at each import and export statement in
    every check mode:
    `Module import is resolved only by check --project ROOT, in a schema_version = 2 project`,
    with `Module export` for an export. An editor can still check one module
    file alone.
  - `check --project` of a `schema_version = 1` project refuses each such
    statement with a PIE-S2708 error:
    `Module import is read only in a schema_version = 2 project: set schema_version = 2 in pietto.toml`.
    A schema-1 project with import or export statements that 0.1.5 accepted
    now fails `check --project`.

#### Project CLI and JSON

- `result.check.files_with_errors` of `check --project --format json` now
  counts every input that is the primary location of an error diagnostic,
  parse or semantic, and `files_ok` is `files_total - files_with_errors`.
  0.1.5 counted parse status only, so a file with only a semantic error
  counted as ok. The keys are unchanged. `result` and `inputs[].kind`
  (`"source"`) are now documented in project CLI JSON v2.
- Explicit-module (schema 2) project JSON v2 diagnostics from the module
  graph, import binding and module resolution now carry the related
  locations those owners compute, each with a `null` message: for example,
  PIE-S2705 points at the private declaration and PIE-S2706 at the colliding
  local declaration. 0.1.5 always wrote `[]`. Legacy-flat (schema 1)
  diagnostics keep `[]`.
- Wrong project schema, still of kind `config_schema`:
  - `check --project` and `emit-sql --project` on a schema 3 or 4
    package-root project now say
    `check --project reads schema_version 1 or 2 projects and emit-sql --project schema_version 2 ones; this schema_version N package-root project is read by explain --project`
    (schema 3 adds ` once converted to schema_version 4`), with the path
    `pietto.toml`. 0.1.5 said
    `Schema-vN ... does not use project source selection.` with a null path.
  - `emit-sql --project` on schema 1 now says it needs `schema_version = 2`
    and to declare cross-file names with import and export. 0.1.5 said
    `Project emit-sql requires the explicit-module project mode.`
- Source patterns and selection:
  - Each pattern fault has its own message: `must use / as the path separator`,
    `must be relative to the project root`,
    `must be a normalized project-relative pattern`, or
    `uses unsupported glob syntax; patterns use only *, ? and a whole ** path part`.
    Unsupported glob syntax is now `project_glob`; it was `project_path`.
  - `matched no .pietto files` now carries the path `pietto.toml` and the
    include and exclude lists.
  - A `pietto.toml` that starts with a UTF-8 BOM now gets
    `pietto.toml starts with a UTF-8 byte-order mark; save it as UTF-8 without BOM.`
    0.1.5 gave a TOML `Invalid statement` error. Such a file is still
    refused.
  - A decimal integer longer than 4300 digits in `pietto.toml` is now
    `config_parse`
    (`Project configuration TOML is invalid: Exceeds the limit (4300 digits) for integer string conversion: value has N digits.`),
    and in a package manifest `Package manifest TOML is invalid.` 0.1.5
    printed a Python traceback in `check --project` and `explain --project`,
    and `emit-sql --project` reported `project_root`
    `Project root could not be pinned.`
  - Selection no longer lists a directory that no include pattern can
    reach, or that an exclude covers completely (`dir/**`), so an unreadable
    directory there, such as a database data directory, no longer fails the
    project. One that could hold a selected file still fails with
    `project_glob`.
- CLI usage:
  - `--project ''` and `--project=` are now a usage error,
    `argument --project: Project root must be a non-empty path.`, in
    `check`, `explain` and `emit-sql`. 0.1.5 used the working directory.
  - In text mode, giving a project directory as the file adds
    `hint: for a project use pietto <command> --project <dir>` when that
    command's `--project` reads the project's schema version (`check` 1 or
    2, `emit-sql` 2, `explain` 4); the `emit-sql` hint also names the
    arguments it needs (`--module FILE --kind KIND --name NAME --dialect DIALECT --emission-contract FILE`).
    JSON v1 output is unchanged.
- Project Explain package diagnostics:
  - A stale dependency pin now reads
    `In dependency package ns/name@ver: Package content digest does not match the sha256 pinned by [[dependencies]] in <declaring package>.`
    0.1.5 blamed `the declared root sha256`.
  - Every error and diagnostic from a dependency package names that
    package.
  - A root-manifest schema error's location kind is now `project_relative`;
    it was `package_relative`.

#### Project SQL emission

- Selector errors: `Selected owner is absent or ambiguous.` is now kept only
  for more than one match. With no match, the error lists the project
  modules, with a `/`-separator hint, or the declarations of that kind in
  the module. The `--module` help shows `models/queries.pietto`. Contract
  source selectors list the modules with sources, or the module's sources.
- Contract errors keep their kinds:
  - `Invalid emission contract structure.` now names the missing key, which
    the path points at, and the expected keys. An unexpected key is counted,
    not echoed.
  - A field-name mismatch says `Field ordinal N must be named <field>`.
  - A contract source selector with an empty `module` or `name`, or a `kind`
    other than `source`, names that key (`sources/0/selector/module`) and
    says what it must be, as `Source selector module must be a non-empty string; modules with sources: <modules>.`
  - `Invalid UTF-8 JSON emission input.` is split into a BOM, non-UTF-8,
    `Invalid JSON emission input: <reason> (line L, column C)`, a duplicate
    key, a non-finite number (`NaN`, `Infinity`, or one that overflows, such
    as `1e400`), nesting depth, an integer of more than 4300 digits
    (`Invalid JSON emission input: Exceeds the limit (4300 digits) for integer string conversion: value has N digits.`),
    and a string with an unpaired surrogate escape such as `"\ud800"`
    (`Emission contract strings must not hold a lone surrogate escape (\uD800-\uDFFF).`).
- A selected source whose file name is not valid UTF-8, which `check
  --project` reads, now makes `emit-sql --project` INPUT_REJECTED
  `project_path`
  `Project source path must be valid UTF-8 to emit SQL: "\udcff.pietto"; rename it.`
  (exit `2`) where a path in the document would name it: in place of SQL,
  whose request lists every selected source; in place of the diagnostics
  and blockers located in that file, which the document leaves out; and
  beside another input error about it or about such a source directory,
  such as `source_read` or `project_glob`, whose `path` is then null. An
  emission document is UTF-8, where such a name has no text. A message that
  names it, such as a PIE-S2103 hint for a `def` it declares or the
  `--module` listing of an `emission_selector` error, shows it escaped as
  in `project_path` (`m\udcff/a.pietto`) and is kept with its status
  and exit code. A PIE-S2701 suggestion or an import hint never names it,
  since no import can spell it. A project that is refused for another reason (a schema 1
  project, a parse or semantic error in another file, or the selected
  owner's blocker, selector, contract or `--dialect`) reports that as
  before. In place of SQL, in a diagnostic located in such a file and
  beside an input error about it, 0.1.5 printed
  `pietto: error: terminal output could not be encoded` and no document,
  also with `--format json`. So did an `--emission-contract` path that is
  not valid UTF-8 and cannot be opened; its `emission_contract_read` error
  now has `path` null.
- Blocker places and reasons, with codes unchanged except where stated:
  - Plan-stage refusals (`order`, `group`, `join`, `window`, ...) are
    located at their ORDER BY item or clause, not the whole declaration.
  - `count`, `count_distinct`, `min` and `max` over Decimal or Float are now
    PIE-B1003 `<fn>_argument_outside_reviewed_int_domain`; they were
    PIE-B1004 `decimal_aggregate_range_proof_missing` or
    `float_aggregate_finite_result_proof_missing`. Only `sum` and `avg` keep
    those proofs.
  - Every refused aggregate is reported at its own item; 0.1.5 reported only
    the first.
  - A refused group key is located at its GROUP BY item; 0.1.5 had location
    null.
  - `complete_ordered_source_schema_required` is located at the source
    declaration, with related locations at the shape fields the contract
    leaves out or maps out of order. A JOIN that reads such a left-out field
    reports `join_input_source_field_not_bound` at the same source; 0.1.5
    had location null.
- Text failure output now follows a premise, release, `order` or Int-range
  blocker with a `hint:` line naming the reviewed value or remedy, for
  example
  `add {"key":"client_encoding","scope":"statement","value":"UTF8"} to "environment"`
  or `the reviewed mysql value is {..."lower_case_table_names=0"}`, and
  prints `related:` locations. The Int-range hint names no storage type,
  since the field's own storage bounds the result. JSON detail tokens are unchanged, and
  `pietto.execution` refusal text matches the CLI.

#### Performance

- A project whose relations read earlier relations along several paths, for
  example `from` the previous relation and `any(...)` over the one before
  it, no longer takes minutes to report an error in an early relation: each
  relation's error report now visits every shared upstream result once.
- An import cycle (PIE-S2703) is reported several times sooner, for example
  a 40-module cycle in about 4 s instead of about 20 s, and an 80-module
  cycle in about 15 s instead of about two minutes: the private module
  inspection now derives each record kind's key sets once instead of once
  per checked scope. Its private cycle records still grow with the cube of
  the cycle length, so very long cycles stay slow.
- These two changes leave results, diagnostics and output unchanged.

#### Documentation

- The [project guide](project-package.md) starts from a minimal
  `schema_version = 2` `pietto.toml` and describes schema 1 as the
  legacy-flat mode, with no JOIN, no `any(...)` and no SQL emission. It
  documents the `[sources]` pattern rules, the per-file resource limits
  (1 MiB of UTF-8, PIE-P1006, and 200,000 tokens, PIE-P1007; the number of
  files, their total size and `pietto.toml` are not limited), and which
  schema each command reads: `check --project` 1 and 2,
  `emit-sql --project` 2, and `explain --project` only 4. A schema 3
  project converts by setting 4 and adding an empty
  `[capability_environment]`.
- Its new section on explaining a package-root project gives a copyable
  schema-4 layout with a schema-2 configuration beside it, a package
  manifest, a standard-library script that computes the package digest, and
  a target example. `explain --project` reports package and capability
  portability, not module semantics, and stops before dependencies when the
  root package fails to load.
- Its project SQL emission section documents the reviewed target releases
  (PostgreSQL 18.6 and MySQL 8.4.12), the field representation of each
  logical type per dialect, each premise's values per dialect and when it is
  needed, a MySQL contract example, that `--output` always writes the JSON
  artifact, and the forms that `check --project` accepts and
  `emit-sql --project` refuses.
- The [configuration contract](spec/pietto-config-v1.md) is rewritten as the
  implemented contract: `schema_version` 1 to 4 with the keys each allows,
  no `[project]` table, an optional `exclude`, the `[package]` and
  `[capability_environment]` tables, and the error kinds.
  [Project CLI JSON v2](spec/project-cli-json-v2.md) marks
  `explain --project` as the separate Project Explain JSON v1 command that
  needs schema 4 and lists the `emission_contract_read`,
  `emission_contract_schema` and `emission_selector` error kinds.
- The README links the new sections, and its Slice13 contract link points at
  the current specification on `main` instead of v0.1.1. The
  [roadmap](roadmap.md) records `explain` for schema 2 projects and wider
  project SQL emission (a PostgreSQL/MySQL parity batch) as follow-ups.

#### Known limitations

These project-mode limits remain. None of them produces wrong SQL.

- **Layered JOIN DAGs are slow to check.** When each relation JOINs the
  relation before it and the one before that, `check --project` and
  `emit-sql --project` take about 2 to 3 times as long for every two more
  layers: a few seconds at 16 layers, and tens of seconds at 20 to 22. This
  release is faster than 0.1.5 on such projects, but the grain that a
  project keeps for each JOIN still copies the factors of every path to its
  inputs; sharing them is deferred (see the [roadmap](roadmap.md)). Only the
  time is affected, and single-file checks are not.
- **A bare PIE-S2333 can hide later errors.** Some relations that a single
  file accepts, or refuses with another code, are still the bare PIE-S2333
  `Project relation semantic completion is unavailable: <r>` in a project,
  for example one whose SELECT output is an always-null number such as
  `o0 = None - 3.0`. The relations that read it report nothing of their own,
  such as an invalid LIMIT, until it is fixed. The
  [diagnostics reference](spec/diagnostics.md#semantic-diagnostics) lists
  these cases.
- **A cross-module shape error can add a bare PIE-S2333.** A source whose
  shape, imported from another module, fails for an error inside its
  declaration other than an unknown type, such as a duplicate field
  (PIE-S2501), still adds the bare PIE-S2333 at the source beside that
  error, where a shape in the source's own module reports only the error.
  So does a source whose field type is an alias, declared in another
  module, of a name that module imports with a relation kind (PIE-S2705).
- **A source without a shape is quiet beside another error.** In a module
  that reports another error, a source without a shape gets no PIE-S2333,
  and so no `(source items has no shape, ...)` advice, until that error is
  fixed.
- **An exported duplicate declaration.** A module that declares a source or
  shape twice and exports it reports PIE-S2704
  `Ambiguous local export declaration: source s` at the export; a single
  file, or the module without that export, reports PIE-S2001 at the second
  declaration.
- **A non-UTF-8 unrecognized argument to `emit-sql --project`.** With JSON
  output, an unrecognized argument that holds a byte that is not valid
  UTF-8 prints `pietto: error: terminal output could not be encoded` on
  stderr and no `INPUT_REJECTED` usage document (exit `2`), as 0.1.5 did;
  `--format text` prints the usage error.
- **A mixed aggregate JOIN.** A relation with JOIN inputs that mixes an
  aggregate with another projection reports only PIE-S2312 in a project,
  with or without ORDER BY. A single file also reports PIE-S2381 when an
  aggregate may read rows repeated by a JOIN and, with ORDER BY, the
  PIE-S2380 of an ORDER BY key that reads an input field outside an
  aggregate. A project relation whose projections are all aggregates still
  reports that fan-out, as a PIE-S2333 with its cause.
- **A relation-name qualifier through a `let` alias is accepted.** After
  `let c = customers` and `from c`, a read such as `customers.price` is
  accepted by `check --project`, and `emit-sql --project` reads the field of
  `c`, while a single file refuses it with PIE-S2102
  `Unknown field: customers.price`. Refusing it in a project would refuse
  programs that check today, so it waits for a decision. The change after
  `0.1.6` that refuses it is described under
  [Unreleased changes following 0.1.6](#unreleased-changes-following-016).
- **A repeated unknown SELECT item.** A SELECT item of an unknown name
  written twice, such as `nosuch`, reports PIE-S2102 at both items in a
  project; a single file reports it at the first, with the PIE-S2305 that
  both report.
- **An import after the target's own import fails.** When the target module
  re-exports a name whose own import of it fails, or imports a name and
  exports it with another kind, an import of the name from that module
  still adds PIE-S2705 (`Imported declaration is unavailable: ...` or
  `Imported declaration is private or not exported: ...`) beside the
  target's error, which it follows. An import of the very kind and name
  whose export the target refuses (PIE-S2704) adds nothing.

### Still deferred

- Reporting a swapped argument pair as one diagnostic, which the 0.1.5 notes
  deferred, is not in this release: a relationship call whose arguments are
  given in the wrong order, such as `PlacedBy(customers, order)` for
  `relationship PlacedBy(order: Order, customer: Customer)`, still reports
  PIE-S2604 at each argument.

### Corrections after publication

These notes were corrected after `0.1.6` was published; the release itself
is unchanged.

- The Project mode highlight said that a failed import keeps its single-file
  code, message and position. A single file resolves no import, so it has no
  such code; the highlight now says what changed, as
  [Module diagnostics](#module-diagnostics) describes: the import error is no
  longer masked, and the relations that read the failed import add no bare
  `PIE-S2333`.
- The known limitation of a mixed aggregate JOIN named only an ORDER BY
  case and the PIE-S2380 that a single file adds. It now also names the
  fan-out PIE-S2381 that a single file reports, with or without ORDER BY.
- The section [Still deferred](#still-deferred) was added: the 0.1.5 notes
  deferred reporting a swapped argument pair as one diagnostic, and these
  notes did not say that it stays deferred.
- The known limitation that a project accepts a relation-name qualifier
  through a `let` alias now points to the change after `0.1.6` that refuses
  it; `0.1.6` itself accepts such a read.

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
