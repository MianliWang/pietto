# Pietto language

Pietto is a gradual semantic SQL authoring DSL. Its compiler pipeline is:

```text
source -> parse -> analyze -> immutable IR -> selected SQL dialect -> CLI text/JSON
```

Pietto compiles SQL; its compiler and CLI do not connect to a database or
execute SQL ([Execution](execution.md) describes the separate execution alpha).
Syntax may be broader than the currently supported semantic and backend subsets.
Unsupported combinations fail closed with deterministic diagnostics.

This page is the complete reference. [Pietto style](style.md) shows one
recommended way to write each thing.

## Source structure

Blocks use a trailing colon and spaces-only indentation. Braces are not block
delimiters, and tabs must not be mixed with spaces.

A line ends at LF, CRLF or a lone CR, and one file may mix them; each counts as
exactly one line end. Every reported position, from parse and indentation
errors through semantic diagnostics in single-file and project commands, has a
one-based line and column, and the column counts characters after the last line
end, so a file with CR endings reports the positions of the same file with LF
endings. No other character ends a line: form feed, vertical tab, U+001C to
U+001E, U+0085, U+2028 and U+2029 are ordinary characters in a comment or string
literal and a syntax error (PIE-P1000) elsewhere, and the leading-tab check
(PIE-P1004) counts lines the same way.

A comment starts with `#` and runs to the line end. `--` starts no comment:
minus signs written together are each a minus, so `amount > 100 -- 50` is
`amount > 100 - (-50)`, a threshold of 150 where SQL would read `100` and a
comment. Each run of minus signs written together reports the warning
PIE-P1009 at its first two, in every command and project that parses source
except `migrate`; write `#` for a comment, or `- -50` for the minus signs.

The single-file `check`, `explain`, and `emit-sql` commands choose the check
mode with `--check-mode loose`, `checked`, or `strict`; the default is
`checked`. The mode sets the severity of two diagnostics: a source without a
shape (PIE-S2303) and a computed projection without an alias (PIE-S2304).
`loose` omits them, `checked` reports them as warnings, and `strict` reports
them as errors. Project commands reject `--check-mode`. SQL emission always
takes its dialect from `--dialect`; PostgreSQL and MySQL are the current
backends.

A file has no header. The older header lines `pietto <number>`,
`mode <mode>`, `dialect <name>` and `encoding <name>`, which warned with
PIE-P1012 from `0.1.9`, are retired as source `is` was: every command and
project that parses source, dependency packages included, except `migrate`,
refuses each one with PIE-P1000 in every check mode. Its suggestion names the
line, as in ``Delete the header line `pietto 0.9`; it has no effect.``; a
`mode loose` or `mode strict` line gets ``Delete the header line
`mode strict`; in a single file pass `--check-mode strict` instead; a project
never applied it.``, and `dialect postgres` or `dialect mysql` gets ``Delete
the header line `dialect mysql`; it has no effect; `emit-sql` takes
`--dialect mysql`.`` A header line never selected a language version, legacy
spelling or the SQL backend.

To migrate, delete the header lines. `pietto migrate FILE > FILE.new` deletes
each one that has no effect (`pietto <number>`, `mode checked`, `dialect`,
`encoding`; a comment on the line stays) and writes the result to standard
output only. A `mode loose` or `mode strict` line set the check mode of a
single file, so `migrate` refuses it with PIE-P1011 (manual migration): delete
it and pass `--check-mode loose` or `--check-mode strict` to the single-file
`check`, `explain` or `emit-sql` instead. A dependency package with a header
line fails to load until it is migrated and published again.

Top-level declarations are `type`, `enum`, `constraint`, `derive`, `def`,
`shape`, `source`, `table`, and `query`. Shape-typed `relationship` predicates
and explicit-kind module `import` / `export` statements are also top-level forms.

### Layout

Single-line clauses omit the colon; multiline clauses use a colon and an
indented block. For example, `select id, total = sum(amount)` and the following
projection preserve the same item order:

```text
select:
    id
    total = sum(amount)
```

This rule also applies to `group by`, `order by`, `where`, `having` and
`qualify`. An `enum`, `def`, `constraint`, `derive` or relationship predicate
header instead always ends with ':', and a short body may follow it on the same
line: `enum Status: active, suspended`, a `def`, `constraint` or `derive` body
`return expression`, or a relationship predicate body, as in
`relationship oc(o: Order, c: Customer): o.customer_id == c.id`. An enum header
line without ':' is PIE-P1000. A list line may contain several
comma-separated items; a comma outside parentheses cannot continue a list on
the next line. A `where:`, `having:` or `qualify:` block joins its lines with
`and`, preserving each line as one operand:

```text
where:
    status == "paid"
    email like "%@%" and coupon_code is None
```

A block cannot follow content already supplied on its header line. An empty
condition block, or a line starting with `and` or `or`, is PIE-P1000. A new
query-local name uses `let name = expression`; SELECT output naming uses
`name = expression` without `let`.

Parentheses permit line breaks and comments without ending the expression.
Continuation indentation need not match a block, but tabs remain invalid:

```text
where (region == "EU"  # Europe
    or region == "NA")

qualify coalesce(lag(n) window(order by item), 0) > 1
```

There is no backslash continuation. An unclosed `(` is PIE-P1008 at the
innermost open parenthesis, and the rest of the file is not parsed. An indented
first code line is PIE-P1000 (`Unexpected indentation.`); indentation containing
a form feed, vertical tab or Unicode space other than an ordinary space is also
PIE-P1000. LF, CRLF and lone CR follow the position rules above.

Declaration and clause words such as `type`, `source`, `select` and `is` can be
field, output, parameter and scalar-binding names where the grammar permits a
name. `any` and `for` are contextual: `any(value)` remains an ordinary function
call, and `def any(...)` and fields named `for` are not banned. Only the exact
`any(predicate for row in relation)` form introduces an existence binder.
`None`, `True`, `False`, Boolean operators and `window` are reserved in their
expression roles. String contents and comments are never rewritten as keywords.

### Formatting source

```bash
pietto fmt shop.pietto            # print the formatted source
pietto fmt --check shop.pietto    # exit 1 if the file is not formatted
pietto fmt --write shop.pietto    # replace the file if it is not formatted
pietto fmt --check --project shop # exit 1 if a module is not formatted
pietto fmt --write --project shop # replace each module that is not formatted
```

`fmt` changes whitespace outside tokens and writes three spellings one way.
It never adds or reorders a token, and keeps the spaces between two tokens of
a line, except around a token it removes, and the text of every comment except
its trailing spaces and tabs. The program stays the same: `check` reports the
same diagnostics apart from their positions, and `emit-sql` writes the same
SQL.

