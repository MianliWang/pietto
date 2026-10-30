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

A file may still begin with the older header lines `pietto <number>`,
`mode <mode>`, `dialect <name>`, and `encoding <name>`, each optional but in
that order, for example `pietto 0.9` followed by `mode checked`. The number is
digits with at most one `.` between them, such as `1` or `0.9`: a bare `pietto`
line or a three-part version such as `pietto 0.1.3` is a syntax error
(PIE-P1000), and the number is not compared with the Pietto version. These
lines do not select a language version: the compiler defaults to the modern
syntax below, and the header never enables legacy spelling. Only `mode` has an
effect, and only in single-file commands, where `--check-mode` overrides it;
`dialect` never selects the SQL backend.

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

### Migrating old source

The public parser uses modern spelling by default. Retired spellings receive
PIE-P1000 before AST normalization; its message states the located rewrite,
which JSON output also carries as the diagnostic's suggestion. The
private legacy reader exists for diagnostics and migration, not as another
public compiler mode. The `pietto NUMBER` header remains metadata; there is no
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
several files, add the imports and exports its modules need and declare each
relationship in the module whose JOINs call it, as a relationship is not
imported (see [project and package](project-package.md#schema-compatibility)).

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
database UNIQUE behavior.

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
        id asc
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
output is accepted (`order by n` with `select n = count()`). A JOIN relation
with an aggregate and no GROUP BY instead refuses the entire ORDER BY clause
with PIE-S2334. A grouped key stays PIE-S2321. When a SELECT item would capture a key that is a bare input
field once `let` names and SELECT output names are inlined (an output of the
same name, which MySQL compares case-insensitively, or any unaliased item,
which PostgreSQL and MySQL each name by rules of their own), the emitted SQL qualifies the key with the name FROM
already gives the input, as in `FROM "sales"."orders" ... ORDER BY
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

Shape parameters resolve by declared shape identity, including their declaring
module; matching field names do not establish the same shape. Each call binds
its actual row occurrences independently, even when several rows share a source
or shape. Current JOIN null-extension remains authoritative over a shape's
original non-null fields. Calls are available in ON, WHERE and SELECT and may
be combined with the admitted Boolean operators. The body is one expression,
on the header line after ':' or alone in its block, as a `def` body is. It may
contain literal filters, comparisons and AND/OR/NOT; it reads only its supplied
rows. Aggregates,
windows, ANY and other relation reads are not available inside a relationship
body. A scalar `def` remains the separate mechanism for reusable scalar inputs.
Callable collisions retain their existing namespaces and report ambiguity.

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
NULL is equivalent to NULL. Only UNION ALL needs no row equivalence, allowing
matching concrete Float/Any/Bytes/Json types. The other five forms reject these
types; Float and aliases remain deferred to Phase 72 without a finite exception.
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
unsupported. D07-FLOAT-DEFERRED also excludes Float and resolved Float aliases,
including finite literals and computed/aggregate/window results; Float row
equivalence belongs to Phase 72. Unselected Float fields do not cause rejection,
and other Float operations, including count_distinct, retain existing behavior.

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

An EXPLICIT_MODULES project also accepts the resolved FROM relation's original
qualified spelling, which 0.1.5 accepted in WHERE, GROUP BY, an ungrouped
ORDER BY and a grouped SELECT only: after
`let c = customers` and `from c`, both `c.id` and `customers.id` read the one
FROM occurrence, in every clause but HAVING and the ORDER BY of a grouped
query, but only in a query without a JOIN, and not inside `any(...)`. A
project HAVING or grouped ORDER BY reads no qualified input field, with or
without an alias: it reports PIE-S2327 or PIE-S2321 as a single file does
(0.1.5 reported the bare PIE-S2333). Elsewhere, such as in a JOIN's `on`, after a JOIN or in a self
JOIN, `customers.id` is refused as in 0.1.5. This does not make an
intermediate alias in an alias chain an input name, and it does not cross a
capture boundary. Single-file checks keep the rule above and accept only
`c.id`.

Every JOIN but CROSS has an `on` predicate: a declared relationship never joins
by itself, and a JOIN without `on` is PIE-S2335
(``JOIN c: write `on` with the condition that matches orders to customers``).
CROSS takes no `on` (PIE-S2336). An `on` is an ordinary row predicate: field
comparisons, calls of [relationship predicates](#named-inputs-and-reusable-relationship-predicates)
such as `on OrderCustomer(orders, customer)`, and their `and`, `or` and `not`
combinations. A relationship call takes, for each parameter, an input that
reads a source of that parameter's shape; a table or query input is no such
row (PIE-S2604 `Unavailable row argument for relationship <name> parameter
<role>`), so write the condition out in `on` to join one.

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
of several rows that tie on every key fill the last places. An ORDER BY that
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
with `limit 1` is NULL for an outer row without a row and that row's value
otherwise; a larger limit keeps the runtime error for more than one row
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
PIE-S2803. To collect per group, group in another table or query, read it with
`from`, and collect a let that captures it. A Collect of a source, table
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
different things. The value has no comparison, ordering, grouping or scalar
value: a reader of the relation may read it with `from` or a JOIN, test it
with `exists` and read its scalar columns, but any read of the nested field
itself (in WHERE, JOIN ON, a row `let`, GROUP BY, `having`, a window,
`qualify`, `order by`, a SELECT expression, `any(...)`, `scalar` or `in`),
selecting it again in another relation, `select distinct` with a Collect item,
and a set operation over it are PIE-S2805.

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

These values are typed but not yet lowered: each Collect read and each Unnest
let is PIE-S2802, so such a project, the admitted programs above included,
does not yet check or emit SQL. Single files, LEGACY_FLAT projects and package
modules refuse both spellings with PIE-S2801, which says how to make a
`schema_version = 2` project.

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

Each parameter names exactly `Bool`, `Int`, `Float` or `Text`, with `| None` when its value may be None; a query declares at most 64 (PIE-S2353), and a repeated
name is PIE-S2001. These declaration checks, the position checks below and the
alias check of an unaliased read run before semantic analysis: each file
reports them after its temporary diagnostics, and semantic analysis then does
not run. In that query's body a bare name equal to a parameter reads
the parameter. A parameter name that is also an input field (a typed VALUES
column of a FROM or JOIN input included), a `let` name, a relation name of the
module, a JOIN binding, a SELECT output or a named window is an error
(PIE-S2354), so a read never changes meaning; a SELECT item that only reads a
parameter needs its own alias. A read is typed as its declaration: a `Text`
parameter is a `Text` operand that is not a literal, so comparing it with a
`Date`, `Timestamp`, `UUID`, `Bytes`, `Json` or enum field is PIE-S2105 (see
Comparisons), and no parameter can stand for a value of those types.

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
(PIE-S2105). Numeric literals may contain separators such as `1_000` and `1_000.25_0`;
they retain the existing length and finite-value bounds. `lower <= value <= upper`
uses the existing inclusive-range semantics, including NULL bounds, and other
admitted comparison chains preserve source order. A single-file expression nests at most 450 levels: each operator,
operand, call, cast or conditional on its deepest path counts one, so a chain
such as `a and b and c` or `x + y + z` nests one level per operand, and a `def`
call counts as its expansion (see [Inline functions](#inline-functions-def)). A
single file with a deeper expression anywhere, a relationship predicate, a
type `ensure` condition and a window frame offset included, fails `check`,
`emit-sql` and `explain` alike with PIE-S2006. A project is not held to that
bound (see Diagnostics, IR, SQL, and output).

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
would return a DECIMAL, emits `a DIV b`. PostgreSQL does not yet truncate an
`Int` operand that it holds as `numeric`, such as `sum` of a `bigint` column
(see [Aggregates and grouping](#aggregates-and-grouping)): there `s / 2` with
`s = 3` is `1.5000000000000000`, while MySQL's `DIV` gives `1`, so a filter on
it can keep different rows. With a `Float` operand the result is a
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
raises an error, while MySQL `/` and `DIV` return NULL. Dividing the smallest
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
PIE-S2395. This expression relaxation applies to single-file checks only. A
`def` body, typed with its declared parameter types, must still have its
declared result type (PIE-S2402). Both project modes keep the typed twin's
diagnostic at an incompatible expression (PIE-S2104, PIE-S2105 or PIE-S2395).
Only an EXPLICIT_MODULES relation refuses `n + None` with PIE-S2333.
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

The closed scalar surface has explicit signatures, and no argument is
converted to fit one, except for the single-file always-null numeric D-12 rule
described above:

```text
lower(Text) -> Text
upper(Text) -> Text
trim(Text) -> Text
len(Text) -> Int
matches(Text, Text) -> Bool
substr(Text, Int, Int) -> Text
replace(Text, Text, Text) -> Text
contains(Text, Text) -> Bool
starts_with(Text, Text) -> Bool
ends_with(Text, Text) -> Bool
coalesce(T, T, ...) -> T
nullif(T, T) -> T
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
```

`sign` returns -1, 0 or 1 as an `Int`. In a single file, D-12 also admits an
always-null Float numeric expression such as `sign(None + fl)`, which is a
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

`coalesce` requires at least two same-canonical-type arguments. In a single
file, D-12 permits an always-null numeric argument of another numeric type;
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
`def Float` or `def Text` takes precedence regardless of its declaration order
or arity; a same-named `constraint`, `derive` or relationship template also
keeps its existing meaning. Qualified calls are not constructors.

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
that derived Date. Date has no independent selected-project source, literal,
parsing, arithmetic, or timezone surface. There is no arbitrary Python
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

- Where: single files and EXPLICIT_MODULES projects (schema version 2). A def
  belongs to its module: another module cannot call it (PIE-S2103), export it
  or import it. An `export def f` or an import item `def f` is PIE-P1000;
  naming the def under another kind, as in `export table f`, is PIE-S2704 (PIE-S2705 for an `import` item). A LEGACY_FLAT
  project check refuses every def with PIE-S2379. PACKAGE_ROOT
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
  conversion (an `Int` value does not fit a `Decimal` parameter). In a
  single-file check, an always-null numeric argument also fits a nullable
  numeric parameter of another numeric type, while retaining its own type; it
  does not fit a Text or non-null parameter. An argument
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
count count_distinct sum avg min max string_agg
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
field values. The selected project numeric boundary admits Int unary `+`/`-`,
`abs` and binary `+`, `-`, `*` only when the compiler can propagate a signed
range that fits the selected physical carrier. `abs` of an `Int` is proved in
its operand's integer type, as unary `-` is, and fits exactly where `-` fits:
where `-id` is PIE-B1002 (`unary_result_outside_physical_range`), `abs(id)`
is PIE-B1002 (`abs_result_outside_physical_range`), though unlike `-` it
reads no query header parameter (PIE-S2355); `abs` of a `Float` or `Decimal`
keeps its argument's carrier. It also admits `avg(Int)` for a direct
Int input with `int_range` evidence, casting that input to the target Float
carrier before aggregation. Empty and all-NULL inputs remain NULL. Project SQL
emission (`emit-sql --project`) reports `sum(Int)` BLOCKED with `PIE-B1004`
(`sum_int_aggregate_range_proof_missing`) until an aggregate-range proof
exists, although `check --project` accepts it and single-file `emit-sql` emits
`SUM`; Decimal `sum`/`avg` require
an exact aggregate range/scale and division proof, and Float `sum`/`avg`
require a finite-result proof. A source range, free JSON declaration, renderer
spelling, or database default rounding rule is not such proof. `min` and `max`
retain their bounded direct-field surface; in EXPLICIT_MODULES projects they
also accept one row `let` name, and the result keeps that value's proven range
while admitting NULL. With JOIN inputs the argument reads the exact JOIN-side
fields of that value under the same fan-out law as a direct field argument; a
value that reads no joined field, such as `level = 3` or a header parameter,
links no JOIN side, so the group keys alone must fix every side. In a single
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

Single-file `emit-sql` renders `sum` without a cast, and `avg` without one
except over `Int`, so each result column has the type the target gives that
aggregate. Over `Float` it is a floating-point type and over `Decimal` it is
PostgreSQL `numeric` or MySQL DECIMAL, as the Pietto types say. `sum(Int)` is
an `Int`, a whole number, returned in the target's exact type: PostgreSQL
`bigint` for a `smallint` or `integer` column and `numeric` for a `bigint`
column, and MySQL DECIMAL. These `numeric` and DECIMAL sums are exact and can
leave the signed 64-bit range. `avg(Int)` is a `Float` average on both
targets: as in project SQL, its argument is cast before averaging (PostgreSQL
`AVG(CAST(x AS double precision))`, MySQL `AVG(CAST(x AS DOUBLE))`), so the
target returns a binary64 average instead of its own decimal one.

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
Every other aggregate, including `min`, `max` and `count_distinct`, must pass
the following conservative rule; a failure is PIE-S2381 at the aggregate call
in every check mode.

Start with the inputs the argument reads, following `let` values, and each
source input whose declared unique key (`name = unique(...)` in its shape) is
entirely in GROUP BY with every key field never None in the source shape.
Field-renaming `let` keys count; computed keys do not. Close that set using
only required equalities, the `==` comparisons of two fields of different rows
among top-level `and` operands, that match every field of a declared unique
key of an input's source to fields of inputs already in the set; the key
fields may be nullable:

- In an INNER or LEFT JOIN's `on`, an equality written by hand, such as
  `orders.customer_id == customer.id`, or one in the body of a relationship
  call there, adds the JOIN's own input in this way; both spellings prove the
  same. In an INNER JOIN's `on` it may also add an earlier input, such as the
  FROM input when the equality matches its key to the JOIN's input.
- In the WHERE, only the equalities of a relationship call that is a
  top-level `and` operand may add an input, any input; a hand-written WHERE
  equality adds none.

The set must then contain the FROM input and every JOIN input; the relation of
an `any` or `not any` filter is never one. RIGHT, FULL and CROSS JOINs add no
dependencies, and neither does an equality or a call under `or` or `not`.
Keys are taken only from source shapes, never inferred through tables or
queries. Outer NULL extension does not justify a RIGHT/FULL
dependency: one NULL left part may match several preserved rows. Group
protection uses the source's never-None key so a NULL-extended part remains
one fixed value within a group.

PIE-S2381 names the JOINs that may repeat the aggregate's rows, as a
project's PIE-S2333 does, and the remedies that can close the rule: matching a
declared unique key of each named input in `on` with a relationship call or a
mandatory positive equality written by hand, `any(...)` for an input that only
filters rows, or aggregating in a separate query first. The matching key may
be nullable; this does not relax the separate GROUP BY requirement that a
source key used to start the grouped set have fields that are never None. It
never suggests grouping by such a
key, which would change the result's grain. With
`inner join customer on orders.customer_id == customer.id`, where the shape of
`customer` declares no unique key, `count(orders.id)` grouped by
`customer.name` reports:

```text
An aggregate may read rows repeated by JOIN customer; match a unique key of customer in `on`, use `any(...)` for an input that only filters rows, or aggregate in a separate query first
```

Once the shape declares `customer_key = unique(id)`, the same `on` proves that
each order matches at most one customer, as the relationship call
`OrderCustomer(orders, customer)` does.

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
without `any(...)`, `order by` and `limit`. An `on` equality does not match
yet the key of a query with GROUP BY, an `any(...)` filter, a window, QUALIFY,
`select distinct`, a JOIN or a FROM over a query block (a grouped query's key
still protects its own GROUP BY), and a refusal then does not ask to match it.
A single file matches only a key that a source's shape declares. A project takes these
equalities only from `on`, never from WHERE, not even from a relationship call
there; a single file also takes those of a relationship call in WHERE (see
above), never a hand-written WHERE equality.
A filtered relationship may preserve an upper bound but does not prove coverage.
OR, NOT, a source name, a same-shaped row or a key on the aggregated side alone
does not supply the missing proof. Nullable keys retain their existing
NULL-sensitive restrictions, especially after RIGHT/FULL unmatched rows.

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

`count()` counts joined rows and needs no input-row fan-out proof; `min`, `max`
and `count_distinct` have no blanket exemption. Unsupported cases remain
PIE-S2333, whose message may identify repeating JOINs and available unique-key
or group-key remedies. The selected SQL/compiled aggregate path still refuses
Bool arguments: typed semantic facts for `count(predicate(...))` do not by
themselves establish emission or source-free execution capability. ANY does not
widen that domain. Project `sum(Int)` still needs the aggregate-range proof
described above.

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
domains, and Float keys stay refused. Grouped result ordering may name the
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
        position = row_number() window(order by id asc)
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
reads. This is a single-file surface:
EXPLICIT_MODULES project checks retain their existing unsupported-window
boundary. Aggregate windows do not accept `ignore nulls`, `respect nulls`,
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
qualification, and direction. Each item names a field: an expression reports
PIE-S2103 (`window partition expression must be a direct field` or `window
order expression must be a direct field`) at the window call. A `let` name
there stands for its value once its `let` names and `def` calls are
expanded: a field, such as with `k = t`, is read as that field, and a value
that is no name, such as with `k = lower(t)` or `k = 3`, is PIE-S2103 at the
window call, as that value written there is (a `def` call written there is
PIE-S2397 instead). In a single file over a known input row a binding's own
errors do not change this, except that a read of a name that PIE-S2329
refused reports nothing more and, otherwise, a binding with an error of its
own whose value is a name, such as `k = nosuch` or `k = j` with `j = k`, makes
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
only selected window results form QUALIFY's selected namespace.

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

The admitted kinds remain `type`, `enum`, `shape`, `source`, `table` and `query`.
An import must name the kind that the target exports: `shape customers` for an
exported `source customers` is PIE-S2705, which names the exported kind.
Re-exports chain through any number of modules. Module resolution preserves declaring identity, visibility, every collision,
dependency evidence, provenance and lineage; it never chooses a first or last
winner. These statements do not add wildcard imports or a new relationship
export kind.

An import cycle is PIE-S2703. While any module cycle exists, project checking
and emission stop before relation completion in every module; completion-only
diagnostics appear after the cycles are resolved. The existing module and
project contracts remain in [Projects and packages](project-package.md).

Shape-typed relationship predicates use the supplied-row form described in
[Named inputs and reusable relationship predicates](#named-inputs-and-reusable-relationship-predicates).
They preserve declared shape identity through imported source/shape aliases.
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
Qualified project SQL admits carrying and projecting these values, `==`/`!=`,
`count`, `count_distinct`, `DISTINCT`, `GROUP BY`, and direct inner/left/right
equality joins. Ordering and inequality comparison, `min`/`max`, full joins,
a `Timestamp` or `UUID` window partition or order key, range/as-of behavior,
timezone conversion, parsing, and other casts remain unavailable.