- A string takes double quotes: `'paid'` becomes `"paid"`; a `"` inside it
  becomes `\"` and a `\'` becomes `'`, so the value is the same (see
  [Expressions](#expressions)).
- An `import` or `export` list on one line loses its parentheses and trailing
  comma: `from "m.pietto" import (def pos, source rows,)` becomes
  `from "m.pietto" import def pos, source rows`. A list over several lines
  keeps them.
- An order item loses its `asc`, which is the default: `order by id asc,
  name desc` becomes `order by id, name desc`, in a relation, a window and an
  aggregate call such as `string_agg(name, ",", order by name asc)` or
  `first(x, order by k asc, id)`. When that `asc` began a line inside
  parentheses, the line goes if nothing else was on it, and a comma right
  after the `asc` moves to the end of the last line before it that is not
  blank, unless that line ends with a comment.

The other spelling of each stays accepted with no warning. `fmt` keeps
`table` and `query`, `1_000`, a one-line clause and its block, comparison
chains and every other trailing comma as written. Until the Phase82 freeze,
`fmt` may write more spellings one way; the release notes list each change.

- Blocks are indented by four spaces; a line inside parentheses moves with the
  line it continues.
- A comment line takes the indentation of the line that follows it in its
  block; an end-of-line comment is preceded by two spaces.
- Exactly one blank line separates two top-level declarations, one-line or
  not, except that consecutive imports and exports have none between them, as
  in Python. The comment lines at the left margin over a declaration belong to
  it: the blank line goes above them, and no blank line stays among them or
  under them. Comment lines at the left margin that no declaration follows
  (after the last declaration or in a file of comments) keep the blank lines
  written among and above them, one at most in a row. Other runs of blank
  lines become one, and blank lines at the start and end of the file are
  removed.
- Trailing spaces and tabs are removed, also at the end of a comment.
- Every line ends with the file's first line ending, a non-empty file ends
  with one line ending, and a leading BOM is kept.

The result is lexed again and must give the same tokens, blocks, code lines,
comments and text apart from blanks and those spellings; when it does not, or
when it would exceed the source size limit, nothing is printed or written and
`fmt` exits 1. A file with parser errors is refused with the diagnostics
`check` reports and exit 1; diagnostics refer to the file as read. `--check`
never writes. `--write` refuses with exit 2, before reading it, a symbolic
link or a file that is not regular. It replaces the file atomically only when
it changes, and then also refuses with exit 2 a read-only file, a file that
belongs to another user, a file that changed after it was read, or a file it
cannot replace. `fmt` has no style options.

`--project ROOT` formats the modules of an explicit-module project
(`schema_version = 2`), the files `check --project` reads, in module order,
each exactly as `fmt` formats one file; it needs `--check` or `--write`.
`--check` reports `would reformat: PATH`, with the module's project-relative
path, for each module that would change, and then exits 1. When the project
cannot be read, `fmt` reports its project errors and each source over the size
limit (PIE-P1006) as `check --project` reports them, formats no module and
exits 2; a project of another schema version is refused as `config_schema`.
When a module has parser errors or cannot be formatted, the diagnostics and
errors of every module are reported, no file is written and `fmt` exits 1.
`--write` refuses with exit 2, before writing any file, a module that is a
symbolic link, and a module to replace that is read-only, belongs to another
user, is not a regular file or is in a directory it cannot write.
It then replaces each module that changes, atomically and in module order, and
stops with exit 2 at the first one that changed after it was read or that it
cannot replace; the modules already replaced stay replaced. It writes no file
that the project does not select.

### Migrating old source

The public parser uses modern spelling by default. Retired spellings receive
PIE-P1000 before AST normalization; its message states the located rewrite,
which JSON output also carries as the diagnostic's suggestion. The
private legacy reader exists for diagnostics and migration, not as another
public compiler mode. The retired `pietto NUMBER` header line selected nothing
(see [Source structure](#source-structure)); there is no
syntax-selector flag or required new header number.

```bash
pietto migrate old.pietto > migrated.pietto && pietto check migrated.pietto
```

`migrate` reads its input without changing it and writes one complete UTF-8
source to stdout only after the result passes the modern parser. It preserves
untouched comments, strings, line endings and a leading BOM. It emits diagnostics
and no partial source when migration needs a decision. It does not validate SQL
backend capability or access a database.

`semi join name on predicate` and `anti join name on predicate` become
`where any(predicate for name in name)` and `where not any(...)` in place: the
JOIN's name binds each row in the unchanged predicate. Before a later JOIN the
WHERE filters at the same point; as the last JOIN it becomes the relation's
WHERE. R2 refines a test in either position as the semi or anti JOIN it
represents when it is alone or AND-composed with other filters. A test under
`or`, over a captured let, or whose predicate reads another block remains
`PIE-R1004` at `save_recoverable` or `recover` (see [execution](execution.md)).
A semi or anti JOIN needs manual migration
(PIE-P1011) when it has no `on`, when lets or a WHERE follow it as
the last JOIN, when the new binder would hide another meaning of its name from
the predicate (the relation of an inner `any(... in name)`, the name alone,
such as an input field of that name, or the FROM input or another JOIN of that
name), and when it is written with `as`, which is an old JOIN binding (below);
0.1.4 wrote every semi and anti JOIN with `as`. The PIE-P1011 of such a JOIN
names its rewrite, such as `where any(predicate for o in orders)` for
`semi join orders as o`. An enum header line without
':' gains it. A source that mixes retired spelling with modern spelling that
`migrate`'s reader of old source cannot read, such as `T | None`, is migrated
by the same rules, except that each of its bare types needs manual migration
(see the nullability rules below); modern spelling that this reader also
reads, such as `source name: Shape = ...`, does not count.

In older source an ungrouped ORDER BY key written as one name alone, where a
SELECT output of another value (a selected window result included) had that
name too, read the input field of that name over a known input row, and over
an unknown row its SQL named the key alone, which the database reads as that
output (see the name rule after `select` in Sources and relations). Where the
FROM input is a source of the same file whose shape, also declared once in
that file, has that field, `migrate` qualifies the key with the FROM name
(`order by order_lines.quantity`). It keeps the key where that source has no
shape or the shape lacks the field, keeps a `let` name and an output of that
same field, and refuses the key with PIE-P1011 over JOIN inputs or any other
FROM input, whose row is not syntactic. A source that the modern parser
accepts, or that also uses modern spelling the old reader cannot read, keeps
every key as written, and `check` reports a key that is still ambiguous.

Old source-bound relationships and `JOIN ... AS ...` require an explicit review
of source and row identity. Unsupported conversions and a legacy Float cast
that would become a call to a same-named callable also require manual migration.
A named window declared after `select` moves, whole lines and their comments
included, to the end of its lets, just before `where`, `group by` or `select`;
since windows now share the let namespace, a window named like a `let` of its
table or query (a value, an input alias, a legacy `let:` binding or a relation
let), or like an input relation or field of its body that a `let` cannot take,
needs manual migration (PIE-P1011) instead. `migrate` knows the fields only of
an input declared in the same file; `check` refuses any other such name.
A source valid under both syntaxes is refused when its interpretation differs:
for example `True`, `False` or `None` as old identifiers versus new literals,
or `return (x)` as an old call to a function named `return` versus a new return
statement. PIE-P1011 reports every relevant occurrence in source order. A form
that proves the whole accepted source is modern, such as source binding with
`=`, prevents this false ambiguity; a numeric header does not. A modern file
that remains genuinely ambiguous can therefore still need manual confirmation
when passed to `migrate`.

Nullability migrates to the two modern states: `T not null` becomes `T`,
`T nullable` becomes `T | None`, and a bare `T`, whose nullability 0.1.4 left
unknown, becomes `T | None`, so migration never adds a claim that a value is
not None. The base type of a `type` alias stays bare, as 0.1.4 never gave an
alias's nullability to the values that use it, and a `nullable` alias is
PIE-P1011, as a modern alias cannot include None. In a source that the modern
syntax also accepts, or that mixes retired spelling with modern spelling that
`migrate`'s reader of old source cannot read, such as `T | None` (not
`source name: Shape = ...`, which it reads), `migrate` cannot tell which
syntax a bare type was written for, so each bare type outside an alias is
PIE-P1011 and never gains `| None`, as 0.1.4 reads it as unknown and the
modern syntax as never None:
``Bare type 'Int' needs manual migration because 0.1.4 reads it as unknown
nullability and modern syntax as never None. Write 'Int | None' where a value
may be None; a source already written in modern syntax needs no migration. No
migrated source was emitted.``

## Single files and projects

`check FILE`, `explain FILE` and `emit-sql FILE --dialect ...` read one file.
A table or query starts with an explicit `from`, may name additional inputs
with `let`, and may use supported INNER, LEFT, RIGHT, FULL and CROSS JOINs,
`any` and `not any` filters before a later JOIN, row-scalar expressions,
relationship predicates and Boolean `any` values.
JOIN availability still depends on its actual inputs, condition and target;
parsing a form is not a promise that every combination emits. Single-file
`check` and both PostgreSQL and MySQL `emit-sql` support these JOINs within the
[single-file JOIN limits](#single-file-joins). Single-file
`explain` refuses each JOIN relation with PIE-I1000 at stage `ir`: Semantic
Metadata Artifact v1 describes one input per relation. Its JSON envelope stays
unchanged.

Single-file SQL emits each table and query as its own statement. A statement
that reads a table or query of the same file, with `from`, a JOIN or
`any(...)`, also an `any(...)` that only its QUALIFY or the ORDER BY after it
reads, defines it, and each table or query that one reads, as a CTE named
after it (`WITH "active_users" AS (...)`), each after the ones it reads, so the
statement runs without that relation in the database; a CTE's body is that
relation's own statement without its `WITH`, except that each unaliased output
(PIE-S2304) takes a private alias `__pietto_column_<n>`, so no read of a CTE
column binds to the name the database would give it. A statement that reads
such a relation by a name it gives no output, such as `lower` for an unaliased
`lower(email)` over a source without a shape, whose fields a check cannot know,
is refused with PIE-B1000 at the reading relation: alias the output, as in
`lower = lower(email)`, and read that name. A CTE takes the place of a
table named without a schema in the CTEs after it and in the statement's
SELECT (MySQL compares the names case-insensitively), so `emit-sql` refuses a
statement with PIE-B1000 when it reads such a table there: read the table
with its schema, or rename the table or query. MySQL emission also refuses a
statement with two CTEs whose names differ only in case, a CTE or QUALIFY
derived table with two outputs whose names differ only in case, and a JOIN
statement with two input or `any` aliases whose names differ only in case:
MySQL compares table aliases without case on a server that keeps its table
names in lowercase (`lower_case_table_names`), which `emit-sql` cannot see.
A statement that
reads a table or query whose own SQL is refused is refused with the same
reason. An explicit-module project also emits the relation it reads as a CTE.

An explicit-module project (`schema_version = 2`) additionally provides module
imports/exports, set operations, DISTINCT, relation blocks (`let name:`), query
header parameters, typed VALUES, `generate_series`, and the existing `exists`,
`scalar` and `in` relation reads within their documented scopes. Project SQL
emission selects one table or query, one dialect and an emission contract.
LEGACY_FLAT and PACKAGE_ROOT keep their existing narrower availability; modern
spelling does not widen those project modes. Single-file commands refuse the
project-only forms with an ERROR: PIE-S2334 for DISTINCT and set operations
(at the FROM or JOIN for a set-operation input), and PIE-S2345 to PIE-S2352 for
relation lets, header parameters, VALUES bodies, relation reads, `capture`
lines and table functions. Only an explicit-module project reads import and
export statements: a single-file command reports each one as a PIE-S2708
WARNING (`Module import is resolved only by check --project ROOT, in a
schema_version = 2 project`), so an editor can check one module file alone,
and a LEGACY_FLAT project check reports each one as a PIE-S2708 ERROR that
asks for `schema_version = 2`.

A LEGACY_FLAT project (`schema_version = 1`) checks no JOIN and no `any(...)`
of the current syntax. Each JOIN, of any kind and whatever its target, is one
PIE-S2334: at its `on`, a relationship call such as
`on OrderCustomer(orders, customer)` included, or at the JOIN when it has no
`on`, with the text
``JOIN customer: a schema_version = 1 project has no JOIN in the current syntax; set schema_version = 2 to check it.``.
Each `any(...)`, before a JOIN or after it, nested or not, in any clause, is
one PIE-S2334 at the `any(...)`, with the text
``any(...): a schema_version = 1 project has no any(...) in the current syntax; set schema_version = 2 to check it.``.
They come in source order, also in a relation whose other diagnostics such a
project omits. 0.1.4 refused this spelling of JOIN and `any(...)` with
PIE-P1000, so this refusal removes nothing that 0.1.4 accepted. The
relationship JOINs that 0.1.4 checked in such a project
(`inner join customers as customer`, a JOIN `via` a relationship and the other
forms written with `as`) are therefore no longer available. Rewrite each as a
`let` and a JOIN with `on` (`let customer = customers`, then
`inner join customer on OrderCustomer(orders, customer)`; `migrate` reports
each old JOIN with PIE-P1011), then set `schema_version = 2`; in a project of
several files, add the imports and exports its modules need, a relationship
included (`from "models/a.pietto" import relationship OrderCustomer`; see
[project and package](project-package.md#schema-compatibility)).

| SQL concept | Pietto source |
| --- | --- |
| Named query block / derived table | `let name:` with an indented body, then `from name` |
| Row input alias | `let buyer = customers`, then `left join buyer on ...` |
| Correlated existence value | `any(predicate for row in relation)` |
| Semi / anti join (`WHERE [NOT] EXISTS`) | `where any(...)` / `where not any(...)`; before a later JOIN it filters at that point |
| Existing whole-relation existence read | `exists name` in an explicit-module project |
| Membership subquery | `value in name`, with one output column |
| Scalar subquery | `scalar name.column` |
| Set combination | `union all a, b`, with an explicit quantifier |

A successful `check` does not prove IR or SQL capability. When completed
single-file facts already show that SQL emission will refuse a relation,
`check` also reports PIE-S2385 WARNING at the cause. PostgreSQL and MySQL
emission both refuse a RANGE frame offset; an effective `ignore nulls` or
`from last` modifier; a FULL JOIN `on` conjunct, a relationship call read as
its body, that is not an equality between an `Int` field of the target and
one of an earlier input (such as `a.id == b.id and b.kind == "x"`,
`a.id < b.id`, `True` or an `or`); and a FULL JOIN after a `where any(...)`
or `where not any(...)` that no RIGHT JOIN takes into its `on`. In a relation
whose FROM does not end at a `mysql.table` source, `check` also warns for an
untyped all-None output read by another relation or by the relation's own
QUALIFY (through a derived table, which PostgreSQL types as text), an
operator whose
operands are all `None` (`None + None`, `-z` for `let z = None`), a CASE,
`coalesce` or `nullif` of only `None` values that an operator, a condition, a
numeric or temporal function or a comparison with a non-Text value would
read, a `Float(...)` or `Text(...)` of a value not known to be `Int` (other
than one that reads a field of unknown type, such as `Text(x + 1)` over a
source without a shape), a `count` of a field typed by a shape, a
`substr` index or `ntile`, `lag`, `lead` or `nth_value` integer literal
outside PostgreSQL's 32-bit range, and a CTE that would hide a table, named
without a schema, that the same statement reads. MySQL emission emits an
untyped all-None output that another relation reads, but refuses one read
after a FULL JOIN, which carries only fields of a builtin type, and `check`
does not warn for that. A relation with an error
gets none of the warnings that follow its expressions or its CTEs. The warning
does not change the command's exit status or attempt SQL emission.
Single-file QUALIFY is typed and lowers after the window stage. PostgreSQL and
MySQL emit it through a private derived-table filter, retaining only visible
selected outputs and applying relation `order by` and `limit` after the filter.
MySQL may merge a CTE whose windows sit in such a derived table into each
read and run those windows once per read, where a window whose order has ties
may pick different rows each time, so a MySQL statement that defines a QUALIFY
relation as a CTE ends that CTE, when it has no `limit`, with
`LIMIT 18446744073709551615`, MySQL's largest, which keeps every row and makes
MySQL materialize the CTE once, as PostgreSQL computes a WITH query once.
Both backends
refuse unsupported navigation modifiers such as `ignore nulls` and `from last`;
MySQL also refuses GROUPS frames with an offset bound and EXCLUDE CURRENT ROW,
GROUP or TIES. MySQL writes an offset-free GROUPS frame as the same RANGE frame
and leaves out an authored EXCLUDE NO OTHERS, which excludes nothing. Over a
Text order the column's collation decides which rows are peers, so under a
case-insensitive one, such as MySQL 8.4's default, `'a'` and `'A'` are peers
on MySQL and not under PostgreSQL's default collation. Both
backends refuse the FULL JOIN cases described in
[Single-file JOINs](#single-file-joins). PostgreSQL also refuses a table or
query that another relation of the file reads with `from` or as a JOIN input
when one of its outputs is `None` itself, such as `v = None`, a `let` name
bound to `None`, or a conditional or `coalesce` whose every value is such a
`None`, as PostgreSQL would give the reader a `text` column where Pietto has
no type (PIE-B1000). A source connector must match the
selected backend. PostgreSQL's untyped NULL restrictions and the project
physical-carrier requirements described below remain in force. Only emission
for the selected target establishes that a source can emit for that target.

A project relation without a JOIN input of its own whose SELECT output is
NULL of no type by NULL propagation (a `None`; a sign or arithmetic with such
an operand; a conditional or `coalesce` whose every value is such a value),
such as `o = None`, `-None`, `None + None` or `amount + (-None)`, completes as
in a single file, its output of unknown type, and so does one whose output has
a type of its own and reads such a value, also through a `let` name, as
`same_value(coalesce(None, None), amount)`, `coalesce(None, None) == amount`
or `n is None` after `let n = None`, its output of the type a single file
gives it (`Bool`); with a JOIN input of its own, only a typed output that
reads such a value directly completes, and in a `select distinct` relation
an output of no type does not complete (bare PIE-S2333, where a single file
refuses `select distinct` with PIE-S2334). The relations that read a typed
output report their own errors (an invalid LIMIT, an unknown field). One
that only tests an untyped output in WHERE (`where o is None`) completes too
and reports its own errors as a single file does, an invalid LIMIT among
them; one that selects or passes it through (`z = o` or `o`) completes too
and reports its own errors as a single file does, except an invalid LIMIT
(PIE-S2307), for which it still reports the bare PIE-S2333 instead; and a
relation with a JOIN input of its own whose output has no type, or reads
such a value through a `let` name, still fails with the bare PIE-S2333,
where a single file accepts it. Project SQL refuses such an output
(PIE-B1003 `expression_evidence_unavailable`). A relation that computes
with, groups by or aggregates an output of unknown type it reads, or reads
its relation as a JOIN input, still fails closed with the bare PIE-S2333,
and so does one that reads as a JOIN input a relation whose typed output
reads such a value through a `let` name, a relation with a Collect read
beside such an output, and one whose output has no type but is not always
NULL, because such a NULL stands beside a typed value in a function call
other than `coalesce` (`abs(amount + (-None))`), a `coalesce` with a typed
value (`coalesce(-None, amount)`), an `in` list (`(-None) in (1, 2)`) or an
`and`/`or` (`(-None) and True`), or whose output is only a `let` name bound
to such a value (`o = m` after `let m = amount + (-None)`), outputs a single
file completes with no type. An explicit-module project check warns at each
such output that completes in a relation without an error and without a JOIN
input of its own, also when a JOIN or `union all` reads the relation,
PIE-S2385 ``Project SQL emission is unavailable because `o` is an untyped
all-None output; ...`` (``... because `o` reads an untyped all-None value;
...`` for a typed output), at the output of the relation that computes the
value (not at the output of a relation that selects or passes it through, as
`z = o`), where a single file warns at the untyped value itself, as a single
file warns where its SQL emission refuses one; unlike a single file, it also
warns at such an output that nothing reads, since project SQL refuses every
one. A typed output that completes in a relation with a JOIN input of its own
gets no warning; project SQL refuses it the same way.

### Top-level constants

A single file may declare a constant at the top level:

```pietto
cutoff: Date = "2024-01-31"
```

The name is a plain name (not a keyword or soft keyword), the type is exactly
`Bool`, `Int`, `Float`, `Text`, `Date` or `Timestamp` (never `| None`, no
`Decimal` yet), and the value is one literal of that type: `True` or `False`;
an integer, or a number with a decimal point for `Float`, optionally after a
minus sign; a Text literal; for `Date` the Text literal `"YYYY-MM-DD"` from
1000-01-01 to 9999-12-31 and for `Timestamp` `"YYYY-MM-DD HH:MM:SS"` with up
to six fractional digits from 1000-01-01 00:00:00 to 9999-12-31
23:59:59.499999 (the civil Timestamp interval). Anything else, `date(...)`,
`Float(...)`, `None` or arithmetic included, is PIE-S2391; a repeated
constant name is PIE-S2001.

A bare name equal to a constant reads it anywhere a value is read: WHERE,
lets, SELECT items, `def` bodies, `any(...)` predicates, JOIN conditions,
`limit`, function arguments. A source's connector is not such a place: what
a source reads is part of its identity, so `postgres.table(name)` with a
constant `name` is PIE-S2391. Each read is the constant's literal at the
read, typed as declared: a `Date` constant is a `Date` (so `year(cutoff)` and
`date_of(at) == cutoff` work, and comparing it with a Text field is a type
error), and PostgreSQL SQL writes it as `DATE '2024-01-31'` /
`TIMESTAMP '2024-01-31 08:30:00.250000'`; `Bool`, `Int`, `Float` and `Text`
reads emit exactly the literal written. A constant changes only SQL bytes,
never a semantic fact. `explain` shows each read after substitution: a
projection that only reads a constant is a `literal` of the declared type. So
that a name has one meaning, a constant named like any other name declared in
the file (definition, field, parameter, let, output, window, binding, import)
or like a built-in function (`lower`, `count`, `Float`, ...) is PIE-S2391; a
constant alone is never a GROUP BY or ORDER BY key (a key computed from one is
checked as the same key written with the literal), and a SELECT item that
only reads a constant names its output (`as_of = cutoff`).

`--set NAME=VALUE` on `check`, `emit-sql` and `explain` (repeatable) changes
one constant for that run. The VALUE is read as a literal of the declared
type, never as source text: `True`/`true`/`False`/`false`; digits with
optional `_` and a leading `-` (`Float` needs a decimal point); any UTF-8
text for `Text` (no quotes); `YYYY-MM-DD` and `YYYY-MM-DD HH:MM:SS[.ffffff]`.
The SQL is byte-identical to writing the value in the file. `--set` never
decides whether the file is valid: an initializer that is not one literal of
its type keeps its own error (PIE-S2391, or PIE-S2387 for `now()`). Usage errors
(exit 2): a name set twice, a name no constant declares, a value that is not
a literal of the type, and `--set` with `--project`; `migrate` and `fmt` take
no `--set`.

A top-level line is a constant when it starts with `name:` and holds an `=`
outside parentheses; any other top-level line parses as it did before
constants existed.

MySQL single-file emission does not emit constants yet: each table or query
that reads one, directly, through a `def` or a relationship or by reading
such a table or query, is PIE-B1000 (`MySQL SQL emission
is not implemented for RelationIR: NAME. MySQL has no top-level constants yet;
emit with --dialect postgres`), until a two-database differential reviews
them; the other relations of the file still emit.

Constants exist only in single files. In an EXPLICIT_MODULES project a
constant is PIE-S2392 pointing to a query header parameter; in a LEGACY_FLAT
project PIE-S2392 points to `schema_version = 2`. A single-file query header
parameter stays PIE-S2346, whose message now points to constants.

### Feature support by target

[Capabilities by mode and target](capabilities.md) shows, for each feature
family, what single files and projects accept and emit on each target. The
features added after 0.1.8 emit as follows. "Project" is
`emit-sql --project` of an explicit-module project; the sections named in the
first column give every rule.

| Feature | PostgreSQL single file | MySQL single file | PostgreSQL project | MySQL project |
| --- | --- | --- | --- | --- |
| `concat(a, b)` ([Expressions](#expressions)) | `(a \|\| b)` | `CONCAT(a, b)` | emitted; refused for only `None` (PIE-B1003) or a binding-width `Text` (PIE-B1004) | refused (PIE-B1003) |
| `same_value(a, b)` ([Expressions](#expressions)) | `(a IS NOT DISTINCT FROM b)` | `(a <=> b)` | select items, WHERE and `let`, select items after a JOIN; `Float` where `==` is, not `Bool`, not in a JOIN `on` or a WHERE after a JOIN | as PostgreSQL, a `Float` only beside an operand that reads no row (two row `Float` operands PIE-B1003), and not a GROUP BY key or DISTINCT column |
| `stddev(x)` ([Aggregates](#aggregates-and-grouping)) | `Int` and `Float` | `Float` (`STDDEV_SAMP`); `Int` refused (PIE-B1000) | `Int` and `Float` | refused: `Int` PIE-B1003, `Float` PIE-B1004 |
| `variance(x)`, `pvariance(x)`, `pstdev(x)` ([Aggregates](#aggregates-and-grouping)) | `Int` and `Float` (`VAR_SAMP`, `VAR_POP`, `SQRT` of `VAR_POP`) | `Float` (`VAR_SAMP`, `VAR_POP`, `STDDEV_POP`); `Int` refused (PIE-B1000) | `Int` and `Float` | refused: `Int` PIE-B1003, `Float` PIE-B1004 |
| `median(x)`, `quantile(x, q)` ([Aggregates](#aggregates-and-grouping)) | `Int` and `Float` (`PERCENTILE_CONT ... WITHIN GROUP`) | refused (PIE-B1000) | `Int`; `Float` refused (PIE-B1004) | refused (PIE-B1003) |
| `first(x, order by k, id)`, `last(...)` ([Aggregates](#aggregates-and-grouping)) | `(ARRAY_AGG(x ORDER BY k ASC, id ASC))[1]`; `last` flips every direction | refused (PIE-B1000) | as a file; the value keeps its carrier; a key orders as a relation ORDER BY key (R19), else PIE-B1003 `first_last_order_key_outside_reviewed_order_domain` | refused (PIE-B1003 `first_last_not_admitted_on_target`) |
| `sum(1 for o in group if t)`, `sum(o.f for o in group if t)` ([Aggregates](#aggregates-and-grouping)) | `COUNT(CASE WHEN t THEN 1 END)`; `COALESCE(CAST(SUM(CASE WHEN t THEN CAST(f AS pg_catalog.int8) END) AS pg_catalog.int8), 0)` | count `COUNT(CASE WHEN t THEN 1 END)`; sum refused (PIE-B1000) | as PostgreSQL single file, `schema_version = 2` (PIE-S2334 in a `schema_version = 1` project); no JOIN inputs | refused: count PIE-B1003, sum PIE-B1004 |
| `any(t for o in group)`, `all(t for o in group)` ([Aggregates](#aggregates-and-grouping)) | `(COUNT(CASE WHEN t THEN 1 END) > 0)`; `(COUNT(CASE WHEN t THEN NULL ELSE 1 END) = 0)` | as PostgreSQL, an integer 0/1 | as PostgreSQL single file, `schema_version = 2` (PIE-S2334 in a `schema_version = 1` project); no JOIN inputs | refused (PIE-B1003 `group_test_not_admitted_on_target`) |
| `max(a, b)`, `min(a, b)` ([Expressions](#expressions)) | `CASE WHEN` of `<`/`>` and `IS NOT NULL`; `Int`, `Decimal`, `Float`, `Text`, `Date`, `Timestamp`, `UUID`, `Bool` | as PostgreSQL; a `Bool` result arrives as an integer 0, 1 or NULL, as every computed `Bool` does on MySQL | `Int`, `Decimal`, `Float`, `Text`, `Date`, `Timestamp`, `UUID` as their comparison and conditional are; `Bool` refused (PIE-B1003) | as PostgreSQL project, except `Date`, refused (PIE-B1003) |
| `lpad(s, width, fill)` ([Expressions](#expressions)) | `CASE WHEN length(s) >= width THEN s ELSE lpad(...) END`; a literal width outside the signed 32-bit range refused (PIE-S2385 at check) | `CASE WHEN CHAR_LENGTH(s) >= width THEN s ELSE LPAD(...) END` | emitted for a width proven in the signed 32-bit range; refused otherwise (PIE-B1002, PIE-B1004) | refused (PIE-B1003) |
| `add_months(d, n)` ([Expressions](#expressions)) | `CAST((d + make_interval(months => CAST(n AS integer))) AS date)` | `DATE_ADD(d, INTERVAL n MONTH)` | emitted; a `None` argument refused (PIE-B1003) | refused (PIE-B1003) |
| `now()` ([Expressions](#expressions)) | `(statement_timestamp() AT TIME ZONE 'UTC')`, in SELECT items and WHERE | refused (PIE-B1000) | emitted, compiled and bound as a template | refused (PIE-B1003 `scalar_call_signature_not_admitted`) |
| Always-null numbers, D-12 ([Expressions](#expressions)) | typed NULL casts | typed NULL casts | `Int` arithmetic with `None`; `Float` and `Decimal` refused | as PostgreSQL |
| `Float` equality ([Float values](#float-values)) | comparisons and GROUP BY; DISTINCT and set forms are project-only | as PostgreSQL; GROUP BY beside a wide `Text` key may split `-0.0` and `0.0` | comparisons, GROUP BY, DISTINCT, ORDER BY, every set form, window `partition by` and `order by`, `string_agg` order keys and FULL JOIN equalities, also over a window `percent_rank` or `cume_dist` result | comparisons with a literal or header parameter, ordering inequalities, `in`, `nullif`, relation ORDER BY and UNION ALL; the other forms refused (PIE-B1003) |
| JOIN aggregates without fan-out ([Aggregates](#aggregates-and-grouping)) | accepted | accepted | accepted | accepted; `sum(Int)` stays PIE-B1004 |
| Top-level constants and `--set` ([Top-level constants](#top-level-constants)) | literals; `DATE '...'`, `TIMESTAMP '...'` | each relation that reads one refused (PIE-B1000) | refused (PIE-S2392) | refused (PIE-S2392) |
| Project aggregate arguments ([Aggregates](#aggregates-and-grouping)): `count`/`count_distinct` of `Text`, `Bool`, `Float`, `Decimal`; `min`/`max` of `Float`, `Decimal`; `sum`/`avg` of `Float`; a row expression argument (`sum(qty * 2)`) | emitted (unchanged) | emitted (unchanged) | emitted, also an argument holding a scalar call over JOIN rows (`count(lower(r.label))`); `Decimal` `sum`/`avg` refused (PIE-B1004) | as PostgreSQL, except `count_distinct` of a `Float` (PIE-B1003), `sum`/`avg` of a `Float` and `sum` of an `Int` such as `sum(qty * 2)` (PIE-B1004), and over JOIN rows an argument holding a scalar call (PIE-B1003); an `Int` expression not proved to fit BIGINT is PIE-B1002 first |
| `count_distinct(a, b, ...)` ([Aggregates](#aggregates-and-grouping)) | `COUNT(DISTINCT CASE WHEN a IS NOT NULL AND b IS NOT NULL THEN ROW(a, b) END)` | `COUNT(DISTINCT a, b)` | as PostgreSQL single file, `schema_version = 2` (PIE-S2334 in a `schema_version = 1` project), also over JOIN rows | refused (PIE-B1003 `count_distinct_tuple_not_admitted_on_target`) |
| `len(c.xs)`, `sum(o.f for o in c.xs ...)`, `any(t for o in c.xs)` ([Nested relations](#nested-relations-collect-and-unnest)) | `sum` and `any` refused at check (PIE-S2334; a single file collects no list); `len(c.xs)` has no list to read (PIE-S2102 for an unknown field, or only the Collect's own refusals) | as PostgreSQL | the count column; `sum` and `any` a scalar subquery over `pg_catalog.unnest` of the list's arrays | refused (PIE-B1003 `collect_not_admitted_on_target`) |
| `min(x)`, `max(x)` of a `Timestamp` or `Date` ([Aggregates](#aggregates-and-grouping)) | emitted (unchanged) | emitted (unchanged) | emitted (unchanged) | emitted as on PostgreSQL: `MIN(x)` and `MAX(x)` keep `DATETIME(6)`, microseconds kept, and `DATE`, NULL for an empty input; over a window refused (PIE-B1003), as every MySQL aggregate window |
| `asof left join`, `asof inner join` ([Backward asof JOIN](#backward-asof-join)) | emitted | emitted, except in a relation with a FULL JOIN (PIE-B1000) | emitted in a table or query without a relation `let NAME:` block whose FROM is not a table function, elsewhere refused (PIE-S2336); a `let NAME:` block as the joined input is PIE-S2386, where a single file refuses the block itself (PIE-S2345); an aggregate after it only where its `on` keys match a unique key (PIE-S2333) | as PostgreSQL |

## Types and shapes

The builtin scalar names are:

```text
Any Bool Bytes Date Decimal Float Int Json Text Timestamp UUID
```

Enum declarations are nominal definitions rather than builtin scalar names.
A declared type has two nullability states: a bare type such as `Int` is
never None, and `Int | None` may be None. This holds alike for shape fields,
`constraint`, `derive` and `def` parameters and results, query header
parameters and typed VALUES columns. A type alias names a type that is never
None, so `type Email = Text | None` is PIE-P1000: write `type Email = Text`
and declare `email: Email | None` where the value may be None. The retired
spellings `T not null` and `T nullable` are PIE-P1000 too, with a suggestion
to write `T` or `T | None`. A field of a source without a shape keeps unknown
nullability.

```pietto
type Age = Int:
    ensure 0 <= self <= 130

enum Status:
    active
    suspended

enum Priority: low, high

shape User:
    id: UUID
    age: Age | None
    status: Status
    email: Text | None
```

Shape items may include fields and named calls such as `valid = check(id > 0)`,
`key = unique(id)` and `lookup = index(id) when id > 0`. An admitted unique
declaration is a trusted Pietto model contract whose authored NULL policy
defaults to `NULLS_DISTINCT`. On an exact source row output, all-`NON_NULL` determinants provide strict row uniqueness;
otherwise the evidence remains lax and usable under standard equality.
This does not claim runtime validation, catalog enforcement, DDL, or physical
database UNIQUE behavior. A `unique(...)` key over a `Float` field means that
no two rows are `==` equal, so a source holding both `-0.0` and `0.0` in that
key violates it.

Constraints and derivations return one explicit expression:

```pietto
constraint Positive(value: Int) -> Bool:
    return value > 0

derive Increment(value: Int) -> Int:
    return value + 1
```

As with `def`, the `return` line may instead follow the header's ':', as in
`constraint Positive(value: Int) -> Bool: return value > 0`.

This source spelling does not turn constraints or derivations into general
runtime-callable functions; their existing semantic roles remain unchanged.

### Float values

A `Float` is a finite IEEE-754 binary64 value. NaN and ±Infinity are not
Pietto values: no spelling makes one, and a project source contract's
`finite_float` domain excludes them. `-0.0` and `0.0` are two encodings of one
value.

- **Equality.** `a == b` is Python's float equality: `-0.0 == 0.0`, and every
  other pair is equal exactly when its bits are. `!=` is its negation. The
  same law serves comparisons, `in`, `nullif`, `any`/`exists` predicates,
  JOIN equalities, GROUP BY keys, DISTINCT, the set operations and declared
  `unique(...)` keys. NULL rules do not change.
- **Order.** Floats order by real value; `-0.0` and `0.0` tie, and tied rows
  have no promised relative order.
- **Merged rows.** GROUP BY, DISTINCT, UNION DISTINCT and INTERSECT/EXCEPT
  are exact about which classes of `==`-equal rows appear and how often. Each
  merged row carries the value of some member of its class; which member is
  unspecified. A group key, DISTINCT row or set row whose class holds both
  `-0.0` and `0.0` may therefore show a zero sign that some of its members do
  not have. A class whose members share one sign shows that sign.
- **Aggregates.** `count_distinct` counts `==`-classes, so `-0.0` and `0.0`
  count once; a `min` or `max` whose extreme class holds both zeros shows the
  value of some member, as a merged row does.
- **Arithmetic.** `+`, `-` and `*` give Python's binary64 result, the sign of
  a zero included (`0.0 * -2.0` and `-(0.0)` are `-0.0`, `x - x` is `0.0`). A
  result outside binary64 is not a value: project SQL on PostgreSQL fails the
  statement with SQLSTATE 22003 instead, and also fails it where a product of
  two non-zero values rounds to zero, which Python gives as `0.0`. It never
  returns an infinity or a wrong value.
- **No later step can tell.** Every Float operation Pietto admits gives
  `==`-equal results for `==`-equal inputs. So no later filter, comparison,
  group key or set operation can tell which zero a merge kept; only the
  shown value's sign can differ.
- **Transport.** Projection, `let` carry, WHERE and JOIN filtering, ORDER BY,
  LIMIT and UNION ALL keep the stored bits, so the sign of a zero survives.
- **Literals.** In project SQL a Float literal is a typed binary64 carrier and
  `-0.0` is a real negative zero. Single-file SQL writes a Float literal as SQL
  number text; the `-0.0` it writes arrives as `+0` on both PostgreSQL and
  MySQL, so a negative zero in single-file output never comes from a `-0.0`
  literal (it can come from stored data or from negating or multiplying a
  Float field).
- **Identity.** A literal's or a bound parameter's identity is its bits:
  `-0.0` and `0.0` are different literals and different bindings, which
  compare equal.

Single-file GROUP BY over a Float keeps the target's own GROUP BY, which puts
`-0.0` and `0.0` in one group and shows one member's sign as the key. On
MySQL a single-file GROUP BY that groups a Float together with a wide Text key
can put `-0.0` and `0.0` in different groups (observed on MySQL 8.4.12 beside
a `VARCHAR(1000)` or wider key; a `VARCHAR(64)` key merged them). Project
emission refuses those MySQL forms instead (see
[project SQL emission](project-package.md#project-sql-emission)).

## Sources and relations

A source optionally names a shape and retains a connector expression without
executing it:

```pietto
shape User:
    id: Int
    email: Text | None

source users: User = postgres.table("public.users")
```

In single-file mode the connector string names one table: `"users"`, or with
exactly one dot `"<schema>.<table>"`, where the schema is a PostgreSQL schema
for `postgres.table` and a MySQL database for `mysql.table`. `emit-sql` quotes
each part separately, so the source above emits `FROM "public"."users"`.
PostgreSQL emission refuses any identifier, including an output name, longer
than 63 UTF-8 bytes with PIE-B1000, because PostgreSQL would truncate it. A
string with more than one dot or an empty part fails `check` with `PIE-S2306`
at the string, except that an empty `mysql.table("")` keeps its existing
`PIE-S2306` on the whole connector call. An argument that is not a string
literal also fails single-file `check`: a bare unquoted name such as `users` with
`PIE-S2102`, and an unquoted dotted name such as `public.users` or another
expression with `PIE-S2306` at the argument, unless the connector call already
has an error of its own: an unknown connector, or `postgres.table` or
`mysql.table` without exactly one argument, fails single-file `check` with
`PIE-S2306` on the whole call whatever its arguments are, unless an argument
reports an error of its own such as that `PIE-S2102`; where defs are
available, a call of a `def` there is PIE-S2397 instead (see
[Inline functions](#inline-functions-def)). Project mode does not split or
interpret the name, although its check still rejects an empty `mysql.table`
string; project SQL emission takes the physical relation from its emission
contract.

Tables and queries share this ordered clause shape:

```text
from
let input = relation / JOIN / ordered existence filter (zero or more)
let value = expression / let name = window(...) (optional, before the tail)
where (optional)
group by (optional)
select
having (optional)
qualify (optional)
order by (optional)
limit (optional)
```

```pietto
shape User:
    id: Int
    email: Text | None

source users: User = postgres.table("users")

table active_users:
    from users
    let normalized = lower(trim(email))
    where email is not None
    select:
        id
        normalized_email = normalized
    order by:
        id
    limit 100
```

After `select` one name rule applies. `select` may list a `let` name directly,
which outputs the binding's value under that name: `let total = price_cents *
quantity` then `select id, total`. A single file does so in a relation without
GROUP BY; any other SELECT output that takes a `let` name is PIE-S2329 at the
binding. Outside a grouped query an `order by` key reads input fields and `let`
bindings, and a key written as one name alone may also name a SELECT output,
which it then reads: `select id, total = price_cents * quantity` then `order by
total desc`. Only a whole key names an output, as in a grouped query, so
`order by total + 1` reads no output. A key that names both an input field and
a SELECT output of another value, a selected window result included, such as
`quantity` after `select quantity = quantity * 2`, is ambiguous (PIE-S2102):
write the input field with its input name, `order_lines.quantity`, or give the
output another name. An output of that same field, such as `quantity`,
`quantity = order_lines.quantity` or a `let` name bound to that field, reads
the same value and is not ambiguous. Emission restates the SELECT output that
a key names, as it inlines a `let` value, so `order by total` emits `ORDER BY
"price_cents" * "quantity"`; a selected window result is ordered by its output
name, or by its position in the SELECT list beside an unaliased item or, on
MySQL, beside another output whose name differs from it only in case. Over an
input row of unknown type, such as a source without a shape, no key is
ambiguous: a key named alone that is a SELECT output of that exact name reads
that output and is emitted as a selected window result is; any other key, a `let` name
bound to a field included, reads the input field, which emission qualifies
where a SELECT item would capture it, as described below. In a query without GROUP BY, a key that is a bare constant once
`let` names and signs are inlined, such as `label` with `let label = "x"` or
`-1`, is PIE-S2380, even from a source without a shape, because SQL reads an
integer as a column position and PostgreSQL rejects other bare constants; so
is a key that names a SELECT output whose value is such a constant, such as
`flag` with `select flag = 1`, over an input row of known type. A computed
constant such as `1 + 1` sorts nothing and is accepted. In a query with
aggregates and no GROUP BY, a key that reads an input field outside an
aggregate is PIE-S2380 too, also from a source without a shape, where any name
that no `let` binds is an input field, while a key that names an aggregate
output is accepted (`order by n` with `select n = count()`). In a single
file, a JOIN relation whose projections are all aggregates, without GROUP BY,
instead refuses the entire ORDER BY clause with PIE-S2334; an EXPLICIT_MODULES
project refuses that relation with PIE-S2333, naming the repeating JOINs when
an aggregate may read rows that a JOIN repeats. A JOIN relation that mixes an
aggregate with another projection, a window included, and whose aggregates
have no error of their own reports PIE-S2312,
the errors of its other SELECT items and QUALIFY and the errors of each key as
above, in a single file and in a project (see PIE-S2312 and PIE-S2380 in the
[diagnostics](spec/diagnostics.md)), except that a project relation whose
`let:` clause or WHERE is refused, such as by a `let` name that is also a
SELECT output name (PIE-S2329), by an unknown or ambiguous field in a `let` value or WHERE or by a type error in WHERE, still reports only that refusal and the
PIE-S2305 of a repeated output name, a known limitation that the PIE-S2312
row lists case by case.
A grouped key stays PIE-S2321. When a SELECT item would capture a key that is
a bare input field once `let` names and SELECT output names are inlined (an
output of the same name, which MySQL compares case-insensitively, or any
unaliased item, which PostgreSQL and MySQL each name by rules of their own),
the emitted SQL qualifies the key with the name FROM already gives the input,
as in `FROM "sales"."orders" ... ORDER BY
"orders"."amount"`; the FROM clause is unchanged. MySQL documents that it
looks every ORDER BY name up among the SELECT output names first, so on MySQL
such an input field inside a key's expression is qualified the same way:
`order by later` with `let later = amount + 1` and `select amount = id` emits
``ORDER BY `orders`.`amount` + 1``, while PostgreSQL, which reads an input
field inside an expression, emits `ORDER BY "amount" + 1`. Single-file
lowering inlines a `let` binding wherever a relation expression reads it, so an
expression that reads bindings and would exceed 768 nested levels or 100,000
expression nodes once they are inlined fails `check` with PIE-S2328. A
conditional or `in` list counts two levels, a function call three, and each let
substitution, a plain alias `b = a` included, one more; a `def` call counts as
its expansion, and a binding that nothing reads is not counted. An expression
written inline is bounded only by PIE-S2006 (450 nested levels, see
Expressions), and moving it into one binding read as `y = v` keeps it accepted.
A `let` name has the type of its value written where it is read, as
emission inlines it: a name whose value is `None`, directly or through other
names, takes its type from where it is read, as `None` does, and over a
source without a shape a name has its binding's type. A binding is typed the
same way with the earlier names it reads, so its errors are reported in the
binding, at their own positions, whether or not anything reads it: with
`k = None` and `j = coalesce(k, 1)`, `j` is an `Int` that is never None, as
`coalesce(None, 1)` is, `d = len(j)` is PIE-S2104 in the binding and
`v = lower(j)` is PIE-S2104 at `lower`; over a source without a shape, with
`w = n is None`, `-w` is PIE-S2105. A cast of a name whose binding has an
error of its own reports only that error, as the cast of the value written
by hand does. An EXPLICIT_MODULES project types `let` names the same way,
with or without JOIN inputs, but a relation there with a binding of unknown
type, such as `k = None`, still fails closed: `check --project` may report
PIE-S2333 at the table or query even when nothing in it is ill-typed, as it
does with JOIN inputs, a GROUP BY or `select distinct`, and
`emit-sql --project` blocks one that passes `check --project` with
PIE-B1003.
A project may also select a `let` name directly in a relation with GROUP BY
(see Aggregates and grouping). LEGACY_FLAT projects check the ORDER BY rule
above as a single file does. An EXPLICIT_MODULES project reports the
ambiguous ORDER BY key above at
`check --project` (PIE-S2102), but in a relation without GROUP BY its SQL
does not yet order by a SELECT output other than a selected window result:
without JOIN inputs
`check --project` accepts such a key and `emit-sql --project` blocks the table
or query with PIE-B1003 `order`, and with JOIN inputs, or without them in a
relation that a project completes itself, such as one with `any(...)` or
QUALIFY, `check --project` reports the key with PIE-S2102 (restate the
expression, or bind it with `let`, select that name and order by it). Without
JOIN inputs or GROUP BY, `check --project` reports an ORDER BY key that reads
an unknown field, also through a field of a shape (`home.nosuch`), or calls an
unknown function (PIE-S2103), and one written as a bare constant (PIE-S2380),
as a single file does; a SELECT output is a key only as the whole key, so
`-total` reads an input field `total`. It does not type the key yet; a
constant that a `let` name binds is ordered by as a value.
Selected project SQL admits the
documented project scalar subset when its physical carrier requirements are
established.

### Named inputs and reusable relationship predicates

`from` introduces the base row input. `let buyer = customers` names another
input without joining it; `left join buyer on ...` introduces that row occurrence.
A name that could mean both an input relation and a scalar value is ambiguous,
not resolved by choosing the first declaration. Pure relation naming may precede
or follow FROM; an expression reading a row input must follow that input's
introduction. Scalar LETs remain after JOINs and before the ordinary WHERE tail,
and named windows (`let name = window(...)`, see [Windows](#windows)) take the
same place. Bare `name = expression` cannot rebind a query name. SELECT aliases
name columns, not row inputs, and therefore have no `let`.

A relationship is optional: write an ordinary ON predicate for a one-off match,
or give a reusable row predicate shape-typed parameters. This complete example
keeps the active-customer test inside ON, including both LEFT JOINs:

```pietto
shape Order:
    id: Int
    customer_id: Int
    order_key = unique(id)

shape Customer:
    id: Int
    status: Text | None
    region_id: Int | None
    customer_key = unique(id)

shape Region:
    id: Int
    name: Text
    region_key = unique(id)

source orders: Order = postgres.table("shop.orders")

source customers: Customer = postgres.table("shop.customers")

source regions: Region = postgres.table("shop.regions")

relationship ActiveOrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id and customer.status == "active"

relationship CustomerRegion(customer: Customer, region: Region):
    customer.region_id == region.id

query order_customers:
    from orders
    let buyer = customers
    left join buyer on ActiveOrderCustomer(orders, buyer)
    let region = regions
    left join region on CustomerRegion(buyer, region)
    select:
        order_id = orders.id
        customer_id = buyer.id
        region_name = region.name
```

`buyer` and `region` are row aliases; `customer_id` and `region_name` are output
columns. The second ON may read `buyer` because the first JOIN already introduced
it. A missing or inactive customer leaves the buyer fields NULL while preserving
the order. The later LEFT JOIN likewise retains unmatched accumulated rows.
Moving the active test to WHERE would change those rows, so predicate extraction
does not move it there.

A source row binds a parameter by declared shape identity, including the
shape's declaring module; matching field names do not establish the same
shape, so a source of another shape with the same fields is PIE-S2604
(`Relationship R parameter p requires declared shape S; the actual row has
a different shape identity`). A table or query row, in a project also one
imported from another module, binds by its output columns: each field of
the parameter's shape needs a column of the same name and type, compared
after alias expansion on both sides, an enum by its declaration. A column
that may be None does not bind a field of type `T`: neither a column of
type `T | None` nor one of unknown nullability, such as a computed `x + 1`,
as for a def parameter (write `coalesce(x + 1, 0)`, or declare the field
`T | None`). A column of unknown type, such as `None` written alone, is
compared by name only, as a def argument is. Decimal precision and scale are
not compared; extra columns are ignored. The first field, in the shape's
order, that does not match is PIE-S2604 at the argument:
`Unavailable row argument for relationship R parameter p: no column f`,
`...: column f is Text, field f is Int`,
`...: column f is Int | None, field f is Int`,
`...: column f is Int of unknown nullability, field f is Int` or, for enums
of two modules with one name,
`...: column f is Tier from "other.pietto", field f is Tier from "types.pietto"`.
A query that selects a source's columns therefore binds where the source
itself does not. In a project, the rows of a query that has a JOIN of its
own bind a parameter only as the FROM row of a query without JOIN: in a
query with a JOIN, or through `any(...)`, their columns are not known where
the call is bound, so the call is PIE-S2604 with no reason, also when a
column does not match; write the test out, as in `on q.id == x.id`. Only a
grouped query's GROUP BY key proves a key of its rows: the parameter
shape's `unique` says nothing about a table or query.
Each call binds its actual row occurrences independently, even when several
rows share a source, table, query or shape. Current JOIN null-extension
remains authoritative over a shape's original non-null fields, for source,
table and query rows alike. Calls are available in ON, WHERE and SELECT and may
be combined with the admitted Boolean operators. The body is one expression,
on the header line after ':' or alone in its block, as a `def` body is. It may
contain literal filters, comparisons and AND/OR/NOT; it reads only its supplied
rows. Aggregates,
windows, ANY and other relation reads are not available inside a relationship
body. A scalar `def` remains the separate mechanism for reusable scalar inputs.
Callable collisions retain their existing namespaces and report ambiguity.
In a project, a relationship one module exports is called in another that
imports it (see [Modules and relationships](#modules-and-relationships)).

There is no public `link` or `relation` binding layer, no inferred FROM, and no
implicit JOIN merely because a relationship is declared. A relationship is not
a foreign key, synchronization rule, database write or promise that a match
exists. Required positive equalities may support a proven upper bound; literal
filters, OR and NOT do not manufacture unconditional equality or coverage.

INNER keeps TRUE matches. LEFT, RIGHT and FULL preserve their respective
unmatched occurrences and NULL-extend the opposite input; RIGHT extends the
whole accumulated left input. CROSS has no ON predicate. There is no `semi
join` or `anti join` (PIE-P1000, with a rewrite suggestion): write
`where any(predicate for row in relation)` or `where not any(...)`, before the
JOIN that should see only the kept rows (see
[Boolean existence with `any`](#boolean-existence-with-any)). FALSE and UNKNOWN
are non-matches.
Inputs, duplicate names, future references and unavailable targets fail closed.
No JOIN kind by itself proves uniqueness, coverage or aggregate fan-out safety.

Selected project SQL retains its existing physical-type limits. An INNER JOIN
whose ON contains a nullable Bool field as a mandatory conjunct can pass
`check --project` yet be BLOCKED by `emit-sql --project` or `compile_query`
with PIE-B1002 `join_output_nullability_drift`. Comparing that field with `True`
does not establish a supported Bool comparison: it can instead report PIE-B1003
`comparison_type_pair_not_admitted`. These target restrictions are separate from
row-predicate and ANY syntax. Moving a condition to WHERE can change outer-JOIN
semantics and is not an automatic rewrite.

### Boolean existence with `any`

`any(predicate for row in relation)` is a `Bool` that is never None. It is True
exactly when at least one row makes the predicate TRUE; FALSE and SQL UNKNOWN
are non-matches. It is False over an empty input. `not any(...)` negates that
result and differs from `any(not predicate for ...)` when no row qualifies or
predicate values are NULL. Literal `None` in a predicate is contextual Bool NULL
and never a match; a known non-Bool body is refused.

`any(...)` takes no `if`: write the test in its body, `any(p and q for o in
r)` (PIE-S2334 ``any takes its test in the body``). `for o in orders` is
every row of `orders` here and in every other generator; in a grouped `sum`
it is refused, never read as the group.

The binder is local to its parentheses. It neither joins an output row nor
reserves that name in the rest of the query. Repeated and nested generators keep
separate row occurrences. The predicate may capture only bindings visible at
that point: ON sees its pre-match prefix and current target, while WHERE/SELECT
see the completed joined row and its actual NULL extension. Scalar LET captures
see only earlier admitted LETs; future, self, an earlier filter's binder and
out-of-scope bindings remain unavailable. Both rows need known fields: an
`any` over a relation of unknown row type, such as a source without a shape,
is PIE-S2334 (`ANY over orders requires known input fields.`), and in a single
file a read of a field of such a FROM row, such as `items.id`, is PIE-S2102
(`Unknown or unavailable field in ANY predicate: items.id`), as is a read of
an output of no type, such as `x = None` of a table the generator reads.

```pietto
shape Order:
    id: Int
    customer_id: Int

shape Customer:
    id: Int
    status: Text | None

source orders: Order = postgres.table("shop.orders")

source customers: Customer = postgres.table("shop.customers")

relationship ActiveOrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id and customer.status == "active"

query customer_flags:
    from orders
    let has_active = any(ActiveOrderCustomer(orders, buyer) for buyer in customers)
    where has_active or orders.id == 1
    select:
        order_id = orders.id
        active_customer = has_active
        no_customer = not any(orders.customer_id == buyer.id for buyer in customers)
```

ANY is also usable directly in ON, SELECT and ordinary tail WHERE expressions,
including OR and admitted scalar wrappers. Its predicate keeps the existing
scalar and type restrictions; this does not add aggregate or window support to
that predicate, or admit Bool aggregate arguments that were previously refused.
The existing whole-relation `exists name` syntax and its project limits remain
separate.

Before a later JOIN, WHERE is restricted to ordered conjunctions of positive
or negative ANY tests:

```pietto
shape Order:
    id: Int
    customer_id: Int

shape Customer:
    id: Int
    status: Text | None

shape Region:
    id: Int

source orders: Order = postgres.table("shop.orders")

source customers: Customer = postgres.table("shop.customers")

source regions: Region = postgres.table("shop.regions")

relationship ActiveOrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id and customer.status == "active"

query qualified_orders:
    from orders
    where any(ActiveOrderCustomer(orders, buyer) for buyer in customers)
    let region = regions
    left join region on orders.id == region.id
    select orders.id
```

An indented WHERE block may list several such tests. Each filter runs at its
exact authored JOIN prefix; an ordinary row filter or OR across tests belongs
at the tail instead. Later RIGHT/FULL behavior must not move the filter across
its boundary. Such a filter keeps each accumulated row once when some row
makes its predicate TRUE (`any`) or when none does (`not any`); repeated
matches never multiply rows, and its binder is not visible to later clauses.
A tail WHERE ANY remains a scalar existence value with the same rows. These
filters replace `semi join` and `anti join`. No Python generator object,
runtime function value or general higher-order call is created.

Within the existing project type domain, a JOIN may read a source with fields
typed by an enum or a shape, or by an alias of either, with or without `| None`, and
`check --project` completes it. A project types a field of an enum, or of an
alias of one, as that enum, with or without a JOIN and whatever the JOIN makes
of its nullability: it may be selected (also from the groups), compared, tested
with `is None` or inclusive comparison chains, grouped, ordered, partitioned or ordered in a
window, the value of `lag`, `lead`, `first_value`, `last_value` or `nth_value`,
or matched in a JOIN `on`, and a read is checked as a single file checks it, so
`lower(c.status)` and `coalesce(c.status, "x")` report PIE-S2104,
`c.status in ("active", "gone")` (`gone` is no label) and
`c.status not like "a%"` report PIE-S2105,
`where c.status` reports PIE-S2202 and a `def` parameter it does not fit
reports PIE-S2395. With JOIN inputs a `let` name bound to it and another
output of enum type may be selected, and `count(c.status)` reports PIE-S2314.
Without JOIN inputs a project does not complete every such read yet: an
aggregate of an enum field (PIE-S2314 in a single file), a selected `let` name
bound to an enum value and a computed output of enum type other than a window
value, such as `coalesce(new_status, status)` of two enum fields or a
conditional between them, report PIE-S2333 at the table or query, and a project
check does not type the ungrouped `order by` of a relation without JOIN inputs
that is not `select distinct`, so `order by lower(status)` passes
`check --project` there. A list output whose `None` option the other operands
leave untyped, such as `amount in (2.5, None)` with a `Decimal` field, reports
PIE-S2333 without JOIN inputs (`status in ("active", None)` is typed by its
label), and a window value function over an enum field of a row that also has
a field of another enum of the same name, declared in another module, reports
PIE-S2333 with or without JOIN inputs. A single file keeps an alias of an enum as the
alias, so its messages name the alias and its window value functions refuse it
(PIE-S2104).

A table, query or relation `let` that outputs a field typed by a shape, or by
an alias of one, and completes on its own can be the relation of an `any(...)`
or `not any(...)` test, in a WHERE before a later JOIN or at the tail. JOINs
may read it when it has a GROUP BY
but no ORDER BY, LIMIT or window function, when it is a set operation, or when
it is a table or query that only selects, renames, filters, orders or limits
the fields of such a source, directly or through other tables or queries that
do only that. In other cases, for example a relation `let` with no GROUP BY or
set operation, or a table or query with a `let` clause or a computed SELECT
output such as `v = id + 1`, those JOINs may report PIE-S2333 at the table or
query, even when the field is never read. After the JOIN, a `where` test, a
`let` value, a SELECT output or an ORDER BY key reads such a field as that
shape where an operator or a function refuses a shape, as a single file does:
`c.home + 1`, `lower(c.home)`, `c.home like "a%"`, `1 <= c.home <= 2`,
`c.home in (1, 2)` or `c.home == 1` reports PIE-S2105 or PIE-S2104 at the
expression. Otherwise
scalar typing reads such a
field as of unknown type, so a `where` test, a SELECT output, a `let` value or
an ORDER BY key may read it only inside an expression whose own type stays
known: a comparison (`==`, `!=`, `<`, `<=`, `>`, `>=`) with another shape
value, `is None`, `is not None`, and `and`, `or` and `not` over such tests,
for example `c.home is None or c.id > 0`. Any other read there is not
supported yet and reports PIE-S2333 at the table or query: the field itself
(selected, also through a `let` name, or used as an ORDER BY key) and an `in`
or `not in` test of it among other shape values, in `where` too. Without JOIN
inputs a SELECT item that tests the field directly, as `b = home is None` and
`b = home == work` do, also reports PIE-S2333, while `b = h is None` for
`let h = home` is typed; in a `select distinct` relation or one with a
Collect read, any SELECT item that reads the field and a `let` bound to it,
even if unread, report PIE-S2333 too. GROUP BY may name
the field, but selecting it from the groups reports PIE-S2333 as well. An
aggregate of it reports PIE-S2315 at the call, and a window partitioned or
ordered by it reports PIE-S2103 (`window partition field type must be
concrete` or `window order field type must be concrete`); a JOIN `on` that
reads such a field reports PIE-S2334 and PIE-S2335. Shape-valued JOIN operands
remain outside the supported condition domain. Project SQL emission has no
representation for enum or shape fields: with or without a JOIN,
`emit-sql --project` reports a table or query that passes `check --project` and
reads a source declaring one BLOCKED with PIE-B1003 (for example
`representation_not_in_initial_domain` at the field), or with PIE-B1003 `order`
for an ORDER BY key that reads a shape-typed field inside an expression, such
as `home is None`.

Without JOIN inputs, the value of a selected `lag`, `lead`, `first_value`,
`last_value` or `nth_value` of a project table or query, and a `lag`/`lead`
default, may be a field typed by a shape, or by an alias of one, as in a single
file a field of the shape itself may be, and the call gives a column of that
shape. A later table or query may select such a column or read it as a window
value again, and reads it elsewhere as it reads a field of the shape, so a
computed output such as `coalesce(previous, payload)` reports PIE-S2333 at the
table or query; a `select distinct` table or query reports such a window value
of its own PIE-S2339. A window value function over such a field of a row that
also has a field of another shape of the same name, declared in another
module, reports PIE-S2333. A project window partitioned or ordered by such a
field is still refused (PIE-S2103, or PIE-S2102 for a grouped key), and a
window of a table or query with JOIN inputs, and a window inside `qualify:`,
also refuse such a value (PIE-S2104 `value type must be concrete`). A single
file keeps an alias of a shape as the alias, so its window value functions
refuse it (PIE-S2104).

An alternate complete table/query body retains named set operands:

```pietto PIE-S2334
query combined:
    union all current_orders, archived_orders
```

EXPLICIT_MODULES project check supports `union`, `intersect`, and `except`, each
with explicit `all` or `distinct` and at least two named operands. Omitted
quantifiers and single operands receive PIE-S2341; no quantifier is defaulted.
Empty bodies and conflicting/repeated quantifiers are syntax errors. Authored
order and repeated uses are retained. Flat operands fold left; named nested sets
preserve their own grouping. Set bodies have no SELECT/order/limit tail;
referenced named inputs keep their own completed clauses.

Under [S9-NAME-1](spec/phase64-slice9-set-operations-explicit-all-distinct-output-identity-v1.md),
output labels come from the first authored operand and alignment is positional.
Output identities belong to the set, with ordinary local result roles and exact
operand provenance. Every operand must be concrete with the same width and exact
canonical types, including independently validated identical Decimal precision
and scale. An unavailable first operand has no first-available fallback; runtime
emptiness does not change labels. Unknown types never match themselves.

For one row-equivalence class with left/right counts m/n, UNION ALL gives m+n,
INTERSECT ALL min(m,n), and EXCEPT ALL max(m-n,0). Their DISTINCT counterparts
give one exactly when either side, both sides, or only the left side is present.
NULL is equivalent to NULL, and Float rows compare by Float equality
(`-0.0 == 0.0`; see [Float values](#float-values)). Only UNION ALL needs no
row equivalence, allowing matching concrete Any/Bytes/Json types. The other
five forms reject these types. On PostgreSQL project emission admits every
Float set form, a window `percent_rank` or `cume_dist` result included. On
MySQL it keeps UNION ALL only for such a result, and it refuses Float INTERSECT
and EXCEPT (MySQL compares `-0.0` and `0.0` as different values there) and
UNION DISTINCT (MySQL kept them apart beside a wide key), and keeps UNION
ALL.
PIE-S2342 covers unavailable inputs/width, PIE-S2343 exact types/Decimal, and
PIE-S2344 required row equivalence. Failed sets keep their original admission
causes; only successful exact owners retire PIE-S2334.

UNION combines nullability conservatively and inherits no branch-local key/FD.
INTERSECT may retain safe subset facts from any operand; EXCEPT uses left value
facts while retaining every right membership dependency. Set alternatives,
quotients and subsets retain separate grain origins. UNKNOWN grain alone is
legal; UNION of GLOBAL inputs does not prove GLOBAL. No source occurrence is
chosen as a representative. Named set outputs compose through replay, either
JOIN role, DISTINCT, nested sets and imports/reexports. Sets do not discharge
single-match obligations. Private combined IR retains every operand occurrence,
active producer and value/membership map for independent verification and
inspection; legacy IR/SQL/Explain retain their negative boundaries.

EXPLICIT_MODULES project check accepts both ordinary `select:` and
`select distinct:`. DISTINCT compares exactly the final visible selected row,
after grouping/window/QUALIFY and projection, before relation ORDER and LIMIT.
Hidden computations, JOIN intermediates and unselected ORDER inputs are excluded.
NULL is equivalent to NULL here; predicate equality and field nullability do not
change. Each quotient class occurs at most once, without selecting a source-row
representative or inventing ordering, a smaller key, or total cardinality <= 1.

The [Slice-8 support contract](spec/phase64-slice8-row-equivalence-distinct-quotient-grain-origin-v1.md)
requires exact type identity and validated identical Decimal precision/scale;
missing or unpropagated Decimal parameters fail closed. Any, Bytes and Json are
unsupported. Float, resolved Float aliases, finite Float literals and computed,
aggregate and window Float results compare by Float equality: each DISTINCT
class merges `-0.0` with `0.0` and shows one member's value
([Float values](#float-values)). Project emission emits Float DISTINCT on
PostgreSQL. MySQL refuses it at emission (MySQL kept `-0.0` and `0.0` apart
beside a wide key), and a window `percent_rank`/`cume_dist` result too.
Project emission also takes Float
`min`/`max` by the same law on both targets, and counts distinct Float values
on PostgreSQL; MySQL refuses a Float `count_distinct` (PIE-B1003). Other Float
operations retain existing behavior.

DISTINCT preserves canonical output fields and gives non-global results a new
quotient grain domain, including inputs with UNKNOWN grain. Sound GLOBAL or
exact input LIMIT 0/1 posture remains at most one, with authored DISTINCT
retained. Its own later LIMIT still limits the quotient result. Relation ORDER
must be determined by visible selected values or existing exact strict FD
proof; PIE-S2340 rejects a hidden representative. Unsupported visible-field
equivalence emits PIE-S2339 ERROR in all check modes, with no successful quotient.

Named DISTINCT outputs compose through imports/reexports, replay and supported
JOIN inputs. Single-file/LEGACY_FLAT/PACKAGE_ROOT, Project Explain and old IR/SQL
keep their existing availability boundaries. Private combined DISTINCT IR
retains the exact visible comparison, quotient origin and ORDER/type proofs
for independent verification and inspection, and project SQL emission
(`emit-sql --project`) emits it as `SELECT DISTINCT`.

Single-match semantic checking is available through explicit private requests on
completed EXPLICIT_MODULES roots. Ordinary authored compilation supplies no
requests; no marker, keyword, CLI flag or JSON field is introduced. A request
counts actual predicate-TRUE right BAG matches per exact left occurrence at one
explicit JOIN boundary. Equal payloads and the rows an `any` filter keeps do
not change this unit. Mandatory positive equalities in that JOIN's ON, written
by hand or in the body of a relationship-predicate call, may establish equality
to the actual right input's unique key.
The exact completed right producer's LIMIT 0/1 and supported real GLOBAL
aggregate/replay roots may also prove the request. A multi-table JOIN has a
separate boundary and request for each step; it does not create an implicit
whole-path proof. Grain, post-JOIN LIMIT/WHERE, a left input's key or estimates
alone do not prove it.
Legal unproved requests retain a private enforcement obligation and emit
PIE-S2337 WARNING in all three modes; invalid requests emit PIE-S2338 ERROR.
Proved requests emit neither. Successful checks include the exact warning in
existing text/JSON diagnostics. Combined Project IR retains every valid request,
its exact JOIN boundary, input pair and proof roots. LEGAL_UNPROVED
may have correctly VERIFIED IR while still requiring downstream enforcement;
INVALID keeps its owner non-concrete. No execution or data repair occurs.

The [private combined IR boundary](spec/phase64-slice10-project-ir-composition-verification-invalidation-inspection-pure-boundary-v1.md)
uses explicit active outputs and existing occurrence/allocation domains.
Inspection requires an exact VERIFIED analysis bundle. Its Phase64 format is
`pietto.phase64-flat-relational-ir-inspection.v1`; unchanged historical inputs
retain their prior formats and bytes. The standard-library pure evaluator
checks closed document-local structure and evidence links, returning a
normalized rejection without bytes for malformed inputs. External JOIN inputs
must retain their producer; internal accumulated inputs must link to the
actual same-owner preceding JOIN output. Pure OK proves document consistency,
not database semantics, single-match fulfillment or execution capability.
Changed semantic roots require rebuilding the overlay and fresh verification.

Single-file JOIN lowering and selected project JOIN lowering consume checked
input occurrences and conditions. Project SQL still requires its explicit
emission contract and verified physical representations; successful parsing or
semantic completion does not substitute for those target premises. Single-file
`explain` keeps its one-input metadata boundary and reports PIE-I1000 at each
JOIN relation.

### Single-file JOINs

Single-file `check` and PostgreSQL `emit-sql` accept INNER, LEFT, RIGHT, FULL
and CROSS JOINs, and `any` or `not any` filters before a later JOIN, over
sources, tables and queries of the same file whose row fields are known. Name
each JOIN input with `let`, then join it by that name: `let customer =
customers` followed by `inner join customer on ...`. Each JOIN introduces a
distinct input occurrence, even when it reads the same relation as another
input, as `let peer = customers` does beside `from customers`. The FROM
input's name is the name written after `from`: a relation's own name, or a
`let` that names the relation, so after `let base = rows` and `from base` the
query reads `base.id`, not `rows.id`. A JOIN may not take the FROM input's name
(`JOIN binding cannot have the FROM input's name: <name>`) or join one name a
second time (`Duplicate JOIN binding name: <name>`), both PIE-S2335 at the
name; a second `let` of one name is PIE-S2604 (`Duplicate query local name`).

An EXPLICIT_MODULES project names the FROM input the same way: after
`let c = customers` and `from c` it reads `c.id`, and refuses `customers.id`
as it refuses any name that is no input. At the read it reports what a
single file reports, such as PIE-S2102 `Unknown field: customers.id`,
with three differences: a QUALIFY predicate that reads it outside a window
reports PIE-S2332 `Unknown QUALIFY reference: customers.id`, as for any
unknown name there; after a JOIN a single file also says that `customers`
names a relation, not a binding, and a project does not yet; and a
project can list a SELECT item's diagnostic before a WHERE test's or a
GROUP BY key's, where a single file follows the source order. 0.1.6
projects accepted `customers.id` in a query without a JOIN, outside
`any(...)`, in every clause but HAVING and the ORDER BY of a grouped query;
write `c.id` there. A project HAVING or grouped ORDER BY reads no qualified
input field, with or without an alias: it reports PIE-S2327 or PIE-S2321 as
a single file does.

Every JOIN but CROSS has an `on` predicate: a declared relationship never joins
by itself, and a JOIN without `on` is PIE-S2335
(``JOIN c: write `on` with the condition that matches orders to customers``).
CROSS takes no `on` (PIE-S2336). An `on` is an ordinary row predicate: field
comparisons, calls of [relationship predicates](#named-inputs-and-reusable-relationship-predicates)
such as `on OrderCustomer(orders, customer)`, and their `and`, `or` and `not`
combinations. A relationship call takes, for each parameter, an input that
reads a source of that parameter's shape, or a table or query whose columns
match the shape's fields by name and type (see
[Named inputs and reusable relationship predicates](#named-inputs-and-reusable-relationship-predicates));
its SQL is the SQL of its body written in `on`. A name that is no input the
call can read is PIE-S2604 `Unavailable row argument for relationship
<name> parameter <role>`.

```pietto
shape Order:
    id: Int
    customer_id: Int

shape Customer:
    id: Int
    region_id: Int

source orders: Order = postgres.table("shop.orders")

source customers: Customer = postgres.table("shop.customers")

relationship order_customer(order: Order, customer: Customer): order.customer_id == customer.id

query active_customers:
    from customers
    where customers.region_id > 0
    select id, region_id

query result:
    from orders
    let buyer = active_customers
    left join buyer on order_customer(orders, buyer)
    select order_id = orders.id, region_id = buyer.region_id
```

`buyer.region_id` is None for an order without an active customer, although
`Customer.region_id` is not `Int | None`: the LEFT JOIN decides.

An unshaped source, including one reached through other relations, is refused
with PIE-S2334 at the JOIN that introduces it (the first JOIN for an unknown
FROM row). A JOIN cycle is PIE-S2302 at the closing read, and output schemas
propagate through both FROM and JOIN dependencies. A JOIN of a table or query
of the same file defines it as a CTE of the reader's SQL (see
[Single files and projects](#single-files-and-projects)).

Use `name.field` for a qualified field, or a bare field name when exactly one
visible input has it. Ambiguity is PIE-S2335 and lists qualified alternatives
in input order (`Ambiguous field: id; write orders.id or c.id`). An unknown
field is PIE-S2102. A relation's name is not an input name: after `let c =
customers`, a read of `customers.name` after the JOINs reports
`Unknown field: customers.name; customers names a relation, not a binding:
write c.name`. Value `let` names, inlined `def` arguments, WHERE, SELECT,
GROUP BY and ungrouped ORDER BY use this row scope. Value lets follow FROM and
every JOIN and precede the WHERE after the last JOIN: one before a JOIN is
PIE-S2604 (`A row-value let must follow FROM and every JOIN and precede
WHERE`), except that a `let` that a later JOIN reads as its input names a
relation, as `from` does, so a name there that is no relation, such as one the
module does not import, is PIE-S2301 (`Unknown relation: <name>`) at the
value, and one after that WHERE is the parser's PIE-P1000 for a misplaced
clause (``Clause `let` is out of order or repeated; ...``). A `let` name
cannot equal a visible input field
(`Let binding cannot shadow input field: <name>`) or an input name or its
relation's name (`Let binding cannot shadow input relation: <name>`), both
PIE-S2329. ORDER BY and `having` may read selected outputs by the name rule
after `select` (see [Sources and relations](#sources-and-relations)). Selected
column names remain the authored alias or the field's own name.

A JOIN's `on` sees the inputs before it and its own input, before that JOIN
adds any NULLs. A read of a later input is `JOIN ON reference is forward:
<text>`, a read of a `let` name, a SELECT output or a relation name is
`JOIN ON reference is unknown: <text>`, and a bare field that several visible
inputs have is `JOIN ON reference is ambiguous: <f>; write <alternatives>`,
each PIE-S2335 at the read. An aggregate there is PIE-S2335 (`Aggregate
expressions are unavailable in JOIN ON.`). A non-Bool `on` is PIE-S2202
(`Expected Bool expression in JOIN ON`), and one whose type stays unknown with
no other diagnostic inside it, such as `coalesce(None, None)`, is PIE-S2202
(`JOIN ON expression type is unavailable; the fields it reads need known
types.`), also in the predicate of an `any` filter before a later JOIN.
A condition made only of `None` values, such as `None if orders.id > 1 else
None`, is such an `on`; PostgreSQL emission also refuses a CASE, COALESCE or
NULLIF of only `None` values as a JOIN ON or EXISTS condition, as it does in a
WHERE, since PostgreSQL types it as text (PIE-B1000). Nullable Bool is
allowed: only TRUE matches; FALSE and NULL do not. Operand errors keep their
scalar diagnostic codes.

JOINs operate on the accumulated left row in source order. LEFT makes its
input's fields nullable; RIGHT makes every earlier input nullable; FULL does
both; CROSS adds every pair without changing nullability. An INNER JOIN proves
direct field leaves of the top-level `and` operands of its `on` non-null, also
inside a relationship call: a Bool field, a comparison's field operand, or
`field is not None`. OR gives no such proof. An earlier outer JOIN's
null-extension is retained: a later INNER JOIN never clears it, and WHERE does
not refine it. These types reach output schemas and `def` argument checks
(PIE-S2395).

An `any` filter in a WHERE before a later JOIN keeps each accumulated row once
when some row of its relation makes the predicate TRUE, and a `not any` filter
keeps it once when none does. Equal-valued rows remain distinct and repeated
matches do not multiply them. The binder is visible only inside its own
parentheses, never in the output or a later JOIN (`Unknown field: c.name`,
`JOIN ON reference is unknown: c.id`). A diagnostic inside the parentheses
names the binder as written: `where not any(o for o in orders)` is
`JOIN ON reference is unknown: o`. A filter adds no NULLs and does not
refine the fields it tests.

A WHERE test that compares a LEFT JOIN target's field, tests it with `like`,
an inclusive comparison chain or as the value of an `in`/`not in` list,
directly or through arithmetic, is never True where that JOIN found no match,
so WHERE drops those rows as `inner join` would. Each LEFT JOIN target that a
top-level `and` conjunct of the WHERE tests this way is a PIE-S2383 warning in
every check mode, once, at its first such conjunct. Move the test into the
JOIN's `on` to keep the unmatched rows, or write `inner join`. An `or`, an
`is None` test, a built-in call such as `coalesce` or an empty `in ()` or
`not in ()` list, which is a constant, is never counted, nor is a target that
a later INNER JOIN's match already reads; a `def` call counts as its body.

PostgreSQL writes one flat SELECT per relation. Every input is aliased by its
name and every field is qualified. Sources use their `postgres.table` name;
tables and queries use their own name. ON writes the authored `on` with each
relationship call written in place: a single comparison stays bare, as in the
example below, and each operand of `and` and `or` is parenthesized. CROSS has
no ON. An `any` filter becomes a correlated `EXISTS` filter on the
accumulated rows and a `not any` filter a `NOT EXISTS` one. INNER, LEFT and
CROSS JOINs keep pending filters in place; the next RIGHT JOIN adds them to its
ON after its own condition and clears them. Filters still pending at the end
precede the authored WHERE, in JOIN order. GROUP BY, HAVING, ORDER BY and LIMIT
then use the existing tail format.

```pietto
shape Customer:
    id: Int
    name: Text
    region_id: Int | None
    customer_key = unique(id)

shape Order:
    id: Int
    customer_id: Int

shape Region:
    id: Int
    name: Text
    region_key = unique(id)

source customers: Customer = postgres.table("customers")

source orders: Order = postgres.table("orders")

source regions: Region = postgres.table("regions")

relationship CustomerRegion(customer: Customer, region: Region): customer.region_id == region.id

query buyers_by_region:
    from customers
    where any(o.customer_id == customers.id for o in orders)
    let region = regions
    left join region on CustomerRegion(customers, region)
    select customer = customers.name, region_name = region.name
```

PostgreSQL `emit-sql` writes the filter after the JOINs:

```sql
SELECT
    "customers"."name" AS "customer",
    "region"."name" AS "region_name"
FROM "customers" AS "customers"
LEFT JOIN "regions" AS "region" ON "customers"."region_id" = "region"."id"
WHERE EXISTS (SELECT 1 FROM "orders" AS "_pietto_any_1" WHERE "_pietto_any_1"."customer_id" = "customers"."id")
```

MySQL `emit-sql` writes the same FROM and JOIN lines with backticks, and the
same pending filters. MySQL compares Text under the column's collation, as all
emitted MySQL SQL does. Its 8.4 default, `utf8mb4_0900_ai_ci`, ignores case
and accents, so `'Toronto'`, `'toronto'` and `'tóronto'` are equal there: a
Text equality in `on` or in an `any(...)` predicate may match rows that
PostgreSQL keeps apart, and so give other duplicates and NULL-extended rows.

FULL JOIN requires every condition leaf, after splitting AND, to be
an equality between a field of an earlier input and a field of its own input,
both of builtin Int type after alias expansion; otherwise both targets report
PIE-B1000. A FULL JOIN with a pending `any` or `not any` filter is also
PIE-B1000: a RIGHT JOIN must come between that filter and FULL to consume it.
These refusals are once per relation; other artifacts remain and the command
exits 1.

MySQL has no FULL JOIN. For one inside these limits, MySQL `emit-sql` writes
the inputs through it as a derived table `__pietto_full`, or the first of
`__pietto_full2`, `__pietto_full3`, ... that no input or `any` alias of the
statement takes in any case: the LEFT JOIN of its condition, then UNION ALL the RIGHT JOIN rows whose first earlier-input
key is NULL. Every key of a matched pair is non-NULL, so those are exactly the
unmatched rows of its own input, and the derived table holds every row and
duplicate a FULL JOIN holds. It carries each field that the rest of the
relation reads as a column `<derived table>_<n>`, and the later JOINs, WHERE,
GROUP BY, windows, QUALIFY, ORDER BY and LIMIT read those columns. Both
branches read each input in one statement, and a table or query of the file
is one CTE, so a CTE that MySQL cannot merge, such as one with LIMIT, is
materialized once and both branches see the same rows; a QUALIFY relation's
CTE ends with such a LIMIT (see [Single files and projects](#single-files-and-projects)).
Each later FULL JOIN
writes its derived table, which holds the earlier ones, in both branches, so
the SQL doubles with each FULL JOIN; MySQL emulates at most 8 in one relation
and refuses more (PIE-B1000). MySQL refuses the
relation (PIE-B1000) when a carried field's type is not builtin or is `Any`,
such as an enum, whose column UNION ALL may turn into a string. The emulation assumes, as all
MySQL emission does, that a field of a builtin type reads a column that is
not ENUM or SET.

Selected windows and named windows over known JOIN rows are typed in single
files and both targets emit their resolved JOIN bindings; a hidden QUALIFY
window uses the same facts. ORDER BY after
an aggregate without GROUP BY remains PIE-S2334. Aggregates over JOIN rows
follow the conservative rule in [Aggregates and grouping](#aggregates-and-grouping).
DISTINCT, relation lets, LATERAL capture, set inputs, VALUES and table
functions retain their separate project-only boundaries.

### Backward asof JOIN

`asof left join NAME on ...` keeps, for each earlier row, the latest row of
`NAME` whose keys match and whose time is at or before the earlier row's time:
for each order, the price that was valid when it was placed. This is the rule
of pandas `merge_asof` with its defaults (backward, exact matches allowed).
`asof inner join` does the same and drops the earlier rows that find none.

```pietto
shape Order:
    id: Int
    product_id: Int
    ordered_at: Timestamp

shape Price:
    product_id: Int
    valid_from: Timestamp
    amount_cents: Int
    price_key = unique(product_id, valid_from)

source orders: Order = postgres.table("shop.orders")

source prices: Price = postgres.table("shop.prices")

query order_prices:
    from orders
    let price = prices
    asof left join price on orders.product_id == price.product_id and orders.ordered_at >= price.valid_from
    select order_id = orders.id, price_cents = price.amount_cents
```

- **Form.** The `on` is zero or more keys `EARLIER.k == NAME.k`, then one time
  test `EARLIER.t >= NAME.t`, joined with `and`, on one line and without
  parentheses. Each test names the earlier input first, and the keys keep
  their written order in the SQL. Both sides of the time test are `Date` or
  both are `Timestamp`, and a key is not a `Float`. A table without keys,
  such as one exchange rate per moment, has only the time test:
  `asof inner join rate on orders.ordered_at >= rate.valid_from`. Another
  spelling of the line, such as `left asof join` or an `on` in parentheses,
  is PIE-P1000, with this form as its hint. Another `on` is PIE-S2336, with
  its rewrite where one exists. A JOIN without `on` is PIE-S2335, and so is
  a field name without its input that both inputs have, as in any JOIN.
- **One latest row.** `NAME` is a `source` whose shape declares a
  `unique(...)` whose fields all lie within the matched key fields and the
  time field: `price_key = unique(product_id, valid_from)` above, or
  `unique(valid_from)` for a rate table without keys. Pietto never picks one
  of several tied rows: without such a unique the JOIN is refused
  (PIE-S2386), and the message names the unique to declare or the key to
  match. A table, a query or a `let NAME:` block is no such input
  (PIE-S2386). The unique is a trusted declaration, not checked at run time:
  on data that breaks it, a single file returns one of the tied rows and a
  project returns each of them.
- **None.** A `None` key or time, on either side, matches nothing. A matched
  row whose other fields are `None` is still a match.
- **Rows.** `asof left join` keeps every earlier row, with the joined fields
  `None` where nothing matches; `asof inner join` drops those rows. Equal
  earlier rows each get their own row, and one joined row may serve many
  earlier rows.
- **After the JOIN.** A `where` test of a joined field tests the chosen row
  and never falls back to an earlier one. After `asof left join` such a test
  also drops the rows without a match and warns (PIE-S2383), as after
  `left join`; to keep them, test the chosen row in `select`:
  `x = price.amount_cents if price.amount_cents > 100 else None`.
- **Aggregates.** The JOIN repeats no earlier row, so in a single file an
  aggregate of earlier fields after it, such as `sum(orders.quantity)`, is
  accepted. An aggregate of a joined field, such as `sum(price.amount_cents)`,
  may count one price for several orders and is refused (PIE-S2381).
- **Limits.** One asof JOIN per query: put the first into its own query and
  `from` it. There is no lower bound or tolerance, no forward or nearest
  direction, no strict `>` and no validity range; each is PIE-S2336, with
  a rewrite where one exists. For a validity range, write a plain `left join price`
  whose `on` has the keys and both tests,
  `orders.ordered_at >= price.valid_from and orders.ordered_at < price.valid_to`.
- **MySQL.** MySQL writes the same SQL with its own quotes: the `LATERAL`
  latest row in a single file, the latest-row test in a project. In a single
  file a `Text` key compares under the column's collation, as in any MySQL
  JOIN, so the declared unique must hold under it (a MySQL `UNIQUE` index on
  those columns ensures that). A single file refuses an asof JOIN in a
  relation with a FULL JOIN, which MySQL emulates with UNION ALL
  (PIE-B1000). Each database finds the latest row fastest with an index
  on the joined table's keys and time, such as `(product_id, valid_from)`.
- **Projects.** An explicit-module project checks an asof JOIN with the same
  rules and messages, except that it reports a JOIN without `on` as
  PIE-S2333. It also needs flat fields: no `collect` or `unnest` in that
  query and no nested-relation field in an earlier input (PIE-S2336). It emits the
  JOIN in a table or query
  without a relation `let NAME:` block whose FROM is not a table function;
  elsewhere, such as a query whose earlier input is a `let NAME:`
  block or whose asof JOIN is inside one, the JOIN is checked and then
  refused with `asof JOIN is not available in projects yet.` (PIE-S2336).
  An aggregate after an asof JOIN is accepted only where its `on` keys match
  a `unique(...)` of the joined source, as after any JOIN, and is otherwise
  refused (PIE-S2333): do the asof JOIN in one query and aggregate in a query
  that reads it with `from`.
- `asof` stays an ordinary name everywhere else: `select asof = orders.id` is
  a valid output.

## Relation blocks and relation references

The parser accepts the following forms. In an EXPLICIT_MODULES project a closed
relation let, a typed VALUES body, a bounded `generate_series` table-function
input, a closed `exists`/`not exists`, `scalar` or `in`/`not in` read, a let
with `capture` lines read by `exists`, `scalar` or `in`/`not in` or joined
LATERAL by `cross join`, `inner join` or `left join` and the header of an
entry query whose own body reads a relation with `from` are
available, as described after the example; every other form is not available
yet:

```pietto PIE-S2346 PIE-S2346 PIE-S2345 PIE-S2345 PIE-S2350 PIE-S2350 PIE-S2348 PIE-S2345 PIE-S2345 PIE-S2351 PIE-S2349 PIE-S2345 PIE-S2347 PIE-S2345 PIE-S2347 PIE-S2352
query vip_report(cutoff: Int, label: Text | None):
    let vip:
        from customers
        where tier == "gold"
        select:
            id
    let big_vip_orders:
        from orders
        where customer_id in vip and total > 1000
        select:
            latest = max(order_day)
    from orders
    where customer_id in vip and order_day >= cutoff
    select:
        id
        latest_day = scalar big_vip_orders.latest
        note = coalesce(label, "none")

query frequent_customers:
    let counts:
        from orders
        group by:
            customer_id
        select:
            customer_id
            n = count()
    from counts
    where n > 10
    select:
        customer_id

query customers_with_recent_orders:
    let recent:
        capture customers
        from orders
        where orders.customer_id == customers.id
        select:
            id
    from customers
    where exists recent
    select:
        id

query all_codes:
    let seed:
        values(id: Int, label: Text | None):
            1, "new"
            2, None
    let codes:
        union all seed, archived_codes
    from codes
    select:
        id

query empty_seed:
    values(id: Int, label: Text | None)

query days:
    from generate_series(1, 31, 1) as n
    select:
        n
```

In an EXPLICIT_MODULES project whose sources have these fields, with
`archived_codes` matching the columns of `seed`, every query above checks as
written; `days` emits and compiles for PostgreSQL only (see below). Single-file
analysis and LEGACY_FLAT projects refuse these forms (see below).

Only an entry `query` header declares parameters. A relation let, `let NAME:`,
starts a top-level table or query body, before its `from`, set operation or
VALUES body; several lets sit side by side. Lets are one level only: a let body
never contains another `let NAME:`. It may start with `capture` lines, one name
per line, and then holds exactly one FROM-based, set operation or typed VALUES
body. There is no inline `from x:` block: a derived table is a let read with
`from x`, and `from` takes a relation name or a table function such as
`generate_series(1, 31, 1) as n`. Scalar row values use `let name = expression` after the JOINs and before
the ordinary WHERE tail; this is distinct from a relation block. A typed VALUES
body has one row per line; its header without `:` has
zero rows. `in` and `not in` take a relation name, `exists` takes a relation
name, and `scalar` reads exactly `relation.column`. A join right side may name
a let, so LATERAL needs no new keyword. An expression in parentheses may
continue over several lines (see [Layout](#layout)).

`values`, `exists`, `capture` and `scalar` are contextual words: existing
fields, relations and calls with these names keep parsing as before. `in
(vip)` remains a one-item literal list and `exists(recent)` a call; an ORDER BY
item `exists asc` still names a column. Other spellings are syntax errors, for
example `from x:`, a nested `let NAME:`, `let NAME:` after `from`, `capture`
outside the start of a let body, `query q():`, a one-part `scalar r` or
`capture a, b`.

In an EXPLICIT_MODULES project (`schema_version = 2`) a relation let whose body
is a FROM-based, set operation or typed VALUES body, without `capture`, is its
own query block. It is not a module declaration: it cannot be exported or
imported, read from another declaration, or selected by `emit-sql --project` or
`compile_query`, and project SQL emits it as one named CTE like a module-level
table or query. A table or query declares at most 64 lets; each let after the
64th is PIE-S2357 at the let, reported like the temporary diagnostics below. A
let name shares one scope with the module's relation names, including every
relation import binding whether or not it resolves, the other lets of its
declaration and that declaration's JOIN bindings; a let named like any of them
is PIE-S2001 at the let, and inside the declaration a `from`, JOIN target or set
operand with that name then resolves to no relation. A let never hides another
name. The other lets and the body of its declaration may read a let any number
of times, by `from`, a JOIN target, a set operand or a relation read (see
below), whether the let is written before or after them; only a let with
`capture` lines is read exactly once (see below). A let that no block of
its declaration reads is PIE-S2359 at the let. Reads must not form a cycle: a
let reading itself, lets reading each other, or a let reading its own
declaration while that declaration reads the let, directly or through other
lets, is PIE-S2302. Its message follows one cycle of reads, starting with the
member written first, where a declaration's lets count as written before it;
when cycles share members, it names one of them. The declaration body is at
nesting depth 0 and a let read by a block at depth d is at depth d + 1 on its
deepest read path; a let deeper than 16 is PIE-S2360 at the let. These errors
fail the project like any other ERROR. Project SQL emits each let once, after
the lets it reads, and every read refers to that one CTE: two lets reading one
let, or one block reading a let twice, never duplicate it. A let keeps its own
LIMIT: a filter written where the let is read stays outside that LIMIT. A source
read only inside a let is a source of the query like any other: the emission
contract describes it, and the compiled query, source qualification and R2
source requirements include it.

In the same projects an expression can read a whole relation block without
capture: `exists name` and `not exists name` test whether it has a row, `scalar
name.column` reads one of its output columns, and `value in name` and `value not
in name` compare a value with its one output column. The name is a source, a
module table or query (a typed VALUES one included), or a let of the
declaration, found by the same lookup as `from` (an unknown name is PIE-S2301; a
read that would make its block read itself, directly or through its lets, other
reads and inputs, is PIE-S2302 at the read). A read is never a FROM, JOIN or set
input of its block, and every occurrence is its own read: `exists r or exists r`
reads `r` twice, and a let read only this way is read. The read block is checked
like any other block, including columns no one selects; project SQL emits it
once as its own named CTE (a source is read directly) and each read as a
subquery over it with a generated alias `e<n>`. Pietto does not promise whether
or when the database evaluates a read or the read block's expressions. A source
read only through relation reads, or only inside a let read that way, is a
source of the query: the emission contract must describe it, and the compiled
query, source qualification and R2 source requirements include it. A read is
available only in WHERE and in the SELECT of an ungrouped query, including a
JOIN reader, a reader of a set and the let bodies of the declaration; in JOIN
ON, a row `let`, the SELECT of a grouped or aggregate query, HAVING, a
window call or window specification, QUALIFY, ORDER BY or LIMIT it is reported
at the read with its family's code, PIE-S2349 for `exists`, PIE-S2348 for
`scalar` and PIE-S2350 for `in`. Outside a relation body, for example in a type
rule, a shape `check`, a type argument or a VALUES row, a read keeps that
pre-admission code.

`exists r` is a `Bool` that is never None: true when `r` has at least one row.
Project SQL renders it as `EXISTS (SELECT 1 FROM <block> AS e<n>)`.

`scalar r.c` has the type of the column `c` and is always nullable: a read of
no row is NULL, a read of one row is that row's value, and a read of more than
one row is the database's own runtime error, PIE-R3003 with SQLSTATE 21000; no
LIMIT is added. An ungrouped `count()` always has one row, so its read is never
NULL at runtime, but the type stays nullable. A set, an authored JOIN, a
relation reading one of them, a typed VALUES body or a table function (directly
or through a let) and a relation whose own errors leave its columns unknown
cannot be read by `scalar` yet, because their columns are not known before
completion: the read
is PIE-S2348, whatever column it names. A typed VALUES body itself declares its
columns in its header and is read like any other relation. An unknown column of any other relation is PIE-S2102 at the read. A
relation whose errors do not change its columns, for example an error in its
WHERE, is read as usual and reports only its own errors. Project SQL renders
the read as `(SELECT e<n>.c FROM <block> AS e<n>)`.

`value in r` and `value not in r` keep the three-valued logic of the literal
list: the test is true when a row of `r` equals a non-NULL `value`; otherwise it
is NULL when `value` is NULL and `r` has rows, or when `r` holds a NULL;
otherwise, and always for an empty `r`, it is false, so over an empty `r` `NULL
in r` is false and `NULL not in r` is true. Duplicate rows do not change the
result. The result is a nullable `Bool` even when neither side can be NULL; `not
in` is never rewritten to an ANTI JOIN, a literal list or a COALESCE, and WHERE
keeps the rows where the test is true. A `value` whose type the literal-list
`in` would not accept against the column of `r` is PIE-S2105 at the test, and so
is a read of a block whose columns are known and are not exactly one. A bare
`None` value takes the type of that one column, like a NULL in a literal list.
The columns of a set, an authored JOIN or a relation reading one of them, a
typed VALUES body or a table function are not known before completion, so for
such a block `check
--project` reports none of these, and `emit-sql --project` and `compile_query`
refuse the query with PIE-B1003 `relation_membership_width_not_one` when it does
not have exactly one output column, with PIE-B1003
`membership_type_pair_not_admitted` when the type or physical carrier of `value`
does not pair with its column, and with PIE-B1003
`expression_evidence_unavailable` for a bare `None` value, which has no type
there; a literal list whose elements are all null is PIE-S2105 at check. Project
SQL renders the read as `(value [NOT] IN (SELECT e<n>.<column> FROM <block> AS
e<n>))`, so an `order by` and `limit` of the read block stay inside its CTE and
no IN subquery carries a LIMIT.

In an EXPLICIT_MODULES project a typed VALUES body is also the body of a
top-level table or query. It is its own zero-input relation, read by `from`, a
JOIN target or a set operand within the same current limits as a set operation
body (grouping over it, by a field or a computed key, with or without JOIN, is
not available yet: PIE-S2333), and its row schema comes only from its header,
never from a named relation or source. Each column is `name: Type`, never
None, or `name: Type | None`, with Type one of `Bool`, `Int`, `Float` or `Text`
(PIE-S2361 otherwise; a repeated name is PIE-S2001). Each row has one cell per
column (PIE-S2362). A cell is a fixed literal, a signed number included; a
name, parameter, call or other expression is PIE-S2363. A cell matches its
column's declared type and nullability: an `Int` is within the signed 64-bit
range, an integer literal is not a `Float`, and `None` appears only in a
nullable column (PIE-S2364). A body has at most 1,000 rows and 64 columns
(PIE-S2365). Rows keep their order and duplicates, and the header alone is a
zero-row relation with its complete schema. A VALUES body has no key, no
functional dependency and an unknown grain.

Project SQL writes every VALUES column alias and every cell, `NULL` included,
inside a CAST to its column's declared type, so no column name or type is left
to the database; cells are never bound parameters. A VALUES table or let read by
the statement is a CTE, a selected VALUES query is a SELECT over a derived
VALUES table, and a zero-row body is a typed `SELECT CAST(NULL AS ...) ...
WHERE FALSE`. A VALUES body joined or combined with a physical source is
emitted and compiled for PostgreSQL and MySQL. A statement whose only inputs are
VALUES bodies reads no physical relation: PostgreSQL runs it under a
session-context qualification (see [Execution](execution.md)), and MySQL
refuses it: `emit-sql` and `compile_query` report it BLOCKED with `PIE-B1003`,
and the MySQL route also refuses any compiled query that reads no physical
relation before connecting (`PIE-R1003`). R2 refuses a query with a VALUES body
before connecting (`PIE-R1004`), because a fixed row has no recovery
coordinate.

PIE-S2365 bounds the source only; it does not promise that a body emits.
Project SQL counts every cell, with its CAST and its source ranges, against the
compiler's limits on generated structure and on the size of the public emission
document, and a body over either limit is BLOCKED with PIE-B1007
(`generated_structure_limit` or `public_artifact_byte_limit`). These limits bind
long before PIE-S2365: a body of 1,000 rows and 64 columns is always BLOCKED,
and 1,000 rows of short cells emit with only about a dozen columns.

In the same projects a relation let may start with `capture NAME` lines, one
name per line, and is then correlated: it reads the current row of one FROM or
JOIN row input of its declaration body. `NAME` is that body's FROM relation
name or a JOIN binding such as `r` in `let r = rhs` followed by `left join r on ...`; the binder of
an `any(...)` test is not a row input, and neither is the binding
of a table function the body reads (the bindings of its JOINs are). Inside the let body
`NAME.field` reads that field of the outer row; bare names and every other
qualified name keep naming the let's own input, so a captured input is never
found by a bare name and adding a field to an outer input never changes what a
bare name inside the let means. Only FROM and JOIN row fields are captured,
never an outer row `let` value, SELECT output, aggregate or window result. A
captured field has the outer input field's type and is nullable when that field
is or when an outer LEFT, RIGHT or FULL JOIN may null-extend its binding: a
null-extended outer row is read as such. An outer JOIN ON condition does not
narrow a captured field. The columns of a set, an authored JOIN, a typed VALUES
body, a table function, a relation reading one of them and a relation whose own
errors leave its columns unknown are not known before completion: a field read of such a captured
input is PIE-S2369, whatever field it names, and a capture line whose fields are
not read is accepted. The let's own FROM relation is not restricted so: a let
over a set, an authored JOIN, a typed VALUES body or a let reading a table
function reads captured fields in its WHERE and SELECT as usual. In the example above `recent` captures `customers`, the
FROM input of `customers_with_recent_orders`.

Unlike other lets, a let with capture lines is read exactly once, by `exists
name`, `not exists name`, `scalar name.column`, `value in name` or `value not in
name` written in the WHERE, or in the SELECT of an ungrouped declaration body
(the positions of any such read: PIE-S2349, PIE-S2348 or PIE-S2350 elsewhere) or
as the target of a JOIN of that body (LATERAL, below), and every outer row,
duplicates included, gets its own result: a correlated read is never rewritten
to a JOIN, deduplicated by key or decorrelated. A correlated `scalar` read is
NULL for an outer row whose let has no row, that row's value for one row, and
the database's own runtime error for more than one (PIE-R3003, SQLSTATE 21000);
a correlated `in` or `not in` keeps the three-valued logic above for each outer
row, and `not in` is never an ANTI JOIN. The column and width rules of `scalar`
and `in` are unchanged (PIE-S2102, PIE-S2105). Its body is a FROM relation with
an optional WHERE and an ungrouped, window-free SELECT; a let joined LATERAL or
read by `scalar`, `in` or `not in` may also end in ORDER BY and LIMIT (below).
Project SQL emits it inside that read as nested derived tables, `EXISTS (SELECT
1 FROM (SELECT ... FROM (SELECT ... WHERE ...) AS t<n>) AS e<n>)`, `(SELECT
e<n>.c<k> FROM (SELECT ...) AS e<n>)` for `scalar` and `(value [NOT] IN (SELECT
e<n>.c0 FROM (SELECT ...) AS e<n>))` for `in`, whose correlated references name
the reading SELECT's own relation alias and column; the left value of `in`
renders, and takes its placeholders, before the let. A correlated block is never
a CTE, while capture-free lets and relations stay top-level CTEs, including lets
the correlated let reads. No let reads a let with capture lines (no nested
correlation), so a correlated read nests at most the two derived tables of its
let's body inside its read, three when the let ends in ORDER BY and LIMIT. A
self-correlation, a capture of an input the
let itself reads, is refused: read that relation through another let first and
read the renamed let, for example `let inner:` with an indented `from orders` and then
`capture orders` in a let that reads `from inner`. These forms report:

- PIE-S2366 at a capture line whose name is not exactly one FROM or JOIN row
  input of the declaration body;
- PIE-S2367 at a capture line that repeats an earlier name of the same let;
- PIE-S2368 at a capture line whose name is also an input of the let itself;
- PIE-S2369 at a captured field the captured input does not have, and at each
  field read of a captured input whose columns are not known before completion;
- PIE-S2370 at the let when its body has a JOIN, row `let`, GROUP BY, an
  aggregate in WHERE or SELECT, a window, QUALIFY, HAVING or DISTINCT, is
  a set operation or VALUES body, reads a table function in its FROM (read it
  through another let), or has ORDER BY or LIMIT without being joined
  LATERAL or read by `scalar`, `in` or `not in` (an `exists` read never takes
  them), or an ORDER BY that reads a captured field or an aggregate, and at
  every read of the let other than its first `exists`, `scalar`, `in`, `not in`
  or JOIN in its declaration body, in source order: a later such read or JOIN,
  a FROM or set operand, or any read written in another let, a JOIN of another
  let included;
- PIE-S2371 at a capture line of a let joined LATERAL whose input is not left
  of that JOIN: the let's own JOIN binding or a later JOIN's binding;
- PIE-S2372 at a RIGHT or FULL JOIN whose target is a let with capture lines
  (a table or query that declares such a let reports PIE-S2334 at each
  `any(...)` it contains).

All but PIE-S2369 are reported with the file's pre-admission diagnostics
(below), in one (path, line, column, code) order with them and before the
file's query header checks; semantic analysis then does not run.

Joining a let with capture lines is LATERAL: no new keyword is needed. Its
capture lines then name the FROM input or the binding of a JOIN written before
the JOIN that reads the let, and every row of those bindings, duplicates
included, gets its own rows of the let:

```pietto PIE-S2345 PIE-S2351
query customers_with_their_orders:
    let their_orders:
        capture customers
        from orders
        where orders.customer_id == customers.id
        select:
            order_id = id
    from customers
    let o = their_orders
    cross join o
    select:
        id
        order_id = o.order_id
```

`cross join` pairs each left row with the let's rows for that row; `inner join
... on <condition>` keeps only the pairs for which the condition is true, and a
pure LATERAL INNER JOIN writes `on True`. `left join ... on <condition>` keeps
those pairs and every left row without one, once, with every field of the let
NULL; its ON chooses pairs and never removes a left row, unlike a later WHERE.
The let's fields are then nullable in the JOIN's output, and a later JOIN
condition, WHERE, SELECT or capture line reads them as null-extended, like the
target of any LEFT JOIN. The JOIN's output, its later JOINs and its tail are
those of any other JOIN. A captured field of a let joined LATERAL reads the row
those earlier inputs built, so it is nullable when its field is or when an
earlier LEFT, RIGHT or FULL JOIN may null-extend its binding; a later JOIN never
changes it. Project SQL emits the let as that JOIN's own derived relation,
`CROSS JOIN LATERAL (SELECT ... FROM (SELECT ... WHERE ...) AS t<n>) AS m<n>` or
`INNER JOIN LATERAL (...) AS m<n> ON ...` (`LEFT JOIN LATERAL` for a LEFT JOIN),
whose correlated references name the JOIN's left input alias and column; the let
is never a CTE. A RIGHT or FULL JOIN of such a let is not available yet
(PIE-S2372), nor is any `any(...)` in the table or query that declares it
(PIE-S2334).

The let body is limited as for an `exists` read, except that a let joined
LATERAL may end in `order by` and `limit`, a top-k per left row:

```pietto PIE-S2345 PIE-S2351
query customers_with_their_last_orders:
    let last_orders:
        capture customers
        from orders
        where orders.customer_id == customers.id
        select:
            order_id = id
        order by:
            order_day desc
            id desc
        limit 3
    from customers
    let o = last_orders
    left join o on True
    select:
        id
        order_id = o.order_id
```

Each left row, duplicates included, gets at most that many of the let's rows
for it, the first ones in that order; with `left join` a left row without any
keeps its one null-extended row. The ORDER BY and LIMIT follow the rules of
any relation result: the limit is static, an ORDER BY key names a field of the
let's input (a computed key is refused at emission with PIE-B1003
`order_expression_requires_established_port`), and the database chooses which
of several rows that tie on every key fill the last places. With `limit 1`,
when several rows tie on every ORDER BY key, or the let has no ORDER BY, the
database picks one of them: Pietto neither warns nor refuses, and the pick may
differ between runs and between PostgreSQL and MySQL. End the ORDER BY with a
field that is unique among the let's rows, such as a declared key
(`order by:` `order_day desc`, `id desc`), to fix it. `limit 1` is no proof
that a JOIN of the let matches at most one row: an aggregate of the left rows
over that JOIN is refused as a possible fan-out (PIE-S2333), as over any JOIN
that may repeat rows. An ORDER BY that
reads a captured field or an aggregate is PIE-S2370 at the let. A key that is
not a field of the let's input is not available either: an unknown name is
PIE-S2102 at the key, and for one of the let's own SELECT outputs this alpha
reports only PIE-S2333 at the declaration, with no diagnostic at the key. Project SQL
keeps both inside that JOIN's derived relation as one more derived table over
the let's SELECT, which carries each ORDER BY key as an extra column:
`LATERAL (SELECT ... FROM (SELECT ... FROM (SELECT ... WHERE ...) AS t<n>) AS
t<n> ORDER BY ... LIMIT <n>) AS m<n>`.

A let read by `scalar`, `in` or `not in` may end in `order by` and `limit` the
same way, on PostgreSQL only: for each outer row, duplicates included, the read
sees at most that many of the let's rows for it, the first ones in that order,
under the ORDER BY, LIMIT and tie rules above. A `scalar` read of such a let
with `limit 1` is NULL for an outer row without a row and otherwise the value
of its first row, the one the database picks among rows that tie; a larger limit keeps the runtime error for more than one row
(PIE-R3003). Project SQL wraps the let's derived tables, ORDER BY and LIMIT
included, in the read's own derived table, so no subquery that `in` reads
carries a LIMIT itself: `(SELECT e<n>.c<k> FROM (SELECT ... FROM (SELECT ...
FROM (SELECT ... WHERE ...) AS t<n>) AS t<n> ORDER BY ... LIMIT <n>) AS e<n>)`
and `(value [NOT] IN (SELECT e<n>.c0 FROM (SELECT ... ORDER BY ... LIMIT <n>)
AS e<n>))`. MySQL does not take this form: `check --project` accepts the
program, and `emit-sql --project` and `compile_query` for MySQL refuse the
query with PIE-B1003 `mysql_correlated_order_or_limit_read_not_admitted` at
each such read, in source order, before any connection; a let joined LATERAL
keeps its ORDER BY and LIMIT on both targets.

In an EXPLICIT_MODULES project a table or query body, or a let body, may read
one bounded table function: `from generate_series(start, stop, step) as n`.
The call is its own zero-input relation, read only by the body that wrote it;
`n` names its rows and its only column, an `Int` that is never None, inside
that body (`n` or `n.n`, and a JOIN body reads it with `from n`). The binding is never looked
up as a relation name: another body's `n` or a module relation `n` is a
different thing, and a let of the declaration named like the binding is
PIE-S2001, as for a JOIN binding. A let with capture lines
reads a table function only through another let (PIE-S2370 otherwise), and no
capture line names its binding (PIE-S2366). `generate_series` with exactly three
arguments is the only admitted table function: any other name is PIE-S2373
and another argument count PIE-S2374. Each argument is a fixed integer literal
within the signed 64-bit range, a signed number included; `None`, a Float, a
Bool, a Text, a name, a parameter or any other expression is PIE-S2375 at that
argument. Only when all three are valid, a zero step is PIE-S2376 at the
third argument, and a call whose rows exceed 1,048,576 is PIE-S2377 at the
call; the rows are `abs(stop - start) // abs(step) + 1` (integer division)
when the step points from start to stop, and zero otherwise. A descending series uses a negative step, and a
step pointing away from `stop` gives zero rows. The rows have no key, no
functional dependency and an unknown grain. The function's identity is a
closed catalog entry with explicit determinism and side-effect evidence that
admission consumes; it says nothing about error behavior or evaluation count,
and it does not make the reading body, its other expressions or any scalar
call pure or deterministic. As for a VALUES upstream, grouping or aggregating
directly over a table-function input is PIE-S2333 for now; read it through a
let or another relation first.

Project SQL writes each table-function input as a CTE read by its body,
`SELECT "n"."n" FROM pg_catalog.generate_series(CAST(start AS
pg_catalog.int8), CAST(stop AS pg_catalog.int8), CAST(step AS pg_catalog.int8))
AS "n"("n")`: the schema-qualified name and the bigint casts fix the one
`bigint` overload in the SQL itself, and the three values are fixed literals,
never bound parameters. The binding is written as that alias and column, so
each binding longer than 63 UTF-8 bytes, which PostgreSQL cannot spell, is
BLOCKED with `PIE-B1002` (`table_function_binding_unrepresentable`) at its own
input. It is PostgreSQL only: MySQL `emit-sql` and `compile_query` report each
table function BLOCKED with `PIE-B1003` (`table_function_not_admitted_on_target`)
at its own input, whether or not the statement also reads a physical source.
Either blocker is reported once per input, in source order, and a MySQL
statement's `scalar` and `in` reads of lets ending in ORDER BY and LIMIT are
refused beside them, in that one source order. PostgreSQL runs a
statement whose only input is a table function under the session-context
qualification of a VALUES-only statement (see [Execution](execution.md)); no
runtime catalog check of the function is made. R2 refuses a query with a table
function before connecting (`PIE-R1004`). PIE-S2377 bounds the series' static
rows; an execution's own `max_rows` still applies. A query whose own body or
one of whose lets reads a table function cannot declare header parameters:
each one is PIE-S2346 (see below).

In EXPLICIT_MODULES the `let NAME:` line, a `capture` line, a typed VALUES
body, a table-function FROM input and an `exists`, `scalar` or `in` read inside
a relation body are admitted, so a let there never receives the temporary
PIE-S2345, a capture line never receives PIE-S2351, a VALUES body never
receives PIE-S2347, a table-function input never receives PIE-S2352 and such a
read never receives PIE-S2348, PIE-S2349 or PIE-S2350; any other unavailable
form inside a let still receives its own code. Every other occurrence of these
forms receives its temporary ERROR diagnostic in every check mode before any
semantic reader runs: PIE-S2345 relation let, PIE-S2346 query header
parameter, PIE-S2347 VALUES body, PIE-S2348 scalar read, PIE-S2349 EXISTS
reference, PIE-S2350 IN reference, PIE-S2351 capture line and PIE-S2352
table-function FROM input. The one exception is a query header that an
EXPLICIT_MODULES project admits (see below). That run then reports no other
semantic diagnostic. Single-file `check`, `explain` and `emit-sql` report them
from semantic analysis; LEGACY_FLAT and EXPLICIT_MODULES project checks, project
`emit-sql` and `compile_query` report them with the owning file's parse
diagnostics, alongside other files' parse errors.
Single-file/LEGACY_FLAT/PACKAGE_ROOT retain their existing availability
boundaries: relation lets, entry-query header parameters, `exists`, `scalar` and
`in` reads and every later family become available only for EXPLICIT_MODULES.
PACKAGE_ROOT `explain --project` does not read relation bodies, so a package
module using these forms can be explained; that does not make its relations
available. The nested-relation spellings below are the exception: a package
module that uses them is refused with PIE-S2801.

### Nested relations: `collect` and `unnest`

An EXPLICIT_MODULES project reads a relation let of the same declaration as one
nested value with a `collect` SELECT item, and expands such a nested field with
an Unnest let that a JOIN then reads:

```pietto PIE-S2345 PIE-S2801 PIE-S2801
shape Order:
    id: Int
    customer_id: Int

source orders: Order = postgres.table("orders")

query customers_with_orders:
    let recent:
        from orders
        select:
            id
        order by id
    from orders
    select:
        customer_id
        recent_orders = collect recent

query expanded:
    from customers_with_orders
    let o = unnest(customers_with_orders.recent_orders)
    cross join o
    select:
        customer_id
```

`collect` is a word only right after `name =` in a SELECT item, so a field,
function, relation or let named `collect` keeps its meaning and
`collect(recent)` is an ordinary call. `name = collect recent` is a whole SELECT
item.

`collect r` reads a relation let `r` of the same table or query, closed or
with `capture` lines, as the bag of its rows: a row that repeats in `r`
repeats in the value. `r` must end in `order by` (PIE-S2804), and the value
keeps that order; rows that tie on every key have no promised order, so end
it with a unique field such as a key. A let with `capture` lines that
`collect` reads may also end in LIMIT, as for `scalar` and `in`, and is read
once: `collect` counts as its one read beside `exists`, `scalar`, `in` and a
JOIN (PIE-S2370). A Collect read is a SELECT item of a table or query without
GROUP BY or aggregates; in a grouped SELECT or in a relation let it is
PIE-S2803. To collect per group, use the per-group detail route below. A
Collect of a source, table
or query, imported or not, instead of a relation let of the same body is
PIE-S2803 too (a name that is no relation there, such as an alias, value or
window `let`, is PIE-S2301 `Unknown relation`), as is one of a let whose
columns are not known before completion (one that reads a VALUES body, a set
operation, an authored JOIN or a table function, or a let that reads one; a
read of a let that fails, through its own errors or a relation it reads,
reports only that failure), and one of a let with a
field that is not `Bool`, `Date`, `Decimal`, `Float`, `Int`, `Text`,
`Timestamp` or `UUID` of known nullability (a type alias counts as the type
it names) or that is itself collected: there is one collection layer. A field
computed with a binary arithmetic or comparison operator (`id + 1`, `id == 1`,
`1 <= id <= 5`), with `and` or `or`, or with `not`, `-` or `+` over one of
those has no known nullability yet. Completion does not yet order the value by
a key of `r` that is one name alone naming a SELECT output other than a
window's (`order by oid` over `oid = id`): order by the input value
(`order by id`) instead, or the table or query reports PIE-S2333. As in a
`select distinct` relation, a SELECT item that reads a field typed by a shape,
and a `let` bound to one, make a table or query with a Collect read report
PIE-S2333; its `where` may still test such a field.

A Collect value is never None: no rows of `r` is the empty value `[]`, and a
row of `r` whose field is None keeps it, so `[]`, a value with one row whose
field is None (`[{v: None}]`) and an outer JOIN's missing row are all
different things. The value has no comparison, ordering or scalar value: a
reader of the relation may read it with `from` or a JOIN, test it with
`exists` and read its scalar columns, but any other read of the nested field
(in WHERE, JOIN ON, a row `let`, `having`, a window, `qualify`, `order by`, a
SELECT expression, `any(...)`, `scalar` or `in`) other than as the list of
`len`, `sum` or `any` (below), `select distinct` with a
Collect item, and a set operation over it are PIE-S2805. A table or query
without JOIN inputs, a window or QUALIFY may group by it and deduplicate it: a
GROUP BY key that is the nested field as written (`group by xs`,
`group by p.xs`), a SELECT item that names that key, and a `select distinct`
item that is the nested field as it is. Two values are one key when both are
None (an outer JOIN's missing container), or when they have the same number of
child rows and their children, in the collected let's order, are pairwise
`same_value`: so `[1.0]` and `[1.00]` are one key, `[-0.0]` and `[0.0]` are
one key and the key shows one member's value, `[]`, `[None]` and None are
three keys, and `[1, 2]` and `[2, 1]` are two. Because the order decides the
key, the collected let's ORDER BY must end in bare fields of its FROM source
that cover a declared `unique(...)` key of that source and are never None, in
a let without JOIN inputs, grouping, aggregates or DISTINCT; otherwise the key
or DISTINCT item is PIE-S2805 (``Nested relation field xs cannot be a GROUP BY
key: the ORDER BY of its collected let does not end in a declared unique key,
so rows that tie have no promised order.``). Beside a JOIN, a window or
QUALIFY, GROUP BY over a nested field, selecting it with GROUP BY or an
aggregate otherwise, and `select distinct` over it stay PIE-S2805. A later
table or query may select the nested field as it is (`n = parent.nested`)
beside a CROSS, INNER or LEFT JOIN or the Unnest of another collection;
selecting it beside a RIGHT or FULL JOIN, a window or QUALIFY, or in a
relation let is PIE-S2805. Selected without a JOIN and without DISTINCT, it
checks, but `emit-sql --project` reports it BLOCKED (PIE-B1003
`expression_evidence_unavailable`), whatever else the project reads.

**List operations of one row: `len`, `sum` and `any`.** An EXPLICIT_MODULES
project reads a row's collected field `c.xs` (a field that a `collect` SELECT
item outputs, read through the binding `c` of the FROM input) with three list
operations, each one value per row:

```pietto PIE-S2345 PIE-S2351 PIE-S2801 PIE-S2334 PIE-S2334 PIE-S2334 PIE-S2334
shape Order:
    id: Int
    customer_id: Int | None
    amount_cents: Int
    paid: Bool

shape Customer:
    id: Int
    name: Text

source orders: Order = postgres.table("shop.orders")

source customers: Customer = postgres.table("shop.customers")

query customer_orders:
    let customer_order_rows:
        capture customers
        from orders
        where orders.customer_id == customers.id
        select id, amount_cents, paid
        order by id
    from customers
    select id, name, order_list = collect customer_order_rows

query customer_order_stats:
    from customer_orders
    select:
        id
        order_count = len(customer_orders.order_list)
        paid_count = sum(1 for o in customer_orders.order_list if o.paid)
        total_cents = sum(o.amount_cents for o in customer_orders.order_list)
        paid_cents = sum(o.amount_cents for o in customer_orders.order_list if o.paid)
        has_paid = any(o.paid for o in customer_orders.order_list)
```

- `len(c.xs)` is the number of elements, an `Int`.
- `sum(o.f for o in c.xs)` adds the `Int` field `f` of each element, and
  `sum(o.f for o in c.xs if TEST)` of each element whose `TEST` is True;
  `sum(1 for o in c.xs if TEST)` counts the elements whose `TEST` is True.
  Each is an `Int`; a sum past 64 bits is an error, never a wrap.
- `any(TEST for o in c.xs)` is whether some element's `TEST` is True, a `Bool`.

`for o in c.xs` reads the elements of this row's own list: the body and the
`if` test read only fields of `o` (`o.paid`), each with the type and
nullability of the collected let's field, and literals. Any other name in
them, a field of the row itself included, is PIE-S2334 suggesting to read the
row's values outside the generator, and a query header parameter is
PIE-S2355 `Query parameters are not available in this position.` A single
name after `in` is a relation or `group` (generators in `any(...)` and
conditional aggregates), never a list: a `sum` generator over a name that is
no relation, `let` or `group` is PIE-S2301 ``Unknown or unavailable generator
source: xs; a row's collected list is read through its row: `for o in c.xs`
`` (in a grouped body, or one whose SELECT items are all aggregates, its hint
is ``for this group's rows write `for o in group` ``), and `len(xs)`
where `len(c.xs)` is admitted is PIE-S2334 at `xs` ``len reads a row's
collected list through its row; write `len(c.xs)` ``. A row whose list is
missing (None, after an outer JOIN) gives None for all three; `[]` gives
`0`, `0` and `False`; an element whose value or test is None adds no value
and no match, so a list of only None values sums to `0`. The results are
None exactly when the list may be missing. `len` of a `Text` keeps its
meaning.

The operations are written in a SELECT item, a row `let` or the WHERE of a
table or query without JOIN, GROUP BY, an aggregate, DISTINCT, a window or
QUALIFY, alone or inside a larger expression (`len(c.xs) + 1`). Anywhere
else (a JOIN query, a relation let, such a table or query, ORDER BY) the read
of `c.xs` is PIE-S2805 as before, now suggesting to read it in those places
and order or group by the output in a later table or query that reads it with
`from`. A JOIN query may select the list itself (`xs = p.xs`) for a later
query to read, and in an INNER, LEFT or CROSS JOIN query that could select it
the suggestion says so (``A table or query with a JOIN reads no list yet:
select the list as it is here, as in `xs = p.xs`, and read it with `len`,
`sum` or `any` in a later table or query that reads it with `from`.``); after
a LEFT JOIN a row without a match has no list. In the WHERE before a later
JOIN a list generator is the parser's PIE-P1000 (``A WHERE before a later JOIN
accepts only conjunctions of any(...) or not any(...); put ordinary row
filters after the JOINs.``). A list `any` reads only its own row's list and is
never a semi-join. `count(c.xs)` is PIE-S2805 suggesting `len(c.xs)`, and so
is `count(xs)` outside a JOIN query; the refused spellings are listed in
[the style page](style.md).

PostgreSQL emits list operations (`emit-sql --project`, `compile_query`,
bundles): `len` reads the list's count column, `sum` and `any` one scalar
subquery each over the element rows of the list's arrays (`ROWS FROM` of one
`pg_catalog.unnest` per child field); a list sum is cast to a checked
`bigint`. MySQL refuses the Collect read a list operation reads until Phase77
(PIE-B1003 `collect_not_admitted_on_target`). Single files, which have no
collected field, refuse a generator over `c.xs` with PIE-S2334 naming
`schema_version = 2`; a `schema_version = 1` project refuses every generator.

**The rows of each group.** To collect per group, group in another table
or query `g`, read it with `from g`, and collect a let that captures `g`,
reads the input that `g` groups and matches each group key with
`same_value`. Here `paid_orders` holds the rows that are counted, and both
`per_region` and the let read it:

```pietto PIE-S2345 PIE-S2351 PIE-S2801
shape Order:
    id: Int
    region: Text | None
    amount: Int
    paid: Bool

source orders: Order = postgres.table("orders")

query paid_orders:
    from orders
    where paid
    select id, region, amount

query per_region:
    from paid_orders
    group by region
    select region, n = count()

query region_orders:
    let members:
        capture per_region
        from paid_orders
        where same_value(paid_orders.region, per_region.region)
        select:
            id
            amount
        order by id
    from per_region
    select:
        region
        n
        items = collect members
```

The members of a group are the rows that the let's `where` matches.
`same_value` is True for two None keys, so a group whose key is None gets
its own rows, and each group's value has as many rows as its `count()`.
With `==`, which is never True for a None operand, the None group's value
is `[]` although its count is not 0. When the grouped query filters its
input before GROUP BY, as here, write the filter in a query of its own and
read that query in both places: a let that reads the unfiltered `orders`
lists every row whose key matches, also the rows the filter removed, so its
value can have more rows than the group's count. A `Float` key groups
`-0.0` and `0.0` together, as GROUP BY does, and each member keeps its own
value. A grouped query with an aggregate and no GROUP BY has one group and
no key: the let captures it and needs no `where`. A `Bool` key cannot be
matched yet: `check --project` accepts the let, but `emit-sql --project`
refuses a `Bool` `same_value`, as it refuses a `Bool` `==` (PIE-B1003
`comparison_type_pair_not_admitted`). A group key that is a nested field,
the output of a `collect`, cannot be matched in the let: the let's read of
it is PIE-S2805, as any read of a nested field in WHERE is. A Collect read
in the grouped query itself is PIE-S2803, and its JSON `suggestion` shows
this route.
On PostgreSQL, `emit-sql --project` writes the Collect read as described
below, with the let's `same_value` as `IS NOT DISTINCT FROM`; MySQL
reports PIE-B1003 for it, as for every Collect read.

An Unnest expands a nested field into rows: write `from p`, then
`let o = unnest(p.field)`, then exactly one `cross join o`,
`inner join o on o.total > 10` or `left join o on True`. A query
`let o = unnest(binding.field)` is an Unnest let when a later JOIN of the same
body names it, the body declares `o` only once and the module defines no
`def unnest`; any other `unnest(...)` call is an ordinary call, and
`any(... for x in o)` reads `o` as a relation. The argument is no expression:
`binding` is the FROM input or a CROSS, INNER or LEFT JOIN written before the
let, and `field` is a nested field that a `collect` SELECT item of its relation
outputs. After `let p = parent` and `from p`, write `unnest(p.nested)`, since
`parent` is no binding of the body. Another binding, a field of another type or
one of unknown type is PIE-S2806, and an unknown field PIE-S2102.

`o` has the fields of the collected let, with their types and nullability, and
`o.total` reads one after the JOIN, in `on`, `where`, the SELECT and
`order by`; name a field that `o` and another input both have with its binding,
such as `o.id` or `p.id`. For each row of the relation so far:

| Its nested value | `cross join o`, `inner join o on ...` | `left join o on ...` |
| --- | --- | --- |
| `[]` | no row | one row, every `o` field None |
| None (an outer JOIN found no row for it) | no row | one row |
| child rows, none of which match `on` | no row | one row |
| k child rows that match `on` | k rows | k rows |

`[]` is zero child rows, None is a missing container and `[{v: None}]` is one
real child row whose `v` is None: a LEFT JOIN's placeholder row is told apart by
the JOIN, never by its fields being None, and after a LEFT JOIN every `o` field
may be None. With `left join`, a condition in `on` keeps every row of the
relation; the same condition in `where` also removes the rows whose placeholder
fails it. The rows have no order, so order the query itself, and a key of the
relation is no longer unique once each of its rows may repeat per child. The
JOIN keeps the rules of any JOIN: a CROSS JOIN takes no `on`, every other kind
needs one (PIE-S2333 names the bindings its `on` would match), and a relation,
import or relation let that is also named `o` makes it `Ambiguous JOIN input: o`
(PIE-S2604), as for an alias let.

Before semantic analysis, PIE-S2807 refuses a RIGHT or FULL JOIN of an Unnest,
a second JOIN of it, any other read of `o` (`from o`, an earlier JOIN, `exists`,
`scalar`, `in`, `not in`, `collect o`, a set operand, `let x = o` or a capture
line), an Unnest in a relation let, and an Unnest beside GROUP BY, an
aggregate, `having`, a window, `qualify`, `select distinct`, `any(...)`, a
Collect read, another Unnest, or a RIGHT or FULL JOIN written before it that
may null-extend its binding, in the same table or query. Unnest in one table or
query, and read it with `from` in another that does the rest.

A project checks Collect reads and Unnest lets; `emit-sql --project` reports
PIE-B1003 for them until their lowering is admitted on the selected target.
Single files, LEGACY_FLAT projects and package modules refuse both spellings
with PIE-S2801, which says how to make a `schema_version = 2` project.

On PostgreSQL, `emit-sql --project` writes each Collect read of the selected
table or query as one LEFT JOIN LATERAL aggregate: a count column with the
field's label, then one array column per child field with the child's label, in
child order. An empty collection is a count of 0 with every array column NULL;
a child row whose fields are all None is a count of 1. A missing outer-JOIN
container has a NULL count and NULL arrays. Whole collections can pass through
named/imported producers, scalar projections and ordinary JOINs. PostgreSQL
admits one CROSS, INNER or LEFT Unnest, with Int, Bool, finite Text, finite Float,
Decimal, Date, Timestamp or UUID children; the final result can retain a sibling
collection. Grouped child producers, query parameters and scalar filters keep
that collection intact. A collection remains unavailable as a scalar operand
or ordering key. A nested GROUP BY key groups by its count column and every
array column (`GROUP BY "s"."c1", "s"."c1_0", ...`), and a nested DISTINCT
field is deduplicated the same way; PostgreSQL compares array elements with
each element type's equality, which is the `same_value` of the decoded
children. MySQL still reports PIE-B1003 for every Collect
and Unnest. The bounded execution domain is specified under
[bounded collections](execution.md#bounded-collect-and-unnest).

### Query header parameters in explicit-module projects

An EXPLICIT_MODULES project admits the header of an entry query whose own body
reads a relation with `from` (not a table function), with or without relation
lets, as long as no let reads a table function:

```pietto PIE-S2346 PIE-S2346
query orders_since(cutoff: Int, label: Text | None):
    from orders
    let next_day = cutoff + 1
    where order_day >= next_day and note == label
    select:
        id
        first_day = cutoff
```

Each parameter names exactly `Bool`, `Int`, `Float`, `Text`, `Date`,
`Timestamp` or `UUID`, or `Decimal(p, s)` with two integer literals
`1 <= p <= 65` and `0 <= s <= min(p, 30)` (the shared type-argument rule
within the Decimal scale PostgreSQL and MySQL producers admit), with `| None`
when its value may be None:

```pietto PIE-S2346 PIE-S2346 PIE-S2346 PIE-S2346
query recent(start: Timestamp, day: Date, floor: Decimal(9, 2), key: UUID | None):
    from orders
    where start <= placed_at and order_day == day and amount >= floor
    select:
        id
```

A query declares at most 64 (PIE-S2353): any other type, a type argument on
any type but `Decimal`, and a `Decimal` without its precision and scale or
outside those bounds are PIE-S2353 at the parameter, and a repeated name is
PIE-S2001. These declaration checks, the position checks below and the alias
check of an unaliased read run before semantic analysis: each file reports
them after its temporary diagnostics, and semantic analysis then does not
run. In that query's body a bare name equal to a parameter reads the
parameter. A parameter name that is also an input field (a typed VALUES
column of a FROM or JOIN input included), a `let` name, a relation name of the
module, a JOIN binding, a SELECT output or a named window is an error
(PIE-S2354), so a read never changes meaning; a SELECT item that only reads a
parameter needs its own alias. A read is typed as its declaration: a `Date`,
`Timestamp`, `UUID` or `Decimal(p, s)` parameter compares with a field of that
type, and a `Text` parameter is a `Text` operand that is not a literal, so
comparing it with a `Date`, `Timestamp`, `UUID`, `Bytes`, `Json` or enum field
is still PIE-S2105 (see Comparisons; declare the parameter with the field's
type instead).

Project SQL writes a `Decimal(p, s)`, `Date`, `Timestamp` or `UUID` read as a
placeholder in that carrier, `CAST($n AS pg_catalog.numeric(p,s))`,
`pg_catalog.date`, `pg_catalog.timestamp` or `pg_catalog.uuid`, with no binding
check of its own. The existing laws of each type apply unchanged: a `Decimal`
parameter compares only with a `Decimal` of the same precision and scale
(PIE-B1005 `decimal_comparison_parameter_conflict`) and, like any Decimal
that is not a source field, is no arithmetic operand (PIE-B1003
`decimal_direct_source_operands_required`); a `Timestamp` or `UUID` value
carries its meaning only from a source field, so selecting such a parameter
as an output emits, compiles, exports and binds, but `execute()` refuses it
when it prepares the result and `save()` when it describes the binding
(PIE-R1004 `QUERY_NOT_EXECUTABLE`, detail `MEANING_OUTPUT`). MySQL has no
carrier for these four types yet: emitting a query that declares one, read or
not, is BLOCKED with PIE-B1003 `query_parameter_type_not_admitted_on_target`
at each such declaration, until a later MySQL catch-up.

A read, or a `let` binding or output whose value reads one, is available
beneath unary, binary, comparison, null-test, BETWEEN, conditional,
literal-list `in` and `Float` conversion and the value arguments of `lower`,
`upper`, `trim`, `contains` (both), `starts_with`/`ends_with` (the text, not
the prefix or suffix), `coalesce` (all), `nullif` (both) and `sign`, in these
positions:

- `let` bindings, `where`, JOIN `on` and the SELECT items of a query without
  GROUP BY, HAVING or aggregates;
- `having` comparisons and `qualify`;
- ORDER BY keys that name a `let` binding or restate a selected expression
  (`order by id + cutoff` with `s = id + cutoff` selected); a restated key
  reuses that SELECT value, so a read in an ORDER key renders no placeholder
  of its own, and under `select distinct` a read counts as a constant leaf.
  Outside a grouped query project SQL does not yet emit a key that names a
  SELECT output (see Sources and relations);
- in a grouped query, a SELECT item that names a computed group key or applies
  `count`, `avg`, `min` or `max` to one `let` name, and an ORDER BY key that
  names an output;
- a GROUP BY key that names a computed `let` binding in a query without JOIN
  inputs (`let bucket = amount * weight` with `group by bucket`).

For example:

```pietto PIE-S2346 PIE-S2346
query weighted(weight: Int, bonus: Int | None):
    from orders
    let bucket = amount * weight
    let boosted = amount + bonus
    group by:
        bucket
    select:
        bucket
        n = count(boosted)
        mean = avg(boosted)
    having:
        n >= weight
    order by:
        n desc
```

A nullable parameter bound to NULL makes `boosted` NULL in every row, so `n` is
0 and `mean` is NULL. Every other position is refused (PIE-S2355), whether it
reads the parameter or a `let` binding or output that reads it: LIMIT, window
expressions and named windows (frame offsets included) except the window
arguments below, other call arguments (such as the bounds of `substr`, `len`,
`replace`, `matches` and the prefix of `starts_with`), a GROUP BY key that names
a parameter, an alias or a key of a JOIN query, other grouped SELECT items (a
direct read, `sum`, `count_distinct`, an aggregate of an expression or of a
parameter), a grouped ORDER BY key that is not an output name, and an ORDER BY
key that reads no field, binding or output. An output that reads a parameter
counts only in HAVING, QUALIFY, ORDER BY and LIMIT; elsewhere its name reads
the input field it may shadow. A position that a literal cannot use either keeps
the literal's diagnostic. A query with parameters is never the input of another
relation, a relation let or the body of a declaration with lets included, nor
read by `exists`, `scalar` or `in` (PIE-S2356). Headers stay PIE-S2346 in
single-file analysis, in LEGACY_FLAT projects, on a VALUES, set-operation or
table-function FROM body and beside a relation let whose FROM is a table
function, whether or not that let reads a parameter.

In a window call that is a SELECT item of a query without GROUP BY, HAVING
or aggregates, a bare read is also available as a window argument: the value
of `lag`, `lead`, `first_value`, `last_value` and `nth_value`, the default of
`lag`/`lead`, and a structural count — the `lag`/`lead` offset, the `ntile`
bucket count and the `nth_value` position:

```pietto PIE-S2346 PIE-S2346
query neighbours(step: Int, fill: Int):
    from orders
    select:
        id
        previous = lag(amount, step, fill) window(order by id)
        bucket = ntile(step) window(order by id)
```

A count parameter must be declared `Int`, not `Int | None` (PIE-S2358). A value
parameter must be `Int` or `Float` and a `lag`/`lead` default parameter `Int`:
`check` accepts the other tags, but `emit-sql` blocks a `Text` or `Bool` value
with PIE-B1003 `window_parameter_value_kind_not_realized_yet` and any other
default with PIE-B1003 `window_default_literal_kind_not_realized_yet`. A
`lag`/`lead` result with a parameter offset may be NULL, as for any nonzero
offset, even if the binding is 0. Any other window argument, window PARTITION BY and ORDER BY
keys, frame offsets and a read nested in an operator inside a window argument
stay refused (PIE-S2355).

The relation lets of an admitted entry query read its header as its own body does:

```pietto PIE-S2346 PIE-S2346 PIE-S2345
query recent_orders(cutoff: Int, label: Text | None):
    let recent:
        from orders
        let next_day = cutoff + 1
        where order_day >= next_day
        select:
            id
            day_after = order_day + 1
    from recent
    where id > cutoff
    select:
        id
        day_after
```

A bare name equal to a parameter reads it in every FROM-based let of the
query, under the same position rules, and a let's own `let` bindings and
outputs that read it are refused where the query's would be (PIE-S2355). The
name must also differ from every let name of the query and from every name
visible in each let's body: its input fields, `let` names, JOIN bindings,
outputs and named windows (PIE-S2354, at the parameter); a let's unaliased
SELECT item that only reads a parameter is PIE-S2354 at the read. A let column
computed from a parameter is an ordinary column for its readers. A let with
`capture` lines is such a let too: its reads render where the let renders,
inside the `exists`, `scalar` or `in` subquery that reads it (on PostgreSQL
also inside the ORDER BY/LIMIT wrapper of a `scalar` or `in` read) or inside
the LATERAL derived table of its CROSS, INNER or LEFT join, ORDER BY and LIMIT
included, and a read in that join's ON renders there. No other declaration
reads the header.

`emit-sql --project` renders every read outside an ORDER BY key as a typed
placeholder under both literal policies (`CAST($n AS pg_catalog.int8)`,
`CAST(? AS SIGNED)`, with the Text collation): PostgreSQL reuses one `$n` for
every read of a parameter, also across the CTE stages of its lets and inside
the subqueries and LATERAL derived tables of its lets with `capture` lines,
MySQL writes one `?` per read in rendering order, and bind-safe literal slots
share the same numbering. One statement renders at most 65,535 placeholders, every
read and every slot use counted, also under a larger declared
`resource_limits` value; more is refused (`PIE-B1007`,
`parameter_occurrence_limit`). The SQL never depends on a value. The unbound
template keeps each parameter's declared carrier; a check that needs the value,
such as the range of `cutoff + 1` or of a later `next_day + 1`, is listed as a
binding obligation naming every parameter it depends on (for a query with
relation lets, also every parameter that a let reads) and runs at every
binding. A query whose parameters are all unread still emits this template;
like any statement that renders no placeholder, it needs no `parameter_protocol`
premise. `compile_query` and `export_bundle` keep the unbound template, and
`execute(..., parameters=...)` binds it on every route; saving, relaying,
recovery and saved reads take the same `parameters` (see
[Parameters](execution.md#parameters)).

The result and post-aggregation positions add no other check: their
obligations are `int_range_representable` (the range of `cutoff + 1`) or
`text_result_width` (the width of `lower(label)`), listed at the operation
that needs it. A source Int proves over its whole physical carrier, so over a
BIGINT `amount` the obligation of `amount * weight` holds only for a weight of
0, 1 or NULL, and that of `amount + bonus` only for 0 or NULL. A HAVING or
QUALIFY read renders in the predicate over the aggregate or window stage, and a
group key or aggregate reads the LET column that holds the value.

A window value or Int default renders the same typed placeholder. A structural
count is int4 on PostgreSQL and renders `CAST(CAST($n AS pg_catalog.int8) AS
pg_catalog.int4)`. MySQL refuses `CAST(? AS SIGNED)` as a `lag`/`lead` offset
or an `ntile` bucket count, so every MySQL count, the `nth_value` position
included, renders a bare `?`. A count binding must lie in the target's
interval: an offset from 0 and a bucket count or position from 1, up to
2147483647 on PostgreSQL and 9223372036854775807 on MySQL (binding obligation
`structural_count_interval`), and a binding outside it is refused before
execution. A Bool or Text value argument and a non-Int default are refused at
emission (PIE-B1003), as the same default literals are.

## Expressions

Expressions include literals, names and dotted names, calls, parentheses,
unary `+`/`-`, arithmetic `+ - * / %`, comparisons, `like`/`not like`,
comparison chains, `is None`, `is not None`, `in`/`not in` literal lists, `not`, `and`,
`or`, the bounded `Float(value)` and `Text(value)` conversions, and the conditional `when_true if condition else
when_false`. The conditional binds loosest and nests to the right, so
`"a" if n > 1 else "b" if n > 0 else "c"` reads as `"a" if n > 1 else ("b" if
n > 0 else "c")`. There is no `case when ... end` form and no `||` operator;
both are syntax errors (PIE-P1000), and `+` does not join `Text` values
(PIE-S2105): write `concat(a, b)`. Numeric literals may contain separators such as `1_000` and `1_000.25_0`;
they retain the existing length and finite-value bounds. `lower <= value <= upper`
uses the existing inclusive-range semantics, including NULL bounds, and other
admitted comparison chains preserve source order. For a half-open range, such
as the timestamps of one month, write `start <= ts < stop`, which includes
`start` and excludes `stop`; it means `start <= ts and ts < stop`, and SQL
writes it so (`('2026-03-01 00:00:00' <= "seen_at") AND ("seen_at" <
'2026-04-01 00:00:00')`). A single-file expression nests at most 450 levels: each operator,
operand, call, cast or conditional on its deepest path counts one, so a chain
such as `a and b and c` or `x + y + z` nests one level per operand, and a `def`
call counts as its expansion (see [Inline functions](#inline-functions-def)). A
single file with a deeper expression anywhere, a relationship predicate, a
type `ensure` condition and a window frame offset included, fails `check`,
`emit-sql` and `explain` alike with PIE-S2006. A project is not held to that
bound (see Diagnostics, IR, SQL, and output).

A Text literal is written in double quotes, `"paid"`; single quotes, `'paid'`,
give the same value, and `pietto fmt` writes double quotes. In either form
`\"` is a double quote and `\'` a single quote, so `'it\'s'`, `"it\'s"` and
`"it's"` are one value, as are `'say "hi"'` and `"say \"hi\""`. `\\` is a
backslash and `\n`, `\r`, `\t`, `\b` and `\f` are a line feed, carriage
return, tab, backspace and form feed; any other escape is PIE-P1000, and a
string ends on its line.

Arithmetic (`+ - * / %` and unary `+`/`-`), `not`, `and`, `or`, comparisons,
`like`/`not like`, inclusive comparison chains, `in`, the arguments of the scalar functions
listed below, of the aggregates and of `lag`, `lead`, `first_value`,
`last_value` and `nth_value`, and a `where`, `having`, shape `check` or
index `when` condition read a type alias operand, argument or condition, an
alias chain included, as the builtin type it expands to. The result has that
base type, not the alias: with `type Age = Int`, `type Money =
Decimal(12, 2)` and `type Email = Text`, `age + 1`, `-age`
and `first_value(age)` are `Int`, `sum(amount)` and `max(amount)` over an
`amount: Money` field are a `Decimal`, `lower(email)` is a `Text` that
`count(lower(email))` accepts, and the SQL is that of the same program with
base-typed fields; with `type Flag = Bool`, `where flag` over a `flag:
Flag` field filters as a `Bool` field does. A pair the base type
refuses is refused alike, such as `amount * 2` or `-amount` (PIE-S2105),
`count` of an alias of `Any` is PIE-S2314 as `count` of `Any` is, and
`lower(amount)` is PIE-S2104, whose message names the type as written (`got
Money`). An alias of an enum or a shape is not expanded there, but it reads
as that enum or shape where operands need one type or family (a comparison,
inclusive comparison chains, an `in` list, `coalesce`, `nullif` and a conditional's branches),
and an alias of an enum as the enum for an aggregate argument too: with
`type Phase = Status`, `count` of a `Phase` field is PIE-S2314 as
`count` of a `Status` field is (`got Phase`), and a `Phase` field compares
with a `Status` field.

`/` follows SQL division. `Int / Int` is an `Int` truncated toward zero (`7 /
2` is `3`, `-7 / 2` is `-3`): PostgreSQL emits `a / b`, and MySQL, whose `/`
would return a DECIMAL, emits `a DIV b`. This holds for the `sum` of an `Int`
too, which PostgreSQL emits as a checked `int8` (see
[Aggregates and grouping](#aggregates-and-grouping)): `s / 2` with `s = 3` is
`1` on both targets. With a `Float` operand the result is a
`Float`, emitted as a bare `a / b` on both targets; Pietto never inserts a
cast. Because Python's `/` keeps the fraction, every `/` whose two operands are
`Int` (an alias of `Int` included) reports the warning PIE-S2106 in every check
mode, where it is written: once in a `def` body, not at its calls, and in a
`let` value, not where its name is read; it checks and emits as before. It is
reported in single files and LEGACY_FLAT projects. To keep the fraction of an
`Int` division, convert explicitly:

```pietto PIE-S2106
shape Order:
    id: Int
    amount: Int
    quantity: Int

source orders: Order = postgres.table("orders")

query rates:
    from orders
    select:
        whole = amount / quantity  # PIE-S2106 warning: truncates
        exact = amount * 1.0 / quantity
        approximate = Float(amount) / quantity
```

`amount * 1.0 / quantity` keeps the decimal digits the target computes
(PostgreSQL `numeric`, MySQL DECIMAL), and `Float(amount) / quantity`
divides binary floating-point values. Any other known operand type, such as
`Text`, `Bytes`, `Json`, `Any` or an enum, is PIE-S2105, as for `+`, `-` and
`*`. Division by zero follows the target: PostgreSQL
raises an error, while MySQL `/` and `DIV` return NULL. Single-file MySQL
`CONCAT` and `REPLACE` also return NULL for a result longer than
`max_allowed_packet`; Pietto still types them by their arguments. Dividing the smallest
`Int` by -1 overflows the signed 64-bit range; what each target does then is
not specified here. Division with a `Decimal` operand is not specified yet: it
has no result type and emits a bare `/`, so each target applies its own
numeric division. The quotient is still a number, as are arithmetic over it
and numbers, `abs` of it and a `coalesce`, `nullif` or conditional of such
numbers, where a `None` takes their type, also through a `let` name (a
column of another relation that holds one is of unknown type there), so a use
that takes no
number is refused as it is for an operand of each numeric type: with
`amount: Decimal(10, 2)` and `label: Text`,
`where amount / 2`, `where coalesce(amount / 2, 0)` and
`where coalesce(amount / 2, None)` are PIE-S2202; `amount / 2 + "x"`,
`amount / 2 == "x"`, `amount / 2 like "x%"`, `amount / 2 in ("x", "y")`,
`"a" <= amount / 2 <= "z"`, `not (amount / 2)` and
`label if amount > 1 else amount / 2` are PIE-S2105, as is
`abs(amount / 2) + "x"`; and `lower(amount / 2)`, `lower(abs(amount / 2))`,
`year(amount / 2)` (`got numeric`) and
`coalesce(label, amount / 2)` are PIE-S2104, in a single file and in an
EXPLICIT_MODULES relation (one with JOIN inputs may fail closed with
PIE-S2333 instead). Where a number fits, it is accepted beside numbers of any
type, so a single file accepts `amount / 2 > 1`, `amount / 2 + 1`,
`(amount / 2) % 2.5`, `amount / 2 in (1, 2.5)` and `abs(amount / 2)`. Beside
another operand of unknown type, other than such a `None`, arithmetic, a
comparison, `like`, inclusive comparison chains, `in`/`not in`, a conditional's branches,
`coalesce` and `nullif` do not check the quotient, as they do not check an
operand of any numeric type there; a parameter that takes no number refuses
it also beside an argument of unknown type. Semantic support is intentionally
narrower than parsing for some type/operator pairs; rejected pairs use diagnostics
rather than implicit conversions. A `None` operand of `+`, `-`, `*`, `/` or
`%`, also a `let` name bound to it, takes the other operand's type, which the
operator must accept: `n + None` is accepted, while `label + None` with a
`Text` field is PIE-S2105, as `label + label` is. The result, always null, has
the type that the operator gives two operands of that type, as its typed twin
does: with `Int` fields `n` and `f1`, `n + None` is an `Int` (so MySQL
divides `(n + None) / 2` with `DIV`), and `trim(None % f1)`,
`lower(None + n)`, `(None + n) == "x"` and `where None + n` are refused as
`trim(f1 % f1)` and the others are, while with a `Decimal` field `d`,
`None / d` is a number of unknown type, as `d / d` is. Beside numbers of
other types, such an always-null number takes the widest of their types
(`Int`, then `Decimal`, then `Float`), nullable, in `+`, `-`, `*`, `/`, `%`,
a sign, a conditional's branches, `in`, `coalesce` and `nullif`, as
PostgreSQL and MySQL convert `Int` to `Decimal` and either to `Float` where
they need one type: with a `Float` field `fl`, `(None + d) + 1.5` and
`(None + n) if b else 1.5` are a `Float`, `coalesce(None + d, n)` is a
`Decimal` and `sign(None + fl)` an `Int`, while `d + 1.5`,
`n if b else 1.5`, `coalesce(d, n)` and `sign(fl)` are refused. The remaining
operands that are not always null must satisfy `in` and `coalesce`'s original
type rule, so `coalesce(d, None + n, fl)` and `d in (fl, None + n)` are refused as
`coalesce(d, fl)` and `d in (fl, 1.5)` are. `%` takes no `Float`, which
PostgreSQL has no remainder for, so `(None + fl) % 2` is still PIE-S2105. A
nullable numeric `def` parameter also takes such a number of another numeric
type, and the call is typed with that number in place, as its SQL is: with
`def fn(x: Float | None) -> Float | None: return x`, `fn(None + n)` is an
`Int`, while `fn(n)` and, with a `Text | None` parameter, `tn(None + n)` are
PIE-S2395. This expression relaxation applies to single-file and project
checks alike. A `def` body, typed with its declared parameter types, must
still have its declared result type (PIE-S2402). A relation whose SELECT
output is such an always-null number completes in a project as in a single
file, so the relations that read it report their own errors.
SQL types an always-null number as Pietto does. Single-file SQL writes a
`None` operand of `+`, `-`, `*`, `/` or `%` as a NULL of the type it takes,
`CAST(NULL AS bigint)`, `numeric` or `double precision` on PostgreSQL and
`CAST(NULL AS SIGNED)`, `DECIMAL` or `DOUBLE` on MySQL (an untyped NULL is
`integer` in PostgreSQL's `NULL * 2`, `numeric` in `NULL - 3.0`, and
`DOUBLE` in MySQL's `n + NULL`), so MySQL divides `n / None` with `DIV`; and
it casts an always-null `Int` or `Decimal` operand of a `Float` result of
arithmetic, a conditional, `coalesce` or `nullif` to `double precision`
(MySQL `DOUBLE`), as `CAST((CAST(NULL AS numeric) + "d") AS double
precision) + 1.5` for `(None + d) + 1.5`, where SQL would otherwise keep the
decimal type of the literal `1.5`. An untyped NULL, as in `None + None`,
stays `NULL`. A `let` name bound to `None` is typed at each read as an
inline `None` there, so `amount + k` after `let k = None` writes
`"amount" + CAST(NULL AS bigint)`. Project SQL (`emit-sql --project`)
emits `Int` arithmetic with a `None` operand on both targets with the NULL
cast to the target's `Int` carrier, `("s0"."amount" + CAST(NULL AS
pg_catalog.int8))` on PostgreSQL and `` (`s0`.`amount` + CAST(NULL AS
SIGNED)) `` on MySQL; the column is in that carrier (`pg_int8`,
`my_signed_int`) and claims the single value 0 as its `int_range`, which
holds for no row, so a sign or arithmetic over it is held to no range of
the other operand. Other always-null numbers stay refused with the rule
they miss: `Float` arithmetic (`float_literal_operands_required`),
`Decimal` arithmetic (`decimal_direct_source_operands_required`), a
`coalesce` or conditional of numbers of different types
(`scalar_call_signature_not_admitted`, `conditional_realization_not_admitted`),
and arithmetic over a `let` name bound to `None`
(`expression_evidence_unavailable`).
PostgreSQL types no
arithmetic whose every operand is `None`, so single-file PostgreSQL emission
refuses `None + None` and `-None`, also as `coalesce(-None, n)` or as
`twice(None)` with `def twice(x: Int | None) -> Int | None: return x + x`
(PIE-B1000); MySQL emits them. PostgreSQL types a conditional, `coalesce` or
`nullif` whose every value is `None` as `text`, so single-file PostgreSQL
emission also refuses one (PIE-B1000) as an operand of an arithmetic, `and`,
`or`, `not` or sign operator, as a `where` condition or a conditional's
condition, as the argument of `abs`, `sign`, `year`, `month`, `day`, `hour`
or `minute`, such as `coalesce(None, None) + 1`, and beside an operand of a
known type that is not `Text`, an enum or `Any` in a comparison, inclusive comparison chains, an
`in` list, `coalesce`, `nullif` or a conditional's branches, such as
`coalesce(None, None) == 1` or `coalesce(None if b else None, n)` with an
`Int` field `n`; MySQL emits them too. As a conditional's branch, a
`coalesce` or `nullif` argument or an `in` operand, such a value takes the
type of the values of known type beside it, as `None` does, so the expression
around it is checked: with a `Text` field `t2`,
`(t2 if b else (None if b else None)) + 1` and
`coalesce(t2, coalesce(None, None)) == 1` are PIE-S2105, as
`(t2 if b else None) + 1` is, and so is `v + 1` in a relation that reads
`v = t2 if b else (None if b else None)`.

Comparisons and inclusive chains such as `lower <= value <= upper` require operands from one family: numeric (`Int`,
`Float`, `Decimal`), `Text`, `Bool`, temporal (`Date`, `Timestamp`), `UUID`,
`Bytes`, `Json`, one enum or one shape. A type alias operand is checked as the
type it expands to, an alias of an enum or a shape as that enum or shape.
Other known pairs, such as an `Int` field compared with `"x"`, a `Bool` field
compared with `1`, or an enum field compared with `1` or with a field of
another enum, report `PIE-S2105` in every check mode. Operands typed `Any`
are not checked. A `Text` literal, or a `let` name bound to
one, also compares with `Date`, `Timestamp`, `UUID`, `Bytes` and `Json`,
because a text literal is the only constant form for those types (whether it
is a valid constant of the type is not checked until typed constants are
decided), and an enum compares with a `Text` literal that is one of its
labels, such as `status == "active"` with `status: Status`. Any other `Text`
operand, such as a field or a call, is PIE-S2105 against those types and an
enum, and so is a `Text` literal that is not a label against an enum:
`born == name` with `born: Date` and `status == "gone"` are refused, as
PostgreSQL has no `date = text` operator and a PostgreSQL enum column rejects
a value that is not one of its labels.

An `in` or `not in` list tests `value == option` for each option, but its value
and options must have one type once aliases are expanded, except that `Decimal`
and `Int` mix as they do in a comparison: with `amount: Decimal(12, 2)` and `n: Int`, `amount in (1, 2)` and `n not in (amount, -3)`
check and emit as written (`"amount" IN (1, 2)` on PostgreSQL), and a `None`
option among them takes the `Decimal` type. A `Text` literal, or a `let` name
bound to one, takes the type of the first operand of an enum or of `Date`,
`Timestamp`, `UUID`, `Bytes` or `Json` where it compares with that operand
(see Comparisons): with `status: Status` of `enum Status: paid, shipped, open`,
`status in ("paid", "shipped")` and `born not in ("2020-01-01")` with a `Date`
field `born` check and emit as written (`"status" IN ('paid', 'shipped')`), and
`status in ("paid", "gone")` is PIE-S2105, as `status == "gone"` is.
Every other mix is PIE-S2105
(`expected same canonical membership operands`) even where the comparison is
accepted, such as `amount in (2.5)` or a `Float` field in `(1, 2)`. A `None`
option is typed only when the other operands have such a type. Otherwise the
list is PIE-S2105 when the value does not compare with another option (see
Comparisons), as `id in (1, "x", None)` with an `Int` field `id` is, and is
not refused for its types when it does, as `amount in (2.5, None)` is not. A
list with another operand of unknown type is not refused for its types. An
EXPLICIT_MODULES
project checks lists and `in` reads alike, and `emit-sql --project` and
`compile_query` then refuse a `Decimal` with an `Int` in a query they otherwise
emit with PIE-B1003 `membership_type_pair_not_admitted`, as they refuse
`amount == 1` with `comparison_type_pair_not_admitted`.

A comparison with `None` is never true: SQL evaluates `x = NULL`, `x <> NULL`
and the ordering comparisons to NULL for every `x`. A comparison (`==`, `!=`,
`<`, `<=`, `>`, `>=`) whose operand is the null literal, or a `let` name bound
to it, is therefore PIE-S2105; write `x is None` for `x == None` and `x is not None` for `x != None` (with both operands null the message suggests neither).
The same applies to an inclusive comparison chain whose value or both bounds are null and to an
`in`/`not in` list whose value or every option is null. An inclusive comparison chain with one
null bound (never true, but false when the other bound fails), an `in` list
with a null among other options (it can still match), a comparison with an
operand that may be NULL at run time, and calls such as `coalesce(x, None)`
stay accepted. Such an inclusive chain is still a `Bool` whose other bound must be
comparable with the value: `None <= n <= "z"` is PIE-S2105, and
`n if flag else None <= n <= 1` is PIE-S2105 for its branches of two
types, and such an `in` list still needs a value that compares with its other
options: `n in (1, "x", None)` is PIE-S2105.
A `None` option written in an `in` or `not in` list that is otherwise accepted
reports the warning PIE-S2107 in every check mode, because it never matches: a
Python reader expects `status in ("open", None)` to find a None status, which
SQL never does. Write `status == "open" or status is None`; a `None` option
makes `not in` never true, so write `status != "open" and status is not None`.
The warning is reported at the list, once, where it is written (also in a
`def` body), in single files and LEGACY_FLAT projects.
In an EXPLICIT_MODULES project the WHERE of a relation with a
`let` binding of unknown type, such as `nothing = None`, or with an error in
a binding is checked as well, as in a single file (a read of a binding with
an error of its own is of unknown type), so `where x == nothing` is PIE-S2105
there too, except in a `select distinct` relation or one with QUALIFY, which
reports PIE-S2333 at the relation, or the binding's own error, instead. In
`having:` a comparison
with the null literal is PIE-S2327 (`Unsupported having expression form:
null literal`) in single-file checks and EXPLICIT_MODULES projects alike, at
the literal; any other `having:` predicate of unknown
type in a project relation with JOIN inputs makes the relation fail closed
with PIE-S2333. Single-file `check` types an authored QUALIFY and its selected
or hidden windows (see [QUALIFY](#qualify)).

`same_value(a, b)` is NULL-safe equality: a `Bool` that is never `None`.
It is True when both operands are `None` or both are equal values, and False
when only one of them is `None`, as Python's `a == b` is for `None`; `a == b`
in Pietto follows SQL instead, and is unknown when either operand is NULL.
The two operands compare exactly as for `==`: the same type families, a
`Text` literal beside a `Date`, `Timestamp`, `UUID`, `Bytes` or `Json` value,
or an enum label beside an enum value, and the same refusals (PIE-S2104
`Invalid argument types for function same_value: expected comparable
operands`). A `None` operand, also a `let` name bound to it or a `def`
argument that is one (reported at the `def` call), is refused with
``Invalid argument type for function same_value at position N: expected a
non-None value, got None; write `x is None` instead``: write `x is None` to
test for `None`.

```pietto
shape Member:
    id: Int
    ref: Text | None

shape Visit:
    id: Int
    member_ref: Text | None
    note: Text | None
    code: Text | None

source members: Member = postgres.table("members")

source visits: Visit = postgres.table("visits")

query matched_visits:
    from visits
    let m = members
    left join m on same_value(m.ref, visits.member_ref)
    where not same_value(visits.note, visits.code)
    select:
        visit_id = visits.id
        same_ref = same_value(visits.member_ref, m.ref)
```

PostgreSQL writes `(a IS NOT DISTINCT FROM b)` and MySQL `(a <=> b)`.
On MySQL a `Text` comparison follows the target's binary collation premise
`utf8mb4_0900_bin`; under another collation `'a'` and `'A'` would be the same
value. A JOIN `on` with `same_value` matches no key: NULL keys match each
other, so a unique key that admits `None` may match many rows, and an
aggregate over that JOIN is refused as for any other `on` that matches no key
of its target (PIE-S2381). Nor does `same_value` count as a WHERE test that
drops a LEFT JOIN's unmatched rows (PIE-S2383): it is True for an unmatched
row whose other operand is `None`.

In an EXPLICIT_MODULES project, `emit-sql --project` admits `same_value`
wherever it admits a built-in call: a select item, WHERE and `let` of one
relation, and a select item after a JOIN, over the operand pairs that `==`
admits there. It refuses `Bool` operands, as it refuses a `Bool` `==`. It
emits a `Float` `same_value` exactly where it emits a `Float` `==`: on
PostgreSQL, and on MySQL only beside an operand that reads no row, such as
`same_value(ratio, 1.5)`, written with `<=>`; a MySQL `same_value` of two
row `Float` operands is PIE-B1003 `comparison_type_pair_not_admitted`, as
their `==` is. On MySQL, a
`same_value` value that is a GROUP BY key (`let k = same_value(a, b)`,
`group by k`) or a SELECT DISTINCT column, also when that value is read
through a `let` name, a named relation (`from t0`, also after a JOIN or
`union all`) or another module, is PIE-B1003
`scalar_call_signature_not_admitted` at the call, which is then in the
upstream relation, possibly in another file; it is reported before the
relation's aggregate blockers. A set operation's own deduplication
(`union distinct`, `intersect distinct`, `except distinct` over such a
column) is not refused; it was not run on a database. MySQL returns
`<=>` grouped or deduplicated as a 4-byte `INT`, not the declared
`my_signed_bool`. PostgreSQL emits both. A JOIN `on` or a
WHERE after a JOIN admits no built-in call yet, so there `same_value` is
PIE-B1003, as `contains` is: in a JOIN `on` with
`match_condition_not_in_row_domain` beside
`scalar_projection_requires_later_slice` and
`join_shape_not_admitted_in_slice7`, and in a WHERE after a JOIN with
`scalar_projection_requires_later_slice` and
`join_shape_not_admitted_in_slice7`. A query
header parameter is not yet a `same_value` operand: `where same_value(a, k)`
is PIE-S2355 (`Query parameters are not available in this position`), while
`where a == k` is admitted. A `having` condition admits no function call, so
`having same_value(c, 3)` is PIE-S2327 (`Unsupported having expression form:
function call`) in single files and projects alike, as any call there is.
Beside an untyped all-`None` value, as in `same_value(coalesce(None, None),
a)` or `same_value(n, a)` after `let n = coalesce(None, None)`, a project
relation without a JOIN input of its own completes as in a single file, its
output a never-`None` `Bool`, with a PIE-S2385 warning at that output;
project SQL refuses it (PIE-B1003 `expression_evidence_unavailable`), as it
refuses `coalesce(None, None) == a`. With a JOIN input of its own, the direct
form completes without the warning and is refused the same way, and the
`let` form still fails with the bare PIE-S2333, where a single file accepts
it.

`max(a, b)` and `min(a, b)` are the larger and the smaller of two values, as
Python's two-argument `max` and `min` are: the first value on a tie (as for
Python, which matters only for `Float` and `Decimal` values that are `==` but
written differently, such as `-0.0` and `0.0`), and `None` when either value is
`None`, where Python raises. They are checked and emitted as the conditional
`(b if a < b else a) if b is not None else b` (`>` for `min`), without the
`is not None` test when `b` is a literal, so SQL gets `CASE WHEN` and never
`GREATEST`/`LEAST`, which skip a NULL on PostgreSQL. The two values must
compare as for `<` and have one canonical type, as `coalesce`'s values and a
conditional's branches do (PIE-S2104 `Invalid argument types for function
max: expected same canonical comparable type`): `Int`, `Decimal`, `Float`,
`Text`, `Date`, `Timestamp`, `UUID` or `Bool` values of one type in a single
file, so `max(n, 1.5)` with an `Int` field is refused where
`max(Float(n), 1.5)` is not; a `None` argument, also a `let` name bound to it,
is refused (PIE-S2104 `Invalid argument type for function max at position 2:
expected a non-None value, got None`). The result is nullable when either
value is. They work in WHERE, inside larger expressions and in a `def` body; a
`None` that a def call passes to such a body is refused at the def call with
the same message. One argument is the aggregate `max(x)`/`min(x)`, unchanged.
For more values nest the calls, `max(a, max(b, c))`; each call writes its
values out again in its conditional, so a nest is bounded as a `def`'s
expansion is (PIE-S2399, more than 1000 expression nodes): five fields nested
in the second position, or seven in the first, fit. Three or more arguments
are PIE-S2309 with the nesting hint, and `greatest`/`least` are unknown
functions (PIE-S2103) whose hint names `max` and `min`. A file that declares a
`constraint`, `derive` or relationship template named `max` or `min` keeps the
two-argument call's earlier meaning (the aggregate's arity error, PIE-S2309);
a `def` of either name stays PIE-S2398. On MySQL, which has no boolean
type, the larger or smaller of two `Bool` values arrives as an integer column
holding 0, 1 or NULL, as every computed `Bool` (such as `a < b`) does there.

```pietto
shape Reading:
    id: Int
    low: Int
    high: Int | None
    label: Text
    taken: Timestamp
    checked: Timestamp | None

source readings: Reading = postgres.table("readings")

query bounded:
    from readings
    where max(low, high) > 10
    select:
        id
        top = max(low, high)
        floor = max(low, 0)
        first = min(label, "m")
        latest = max(taken, checked)
```

`top` is `Int | None` (None where `high` is); `floor` is an `Int`; `latest` is
a `Timestamp | None`.

The closed scalar surface has explicit signatures, and no argument is
converted to fit one, except for the always-null numeric D-12 rule described
above:

```text
lower(Text) -> Text
upper(Text) -> Text
trim(Text) -> Text
len(Text) -> Int
matches(Text, Text) -> Bool
substr(Text, Int, Int) -> Text
replace(Text, Text, Text) -> Text
lpad(Text, Int, Text) -> Text
concat(Text, Text, ...) -> Text
contains(Text, Text) -> Bool
starts_with(Text, Text) -> Bool
ends_with(Text, Text) -> Bool
coalesce(T, T, ...) -> T
nullif(T, T) -> T
same_value(T, T) -> Bool
abs(Int) -> Int
abs(Float) -> Float
abs(Decimal) -> Decimal
sign(Int | Decimal) -> Int
year(Date | Timestamp) -> Int
month(Date | Timestamp) -> Int
day(Date | Timestamp) -> Int
hour(Timestamp) -> Int
minute(Timestamp) -> Int
date_of(Timestamp) -> Date
add_months(Date, Int) -> Date
```

`sign` returns -1, 0 or 1 as an `Int`. D-12 also admits an always-null Float
numeric expression such as `sign(None + fl)`, which is a
nullable `Int`. PostgreSQL `sign` itself returns
`double precision` for an integer argument and `numeric` for a numeric one, so
PostgreSQL SQL casts the result: single-file `emit-sql` renders
`CAST(sign(x) AS bigint)` and project SQL `CAST(sign(x) AS pg_catalog.int8)`.
MySQL `SIGN` already returns an integer; single-file MySQL SQL renders
`SIGN(x)` and project SQL `CAST(SIGN(x) AS SIGNED)`.

`abs` picks its line by the argument's type and keeps the argument's
nullability; a `None` argument is read as a `Decimal`, an argument of unknown
type, such as a field of a source without a shape, makes it a number of
unknown type, as a quotient with a `Decimal` operand is (see above), so
`abs(t) * 2` and `abs(t) % 2` pass `check` there while `lower(abs(t))` is
PIE-S2104 (`got numeric`), and any other type, such as `Text`, is PIE-S2104
(`expected Int, Float or Decimal`). It emits
`abs(x)` on PostgreSQL and `ABS(x)` on MySQL, which return the argument's
type. Project SQL (`emit-sql --project`) proves an `Int` result as it proves
unary `-` (see Aggregates and grouping).

`concat` joins two or more `Text` values in order; an alias of `Text` is a
`Text` there, also one imported from another module. It is `None` when any
argument is `None`, so it is `Text | None` when an argument may be `None`, and
a `None` argument is read as a `Text`, as for `lower`. One argument (or none)
is PIE-S2104 (`Invalid arguments for function concat: expected at least 2,
got 1`), and a known argument of another type is PIE-S2104 at its position
(`Invalid argument type for function concat at position 2: expected Text,
got Int`, and `got numeric` for a number of unknown type such as
`amount / 2`); write `Text(n)` for an `Int`. Pietto has no `||` operator (its
parser hint reads ``Write `concat(a, b)` to join Text, or `or` for a
condition.``), and `+` does not join Text: `label + label` stays PIE-S2105,
whose message ends ``use `concat(...)` to join Text values`` beside a `Text`,
the null literal or a number of unknown type, ``use `concat(...)` with
`Text(n)` to join Text values`` beside an `Int`, and at `expected numeric
operands` beside a value of another type. `CONCAT(...)` and other spellings
are PIE-S2103 with the hint ``write `concat(...)` in lowercase``. None of
these hints applies where `concat` names a callable of the program's own (see
the constructor paragraph).

PostgreSQL SQL, in single files and projects, renders `(a || b || c)`, not
PostgreSQL `concat()`, which skips NULL arguments; in a single file an
argument whose type is not known to be `Text`, such as a field of a source
without a shape, is rendered `CAST(x AS text)`, since `||` of a `jsonb`, an
array or a `bytea` value is no text concatenation. Single-file MySQL SQL
renders `CONCAT(a, b, c)`. PostgreSQL project SQL (`emit-sql --project`)
gives the result the arguments' one Text profile and a width of the sum of
their widths (a `None` argument adds none); it refuses `concat` of only
`None` values (PIE-B1003 `scalar_call_signature_not_admitted`) and of a
`Text` whose width each binding fixes (PIE-B1004
`text_concat_result_bound_missing`). MySQL project emission refuses `concat`
(PIE-B1003 `scalar_call_signature_not_admitted`, at the `let`, clause or
select item that holds the call, also through a `def` body), as it refuses
`round` and `date_trunc`: MySQL types a `CONCAT` result from its arguments'
storage lengths and counts the literal anchors project SQL writes by their
UTF-8 bytes, so the result type would not be the declared width. A query
header parameter read in a `concat` argument is PIE-S2355, as for `replace`.
Single-file `explain` types each `concat`; `explain --project` keeps its
scope (an explicit-module project is `config_schema`, and a package-root
explain does not type expressions).

`lpad(s, width, fill)` pads `s` on the left with `fill` until it has `width`
characters, and never shortens it: a `s` of `width` characters or more, and
any `s` beside a width of 0 or less, is `s` itself, as Python's
`s.rjust(width, fill)` gives, where SQL `LPAD` cuts a longer value (and MySQL
`LPAD` gives NULL for a negative width). `fill` is one character written in
the call as a `Text` literal, such as `"0"` or `" "`; there is no default. It
is `None` when `s` or `width` is `None`, so it is `Text | None` when either may
be `None`, and a `None` `s` is read as a `Text`. A call with two arguments is
PIE-S2104 `Invalid arguments for function lpad: expected 3, got 2; fill must be
a one-character Text literal, such as "0"`, and a fill that is not a
one-character `Text` literal written in the call (a field, a `let` name,
`None`, `""`, `"00"`) is PIE-S2104 `Invalid arguments for function lpad: fill
must be a one-character Text literal, such as "0"`. An unknown `rjust` call, in
any letter case, and Python's method form `code.rjust(5, "0")` are PIE-S2103
with the hint ``write `lpad(s, width, fill)`, which pads like Python
`str.rjust` and never truncates``.

PostgreSQL SQL is `CASE WHEN length(s) >= width THEN s ELSE lpad(s, CAST(width
AS integer), 'f') END` (project SQL: `(CASE WHEN length(s) >= width THEN s ELSE
lpad(s, CAST(width AS pg_catalog.int4), 'f') END)`), and single-file MySQL SQL
is `CASE WHEN CHAR_LENGTH(s) >= width THEN s ELSE LPAD(s, width, 'f') END`; `s`
and `width` are written more than once. In a single file, PostgreSQL
emission refuses a width written as an integer literal outside the signed
32-bit range, also under unary signs or read through a `let:` name, as it
refuses such a `substr` index (PostgreSQL folds the cast when it plans the
statement and fails where Python would give `s` for a negative width), and
`check` warns PIE-S2385 `this lpad width is outside PostgreSQL's 32-bit
integer range`; another width outside that range may raise a PostgreSQL
error, never another value. A CASE, `coalesce` or `nullif` of only `None`
values as the width, or as an `add_months` argument, is PIE-S2385
`PostgreSQL types a CASE, coalesce or nullif of only None values as text,
which function lpad does not take` (`... add_months does not take`), and
PostgreSQL emission refuses it.
PostgreSQL project SQL gives the result the text's profile and a width of the
larger of the text's width and the width's upper bound; it refuses a width
whose proven range leaves the signed 32-bit range, such as an `Int` field
stored as `bigint` (PIE-B1002 `lpad_width_outside_physical_range`), a text or
width with no proven bound, a `None` width included (PIE-B1004 `lpad_result_bound_missing`), and a
`None` text (PIE-B1003 `scalar_call_signature_not_admitted`). MySQL project
SQL refuses `lpad` (PIE-B1003 `scalar_call_signature_not_admitted`).

`add_months(d, n)` moves the `Date` `d` by `n` whole months, back for a
negative `n`. When the day does not exist in the month reached, it is that
month's last day, and a last day does not stay one: `add_months(d, 1)` is
2024-02-29 for 2024-01-31 and 2024-03-29 for 2024-02-29. It is `None` when `d`
or `n` is `None`; a `None` `d` is read as a `Date`. It takes only a `Date`: a
`Timestamp` is PIE-S2104 `Invalid argument type for function add_months at
position 1: expected Date, got Timestamp; add_months takes a Date, such as
add_months(date_of(ts), n)`. PostgreSQL SQL is `CAST((d +
make_interval(months => CAST(n AS integer))) AS date)` (project SQL: `CAST(n AS
pg_catalog.int4)`), and single-file MySQL SQL is `DATE_ADD(d, INTERVAL n
MONTH)`; PostgreSQL raises an error for an `n` outside the signed 32-bit range,
a number of months far past any date. A result after 9999-12-31 is outside
Pietto's dates: PostgreSQL gives a later date, MySQL NULL. PostgreSQL project
SQL keeps the `Date` carrier and refuses a `None` argument (PIE-B1003); MySQL
project SQL refuses `add_months` (PIE-B1003 `scalar_call_signature_not_admitted`).

A `def lpad` or `def add_months` is PIE-S2398 with a suggestion to rename it
(see the def section), and a `constraint` or `derive` of either name no longer
makes a call of that name PIE-S2103: the call means the built-in.

`now()` takes no argument and is a `Timestamp` that is never None: the start
of the running SQL statement in UTC, without a time zone, with microseconds.
All `now()` reads of one statement are one value, whichever rows and clauses
read it; each new execution of the SQL reads a new value. The session time
zone does not change it: PostgreSQL SQL converts the statement start to UTC
itself (`statement_timestamp() AT TIME ZONE 'UTC'`, not PostgreSQL `now()`,
which is the transaction start), so SQL that `emit-sql` prints gives the UTC
value in any session, and Pietto's own PostgreSQL and MySQL connections run
in UTC anyway (`timezone=UTC`, `time_zone='+00:00'`). `date_of(now())` is the
UTC date. A column that stores local time differs from `now()` by the local
offset. MySQL emission refuses `now()` for now: single-file SQL with PIE-B1000
(`Unsupported MySQL function call: now`), project SQL with PIE-B1003
`scalar_call_signature_not_admitted`.

`now()` is evaluated when the SQL runs, never when Pietto checks, emits,
explains, compiles or loads it: emitted SQL, compiled bundles and golden
fixtures hold the expression, never a value. A saved result keeps the values
of the run that saved it, so a replay or a verified export shows those values
and does not read `now()` again. `relay_live` (PIE-R1004
`STATEMENT_SNAPSHOT_ENTRY`) and R2 `save_recoverable`/`recover` (PIE-R1004
`PUBLIC_R2_STATEMENT_SNAPSHOT`) refuse a query that reads `now()`, before
any workspace or sink work, because a resumed attempt would read another
statement's value.

`now()` is admitted only in a SELECT item, outside a window, and in a WHERE
(PIE-S2387 elsewhere, with a specific hint for a GROUP BY key, an ORDER BY
key, a JOIN `on` and a field `derive`). A `let` or SELECT item that a GROUP BY
or ORDER BY of its own body names is that key, so `select: t = now()` with
`order by t` is refused like `order by now()`. The refusal reads where the
call is written: a `let` that only another `let` reads gets the generic text
even when that other `let` is a GROUP BY key, and a key that reads a column
another relation selected from `now()` (`table b: from a` / `group by t`) is
accepted, as a column whose value is the same in every row. Pietto has no
column default; a field `derive`, the per-row stored value, refuses `now()`,
and a window function's default argument (`lag(x, 1, now())`) is a window
argument, which gets the generic refusal. A `def` body cannot read `now()`,
but a `def` call can take it as an argument in those positions: the parameter
written twice is still one value. A call with arguments, `now(x)`, is not the
builtin: it is a file's own `relationship now(row: Row)` (which keeps its
meaning in every position) or PIE-S2104. A top-level constant's value cannot
be `now()` (PIE-S2387, the generic text).

In a single file the existing SELECT limits stand: a grouped query cannot
select a computed expression, so `t = now()` beside `group by k` is PIE-S2319
(`Grouped scalar projection expressions are not supported yet`), and an
aggregate takes a direct field, so `max(now())` is PIE-S2315.

`coalesce` requires at least two same-canonical-type arguments. D-12 permits
an always-null numeric argument of another numeric type;
the remaining operands still follow this rule, and the result uses the widest
numeric type as described above. Beside an argument of unknown type its
arguments of known type must still compare with each other (see Comparisons),
as SQL has no common type for them otherwise:
over a source without a shape `coalesce(t, 1, "x")` is PIE-S2104, while
`coalesce(t, 1, 2.5)` is not refused.
`nullif` requires exactly two. `substr` is one-based and requires a
statically admitted positive start and nonnegative count, each an `Int`
literal written in the call (a `let` name bound to one is PIE-S2104 too,
also in a `def` argument).
PostgreSQL additionally requires each
static `substr` index to fit its signed `int32` argument range. An unshadowed
`Float(value)` and `Text(value)` are scalar conversions: each accepts `Int` after alias
expansion and preserves the operand's nullability. `Float` may lose binary64
precision; `Text` produces the Int's exact signed-decimal text. A known operand
of another type, including `Float`, and the null literal are PIE-S2105. An
operand of unknown type stays unknown; an error in that operand is reported
without an additional conversion error. An unsupported `Float` conversion
reports `Invalid cast from SOURCE to Float: only Int-to-Float conversion is
supported; write Float(expression)`; an unsupported `Text` conversion reports
the corresponding Int-to-Text and `Text(expression)` wording. No other
primitive conversion is introduced. A constructor call with other than one
argument is PIE-S2104 (`Invalid arguments for constructor Float: expected 1,
got N` or `Invalid arguments for constructor Text: expected 1, got N`). A local
`def Float`, `def Text` or `def concat` takes precedence regardless of its
declaration order or arity; a same-named `constraint`, `derive` or
relationship template also keeps its existing meaning, in the file's queries
and in its `def` bodies alike. In such a file a `concat` call that no
relationship call binds is PIE-S2103 with its earlier message: ``Unknown
function: concat; concat is a derive, which cannot be called; write a `def`
instead`` beside a `derive` (`concat is a constraint` beside a
`constraint`), and `Unknown function: concat; string concatenation is not
supported yet` beside a relationship template. In a schema_version = 1
project, whose files are one namespace, such a callable of any file keeps
that meaning in all its files. There, and in a file that declares such a
callable, the `||`, `+` and `CONCAT(...)` messages keep their earlier text,
which does not point to `concat(...)`: ``String concatenation with `||` is
not supported yet.``, `+` of a `Text` ending `expected numeric operands;
string concatenation is not supported yet` beside any operand, and
`CONCAT(...)` with the hint `string concatenation is not supported yet`. A
callable that only another module declares leaves the builtin in place, as it
leaves `Float`. Qualified calls are not constructors.

PostgreSQL supports `round(value[, digits])` and `date_trunc(unit, value)` in
both single-file and project SQL emission. Single-file MySQL emission supports
them too; MySQL project emission refuses these shapes unless an equivalent form
is proved. `round` accepts a Decimal value and an optional
static Int `digits` from -30 through 30 after `let` expansion. A Float value is
accepted only with integer rounding. A tie rounds half away from zero, for a
Float and a Decimal alike, as PostgreSQL rounds a `numeric`: `round(2.5)` is 3
and `round(-2.5)` is -3. This differs from Python, whose `round` takes a tie
to the even neighbour: `round(2.5) == 2`, also for a `Decimal` under the
default context.
`date_trunc` accepts `year`, `month`, or `day` for Date values, and additionally
`hour` or `minute` for Timestamp values. These calls preserve the operand's
nullability.
MySQL's ROUND of a DOUBLE follows the C library and may round a tie to even,
so single-file MySQL SQL rounds a Float as PostgreSQL SQL does, from its
integer part: `CASE WHEN ABS(x - TRUNCATE(x, 0)) >= 0.5 THEN TRUNCATE(x, 0) +
CASE WHEN x < 0 THEN -1.0 ELSE 1.0 END ELSE TRUNCATE(x, 0) END`, which is
exact. Both targets must round the same value, so it refuses (PIE-B1000) a
Float `+`, `-`, `*` or `/` without a DOUBLE operand anywhere in the argument.
A DOUBLE is a Float column, an Int-to-Float cast, an `avg` of an Int,
`percent_rank`, `cume_dist`, or a value computed from one, such as `ratio * 2`.
PostgreSQL computes other Float arithmetic exactly as `numeric`, and MySQL as
a DECIMAL with a smaller division scale, or as a DOUBLE beside an exponent
literal: with an Int `amount` of 0, `round(amount + 0.5 - 0.00000000000000001)`
is 0 on PostgreSQL, and MySQL, which reads `1e-17` as a DOUBLE, would get 1.
It also refuses a read of a Float relation output, such as a CTE column,
unless that output is such a DOUBLE: PostgreSQL holds
`v = 0.5 - 0.00000000000000001` as `numeric`. MySQL has no `date_trunc`;
single-file MySQL SQL builds the start of the unit from the
value's parts. For a Date `x` it writes
`DATE_SUB(x, INTERVAL (DAYOFYEAR(x) - 1) DAY)` for a year,
`DATE_SUB(x, INTERVAL (DAYOFMONTH(x) - 1) DAY)` for a month and `x` for a day.
For a Timestamp `x` it writes the same year or month form over `DATE(x)`, or
`DATE(x)` for a day, inside `TIMESTAMP(...)`, and
`TIMESTAMP(DATE(x), MAKETIME(HOUR(x), 0, 0))` for an hour or
`TIMESTAMP(DATE(x), MAKETIME(HOUR(x), MINUTE(x), 0))` for a minute. Every
lower part is zero, as PostgreSQL `date_trunc` on a timestamp without time
zone gives, also in a year below 100, which MySQL's `MAKEDATE` would read as
two digits. It assumes a Date is a valid calendar date, without
MySQL's zero day or month. Each unit but `day` writes `x` more than once, so
MySQL refuses (PIE-B1000) such a `date_trunc` whose value holds another
`date_trunc`, whose SQL would grow exponentially with nesting.
`in`/`not in`, `not`,
conditional expressions, `like`/`not like` with `ESCAPE '!'`, and inclusive comparison chains
retain their ordinary SQL NULL behavior. In a single file, a nonempty `not in` list
without a `None` option whose value reads a field whose type is `| None`, directly or
through arithmetic, is a PIE-S2384 warning in every check mode, as it is never True
when that value is None while Python's `None not in (...)` is: write
`status not in ("closed",) or status is None` to accept None, or
`status is not None and status not in ("closed",)` to reject it, and either
test silences the warning, as a top-level `where status is not None` does for
every clause of the relation. In a pattern `!` escapes the next
character, so `!!` matches a literal `!`; a literal pattern, or a `let` name
bound to one, that ends in an unpaired `!` is PIE-S2105. `matches` remains
outside the selected
project SQL scalar subset.

A condition must be a `Bool`: a `where`, `having`, shape `check` or index
`when` condition (PIE-S2202), an operand of `and`, `or` or `not`, and the
condition of a conditional (PIE-S2105). An operand of `and` or `or`, or the
condition of a conditional, of a known type that is not `Bool` is refused also
beside an operand or branch of unknown type that reported no error of its own
and reads no `let` binding with one. A call of one of the functions above but
`coalesce` and `nullif` has the result type its signature gives it (a number
for `abs`) also beside an argument of unknown type, as the call has that type
or fails wherever it runs, and each of its arguments of known type is checked
against the signature. So over a source without a shape `where len(t)`,
`where lower(t)` and `where abs(t)` are PIE-S2202, `not lower(t)`, `t and 5`
(also as the lines `t` and `5` of a `where:` block) and `1 if len(t) else 2`
are PIE-S2105, also through a `let` name bound to such a call, `lower(t) + 1`
is PIE-S2105, `where len(t) + 1` PIE-S2202 and `matches(t, 1)` PIE-S2104, and
`len(t) / 2` is an `Int` division (MySQL `DIV`), while `where t`,
`where coalesce(t, u)`, `where contains(t, "x")` and `year(t) + 1` pass. A call
whose always-null argument, or `Decimal` quotient, leaves its type unknown has
its result type as well: `where lower(coalesce(None, None))` is PIE-S2202 in a
single file and in an EXPLICIT_MODULES relation, with or without JOIN inputs,
and with a `Decimal` field `d`, `sign(d / 2) / 2` is an `Int` division. Over a
source without a shape a `count()` output, and a `count` or `count_distinct`
output whose argument reads a field, is an `Int` to `having`, so with
`c = count()` or
`c = count(t)`, `having c` is PIE-S2202 and `having c and m > 1`
PIE-S2105. These are types that the checks read inside the relation: over
such a row `explain` shows the type of an output of a relation with GROUP BY,
such as `Int` for `c = count(t)` and `len(max(t))`, while every output of a
relation without GROUP BY, also `z = 1`, is of unknown type there, and the
outputs of either are of unknown type to a relation that reads it. An unknown
type that an error of its own explains, or one of a `let` binding it reads,
reports nothing more, and neither does a call whose
argument reads such a binding or a name whose error is reported where it is
bound, such as a forward reference to a later `let` binding.

Selected project SQL admits this closed Q1 surface only when every operand has
an established carrier. A conditional emits `CASE WHEN condition THEN
when_true ELSE when_false END`: NULL conditions take the else branch, and the
two value branches require the same canonical type and physical realization.
For `--literal-policy bind-safe`, its parameter uses follow that rendered order
(condition, true branch, false branch), not source-tree operand storage order;
the SQL bytes must be consumed with the artifact's `fixed_values` and
`parameter_uses`. A computed relation `order by` uses an established selected
expression from the current result scope, retains its authored direction and
the target's NULL/collation behavior, and rejects hidden-input reuse or an
arbitrary alias fallback.

Single-file `emit-sql` renders `year(x)` as PostgreSQL
`CAST(EXTRACT(YEAR FROM x) AS bigint)` and MySQL `YEAR(x)`, and `month`,
`day`, `hour` and `minute` alike. PostgreSQL resolves no `EXTRACT` of an
untyped NULL, so for a `None` argument, also a `let` name bound to `None` or
a `def` argument that is `None`, the PostgreSQL SQL is `CAST(NULL AS bigint)`.

Selected project SQL carries `year`, `month`, `day`, `hour`, and `minute` from
an exactly qualified `Timestamp` source: timezone-free proleptic Gregorian
microseconds over the stated civil interval and PostgreSQL
`timestamp without time zone(6)` or MySQL `DATETIME(6)`. Their results are
physical signed integers with ranges `1000..9999`, `1..12`, `1..31`, `0..23`,
and `0..59`, respectively. `date_of` admits that exact Timestamp carrier and
preserves NULL as a derived Gregorian Date in `1000-01-01..9999-12-31`, emitted
as PostgreSQL `DATE` or MySQL `DATE`; `year`, `month`, and `day` also accept
that derived Date. A `Date` source field requires PostgreSQL `date` or MySQL
`DATE` over the same civil interval without a time zone, as its source's
`row_domain_matches` premise declares, and is carried and compared as the
paragraph on Timestamp and UUID source meaning below describes. Date has no
literal, parsing, arithmetic, or timezone surface. There is no arbitrary Python
evaluation, user code execution, or general cast language.

## Inline functions (`def`)

A `def` names a reusable scalar expression with typed parameters. Pietto checks
it once where it is declared. Before any call site is checked, it replaces every
call with the def's body and puts each argument in place of its parameter. It
never creates a database function: a call emits exactly the SQL of the same
expression written out by hand.

```pietto
shape Order:
    id: Int
    email: Text | None
    coupon_code: Text | None
    ordered_at: Timestamp

source orders: Order = postgres.table("shop.orders")

def reachable(email: Text | None, coupon: Text | None) -> Bool | None: return email like "%@%" and coupon is None

def in_2026(ts: Timestamp) -> Bool | None:
    return "2026-01-01 00:00:00" <= ts <= "2026-12-31 23:59:59"

table reachable_2026:
    from orders
    where:
        in_2026(ordered_at)
        reachable(email, coupon_code)
    select:
        id
```

`emit-sql --dialect postgres` writes the same WHERE as the hand-written
`("2026-01-01 00:00:00" <= ordered_at <= "2026-12-31 23:59:59") and
(email like "%@%" and coupon_code is None)`:

```sql
WHERE ("ordered_at" BETWEEN '2026-01-01 00:00:00' AND '2026-12-31 23:59:59') AND (("email" LIKE '%@%' ESCAPE '!') AND ("coupon_code" IS NULL))
```

- Where: single files and EXPLICIT_MODULES projects (schema version 2). In a
  project, a module may export a def (`export def pos`) and another may import
  it (`from "models/a.pietto" import def pos`, or `def pos as p`), in either
  list form; a re-export chains as any other. A def that is not exported stays
  a private helper of its module; calling it, or an exported def that is not
  imported, from another module is PIE-S2103 with the export and import to
  write. Naming the def under another kind, as in `export table f`, is
  PIE-S2704 (PIE-S2705 for an `import` item). The def's body and signature
  are checked once, in its module, where an alias in the signature is read as
  the type it expands to there; a call is inlined, and checked, at the call,
  as a call of a local def is, so the SQL is the same as the local def's; a
  `concat` call in its body stays the built-in also in an importer that
  declares a callable `concat`. A def import binding that collides with a
  local declaration (a def or relationship included) or another import
  binding is PIE-S2706 (`; import def pos as <name>`); a module's own def
  collides only with a def or relationship import. A def import binding named
  like a built-in
  function, `Float`, `Text` or `concat` included, is PIE-S2398. A def import
  item that fails, or a def import along an import cycle (PIE-S2703), stops
  the check before semantic analysis, as a def error does. `def *` and a
  `constraint` or `derive` item are PIE-P1000. A LEGACY_FLAT project check
  refuses every def with PIE-S2379, and a PACKAGE_ROOT package module refuses
  each def or relationship item with PIE-S2707. PACKAGE_ROOT
  `explain --project` does not check defs, so a package module with a def can
  be explained; that does not make the def available.
- Signature: each parameter and the result have exactly one of the types
  `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp` or `UUID`,
  without type arguments, bare when the value is never None and with
  `| None` when it may be None. A type alias declared in the same
  file is read as the type it expands to, as an operator reads one, when its
  chain of aliases ends at one of these types and no alias in the chain has
  type arguments or an `ensure`; its nullability is the one written in
  the signature. Any other alias (such as one imported into a module, or an
  alias of an enum), an enum, `Any`, `Bytes`, `Json`, type arguments or a
  shape (a row type rather than a scalar def parameter) is PIE-S2397. Arguments are
  positional only.
- Body: one `return` expression, on the `def` line or in an indented block. It
  reads only its parameters and may use literals, operators, the built-in
  scalar functions and other defs. Every parameter must be used (PIE-S2397).
  An aggregate or a qualified name is PIE-S2397, and a `window` call cannot be
  written there (PIE-P1000). An `exists`, `scalar` or relation `in` read is
  PIE-S2348 to PIE-S2350. Any other name is PIE-S2102. A parameter may share
  the name of a function: `def f(upper: Text) -> Text:
  return upper(upper)` calls `upper` on its argument. A `constraint` or
  `derive` cannot be called from a body or anywhere else (PIE-S2103).
- Result: the body is typed with the declared parameter types, so a `Text`
  parameter is a `Text` operand that is not a literal: a body that compares
  it with a `Date`, `Timestamp` or `UUID` parameter, such as `return d > s`
  with `d: Date | None` and `s: Text | None`, is PIE-S2105 at the def,
  also when no call passes it a value or every call passes a literal, and a
  `Date`, `Timestamp` or `UUID` parameter takes no `Text` literal argument
  (PIE-S2395), so no def parameter stands for a constant of those types; the
  body can compare with one written as a literal (`return d > "2020-01-01"`).
  Its type must be the declared result type, and a result without `| None`
  needs a body that the checker proves non-null (PIE-S2402). A body is proven
  non-null when every value it reads is non-null, except through `/`, `%`,
  `and`, `or`, `nullif` or `matches`: in a body a comparison, an inclusive chain or
  `+`, `-` or `*` of non-null
  operands is non-null, so `def lt(a: Int, b: Int) -> Bool:
  return a < b` is accepted, and so are bodies such as `not lt(x,
  1)` and `abs(a - b)` over non-null parameters, while MySQL `/` and `%` give
  NULL for a zero divisor. `is None`, `coalesce` with a non-null argument and
  a conditional with non-null branches are non-null whatever else they read.
  An argument of a def call fits its parameter as it does outside a body,
  every part of it typed as there, where a comparison, an inclusive chain or
  arithmetic keeps its unknown nullability: neither `y + 1` nor `abs(y + 1)`
  fits a parameter without `| None`, also in a body, so `return lt(y + 1, 2)` and
  `return lt(abs(y + 1), 2)` are PIE-S2395 (see Calls below). An argument
  that fits is then read as any other value: with `def idn(x: Int | None)
  -> Int | None: return x`, `return idn(a + b)` over non-null `a` and `b`
  is non-null. A body that is always null
  (the same forms as for arguments below, such as `x + None`) fits only a
  `| None` result, of its type where it has one (`x + None` with an `Int`
  parameter `x` is an `Int`), and a body whose type the checker cannot
  determine, such as `-None if x > 0 else x`, fits none (PIE-S2402), while
  `coalesce(None, None) if x > 0 else x` has the type of `x`, as
  `None if x > 0 else x` does.
- Names: defs share the callable namespace with `constraint` and `derive` (a
  repeated name or parameter is PIE-S2001). A def cannot take the name of a
  built-in scalar, aggregate or window function or of `generate_series`
  (PIE-S2398). Fields, lets and relations are values, not functions, so a def
  may share their names.
- Recursion: a def that calls itself, directly or through other defs, is
  PIE-S2396, wherever in the body the call is written (also in a refused
  position such as a type argument). It is reported at the first def of the
  cycle, and the message names the cycle (`f -> g -> f`).
- Calls: a call passes exactly one argument per parameter (PIE-S2395). Each
  argument's type, after alias expansion, must be the parameter type, with no
  conversion (an `Int` value does not fit a `Decimal` parameter). An
  always-null numeric argument also fits a nullable numeric parameter of
  another numeric type, while retaining its own type, in a project as in a
  single file (`fn(None + amount)` for `def fn(x: Float | None)`), and project
  SQL writes the inlined argument as above; it does not fit a Text or
  non-null parameter. An argument
  that is nullable, or whose nullability is unknown, does not fit a parameter
  without `| None`; `id + 1` is such an argument even when `id` is never None.
  An argument that is always null (`None`; a sign, `not`, arithmetic or
  comparison with an always-null operand, such as `id + None`; or a
  `coalesce` or conditional of such values) fits only a nullable
  parameter, and its type is still checked when it has one: `id + None` is
  an `Int` and a comparison such as `id == (id + None)` is `Bool`. A def
  argument is checked as it is
  written into SQL, with each `let` name replaced by its value: the type,
  nullability and errors of the value written there by hand decide whether
  it fits. With `k = None`, `j = coalesce(k, n)` and `m = id + None`, the
  arguments `k`, `k + 1` and `m` are null, and `lower(k)` and `j` are
  `Text | None` and `Int | None`, as `lower(None)` and
  `coalesce(None, n)` are. Over a source without a shape a `let` value has
  the type it has written there: with `u = True` or `u = a is None`, the
  argument `u` is a `Bool` that is never None, while `u = coalesce(a, 1)`
  stays unknown, as the field `a` is. A `let` name whose binding has an error of its own is
  not replaced, so that its error stands alone; nor is one that is an
  unknown field where it is read, as in a grouped select item (PIE-S2102);
  and one that an aggregate argument reads is checked with its binding's
  type, and is null where its value written in is null. These are
  PIE-S2395 at the call, also when the call is in a def
  body, reported once however many times the body uses the argument and
  only for the innermost call that does not fit: an argument that does not
  fit is unknown to every expression around it, also through a built-in call
  such as `len`, and to an aggregate whose argument it is or is part of, also
  as the value of a `let` name the aggregate reads, which adds no
  PIE-S2315 beside it when it accepts the argument's form for some argument
  type, as for a field of unknown type: `count(nn(n + 1))` is PIE-S2395
  alone, also through a `let` name the aggregate reads, with `w = n + 1` or
  `j = n` and `w = j + 1`, and so are `count(nn(n + 1) + 1)` and `count(w)`
  with `w = nn(n + 1)`. A form the aggregate accepts for no argument type
  is PIE-S2315 too: `count(nn(upper(text)))` is PIE-S2395 and PIE-S2315, as
  `count(upper(text))` is PIE-S2315, also through a `let` name the
  aggregate reads, with `w = upper(text)` or a constant such as `w = 1.5`,
  and `min(nn(n) + 1)` is both, as `min(n + 1)` is PIE-S2315.
  A null argument is no exception: `sum(nn(None))` is PIE-S2395 and
  PIE-S2315, as `nn(None)` outside an aggregate is PIE-S2395, and so is
  `sum(nn(k))` with `k = None`, while `count(nn(n + None))` is PIE-S2395
  alone, also as `count(nn(w))` with `w = n + None`. A
  select output that is a field or `let` name passed to a def it does not
  fit, a group key included, has no type, as a computed output with an
  error has; in a project its relation then fails with that error, and a
  relation that reads it follows that error and reports nothing of its own.
  An argument with an
  error of its own that leaves its type unknown, such as a comparison with
  the null literal (`text == None`, PIE-S2105) or `k + zz` with an unknown
  field `zz`, is not checked against its parameter. A `let` value is typed
  as it is written wherever it is read (see Relations), so a value that is
  ill-typed once the null it reads takes its type reports its errors in its
  binding, at their own positions, whether a def argument, another
  expression or nothing reads it, and an argument that reads it is checked
  against its parameter when the value still has a type: with
  `i = upper(k) + 1`, the binding `i` is PIE-S2105, as `upper(None) + 1`
  is, and with `d = len(j) + len(j)`, the binding `d` is two PIE-S2104, one
  at each `len`, as the value written by hand is. The argument `lower(j)` is
  PIE-S2104 at `lower`; `lower(j) == "a"` passed to a `Bool`
  parameter is that PIE-S2104 and PIE-S2395, as the comparison is still
  `Bool` of unknown nullability; and with `w = lower(j) is None`, the
  binding `w` is PIE-S2104 and, in a single file, `w` passed to an
  `Int` parameter is PIE-S2395, as `w` is a `Bool` that is never None (a project
  check does not check an argument that reads a binding with an error of its
  own). An argument whose type is unknown for another reason is not checked
  either, as the same expression written
  by hand is not: a field of a source without a shape; `None` inside `and` or
  `or`, such as `None and True`; or an always-null value other than `None`
  that has no type, such as `-None` or `None + None` (while `id + None` is
  an `Int`), inside `coalesce`, `nullif`, a conditional or an `in` list, as
  in `coalesce(-None, n)`, except a conditional, `coalesce` or `nullif` whose
  every value is `None`, which takes the type beside it there as `None` does
  (see Expressions): `coalesce(None if b else None, n)` is checked as
  `coalesce(None, n)` is. A built-in call whose signature fixes its result type
  has that type whatever the types of its arguments are, unless an
  argument's own error, or a `let` binding's, explains them (see
  Expressions), so its type is
  checked: over a source without a shape `len(t)` passed to a
  `Text | None` parameter is PIE-S2395. Its nullability then follows from
  an argument of unknown type and is not checked, as that argument's is not:
  `lower(t)` and `year(None)` pass a parameter without `| None` as `t` does,
  also through an operator, a conditional or a `let` name, as in `len(t) + 1` or
  `k` with `k = lower(t)`. A comparison with null is never true
  wherever the expansion puts it:
  `low(None)` with `def low(x: Int | None) -> Bool | None: return x < 3`
  is PIE-S2105 at the call, as `None < 3` is by hand, unless the null
  argument (also a `let` name bound to `None`) does not fit its parameter,
  which is then the one error. An argument cannot use the legacy whole-relation
  reads (`exists`, `scalar` or relation `in`) yet (PIE-S2395). A checked ANY
  expression is instead an ordinary Bool scalar argument; each repeated or
  discarded occurrence retains its own scope and validation obligations.
- Positions: a call is refused (PIE-S2397), in a def body as anywhere else,
  where the written form must be a literal, a field or a window call that
  Pietto checks by a rule of its own: inside a window computation (a window
  function's arguments, PARTITION BY, ORDER BY, frame or a named window), as
  a table function or in its input, LIMIT, a VALUES row, a source connector,
  a type argument, and the ORDER BY of a grouped relation; the message names
  the innermost such position. A window
  call may itself be an argument, as in a
  QUALIFY `top(row_number() window(order by id))`. Anywhere else the argument's type
  and nullability are checked wherever the expansion is typed. These
  positions are not typed today, so the type and nullability of an argument
  there are checked no more than the same expression written by hand (the
  argument count, relation-read and position rules above still apply): a type
  or field `ensure`;
  in a project check, the ungrouped `order by` of a relation without JOIN inputs
  that is not `select distinct` (`emit-sql --project` blocks a mismatched
  argument there with PIE-B1003 without naming it; with JOIN inputs or
  `select distinct` the argument is checked).
  In a project, a mismatch is reported where the same error written by hand
  would be: where a project reports the errors of a position as PIE-S2333 at
  the relation, such as a grouped `having` or an aggregate argument
  without JOIN inputs (whose own aggregate and grouping errors it reports as
  a single file does), a select over a VALUES let, the ORDER BY of a
  global-aggregate query or the WHERE of a `select distinct` relation or one
  with QUALIFY that has a `let` binding of unknown type, such as `k = None`,
  the mismatch is PIE-S2333 there too, also for a `let` name that an
  aggregate reads, which is checked with its binding's type.
- Expansion: each call becomes one parenthesized expression. An argument that
  the body uses n times is written n times in the SQL, as it would be by hand:
  with `def twice(x: Int | None) -> Int | None: return x + x`, the item
  `d = twice(id + 1)` emits `("id" + 1) + ("id" + 1) AS "d"`. No Pietto
  function is volatile (there is no `now`, `random` or UUID generator; such
  calls are PIE-S2103), and an aggregate argument gives one value per group,
  so the results do not change. Every inlined node keeps a real location:
  the body is at the call, and each use of an argument is at the argument's
  own text. An error inside an argument (other than a PIE-S2395 mismatch,
  which is at the call) is therefore reported at the argument, and an error
  that the body makes with its arguments at the call. A call is written once,
  so each such error is reported once, however many times the body uses the
  argument and however many body nodes make it: `low(None)` with
  `def low(x: Int | None) -> Bool | None: return x < 3 or x < 4` is one
  PIE-S2105 at the call, also when the call is itself an argument. This holds
  in a single-file check and in a project check, a JOIN ON condition and a
  query header parameter read in a position that refuses it (PIE-S2355)
  included. A def body is checked at the def before any call, and there a
  single-file check reports an error in a call as often as its expansion
  makes it, except an argument mismatch (PIE-S2395), which is reported once
  as at any call (with `def dup(x: Int) -> Int: return coalesce(x, x)`, a
  body `dup(True)` is one PIE-S2395), and an error in an operand that a
  comparison chain copies, including an error anywhere in that operand's
  text, which is reported once; for example, `x` in `0 < x < 10` is copied.
  The value of an inclusive chain `lower <= value <= upper` is not itself
  copied, so its error is reported as often as the expansion makes it unless
  the error lies in copied operand text, either around that chain or nested in
  its value.
  An explicit-module project check reports a diagnostic equal to an earlier
  one once, at its first position, so it reports each such error once. With
  its arguments, one expansion has at most 1000 expression nodes and 64
  levels of nesting (PIE-S2399); every expression counts, also those in a
  window call's arguments and specification and in a cast's type arguments.
  A single file counts the 450 levels of an expression (PIE-S2006, see
  Expressions) with every call in it replaced by its expansion, so a call
  nested 400 levels deep whose body nests 60 levels makes the expression 459
  levels deep.
- Reporting: an error in a def itself (PIE-S2001 for a def, PIE-S2396 to
  PIE-S2399, PIE-S2402, or any error in its body, such as a PIE-S2395
  mismatch or a PIE-S2105 of a call written there), a wrong argument count or
  a relation-read argument stops the check of the file before semantic
  analysis, so other semantic errors appear once these are fixed. In a
  project these are reported with the file's parse and pre-admission
  diagnostics, take the place of its capture and header checks, and no
  project semantic analysis runs. Type and nullability mismatches of
  arguments (PIE-S2395) at a call outside a def body are reported during
  semantic analysis with the other errors. A problem that only the position
  of a call can cause, such as a form that `having` does not support, is
  reported at the call.
- `explain` does not list defs. Their effect is part of the expressions they
  were inlined into, and lineage locates each use of an argument at the
  argument.

## Aggregates and grouping

The current aggregate family is:

```text
count count_distinct sum avg min max stddev variance pvariance pstdev median quantile string_agg first last
```

`string_agg(value, delimiter, order by key[, key ...])` accepts two Text row
expressions and at least one internal order key. It preserves every key,
direction, duplicate and tie exactly as written; it adds no tie-breaker and is
not a window aggregate. PostgreSQL emits it; MySQL refuses it rather than use
a truncating session-dependent aggregate. Over a source without a shape it is
still an aggregate projection: beside another projection, a window included,
without GROUP BY it is PIE-S2312, as `max` is, and `emit-sql` refuses it with
PIE-B1000 there, as it refuses every aggregate over such a source (see below).

`count()` lowers to `COUNT(*)`; supported `count(field)` forms count non-null
field values. `count` of a `Bool` field counts its False values too; to count
the True ones write `sum(1 for o in group if o.paid)` (PIE-S2388 warns). The selected project numeric boundary admits Int unary `+`/`-`,
`abs` and binary `+`, `-`, `*` only when the compiler can propagate a signed
range that fits a signed 64-bit integer, or, on PostgreSQL, a `bigint` range
that leaves signed 64 bits but meets them. The result keeps its operands' own
integer type where the range fits it; on PostgreSQL an operation on `int2` or
`int4` operands whose range leaves that type is computed in `bigint`, its first
operand written `CAST(x AS pg_catalog.int8)`, and MySQL computes every Int
operation in signed 64 bits. On PostgreSQL an operation on `bigint` operands
whose range may leave signed 64 bits, such as `qty + 1` over a `bigint` field,
is emitted unchanged: PostgreSQL's `bigint` operators are checked, so a value
outside signed 64 bits is never returned wrapped; the statement may fail at
run time with SQLSTATE 22003 (`bigint out of range`) instead, and whether and
when it fails depends on the execution plan. The result's range is the part
of the exact range inside signed 64 bits. PostgreSQL may also raise the error
while it plans the statement, wherever it reduces such an operation's
operands to constants, as in `(9223372036854775807 if True else 0) + 1` or
`coalesce(9223372036854775807, id) + 1`, or through a bound slot or parameter
value: the statement then fails even over no rows, or with the operation in a
branch no row takes. A range wholly outside signed 64 bits, as that of a
constant such as `9223372036854775807 + 1`, stays PIE-B1002, as such an
operation could only fail, and MySQL keeps PIE-B1002 for any result not
proved to fit signed 64 bits. `abs` of an `Int` is proved as
unary `-` is and fits exactly where `-` fits: where `-id` is PIE-B1002
(`unary_result_outside_physical_range`), as over a MySQL `BIGINT` field,
`abs(id)` is PIE-B1002 (`abs_result_outside_physical_range`), though unlike
`-` it reads no query header parameter (PIE-S2355); `abs` of a `Float` or
`Decimal` keeps its argument's carrier. It also admits `avg(Int)` for a direct
Int input with `int_range` evidence, casting that input to the target Float
carrier before aggregation. Empty and all-NULL inputs remain NULL. PostgreSQL
single-file and project SQL emission emit `sum(Int)` as
`CAST(SUM(CAST(x AS pg_catalog.int8)) AS pg_catalog.int8)`: the
sum accumulates exactly and its result is a nullable `Int` over the whole
signed 64-bit range, and a sum outside that range is the run-time error
SQLSTATE 22003, never a wrong value, by the same rule. Project SQL on MySQL reports
`sum(Int)` BLOCKED with `PIE-B1004` (`sum_int_aggregate_range_proof_missing`),
as `CAST(DECIMAL AS SIGNED)` would clamp an out-of-range sum, although
`check --project` accepts it and single-file MySQL `emit-sql` emits `SUM`; Decimal
`sum`/`avg` require
an exact aggregate range/scale and division proof (a Decimal sum has no
bounded precision and a Decimal average no fixed scale, so no `Decimal(p, s)`
carrier holds the result: `decimal_aggregate_range_proof_missing`), and on
MySQL Float `sum`/`avg` require a finite-result proof. PostgreSQL project SQL
emits `sum` and `avg` of a finite `Float` as the single-file `SUM(x)` and
`AVG(x)` with the R13 evidence `target_checked_binary64_overflow`: the target
raises SQLSTATE 22003 instead of returning an infinite value (`avg` also where
its running sum of squares overflows, about |x| > 1e154). Project SQL on both
targets also emits `count` and `count_distinct` of a `Text`, `Bool`, `Float`
or `Decimal` value and `min` and `max` of a `Float` or `Decimal` value, under
the GROUP BY key law (`-0.0` and `0.0` are one distinct value; an extreme of
equal values may be either member), except `count_distinct` of a `Float` on
MySQL, which stays BLOCKED (PIE-B1003
`count_distinct_argument_outside_reviewed_int_domain`): MySQL kept `-0.0` and
`0.0` apart in deduplication beside a wide key. These
wider argument types are for grouped and whole-relation aggregates; an
aggregate over a window keeps the `Int` domain (PIE-B1003 or PIE-B1004). A
source range, free JSON declaration, renderer
spelling, or database default rounding rule is not such proof. `min` and `max`
retain their bounded direct-field surface; in EXPLICIT_MODULES projects they
also accept one row `let` name, and the result keeps that value's proven range
while admitting NULL. With JOIN inputs the argument reads the exact JOIN-side
fields of that value; `min` and `max` need no fan-out proof, over a field or a
value that reads no joined field, such as `level = 3` or a header parameter. In a single
file `min` and `max` accept no `let` name. Over an input row of known shape,
the argument of a `min` or `max` that is a whole aliased SELECT item and reads
a `let` name is never accepted, even where the argument with each name's
value written in place is: `max(w)` is PIE-S2315 with `w = 3`, as `max(3)`
is, and also with `w = n` for a field `n`, `w = f(n)` for a `def` that returns
its argument, or `w = z` for a field `z` of unknown type (such as `z = None`
in the relation it reads), although `max(n)`, `max(f(n))` and `max(z)` are
accepted. Beside PIE-S2315 the argument reports the errors of its bindings and
the other errors of the argument written in place, such as PIE-S2395 for a
`def` argument that does not fit (`max(f(w))` with `w = status` reports both,
although `max(f(status))` is PIE-S2395 alone). With each name's value written
in place, an argument of a known type that `min` or `max` refuses is PIE-S2314
instead (`max(w)` with `w = status`, as `max(status)`), and one whose value
reads an unknown name, a binding that reads itself or a name that PIE-S2329
refused reports only the errors of those bindings (PIE-S2102, PIE-S2330,
PIE-S2329), as `max(nosuch)` does. Over an input row of unknown shape, such as
a source without a shape or a relation that reads one, a local `let` name is
not an input field in this argument: `max(w)` with `w = 3` reports PIE-S2102
`Unknown field: w`, as `min(v)` with `v = x` reports it for `v`. A direct input
field such as `max(x)` still passes `check` there, and `emit-sql` refuses it
with PIE-B1000.
`count_distinct` includes direct fields and the bounded Text lower/trim chain.
Literal-only and arbitrary expression widening remain fail closed unless a
current retained contract says otherwise.

`count_distinct(a, b, ...)` with two or more arguments counts the distinct
tuples of its arguments among the rows in which none of them is None, as
`count_distinct(x)` does not count None (pandas
`DataFrame.value_counts(dropna=True)`, MySQL `COUNT(DISTINCT a, b)`; polars
`n_unique` would count null as a value). It is an `Int`, never None, and 0
when no row has every field. Each argument is a different direct field, or a
`let:` name of one, of a type that `count_distinct(x)` takes (`Bool`, `Int`,
`Float`, `Decimal`, `Text`, `Date`, `Timestamp`, `UUID`); fields may come from
different JOIN inputs, and no fan-out proof is needed, as a repeated row only
repeats a tuple already counted. Two tuples are the same when each field is
`count_distinct(x)`'s same value: `-0.0` and `0.0` are one value, `Decimal`
`1.0` and `1.00` one value, and Text compares under the target's equality
(PostgreSQL `COLLATE "C"`, MySQL `utf8mb4_0900_bin`, both NO PAD). The
refusals are reported at the argument: a field written twice (also through a
`let:` name of it, or once bare and once qualified by its binding,
`count_distinct(pot, sales.pot)`) is PIE-S2104 ``Invalid arguments for
aggregate count_distinct: a is written twice; write `count_distinct(a)` ``,
an argument that is not a direct field (`count_distinct(lower(a), b)`, a
computed `let:`, `None`) is PIE-S2315, and a type `count_distinct(x)` refuses
(an enum) is PIE-S2314. `count_distinct()` is PIE-S2309 `... expects at least
1 argument, got 0`. To count distinct computed values, compute them in one
query and count them in a query that reads it (`let` is not enough: a
computed `let:` is an expression argument).

PostgreSQL emits it as one anonymous record:
`COUNT(DISTINCT CASE WHEN "a" IS NOT NULL AND "b" IS NOT NULL THEN ROW("a", "b") END)`,
in a single file and in a `schema_version = 2` project (each field under the
R13 law of `count_distinct(x)`: on PostgreSQL also `Text`, `Bool`, `Float`
and `Decimal` fields under the GROUP BY key law), also over JOIN rows.
Without the `CASE`, `COUNT(DISTINCT (a, b))` would count a row such as
`(NULL, 'x')`, which MySQL skips. Single-file MySQL emits MySQL's own
`COUNT(DISTINCT a, b)`, which skips a row in which any field is NULL and
counts `-0.0` and `0.0` as one value, as a two-database differential
measured; a MySQL project refuses it with PIE-B1003
`count_distinct_tuple_not_admitted_on_target`. A `schema_version = 1` project
refuses it with PIE-S2334 (``count_distinct(a, b, ...): a schema_version = 1
project has no count_distinct of several columns in the current syntax; set
schema_version = 2 to check it.``). It is no window aggregate (PIE-S2103
``Aggregate window functions are not implemented: count_distinct; ...``,
unchanged).

`nunique(x)` and `n_unique(x)`, in any letter case, are PIE-S2103 with the
hint ``write `count_distinct(x)`, which does not count None (polars
`n_unique` counts null as a value; pandas `nunique()` skips it by default);
for several columns `count_distinct(a, b)` ``, also as the JSON
`suggestion`. `count(distinct a, b)` keeps PIE-P1000; its hint reads ``Write
`count_distinct(x)` for COUNT(DISTINCT x), or `count_distinct(x, y)` for
several columns.`` `count_distinct((a, b))` and `len(set((o.a, o.b) for o in
group))` keep PIE-P1000 at the comma, with the hint ``Write
`count_distinct(a, b)` for the distinct combinations of several columns.``;
an unknown `set` call (any case) keeps PIE-S2103 and adds ``; write
`count_distinct(a, b)` for the number of distinct combinations of several
columns, `count_distinct(x)` for one``, also as the JSON `suggestion`.

In project SQL an admitted expression argument (`sum(qty * 2)`,
`count(lower(label))`) is emitted inside the aggregate by the same rules as a
`let`: it is admitted exactly where `let t = qty * 2` with `sum(t)` is, and
refused with the same blocker where that `let` is (for example `%` is
`binary_operator_not_admitted`, Float arithmetic over a field on MySQL
`float_literal_operands_required`, an `Int` times a `Decimal` literal
`arithmetic_requires_signed_int_operands`). Over JOIN rows PostgreSQL also
emits an aggregate argument that holds a scalar call such as `lower`
(`count(lower(r.label))`), while a joined `let t = lower(r.label)` with
`count(t)` stays BLOCKED: a joined `let` admits such a call only directly
in a SELECT item. MySQL applies the same rules, except that it keeps such an
aggregate argument over JOIN rows BLOCKED (`operator_not_implemented_in_slice6`);
there an `Int` expression must first be proved to fit BIGINT
(`arithmetic_outside_physical_range` otherwise).

Single-file `emit-sql` renders `sum` without a cast except for PostgreSQL
`sum(Int)`, which emits the checked `int8` input and result casts above. Its
result is a nullable signed-64-bit `Int`; a sum outside that range, including
one over a physical `bigint` column, fails with SQLSTATE 22003 rather than
returning an exact out-of-range `numeric`. PostgreSQL may raise that error
while planning or execution; Pietto makes no error-timing guarantee. `sum`
over `Float` or `Decimal` remains target-native, and MySQL `sum(Int)` remains
its target-native DECIMAL form. `avg` remains without a cast except over
`Int`. `avg(Int)` is a `Float` average on both
targets: as in project SQL, its argument is cast before averaging (PostgreSQL
`AVG(CAST(x AS double precision))`, MySQL `AVG(CAST(x AS DOUBLE))`), so the
target returns a binary64 average instead of its own decimal one.

`stddev(x)` and `variance(x)` are the sample standard deviation and variance,
as Python's `statistics.stdev` and `statistics.variance` (pandas `std()` and
`var()`); `pstdev(x)` and `pvariance(x)` are the population standard deviation
and variance, as `statistics.pstdev` and `statistics.pvariance` (numpy `std`
and `var`). Each reads the non-None values of one direct `Int` or `Float` field
(or an alias of either). Its result is a nullable `Float`: `stddev` and
`variance` are None for fewer than two values, `pstdev` and `pvariance` are
None for no value and 0.0 for one, where Python raises; an empty or all-None
input gives None. Any other argument type, `Decimal` included, is PIE-S2314
(`expects Int or Float field argument`); an expression, a literal or a `let`
name is PIE-S2315 in a single file and in a project (where `min` and `max` take
a `let` name and these four do not). In a project a query header parameter
argument is refused earlier, with PIE-S2355, as for every aggregate outside
`count`, `avg`, `min` and `max`. The four take the positions of the other
non-window aggregates; in a window each is PIE-S2103 with the suffix `window
aggregates are sum, count, avg, min and max`, in a single file and in a
project, and without the suffix where the relation admits no such window (a
hidden QUALIFY window in a query with aggregates and no GROUP BY). Over JOIN
rows they read the rows a JOIN repeats, as `sum` does (PIE-S2381), and skip
the rows a LEFT JOIN keeps without a match. A `schema_version = 1` project
checks them as it checks `stddev`.

PostgreSQL emits `variance` as `CAST(VAR_SAMP(x) AS double precision)`,
`pvariance` as `CAST(VAR_POP(x) AS double precision)`, `stddev` as
`SQRT(CAST(VAR_SAMP(x) AS double precision))` and `pstdev` as
`SQRT(CAST(VAR_POP(x) AS double precision))` in a single file, with
`pg_catalog.float8` in place of `double precision` in a project; the argument
is never cast. The variance of an integer is computed in `numeric` from exact
sums, divided once at a result scale of at least 17 significant digits, and
rounded once to binary64 by the cast, and the square root rounds correctly:
`variance` and `pvariance` of an `Int` are within ε·v of Python's
`statistics.variance` and `statistics.pvariance` (ε = 2^-52), and `stddev`
and `pstdev` within 2·ε·s of `statistics.stdev` and `statistics.pstdev`.
`STDDEV_SAMP(int8)` and `STDDEV_POP(int8)` are never emitted, as they round
the `numeric` square root before the cast. A `Float` variance is accumulated
in binary64, and its error grows with the number of values n and with their
magnitude over their spread: with s the true deviation and r the root mean
square of the values, a deviation is within 4·ε·s + 8·n·ε·r of the true one
and a variance within about 2·s times that, a relative error of about
16·n·ε·r/s (bounds measured on PostgreSQL 18.6 and MySQL 8.4 by a
two-database differential); a variance below about 1e-322 or a deviation
below about 1e-161 may be 0, and the sign of a zero is unspecified. When the
accumulated sum of squares overflows (about |x| > 1e154), PostgreSQL fails
the statement with SQLSTATE 22003 instead of returning a value, also where
the true result is finite.

Single-file MySQL emits `STDDEV_SAMP(x)`, `VAR_SAMP(x)`, `VAR_POP(x)` and
`STDDEV_POP(x)` for a `Float`. An `Int` argument is refused with PIE-B1000
(`MySQL aggregate stddev of an Int argument is not supported`; `variance`,
`pvariance` and `pstdev` name themselves and add `; emit with --dialect
postgres`): MySQL computes an integer variance in DOUBLE. Pietto never emits
`STD`, `STDDEV` or `VARIANCE`, which are the population forms on MySQL and the
sample forms on PostgreSQL. `var`, `std`, `VARIANCE` and `STDDEV` are
PIE-S2103 with a hint that names both the sample and the population form, as
pandas and numpy, and PostgreSQL and MySQL, disagree on them; `var_samp`,
`var_pop`, `stddev_pop`, `pstddev` and `statistics.variance`,
`statistics.pvariance` and `statistics.pstdev` are PIE-S2103 with a hint that
names the one Pietto form, and `PVARIANCE` or `PSTDEV` one that says to write
it in lowercase; each of these hints is also the JSON `suggestion`.
`stddev(x, ddof=0)` is PIE-P1000: there are no keyword arguments. A `def
stddev`, `def variance`, `def pvariance` or `def pstdev` is PIE-S2398, as a
`def` named after any other aggregate is; its suggestion says to rename the
def. Semantic Metadata Artifact v1 lists none of the four, as it lists no
`string_agg`.

`median(x)` and `quantile(x, q)` are the interpolated median and quantile of
the non-None values of one direct `Int` or `Float` field (or an alias of
either), as pandas' `Series.median()` and `Series.quantile(q)` with its default
`linear` method. `median(x)` is `quantile(x, 0.5)`. Each value is taken as its
Float (binary64) image; with `v` the sorted images, `n` their count and
`p = q * (n - 1)`, the result is `v[p]` when `p` is whole and otherwise
`lo + (p - floor(p)) * (hi - lo)` in binary64, with `lo` and `hi` the values
at `floor(p)` and `ceil(p)`. The result is a nullable `Float`: an empty or
all-None input gives None, where Python raises. Because an `Int` is taken as
its Float image, values beyond 2^53 may round first: the median of the signed
64-bit extremes `-9223372036854775808` and `9223372036854775807` is `0.0`, as
pandas gives, where `statistics.median` of the exact integers gives `-0.5`; the
interpolation may differ from pandas in the last binary64 digit for `q` at or
above 0.5, where numpy writes `hi - (hi - lo) * (1 - f)`. Between two Floats
more than the largest Float apart (about 1.8e308) the interpolation is an
infinity, without an error.

`q` is a Float literal from 0.0 to 1.0 written in the call, such as `0.9` for
the 90th percentile; any other second argument is PIE-S2104, at that argument
(`q 1.5 is outside 0.0 to 1.0` for a Float literal out of range, `q must be a
Float literal from 0.0 to 1.0, written in the call` for an Int literal, a
signed literal, a field, a `let` name or an expression). Any other argument
type, `Decimal`, `Date` and `Timestamp` included, is PIE-S2314 (`expects Int or
Float field argument`); an expression or a `let` name is PIE-S2315 in a single
file and in a project, as for `stddev`. `median` and `quantile` take the
positions of the other non-window aggregates: an aliased select item, which
HAVING reads by its alias (a direct call in HAVING is PIE-S2308); in a
window they are PIE-S2103, as `stddev` is. Over JOIN rows they read the rows a
JOIN repeats, as `sum` does (PIE-S2381), and skip the rows a LEFT JOIN keeps
without a match.

PostgreSQL emits `median(x)` as
`PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY x)` and `quantile(x, q)` with `q`
in place of `0.5`; an `Int` argument is cast first, `CAST(x AS double
precision)` in a single file and `CAST(x AS pg_catalog.float8)` in a project,
where the fraction of a `quantile` is the anchored literal
`CAST('0.9' AS pg_catalog.float8)` under either literal policy. Pietto never
emits `PERCENTILE_DISC`. MySQL has no interpolated percentile: a single file is
refused with PIE-B1000 (`MySQL aggregate median is not supported: MySQL has no
interpolated percentile; emit this relation for PostgreSQL`), a project with
PIE-B1003 `quantile_not_admitted_on_target`. A `Decimal` median is not
available: PostgreSQL's `percentile_cont` has no `numeric` form and would take
a `Decimal` as a Float. The ordered-set spelling `percentile_cont(0.5) within
group (order by x)` is PIE-P1000 at `within`, with a hint naming `quantile`
and `median`; `percentile_cont`, `percentile`, `percentile_approx`,
`approx_percentile` and `percentile_disc` calls are PIE-S2103 with a hint. A
`def median` or `def quantile` is PIE-S2398 with a rename suggestion. Semantic
Metadata Artifact v1 lists neither aggregate, as it lists no `stddev`.
`any` and `all` are built-in names too: a `def any` or `def all` is
PIE-S2398 with a rename suggestion, so `any(x)` and `all(x)` never call a
`def` and their PIE-S2103 hints (``write `any(o.x for o in group)` ``) are
never wrong.

`first(x, order by k1 [desc], k2 [desc], ...)` is the value of one direct field
`x` at the first member row of the group in that order, and `last(...)` the value
at the last row: Python's `sorted(group, key=lambda r: (r.k1, r.k2))[0].x` and
`[-1]`, for keys that are not `Text` (a `Text` key orders by the target collation,
as a relation ORDER BY does, which may change which row is first but never whether
one is). The internal `order by` is required, written as `string_agg` writes it.
Pietto never picks one of several tied rows, so the order must be total, and is
proven so statically:

1. every key is a direct field of the FROM input, bare or qualified (a `let` name
   whose value is a field reads as that field);
2. no key is None on a member row: its type has no `| None`, or a top-level `and`
   conjunct of the query's `where` tests it with `is not None` (bare, qualified or
   through a `let` name), which drops every row whose key is None before any group
   forms. The type of the key does not change; only this rule reads the conjunct,
   as PIE-S2384 does. An `or`, a test under `not`, a `having` or another query's
   `where` is no proof;
3. the order ends in a unique key: the keys, together with the GROUP BY keys that
   are direct fields of the input and never None by rule 2, cover every field of
   one `unique(...)` of the FROM source's shape. Since every key is a direct field
   that is never None, a key written after a complete unique key is admitted and
   never changes the order (`order by id, sold_at`). A computed GROUP BY key never
   counts, nor does a key that may be None (SQL unique keys admit repeated NULLs).
   Only the FROM source's declared keys are read: over a table or query input the
   order is refused with a hint to read the source, and over a source without a
   shape, whose fields are not known, with a hint to give it a shape with a
   `unique(...)` key.

A None `x` at the chosen row is the result: the value is never skipped (SQL
`FIRST_VALUE`, pandas `nth(0)`; pandas `GroupBy.first()` skips None and is not this
one). `x` is one direct field (or a `let` name of one) of type `Int`, `Decimal`,
`Float`, `Text`, `Bool`, `Date`, `Timestamp` or `UUID`; an enum or any other type
is PIE-S2314 and an expression PIE-S2315. The result has the field's type and may
be None when the field may be, or when the query has no GROUP BY (an empty input
gives None); under GROUP BY each group has a row, so the result of a non-None field
is never None. `first` and `last` take the positions of the other non-window
aggregates (an aliased select item; elsewhere PIE-S2308). A key that is not a
direct field, may be None, or leaves the order without a unique key is PIE-S2104
at the first key that fails (the last rule at the call), each with a hint that is
also the JSON `suggestion`; a call without `order by` is PIE-S2104 ``expected ORDER
BY key; a group's rows have no order: write `first(x, order by k, id)` ``. A
generator argument (`first(o.x for o in group)`) is PIE-S2334 ``first takes no
generator; write `first(x, order by k, id)` ``, and over JOIN rows the call is
PIE-S2334 ``first over JOIN rows is not available yet; join in one query, then group
it in another that reads it with `from` ``. A call with an error inside it, such as
an unknown field of a key, reports that error alone, in a single file and a project
alike. With a `window`, an internal `order by` is the one PIE-S2104 ``Internal ORDER
BY is not supported in a window; for one value per group, drop the `window(...)` ``,
and `first(x) window(...)` without one is PIE-S2103 `Aggregate window functions are
not implemented: first; ...`; for one value of a row's window, `first_value(x)
window(...)` is the window function. An internal `order by` on any other call is
PIE-S2104 `Internal ORDER BY is only supported by string_agg, first and last`.

`unique(...)` is a trusted declaration that Pietto never checks against the data:
over rows that break it, PostgreSQL returns the value of one of the tied rows,
silently, as for an asof JOIN. `ARRAY_AGG` collects the group's values per item,
so the memory of a `first` or `last` is linear in the group.

PostgreSQL emits `first(x, order by k, id)` as
`(ARRAY_AGG(x ORDER BY k ASC, id ASC))[1]` and `last` with every key direction
flipped, `(ARRAY_AGG(x ORDER BY k DESC, id DESC))[1]`; since no key is None, NULL
placement never enters, and `ARRAY_AGG` keeps a None value and is NULL over no row.
A schema_version = 2 project checks the same rules and emits the same shape
(`spelling` `ARRAY_AGG`). MySQL has no ordered first or last yet: a single file is
refused with PIE-B1000 (`MySQL has no ordered first or last yet; emit with
--dialect postgres`), a project with PIE-B1003
`first_last_not_admitted_on_target`; a window in a derived table is the planned
MySQL route. A schema_version = 1 project has no `first(...)` or `last(...)`
(PIE-S2334, `set schema_version = 2 to check it`). `any_value`, `nth`, `head`,
`arg_max`, `argmax`, `max_by`, `idxmax`, `arg_min`, `argmin`, `min_by` and
`idxmin` calls are PIE-S2103 with a hint to the `first` form, and a `def first` or
`def last` is PIE-S2398 with a rename suggestion. Semantic Metadata Artifact v1
lists neither aggregate, as it lists no `string_agg`. In a project an internal
order key written as a `let` name is PIE-S2333 `Project relation semantic
completion is unavailable`, as for `string_agg`, where a single file accepts it,
and one that fails the order proof (a computed `let` key included) is that
PIE-S2104 alone, as in a single file; a `let` name as the value is accepted in
both, and a computed `let` value is the PIE-S2315 alone in both.

The PostgreSQL SQL of the `shop_plants` query of the [style guide](style.md):

```sql
SELECT
    "shop_id" AS "shop_id",
    (ARRAY_AGG("plant" ORDER BY "sold_at" ASC, "id" ASC))[1] AS "first_plant",
    (ARRAY_AGG("plant" ORDER BY "sold_at" DESC, "id" DESC))[1] AS "latest_plant",
    (ARRAY_AGG("plant" ORDER BY "price_cents" DESC, "id" ASC))[1] AS "priciest_plant",
    (ARRAY_AGG("plant" ORDER BY "price_cents" ASC, "id" ASC))[1] AS "cheapest_plant",
    (ARRAY_AGG("pot_size" ORDER BY "weight_kg" ASC, "id" ASC))[1] AS "lightest_pot"
FROM "nursery"."sales"
WHERE "weight_kg" IS NOT NULL
GROUP BY
    "shop_id";
```

**Conditional count and sum, and the test of a group.** A generator `BODY for o in SOURCE if TEST` is
written only as the only argument of a call, with one `for` and at most one
`if`; a conditional in TEST takes parentheses, as in Python. Its meaning is
fixed by SOURCE alone: a relation name (a source, table, query, import or
`let` of the query) is every row of that relation, as in `any(...)`; `group`,
when no such relation is named `group`, is the rows of the current group: the
rows that `from` and `where` keep with this key, each as often as it occurs,
the rows `count()` counts. A relation or `let` named `group` keeps its meaning
in `from` and `any(...)`.

A single file and a `schema_version = 2` project admit four generators:

- `sum(1 for o in group if TEST)`: the number of rows of the group whose
  TEST is True (a None TEST is no match). An `Int`, never None, 0 for none.
- `sum(o.f for o in group if TEST)`, `f` an `Int` field or an alias of `Int`:
  the sum of the non-None `o.f` of the rows whose TEST is True. An `Int`, never
  None, 0 when no row matches; a sum outside signed 64 bits is an error.
- `any(TEST for o in group)`: True when TEST is True for at least one row of
  the group. `all(TEST for o in group)`: True when TEST is True for every row
  of the group. Each is a `Bool`, never None; with no row (a query with
  aggregates and no GROUP BY over an empty input) `any` is False and `all` is
  True, as in Python. The body is the test: neither takes `if` (count the
  exceptions instead, `n = sum(1 for o in group if q and not p)`, then
  `having n == 0`).

Each is a whole aliased SELECT item of a grouped query, or of a query with
aggregates and no GROUP BY (whose whole input is one group), as every other
non-window aggregate; `having` and `order by` read its output name. TEST is a
Bool row expression that reads the member's fields as `o.f` and, besides
them, only GROUP BY key fields; it holds no aggregate, window, `any(...)`,
generator, relation read or captured field. A relation with JOIN inputs takes
no group generator yet: join in one query and group it in another that reads
it with `from`.

The test of a group reads TEST in two steps. Each row's TEST is evaluated as
WHERE evaluates the same expression, so it is True, False or None; then
`any` is True when some row's TEST is True and `all` when every row's TEST
is True, a None TEST being "not True" (Python's `any([None])` and
`all([None])` are False too). The fold agrees with Python always; a row's
TEST agrees with Python's truthiness of the same expression except where a
None reaches `not`, `!=` or `not in`, or `==` compares two Nones: Python
makes those True (`not None`, `None != "x"`), SQL keeps None. So over
`flagged = [None]`, `all(not o.flagged for o in group)` is False in Pietto
and True in Python, and over `status = [None]`, `any(o.status != "x" for o
in group)` is False in Pietto and True in Python. Write Python's meaning
where you want it: `all(not coalesce(o.flagged, False) for o in group)`,
`any(o.status != "x" or o.status is None for o in group)`. A `not in` over a
nullable field warns (PIE-S2384) in TEST as in WHERE. pandas
`GroupBy.all()`/`any()` skip None (`skipna=True`), so pandas `all` of
`[True, None]` and of `[None]` is True where Python and Pietto give False.

In a SELECT item `any(... for o in group)` is always the test of a group:
while a relation or `let` named `group` is visible there it is refused
(PIE-S2334 ``Generator over group in any: group is the relation group, not
this group; rename the relation group to read this group's rows``), as
`sum` and `all` are; in a WHERE, a row `let` and a JOIN `on` it keeps its
relation meaning (with no relation named `group` there it is PIE-S2301,
``a group's rows exist only after `group by`; test a row's own fields
directly``). `any(...)` and `all(...)` of a group in `having` are refused
(PIE-S2334 and PIE-S2308): select the test and read its output name there.
A `def any` or `def all` is PIE-S2398. The other refusals are listed in the
PIE-S2334 row of
[diagnostics](spec/diagnostics.md). A `schema_version = 1` project refuses
every generator at check with PIE-S2334 (``sum(... for ...): a
schema_version = 1 project has no generator in the current syntax; set
schema_version = 2 to check it``). In a project TEST reads no query header
parameter yet (PIE-S2355 `Query parameters are not available in this
position.`, as for every aggregate argument, with no suggestion). TEST reads
no `let` of the query, a computed GROUP BY key included (PIE-S2334
``Generator reads the let k outside its member; write the let's expression
over fields of o, such as `o.f` ``): write the let's expression with member
fields, such as `if o.id + 1 > 2`. A project `any(... for o in group)` outside
a SELECT item that names no relation keeps its own PIE-S2301 `Unknown
relation: group` at the `any(...)` (PIE-S2334 `ANY is not supported in this
context` in `having`) and suggests what a single file suggests.

PostgreSQL emits the count as `COUNT(CASE WHEN TEST THEN 1 END)` and the sum
as `COALESCE(CAST(SUM(CASE WHEN TEST THEN CAST(f AS pg_catalog.int8) END) AS
pg_catalog.int8), 0)`; TEST is written as the same expression in a WHERE
would be. MySQL writes the count the same way, `COUNT(CASE WHEN TEST THEN 1
END)`, a `BIGINT`, and refuses the sum with PIE-B1000 `MySQL conditional sum
of an Int argument is not supported`, as MySQL adds integers in DECIMAL.
The test of a group is `(COUNT(CASE WHEN TEST THEN 1 END) > 0)` for `any`
and `(COUNT(CASE WHEN TEST THEN NULL ELSE 1 END) = 0)` for `all`: COUNT is
never NULL, so no row gives False and True, and a None TEST takes no `WHEN`
branch, so it counts for `all` as a failure. Single-file MySQL writes the
same form, an integer 0/1 (the computed-Bool wire type), as a two-database
differential checked.

Project SQL (`emit-sql --project`) writes the same forms on PostgreSQL
(`COUNT(CASE WHEN TEST THEN 1 END)` and the `COALESCE`d checked `SUM`), each
result a non-null `pg_int8`, the sum's R13 requirement with the evidence
`target_checked_signed64_narrowing`; compiled bundles and live templates
carry them unchanged. A test that reads no field (`if True`) checks, but
project SQL refuses it (PIE-B1003 `conditional_test_reads_no_field`). MySQL
project SQL keeps both BLOCKED: the count with PIE-B1003
`conditional_count_not_admitted_on_target`, the sum with PIE-B1004
`sum_int_aggregate_range_proof_missing`, as `sum(Int)`. The test of a group
is written in project SQL as in a single file, a non-null `pg_bool` with no
R13 evidence; a test that reads no field (`any(True for o in group)`) is
PIE-B1003 `group_test_reads_no_field` on both targets, and MySQL project SQL
keeps it BLOCKED with PIE-B1003 `group_test_not_admitted_on_target`.

`count(x)` of a `Bool` field counts every row whose `x` is not None, False
included; outside a window call a single-file check warns about it
(PIE-S2388) and names `sum(1 for o in group if o.x)`, which counts the rows
where it is True.

Over a source without a shape, whose fields have no type, GROUP BY keys and
aggregate arguments read its fields by name, and an aggregate is checked as
over a row of field types its argument allows, with one type for each field
however often the argument reads it: `count(x)`, `count(x + 1)`,
`count(x * x - x)`, `count_distinct(lower(t))`, `sum(x * 2)` and `min(x)`
pass. A part of the argument whose type is known, such as a literal or a
built-in call, is still checked as over a known row: `count(x + "a")`,
`count(x % 2.5)`, `count(lower(x + 1))` and `count(len(x) + x)`, which no type
of `x` makes typed, are PIE-S2315 at the call, as is a form the aggregate
never takes, such as `min(x + 1)`. A `None` operand has no type and is not
checked, as the database types it from the other operand: `count(x + None)`
passes; with a known numeric `x`, `count(x + None)` still reports PIE-S2315
for the unsupported argument form.
An argument with an error of its own, such as `count(x and 1)` (PIE-S2105),
reports nothing more. The ORDER BY of a grouped relation over such a source
is PIE-S2321 at the clause, whatever its keys. These checks do not make
aggregation over an unknown input row available to SQL emission: even
`n = count()` keeps an unknown output type, and `emit-sql` refuses it with
PIE-B1000, or with PIE-I1000 for a grouped window. A relation that reads one
over such a source also reads its outputs as of unknown type.

A single-file aggregate over JOIN rows must not read rows that a JOIN may
repeat. `count()` without an argument counts joined rows and needs no proof.
`min`, `max` and `count_distinct` need none either: each depends only on the
set of non-None values a group holds, and a JOIN that repeats a row only
repeats a value already in that set. Every other aggregate must pass the
following conservative rule; a failure is PIE-S2381 at the aggregate call in
every check mode.

Start with the inputs the argument reads, following `let` values, and each
source input whose declared unique key (`name = unique(...)` in its shape) is
entirely in GROUP BY with every key field never None in the source shape.
Field-renaming `let` keys count; computed keys do not. Close that set using
only required equalities, the `==` comparisons of two fields of different rows
among top-level `and` operands, that match every field of a unique key of an
input to fields of inputs already in the set; the key fields may be nullable.
A unique key is one that the input's source shape declares, or, for a grouped
table or query that selects each of its GROUP BY keys as its plain read
(`order_id` or `oid = order_id`), every output that selects one: GROUP BY
gives one row per distinct key tuple, and a NULL key, one group, never equals
anything under `==`. A key selected under two names (`order_id` and
`oid = order_id`) is matched only by an `on` that matches both, as in a
project.

- In an INNER or LEFT JOIN's `on`, an equality written by hand, such as
  `orders.customer_id == customer.id`, or one in the body of a relationship
  call there, adds the JOIN's own input in this way; both spellings prove the
  same. In an INNER JOIN's `on` it may also add an earlier input, such as the
  FROM input when the equality matches its key to the JOIN's input.
- A LEFT JOIN's `on` adds an earlier input whose key it matches, and a RIGHT
  JOIN's `on` adds its own input, only for a `count`, `sum`, `avg` or
  `stddev` whose argument is a field, or a `let` name of one, of an input the
  JOIN NULL-extends (the LEFT JOIN's own input; an earlier input of the RIGHT
  JOIN), or of an input whose INNER or LEFT JOIN `on` equates one of its
  fields with a field of such an input, which then finds no match either.
  Such an aggregate skips the one row the JOIN keeps for each row without a
  match, where the match does not hold. So
  `from customers left join orders on orders.customer_id == customers.id`
  grouped by `customers.region` admits `sum(orders.amount)`,
  `count(orders.id)` and `avg(orders.amount)`, and the RIGHT spelling
  `from orders right join customers on ...` admits `sum(orders.amount)`;
  adding `left join items on items.order_id == orders.id` also admits
  `sum(items.qty)`. An argument that is not None there, as
  `count(coalesce(orders.amount, 0))` or `count(customers.id)`, is
  refused.
- In the WHERE, only the equalities of a relationship call that is a
  top-level `and` operand may add an input, any input; a hand-written WHERE
  equality adds none. A top-level `and` operand `x.f is None`, where `x` is a
  LEFT JOIN's input and its source shape declares `f` never None, adds `x`:
  WHERE then keeps only the one row `x` NULL-extends for each row without a
  match (`where orders.id is None` after `left join orders`). Under `or` or
  `not`, or for a field that may be None (`orders.note`), it adds nothing,
  and `is not None` adds nothing either.

The set must then contain the FROM input and every JOIN input; the relation of
an `any` or `not any` filter is never one. FULL and CROSS JOINs add no
dependencies, a RIGHT JOIN adds only the one above, and neither does an
equality or a call under `or` or `not`. Keys are taken from source shapes and
from the GROUP BY keys of a grouped table or query, never inferred through
other tables or queries. Outer NULL extension does not justify a FULL
dependency: one NULL left part may match several preserved rows. Group
protection uses the source's never-None key so a NULL-extended part remains
one fixed value within a group.

PIE-S2381 names the JOINs that may repeat the aggregate's rows, as a
project's PIE-S2333 does, and the remedies that can close the rule: matching a
declared unique key of each named input in `on` with a relationship call or a
mandatory positive equality written by hand, `any(...)` for an input that only
filters rows, or aggregating in a separate query first. Every PIE-S2381 message
then names the two-level route below, whatever its remedies; a project's
PIE-S2333 cause does not name it, but the same route closes it. Where the `on` of a
LEFT JOIN already matches the key of an earlier input, or that of a RIGHT
JOIN the key of its own input, the missing piece is not the key: the
aggregate reads the rows that JOIN keeps without a match, and the remedy says
``read no row that JOIN orders keeps without a match`` instead. Where the
aggregate already reads none of those rows (its argument is a field of an
input that is None on each of them, also through a later FULL JOIN's `on`),
the missing piece is a proof a single file does not make, and the input is
not named. A single file does not name an input whose key only the `on` of
FULL JOINs, or of RIGHT JOINs from their own inputs, matches; it then names
only the last two remedies. In both modes, a LEFT JOIN whose input WHERE
keeps NULL-extended on every row (`where payments.id is None`) is not named as
repeating, and its `on` does not count as matching a key: with
`left join orders ... left join payments on payments.order_id == orders.id`
and that WHERE, the refusal asks for a unique key of orders, not for rows
that JOIN payments keeps without a match, which are the only rows WHERE
keeps. The matching key may
be nullable; this does not relax the separate GROUP BY requirement that a
source key used to start the grouped set have fields that are never None. It
never suggests grouping by such a
key, which would change the result's grain. With
`inner join customer on orders.customer_id == customer.id`, where the shape of
`customer` declares no unique key, `count(orders.id)` grouped by
`customer.name` reports:

```text
An aggregate may read rows repeated by JOIN customer; match a unique key of customer in `on`, use `any(...)` for an input that only filters rows, or aggregate in a separate query first; two-level route: group a first query by a unique key of each input the aggregate reads and by every other field that query selects, select an aggregate such as `count()` in it too, then aggregate in a second query that reads `from` it
```

Once the shape declares `customer_key = unique(id)`, the same `on` proves that
each order matches at most one customer, as the relationship call
`OrderCustomer(orders, customer)` does.

**The two-level route.** To aggregate values that a JOIN repeats, use two
queries. The first groups by a unique key of each input the aggregate
reads and by the other fields it selects for the second query (PIE-S2318
otherwise), so it has one row per row of those inputs (a LEFT JOIN that
matches none of them adds one row of None per other group key, which an
aggregate of their fields skips); the second reads `from` the first and
aggregates its rows, each once. A JOIN of orders to their items and to their payments
repeats each item once per payment of its order, so `avg(item.qty)` over
it is refused, also when the query groups by `orders.id`. There each item
of a group repeats equally often and the average would not change, but the
rule has no proof that a group key fixes how often each row repeats; the
same query grouped by `orders.customer_id` weights orders by their payment
counts. In two levels:

```pietto
shape Order:
    id: Int
    customer_id: Int
    order_key = unique(id)

shape Item:
    id: Int
    order_id: Int
    qty: Int | None
    item_key = unique(id)

shape Payment:
    id: Int
    order_id: Int

source orders: Order = postgres.table("orders")

source items: Item = postgres.table("items")

source payments: Payment = postgres.table("payments")

query per_item:
    from orders
    let item = items
    left join item on item.order_id == orders.id
    let payment = payments
    left join payment on payment.order_id == orders.id
    group by item.id, item.qty, orders.customer_id
    select:
        item_id = item.id
        qty = item.qty
        customer_id = orders.customer_id
        joined_rows = count()

query average_qty:
    from per_item
    group by customer_id
    select customer_id, average_qty = avg(qty)
```

`per_item` has one row per item (and one per customer for the orders
without items, whose `qty` is None and is skipped by `avg`). A grouped query
selects at least one aggregate (PIE-S2320), here `count()`, which needs no
proof. The usual case counts per order and sums per customer: the first
query groups by `orders.id` and the order fields it keeps and selects
`lines = count(item.id)`, and the second selects `sum(amount)` and
`sum(lines)` (see the [style page](style.md)); without a declared key of
orders that count is PIE-S2381 itself. The route is two ordinary grouped
relations: single files emit it on PostgreSQL and MySQL; an
EXPLICIT_MODULES project emits, compiles and binds it on PostgreSQL, while
its MySQL emission blocks each Int `sum` (PIE-B1004
`sum_int_aggregate_range_proof_missing`), as for any project MySQL Int
`sum`.

GROUP BY accepts fields and `let` names that rename fields. Self-join keys
such as `customers.id` and `peer.id` remain distinct; a bare and qualified
read of the same field remain one key. SELECT aggregates must be directly
aliased (PIE-S2313). `having` and grouped ORDER BY read their selected
outputs. ORDER BY after an ungrouped aggregate is PIE-S2334 even when fan-out
is safe. This rule does not widen the existing aggregate argument/type domain
or any window contract beyond the admitted window families.

In an explicit-module project, an aggregate over one input must not silently
count that input several times because another JOIN side can match repeatedly.
Every boundary that can multiply its rows needs the existing exact fan-out proof.
An all-non-null unique group key of the other side can supply a group proof;
a mandatory positive equality to a matching declared unique key can supply a
bounded-match proof where the current JOIN kind and NULL state permit it.
In both single files and projects a mandatory positive equality is a top-level
`and` conjunct of `on` that compares two fields, bare or qualified, with `==`;
one written by hand, as in
`inner join customers on orders.customer_id == customers.id`, proves what the
same equality in a relationship body proves. A project also matches a key
that a query carries from its FROM input through only `select`, a `where`
without `any(...)`, `order by` and `limit`, and, for an aggregate's fan-out
proof, the GROUP BY keys of a grouped query, all of them matched by an INNER
or LEFT JOIN's `on` (each output that selects one, when one is selected
twice). Where a FULL JOIN's `on` already matches the key of an earlier input,
which nothing proves, a refusal names only the last two remedies; where it
matches the key of its own input, it names the rows that JOIN keeps without a
match, as for RIGHT. An `on` equality does not match yet the key of a query
with an `any(...)` filter, a window, QUALIFY, `select distinct`, a JOIN or a
FROM over a query block, and a refusal then does not ask to match it; nor does
a refusal ask to match a grouped query's keys. A single file matches the keys
a source's shape declares and the GROUP BY keys of a grouped table or query. A project takes these
equalities only from `on`, never from WHERE, not even from a relationship call
there; a single file also takes those of a relationship call in WHERE (see
above), never a hand-written WHERE equality.
A filtered relationship may preserve an upper bound but does not prove coverage.
OR, NOT, a source name, a same-shaped row or a key on the aggregated side alone
does not supply the missing proof. Nullable keys retain their existing
NULL-sensitive restrictions, especially after RIGHT/FULL unmatched rows.
A project refuses such an aggregate with PIE-S2333 at the relation, naming
the JOINs that PIE-S2381 names. A JOIN relation that also mixes an aggregate
with another projection without GROUP BY (PIE-S2312) reports PIE-S2381 at
each refused aggregate after that PIE-S2312 instead, in a project as in a
single file, except where the project relation's `let:` clause or WHERE is
refused: it then reports neither PIE-S2312 nor PIE-S2381 (a known limitation;
see PIE-S2312 in the [diagnostics](spec/diagnostics.md)). Neither a single
file nor a project reports that PIE-S2381 when a SELECT item, a window,
QUALIFY or an ORDER BY key reads a name that several inputs have (PIE-S2335)
or a dotted name of no field (PIE-S2102).

The bounded RIGHT/FULL proof starts only when each left row has at most one
RHS match. A RIGHT or FULL JOIN can then keep unmatched right rows beside an
all-`None` left extension. An aggregate keeps its proof when it reads none of
those unmatched rows: its argument is `None` there, WHERE is never true there,
or a later JOIN's `on` never matches them. Pietto decides this from values. A
field of the all-`None` side is `None`; a field that its input declares never
`None` and that no LEFT, RIGHT or FULL JOIN may null-extend is not;
comparisons of `Int` or `Bool` constants, `in ()` (false), `not in ()` (true),
`coalesce`, `nullif(x, x)` and a conditional whose condition is decided there
give constants; and an `and` of comparisons of one field with `Int` constants
that no value satisfies together, such as `c.id > 5 and c.id < 3`, is never
true. The proof also holds when WHERE holds every field of a unique key of
the right input to one `Int` constant, with `==`, `in` and one value, or
`>=` and `<=` of the same value, joined by `and`: then the aggregate reads
those rows of one right row at most. So after
`right join c on order_customer(orders, c)` and `cross join r`, `count(r.id)`
grouped by `orders.id` is accepted with `where r.id is None`,
`where orders.rush or c.id is None`,
`where (orders.amount if orders.rush else 0) > 0` or `where c.id == 3`,
while `where c.id is not None`, `where c.id > 2 and c.id < 5`,
`where c.id in (3, 4)` and `where c.region_id == 3` read the unmatched rows
of two customers, which the CROSS JOIN repeats, and are PIE-S2333. Other
correlations, such as `c.id > 3 and c.id < 5`, which admits one `Int`, are
not used.

A LEFT JOIN is the mirror: its `on` matching a key of an earlier input bounds
each right row to one row of it, except on the row it keeps for a left row
without a match, beside a NULL-extended right input that several such rows
share. An aggregate keeps that proof when it reads none of those rows, decided
from values as above (its argument is None there, WHERE is never true there,
or a later JOIN drops them). One that reads only such rows, because WHERE is
never true where the right input's never-None fields are not None (as in
`where orders.id is None`), reads one row per left row, so its left side
determines the right input.

`count()` counts joined rows and needs no input-row fan-out proof, and neither
do `min`, `max` and `count_distinct`, which depend only on the set of values
a group holds. Unsupported cases remain
PIE-S2333, whose message may identify repeating JOINs and available unique-key
or group-key remedies. The selected SQL/compiled aggregate path still refuses
Bool arguments: typed semantic facts for `count(predicate(...))` do not by
themselves establish emission or source-free execution capability. ANY does not
widen that domain. Project and single-file PostgreSQL `sum(Int)` follow the
checked `bigint` rule described above; project MySQL stays PIE-B1004.

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

relationship OrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id

query orders_per_customer:
    from orders
    let customer = customers
    inner join customer on OrderCustomer(orders, customer)
    group by customer.name
    select:
        customer_name = customer.name
        order_count = count(orders.id)
        largest = max(orders.amount)
```

The declared customer key is the relevant match premise; the relationship's
name alone is not. Removing that premise can make aggregates over order fields
unavailable even though the JOIN itself is legal. Selecting a SQL target still
requires the target's representation and aggregate proofs.

Grouped relations preserve group-key order and selected aggregate output
identity. `having` and grouped result ordering use the current selected
output rules; they are not general post-aggregate expression languages.

In EXPLICIT_MODULES projects, a group key may also name one row `let` binding
whose value is computed, such as `bucket = amount * 2` with `group by bucket`;
the key is selected by that `let` name. Emitted SQL establishes the value once
in its LET stage and groups by that qualified column, never by a repeated
expression, an ordinal, or an output alias. Such a key is not assumed injective
and never supplies source-row grain. It passes the same comparison-domain check
as a field key: Int keys use the LET site's proven range, Decimal keys keep the
value's exact precision and scale, Bool and Text keys keep their comparison
domains, and Float keys compare by Float equality, so a key may show a zero
sign some of its members do not have. Project emission emits a Float key on
PostgreSQL; MySQL keeps it refused. Grouped result ordering may name the
key's selected output; without JOIN inputs a `having` reference to that
output keeps its existing rejection. With JOIN inputs the key records every JOIN
side its value reads, including both sides of `agg.rid > r.rid`, but it never
proves that a side is unique per group, so it never removes a fan-out refusal;
only direct field keys that form a strict unique key, as described above, can
do that. There, `having` and grouped result ordering may name the key's
selected output. In a single file, QUALIFY uses its complete selected-output
and pre-window-input namespace. In an EXPLICIT_MODULES project, QUALIFY keeps
the project query-block rule: its selected bindings are window results, not
ordinary projection aliases. In either mode, a window argument, PARTITION BY
or ORDER BY that names the computed key keeps its existing window-specific
refusal (see [Windows](#windows)).
With JOIN inputs a `let` binding that only renames a field, such as
`g = r.n` with `group by g`, groups by that field, and selecting the name
selects that field's key, as selecting the field does. A `let` alias of a
computed binding, single-file checks, and LEGACY_FLAT projects keep their
existing rejection (a single file says what to write instead: the field in
place of a `let` name of a group key field, an EXPLICIT_MODULES project for a
computed key, or that the name is not a GROUP BY key); with JOIN inputs a selected `let` name that names no group
key, such an alias included, is PIE-S2333 at the table or query rather than an
unknown field.

## Windows

The following single-file window forms also apply to a relation with known JOIN
inputs. PostgreSQL and MySQL preserve resolved input bindings in their SQL.
Projects keep their separate completion and target limits.

Direct selected window expressions use a parenthesized `window` specification:

```pietto
shape User:
    id: Int

source users: User = postgres.table("users")

query ranked:
    from users
    select:
        position = row_number() window(order by id)
```

The bounded window identities are `row_number`, `rank`, `dense_rank`,
`percent_rank`, `cume_dist`, `ntile`, `lag`, `lead`, `first_value`,
`last_value`, and `nth_value`. `sum`, `count`, `avg`, `min`, and `max` may also
be used as direct aliased window projections when their ordinary aggregate
argument and result contract admits the call; a window does not count a field
typed by a shape (PIE-S2104), and over a source without a shape every
aggregate window that reads a field, as an argument or a partition or order
key, is PIE-S2103 (`window input schema must be concrete`), as every window is
outside GROUP BY, while `count() window()` reads none and is accepted;
under GROUP BY over such a source `check`
accepts a window, selected or in QUALIFY, as 0.1.4 did, and `emit-sql`
refuses the relation (PIE-I1000), since its groups type no field the window
reads. EXPLICIT_MODULES projects admit the same aggregate windows, selected,
over grouped rows, in a hidden QUALIFY window and over JOIN rows, with one
more rule: each argument is a direct field (an input field, under GROUP BY a
key or an aggregate output, or a `let` name bound to one). Another argument,
such as `sum(amount * 2)` or a `let` name whose value is computed, is
PIE-S2103 (`Unsupported window computation for function sum: argument must be
a direct field in a project`), once the ordinary aggregate argument rules
admit it (`count(1)` stays PIE-S2104). Project PostgreSQL SQL keeps the
project aggregate laws over the window: `sum` of an Int is
`CAST(SUM(CAST(x AS pg_catalog.int8)) OVER (...) AS pg_catalog.int8)`, which
fails with SQLSTATE 22003 rather than returning a wrong total, `avg` of an Int
is `AVG(CAST(x AS pg_catalog.float8)) OVER (...)`, `count()` is
`COUNT(*) OVER (...)`, and `min`, `max` and `count(x)` are the plain aggregate
with `OVER`; a `Decimal` or `Float` `sum` or `avg` is PIE-B1004 and another
argument outside the reviewed domain PIE-B1003, as for the grouped aggregate.
Project MySQL SQL refuses each aggregate window with PIE-B1003
(`window_aggregate_approved_non_support_on_mysql`) until its real-database
differential. Aggregate windows do not accept `ignore nulls`, `respect nulls`,
`from first`, or `from last`; each reports PIE-S2104 rather than being omitted
from emitted SQL. PostgreSQL and MySQL
preserve an omitted frame: with `ORDER BY` its default is peer-inclusive `RANGE
UNBOUNDED PRECEDING` through the current row; without `ORDER BY` the whole
partition is the frame. Both emit the ordinary aggregate's SQL with `OVER`, so
MySQL `sum` of an Int window is DECIMAL and `avg` of an Int casts it to
DOUBLE, as grouped MySQL aggregates do. MySQL may compute a sliding `sum` or
`avg` frame of DOUBLE values by removing the rows that leave it, which can
round differently; it does not under its default session setting
`windowing_use_high_precision = ON`, which single-file MySQL SQL assumes as it
assumes the other default session settings.
Partition and resolved order items preserve source order, duplicates,
qualification, and direction. Each item names an input field or a `let`: an
expression written there reports PIE-S2103 (`window partition expression must
be a direct field` or `window order expression must be a direct field`) at the
window call, and a `def` call written there PIE-S2397. To order or partition
by a computed value, bind it with `let` and name the binding; where that works
and the expression reads an input field, the PIE-S2103 message ends with
``; compute it in a `let` and name that `let` in the window``. A `let` name
there stands for its value once its `let` names and `def` calls are expanded:
a field, such as with `k = t`, is read as that field; a value computed from
input fields with literals, operators, conditional expressions, casts and
scalar or `def` calls, such as with `k = lower(t)`, `k = score != 3` or
`k = shifted(score)`, is a key of that value, in a selected window, a named
window and a QUALIFY window, an aggregate window included; and a value that
reads no input field, such as with `k = 3`, `k = -3` or `k = 1 + 2`, which
orders nothing, or that reads anything else, such as an `any(...)` or an
aggregate, is PIE-S2103 at the window call. A single file writes a computed
key's value in the window specification (`PARTITION BY ("category" <> 'x')`);
an EXPLICIT_MODULES project computes it in the stage before the window and
orders or partitions by that column. A computed key that may be None is
ordered as a nullable field key is. A grouped window, whose keys are GROUP BY
keys and aggregates, and a window over JOIN inputs, in single files and
projects, keep the field-only rule: a computed `let` key there is PIE-S2103,
and an expression written there gets no hint. A computed key that reads a
query parameter stays PIE-S2355. Single-file MySQL refuses a key that names a
computed Text `let` (PIE-B1000, `MySQL does not support a computed Text window
key`): MySQL could compare such a value under the connection collation rather
than a column's. A two-database differential (PostgreSQL 18.6, MySQL 8.4.12)
of the other computed keys, single file and project, matched the expected
rows on both databases. In a single file over a known input row a binding's own
errors do not change this, except that a read of a name that PIE-S2329
refused reports nothing more and, otherwise, a binding with an error of its
own whose value is a name or a computed key value, such as `k = nosuch`,
`k = j` with `j = k` or `k = lower(nosuch)`, makes
the item an unknown field (PIE-S2102 `Unknown field: k`) beside that error. An
EXPLICIT_MODULES relation over a known input row checks no window that reads
a `let` binding of unknown type, such as `k = None` or
`k = coalesce(None, None)`, or with an error of its own: the relation fails closed
with that binding's error or with PIE-S2333 at the table or query. Over
an unknown input row a selected window that reads a `let` name is instead
PIE-S2103 at the window call, whatever the name's value: in a single file over
the row of a source without a shape, read with `from` directly or through a
chain of `from` inputs, and in an EXPLICIT_MODULES relation without JOIN
inputs also over the row of a table or query one of whose SELECT outputs has
an unknown type or an error.

```pietto
shape Member:
    id: Int
    group_id: Int
    review_year: Int
    level: Int

source members: Member = postgres.table("members")

def size_band(level: Int) -> Int: return 1 if level <= 2 else 2

query review_order:
    from members
    let off_year = review_year != 2024
    let band = size_band(level)
    select:
        id
        sheet_no = row_number() window(partition by group_id order by off_year, band, id)
```

The value of `lag`, `lead`, `first_value`, `last_value` or `nth_value` and a
`lag`/`lead` default is a direct field or a literal: a `let` name there whose
value is a field, such as with `k = amount`, is that field, and one whose value
is no field, such as with `k = amount + 1` or `k = 1`, is PIE-S2104 at the
call, naming the `let` (``value must be a direct field or Bool, Text, Int,
Float, or NULL literal, not the `let` name k``).
(Single-file `check` types an authored QUALIFY and its selected or hidden
windows; see [QUALIFY](#qualify).)
Window specifications recognize authored ROWS, RANGE, and GROUPS forms with
optional EXCLUDE:

```text
rows 2 preceding
rows between 2 preceding and current row
range 2 preceding
range between 2 preceding and current row
groups 2 preceding
groups between 2 preceding and current row
rows between 2 preceding and 2 following exclude current row
range current row exclude ties
groups current row exclude group
```

Bounds may use `unbounded preceding`, an expression plus `preceding`, `current
row`, an expression plus `following`, or `unbounded following`. Ranking,
distribution, `ntile`, `lag`, and `lead` remain frame-insensitive, and an
explicit ROWS, RANGE or GROUPS frame on them is PIE-S2104. `first_value`,
`last_value`, and `nth_value` are frame-sensitive and use a concrete Pietto
effective frame even when source omits one. A `GROUPS` frame requires an
`ORDER BY`; aggregate windows without one report PIE-S2104. In a selected
window, named windows included, single-file checks require each ROWS, GROUPS or RANGE
offset to be, once `let` names are inlined, a nonnegative `Int` literal up to
9223372036854775807, and refuse a literal `ntile` count, `lag`/`lead` offset or
`nth_value` position above that value (PIE-S2104); PostgreSQL emission also
requires those three to fit signed `int32` (PIE-B1000). An EXPLICIT_MODULES
project check requires the same of each RANGE offset of any window, a QUALIFY
window included (PIE-S2104), since no target emits another RANGE offset. The
result of `lag`, `lead`, `first_value`, `last_value` and `nth_value` has the
type of its value,
or of the `lag`/`lead` default when the value is `None`, an enum's included,
so in a single file a later relation may combine the column with a field of
that enum, as in `coalesce(previous, status)`. The value or default may have
an unknown nullability, as an earlier relation's computed column such as
`v = m + 1` has, where the result's nullability does not depend on it:
always for `first_value`, `last_value` and `nth_value`, whose result may be
null; for a `lag` or `lead` value at an offset other than the literal 0
without a default or with a nullable or `None` one; and for a default when the
value is nullable or `None`, or at offset 0. Otherwise, as in `lag(v, 0)` or
`lag(v, 1, 0)`, the call reports PIE-S2104 (`value type must be concrete`, or
`default type must be concrete` for the default). PostgreSQL types a string
literal value, such as `lag("b")`, only from a default, so without one
PostgreSQL emission writes it as `CAST('b' AS text)`. Single-file `check`
applies the same admitted-window checks to QUALIFY windows. RANGE offsets retain
unresolved Phase 64 type/arithmetic requirements. GROUPS uses canonical peer
groups; EXCLUDE is a removal-only membership filter after base-frame clipping.

Value/navigation modifiers occur between the call and `window`:

```text
previous = lag(value) ignore nulls window ordered
first = first_value(value) respect nulls window(order by id)
nth = nth_value(value, 2) from last ignore nulls window(order by id)
```

Omitted NULL treatment means `RESPECT NULLS`; omitted `nth_value` direction
means `FROM FIRST`. Modifiers belong only to the concrete function use and are
never inherited from a named-window template. `check` accepts these forms, but
unsupported backend combinations such as PostgreSQL/MySQL `IGNORE NULLS`,
`FROM LAST`, MySQL GROUPS with an offset bound, or MySQL EXCLUDE CURRENT ROW,
GROUP or TIES fail closed when SQL is emitted (project MySQL emission keeps
its own GROUPS and EXCLUDE limits):
single-file `emit-sql` reports `PIE-B1000`, and project SQL emission reports
the table or query BLOCKED with `PIE-B1003`.

Each table or query body may declare query-local named-window templates with
`let`, among its lets after FROM and every JOIN and before `where`, `group by`
and `select`:

```pietto
shape Account:
    id: Int
    account_id: Int

source accounts: Account = postgres.table("accounts")

query ranked:
    from accounts
    let ordered = window(order by id)
    let per_account = window ordered(partition by account_id)
    select:
        id
        position = row_number() window ordered
        account_position = row_number() window per_account
```

Calls use a template directly or add missing local components monotonically:

```text
result = row_number() window ordered
result = row_number() window ordered(partition by account_id)
```

Empty roots and pure aliases use `let name = window()` and
`let alias = window base`. A window declared after `select`, where earlier
versions placed it, is PIE-P1000 with a suggestion to move it, and a window
anywhere else outside the lets, such as before FROM, between JOINs or after
`where`, is a syntax error (PIE-P1000). A window shares the let namespace of
its table or query: a window named like a value `let`, an input alias or, in an
EXPLICIT_MODULES project, a relation let of the same declaration is PIE-S2604
(`Duplicate query local name`) at the later of the two, while two windows of one
name stay PIE-S2110. Nor may a window, as a value `let` may not, take the name
of an input relation (the FROM binding and, with JOINs, also the FROM relation
and each JOIN's binding and relation) or of an input field (a field its
declaration gives the FROM input or a JOIN input): that is PIE-S2329
(`Let binding cannot shadow input relation` or `input field`) at the window, while a SELECT output name may repeat a window's.
Like a value `let`, a window reads only the value `let`
names declared before it: a read of one declared after it is PIE-S2330
(`Let binding cannot reference a later binding`) at the read.
Window references are query-block-local, forward/backward capable, and single-base;
duplicates, dangling references, cycles, and repeated inherited components
fail closed. Named declarations and uses preserve relation-local occurrence
identity in private IR, Project semantic provenance, and package inspection.
MySQL may preserve reachable source order; PostgreSQL uses stable base-first
ordering; exact inline fallback is used when native inheritance is not
representable. Unsupported target shapes fail closed without erasing semantic
provenance. Named windows do not cross relation blocks. Arbitrary nesting and
window expressions in unsupported clauses remain rejected.

## QUALIFY

Query blocks may add one inline `qualify expression` or an indented `qualify:`
block, whose lines are joined with `and` as in a `where:` block, after
`select` and optional `having`, but before relation `order by` and `limit`:

```pietto
shape Item:
    item: Text

source items: Item = postgres.table("items")

query top_items:
    from items
    select:
        item
    qualify row_number() window(order by item) <= 3
```

QUALIFY has its own expression grammar with the existing scalar precedence and
AST forms plus an inline-only hidden `WindowExpr`. Hidden named-window uses are
not accepted, and adding QUALIFY does not make window expressions legal in
WHERE, LET, GROUP BY, or the global scalar grammar.

In a single file, outer QUALIFY names resolve across the complete pre-window
input bucket and complete selected-output bucket. Under GROUP BY the
pre-window input bucket holds only the GROUP BY keys:
a key field, bare or qualified, and a `let` name that is a key or whose value,
also inside an `any(...)`, reads no other input field; any other input read is
PIE-S2102 (`Unknown field: price`). A query with aggregates and no GROUP BY is
one group without keys: its QUALIFY reads selected outputs and `let` names
that read no input field, and a hidden window there is PIE-S2103 (`a query with
aggregates and no GROUP BY admits no hidden QUALIFY window`). Over a source
without a shape these rules hold for the names of the fields the relation
reads, as its grouping reads them, and a name that a SELECT output has reads
that output: no collision with an unknown input field can be known there. An
aggregate is read through the selected output that computes it: an aggregate
call in a
single-file QUALIFY predicate is PIE-S2308 (`Aggregate count() is not allowed
in qualify clause; use it only as a direct aliased select projection`), with
or without GROUP BY; an aggregate window there stays legal. A unique selected
alias is bare-only and a qualified name remains input-only; duplicate outputs
retain their own diagnostics. Any collision of a selected output with a field
of the whole input, grouped or not, is ambiguous, including candidates that
evaluate to the same field, so no candidate wins; under GROUP BY or
aggregates the message offers the qualified name only when QUALIFY can read
it (`Ambiguous field: price is both the input field items.price and a SELECT
output; give the output another name`). A hidden window reads what a
selected window of the query reads and cannot consume a selected window
result: under GROUP BY, the selected keys and aggregates by their output
names. A name that such an output shares with an input field whose value it
is not, such as `cat` for `cat = max(price)` grouped by `cat`, is ambiguous
there too (PIE-S2102), in a hidden or a selected window. In an EXPLICIT_MODULES project, the existing query-block rule remains:
only selected window results form QUALIFY's selected namespace. A hidden
window in a project query with aggregates and no GROUP BY, also over JOIN
rows, is the same PIE-S2103 as in a single file (`a query with aggregates and
no GROUP BY admits no hidden QUALIFY window`), at the call. A project
relation with JOIN inputs that mixes an aggregate with another projection
without GROUP BY (PIE-S2312) checks its QUALIFY by the single-file rules
above beside that error, unless its `let:` clause or WHERE is refused, when
it reports only that refusal (a known limitation; see PIE-S2312 in the
[diagnostics](spec/diagnostics.md)).

An EXPLICIT_MODULES QUALIFY requires at least one selected or hidden window
computation. A single-file QUALIFY has no corresponding window-presence gate,
but its predicate and every hidden window reuse the scalar and Bool kernels; a
known nullable Bool is legal. SQL truth retains only TRUE and drops FALSE or
UNKNOWN. Completed EXPLICIT_MODULES semantics and private Query-block IR retain
QUALIFY, final relation ordering and output. Single-file Script IR also lowers an admitted
QUALIFY from its typed predicate and selected/input bindings; it is not an
automatic PIE-I1000 in `explain` or `emit-sql`. Project SQL emission
(`emit-sql --project`) keeps its separate query-block route.

## Modules and relationships

Module statements keep explicit declaration kinds, aliases and source order
(checked alone, as a single file, each is the PIE-S2708 warning):

```pietto PIE-S2708 PIE-S2708
from "shared/types.pietto" import (
    type UserId,
    shape User as SharedUser,
)
export type UserId, shape SharedUser
```

An import target is the path of another selected source of the project,
relative to the project root and written with `/` separators: no `./`, no
leading `/`, no `..` and no `\`. In a project that selects
`models/*.pietto`, `models/orders.pietto` imports `models/types.pietto` as
`from "models/types.pietto" import (...)`, never `from "types.pietto"`. An
unresolved target is PIE-S2701; when a selected path is what it may have
meant (relative to the importing file, with another letter case or a
different separator, or without `.pietto`), the message names it. A source
that `[sources]` excludes is not selected, so no module can import it.

The admitted kinds are `type`, `enum`, `shape`, `source`, `table`, `query`,
`def` and `relationship`. An import must name the kind that the target exports: `shape customers` for an
exported `source customers` is PIE-S2705, which names the exported kind.
Re-exports chain through any number of modules. Module resolution preserves declaring identity, visibility, every collision,
dependency evidence, provenance and lineage; it never chooses a first or last
winner. These statements do not add wildcard imports (`def *` is PIE-P1000),
qualified calls such as `a.pos(x)` (PIE-S2103 says which import to write, then
to call `pos(...)`), or `constraint` and `derive` items (PIE-P1000).

An import cycle is PIE-S2703. While any module cycle exists, project checking
and emission stop before relation completion in every module; completion-only
diagnostics appear after the cycles are resolved. The existing module and
project contracts remain in [Projects and packages](project-package.md).

Shape-typed relationship predicates use the supplied-row form described in
[Named inputs and reusable relationship predicates](#named-inputs-and-reusable-relationship-predicates).
They preserve declared shape identity through imported source/shape aliases.
A module may export a relationship (`export relationship OrderCustomer`) and
another may import it (`from "models/a.pietto" import relationship
OrderCustomer`, or `relationship OrderCustomer as oc`), in either list form; a
re-export chains as any other. The relationship's body and parameter shapes
are checked once, in its module: a call in the importer, in `on`, WHERE,
SELECT or `any(...)`, binds its rows as a call of a local relationship does,
each row by the declaring module's shape identity (a source of a shape that
the importer declares itself has another shape, PIE-S2604), and the SQL is
the same as the local relationship's; a `concat` call in its body stays the
built-in also in an importer that declares a callable `concat`. An importer
need not import the parameter shapes to call it. A relationship that is not
exported stays private to its module; calling it, or an exported one that is
not imported, from another module is PIE-S2103 with the export and import to
write; when only a module that imports the calling one declares it, or the
calling module already declares or imports the name, PIE-S2103 says to
declare it in the calling module, as before. A relationship import binding
that collides with a local declaration (a def or relationship included) or
another import binding is PIE-S2706 (`; import relationship OrderCustomer as
<name>`); a module's own def or relationship collides only with a def or
relationship import. A binding named like a built-in function, `Float`,
`Text` or `concat` included, is PIE-S2398. A def or relationship import or
export item that fails, or one along an import cycle (PIE-S2703), stops the
check before semantic analysis. A PACKAGE_ROOT package module refuses each
def or relationship item with PIE-S2707.
Their validation and callable-resolution errors use PIE-S2604. Old endpoint
metadata, source-bound one-line relationships and VIA paths are legacy forms:
the modern public parser refuses them, and `migrate` requests manual identity
review rather than guessing equivalent templates, row aliases or proof facts.

## Diagnostics, IR, SQL, and output

Parser, semantic, IR, backend, and runtime diagnostic families remain
separate. Diagnostic codes, ordering, and source locations are stable public
behavior as described in [diagnostics](spec/diagnostics.md).

A single-file expression that nests more than 450 levels (see Expressions), in
a relationship predicate or a type `ensure` condition too, fails closed with
PIE-S2006 over that whole file. In a project, an expression nested deeper than
the compiler's recursion limit allows, such as a WHERE of several hundred `and`
conditions, fails closed with PIE-S2006 over one whole file. A project reports
it from `check --project` and, BLOCKED, from `emit-sql --project`: for the
module whose own syntax checks exceed the limit, or, once the modules are
analyzed together, for the module whose syntax, each `def` call counted as its
expansion, nests deepest, Project emission uses more of the limit than project
checking, so `emit-sql --project` can report PIE-S2006 for a project that
`check --project` accepts; when planning or emitting the selected `table` or
`query` exceeds the limit, it reports it for the selected module, also when the
deep syntax is in a declaration it reads from another module.

IR construction consumes successful semantic facts without reparsing or
mutating earlier stages. SQL backends consume IR and fail closed on unsupported
hand-built or unavailable shapes. Stable reviewed SQL bytes are owned by the
[golden fixture policy](spec/golden-fixture-policy-v1.md).

CLI JSON contracts are [CLI JSON v1](spec/cli-json-v1.md),
[project JSON v2](spec/project-cli-json-v2.md), and
[Semantic Metadata Artifact v1](spec/semantic-metadata-artifact-v1.md).

## Parameterized Decimal domain (Phase67 Slice06)

The shared type-argument rule accepts `Decimal(p, s)` with integer literals `1 <= p <= 65` and `0 <= s <= p`. This deliberately extends the previous precision ceiling of 38 at existing type sites and safe aliases. Plain `Decimal` and `Decimal()` still carry no parameter fact. Argument syntax, diagnostics and arithmetic precision policies are unchanged.

Current PostgreSQL/MySQL producer admission additionally requires matching retained/storage/domain parameters and `s <= min(p, 30)`. Language acceptance alone is not producer success. The private result adapter uses Decimal128 for p<=38 and Decimal256 for p=39..65; it does not infer parameters or widen the language domain from Arrow capacity.

## Timestamp and UUID source meaning

Builtin names alone do not supply temporal/UUID meaning to project SQL. The
compiler derives the approved closed meaning only for exact verified
source/type occurrences and retains it through the result contract; source
declarations and Arrow metadata cannot manufacture the upstream evidence.

Civil Timestamp values are timezone-free proleptic Gregorian microseconds in
the inclusive interval `1000-01-01 00:00:00.000000` through
`9999-12-31 23:59:59.499999`; the last fractional bound applies only at that
final endpoint. UUID values preserve all 128 bits in standard big-endian order,
with no version restriction. The selected source mapping is PostgreSQL
`timestamp without time zone(6)`/`uuid` and MySQL `DATETIME(6)`/`BINARY(16)`.
Qualified project SQL admits carrying and projecting these values, and a
source or derived `Date` too, `==`/`!=`, `count`, `count_distinct`,
`DISTINCT`, `GROUP BY`, and a window partition key, which compares by equality
as `GROUP BY` does; a source field of these types, but not a derived `Date`,
is also a key of a direct inner/left/right equality join. Timestamp and Date
values of one carrier also compare with `<`, `<=`, `>`, `>=` and inclusive
comparison chains, in WHERE and in a JOIN ON condition alike, and order a
result or a window; they are also `min`/`max` arguments, whose result keeps
the carrier and admits NULL (MySQL `MIN` and `MAX` return `DATETIME(6)`,
microseconds kept, and `DATE`). UUID values of one carrier also compare
with `<`, `<=`, `>`, `>=` and inclusive comparison chains and order a result
or a window, by their 16 bytes compared as unsigned big-endian values: the
order of PostgreSQL `uuid_cmp`, of MySQL `BINARY(16)` byte comparison and of
Python `uuid.UUID`. `min`/`max` of a UUID, a
Timestamp compared with a Date, full joins on these keys, a RANGE frame offset
over a temporal or UUID order key, range relationships, timezone conversion,
parsing, and other casts remain unavailable (the latest earlier row is the
[backward asof JOIN](#backward-asof-join)); `min` and `max` refuse a UUID argument with
PIE-S2314 before emission.
