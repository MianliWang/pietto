# Pietto language

Pietto is a gradual semantic SQL authoring DSL. Its compiler pipeline is:

```text
source -> parse -> analyze -> immutable IR -> selected SQL dialect -> CLI text/JSON
```

Pietto compiles SQL; its compiler and CLI do not connect to a database or
execute SQL ([Execution](execution.md) describes the separate execution alpha).
Syntax may be broader than the currently supported semantic and backend subsets.
Unsupported combinations fail closed with deterministic diagnostics.

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

The single-file `check`, `explain`, and `emit-sql` commands choose the check
mode with `--check-mode loose`, `checked`, or `strict`; the default is
`checked`. The mode sets the severity of three diagnostics: implicit
nullability (PIE-S2005), a source without a shape (PIE-S2303), and a computed
projection without an alias (PIE-S2304). `loose` omits them, `checked` reports
them as warnings, and `strict` reports them as errors. Project commands reject
`--check-mode`. SQL emission always takes its dialect from `--dialect`;
PostgreSQL and MySQL are the current backends.

A file may still begin with the older header lines `pietto <number>`,
`mode <mode>`, `dialect <name>`, and `encoding <name>`, each optional but in
that order, for example `pietto 0.9` followed by `mode checked`. The number is
digits with at most one `.` between them, such as `1` or `0.9`: a bare `pietto`
line or a three-part version such as `pietto 0.1.3` is a syntax error
(PIE-P1000), and the number is not compared with the Pietto version. These
lines are accepted for now and will be retired later. Only `mode` has an
effect, and only in single-file commands, where `--check-mode` overrides it;
`dialect` never selects the SQL backend.

Top-level declarations are `type`, `enum`, `constraint`, `derive`, `def`,
`shape`, `source`, `table`, and `query`. Relationship metadata and module
`import` / `export` statements are also accepted at top level.

### Layout

Lines end at LF, CRLF or a lone CR, as [Source structure](#source-structure)
states; the layout rules below, the indentation and parenthesized-line checks
among them, count each as one line end. A file must not start indented:
an indented first code line, after any blank or comment lines, is PIE-P1000
(`Unexpected indentation.`) at that line. The rest of the file is measured as
if that line started at column 0, so a file indented as a whole can also get a
PIE-P1003 at a later line. A line may be indented with spaces only: a tab is
PIE-P1004, and a form feed, a vertical tab or a Unicode space such as a
no-break space in a line's indentation is PIE-P1000 (`Unexpected character
U+000C in indentation; indent with spaces.`).

A list clause, that is `select:`, `select distinct:`, `group by:`, `order by:`
(of a relation or a window), `partition by:`, the row `let:` and `enum NAME:`,
writes its items after `:` on the header line, separated by commas, or in an
indented block whose lines each hold one item or a comma-separated list. It
uses one form or the other: content on the header line cannot be followed by
an indented block. A list has no trailing comma; a line that ends with `,` is
PIE-P1000 and does not continue on the next line. Inside parentheses, call
arguments and parameter lists keep their optional trailing comma. In `select`,
`name = expr` names one item, like a keyword argument in a Python call, so
`select: id, total = sum(amount)` has two items. A window item such as
`n = row_number() window w` stands alone on its block line.

A condition clause, that is `where:`, `satisfying:` and a shape's
`check NAME:`, holds one condition after `:` or one condition per line of an
indented block. The lines are joined with `and`, each line as if it were
written in parentheses, so

```pietto
where:
    status == "paid"
    email like "%@%" and coupon_code is null
```

means `where (status == "paid") and (email like "%@%" and coupon_code is
null)`. `where x` and `where: x` are the same clause. A block line cannot
start with `and` or `or`; one condition continues over several lines inside
parentheses (below). An empty condition block is PIE-P1000.

Only these clauses, a one-line relationship, the one step of a JOIN header
and a `def` body take content after `:` on the header line (see
[Sources and relations](#sources-and-relations) and
[Inline functions](#inline-functions-def)). A window block (`window:`,
`window name:` or `window name = base:`) never does: `window w: order by: id`
is PIE-P1000, while `window w:` followed by an indented `order by: id` is
accepted. The bodies of `shape`, `table`, `query`, `qualify:`, `import`,
`export` and a relation let stay indented blocks.

Inside parentheses, line breaks do not end the line, so an expression can
continue over several lines. The depth of the space indentation of the
continuation lines does not matter (a tab there is still PIE-P1004), and blank
lines and comments may appear between them:

```pietto
where (region == "EU"    # Europe
    or region == "NA")
```

There is no backslash continuation, and only parentheses join lines. A `(`
that is never closed is PIE-P1008 at the innermost open parenthesis, and the
rest of the file is not parsed. A window block that opens inside parentheses
(`window:` or `window name:` ending a line in `qualify:`) keeps its line breaks
until those parentheses close, as it always did:

```pietto
qualify:
    coalesce(lag(n) window:
        order by:
            item
    , 0) > 1
```

Some keywords are soft. `pietto`, `mode`, `dialect`, `encoding`, `loose`,
`checked`, `strict`, `type`, `enum`, `constraint`, `derive`, `shape`, `check`,
`unique`, `on`, `index`, `when`, `source`, `table`, `from`, `where`, `select`,
`query`, `limit`, `ensure` and `is` may also name a shape field (and its
`unique` or `index` entries), a `select` output, a row `let:` binding, a
parameter or a typed VALUES column, and expressions read such a name as usual,
as in `where type == "click"` or `scalar r.select`. They do not name
declarations or relations. `and`, `or`, `not`, `null`, `true`, `false`,
`between`, `like`, `nullable` and `window` are reserved.

None of this changes meaning. A clause written on its header line, as comma
lines or as a condition block parses to the same tree as its one-item-per-line
form or its `and` chain, and checks and emits the same SQL. Rewritten with
these forms (and the one-line `type T = Int not null ensure ...` form), a
105-line single-file program of two tables and a window query becomes 85
lines, and `emit-sql` writes byte-identical SQL for PostgreSQL, and for MySQL
with the source written as `mysql.table`. One of its tables, before:

```pietto
shape Order:
    id: Int not null
    customer_id: Int not null
    status: Text not null
    region: Text not null
    email: Text nullable
    coupon_code: Text nullable
    ordered_at: Timestamp not null

source orders: Order is postgres.table("shop.orders")

table paid_orders_2026:
    from orders
    let:
        in_2026 = ordered_at between "2026-01-01 00:00:00" and "2026-12-31 23:59:59"
        reachable = email like "%@%" and coupon_code is null
        contact = lower(trim(email))
    where status == "paid" and in_2026 and reachable and region in ("EU", "NA")
    select:
        id
        customer_id
        region
        contact_email = contact
    order by:
        ordered_at desc
        id desc
    limit 100
```

and after, over the same shape and source:

```pietto
table paid_orders_2026:
    from orders
    let: contact = lower(trim(email))
    where:
        status == "paid"
        ordered_at between "2026-01-01 00:00:00" and "2026-12-31 23:59:59"
        email like "%@%" and coupon_code is null
        region in ("EU", "NA")
    select:
        id, customer_id, region
        contact_email = contact
    order by: ordered_at desc, id desc
    limit 100
```

The conditions need no `let:` names, so `let:` and `where` take one line more
than before; `select` and `order by` take fewer, and `from` and `limit` keep
their one line.

## Single files and projects

`check FILE`, `explain FILE` and `emit-sql FILE --dialect ...` read one file.
A table or query reads a relation with `from` and may add row `let:` bindings,
`where`, grouping and aggregates, `satisfying`, window calls, `order by` and
`limit`. Single-file `check` and PostgreSQL `emit-sql` also support INNER,
LEFT, RIGHT, FULL, CROSS, SEMI and ANTI JOINs, binding-field reads and guarded
aggregation over JOIN rows, within the [single-file JOIN limits](#single-file-joins).
MySQL emission refuses each JOIN relation with PIE-B1000 and keeps the file's
other artifacts. Single-file `explain` refuses each JOIN relation with
PIE-I1000 at stage `ir`: Semantic Metadata Artifact v1 describes one input
per relation. Its JSON envelope stays unchanged.

The following forms need an explicit-module project (`schema_version = 2`, see
[Projects and packages](project-package.md#schema-compatibility)):
`select distinct:`, set operations (`union`, `intersect`, `except`), relation
lets (`let NAME:`), query header parameters, typed VALUES bodies,
`generate_series`, and `exists`, `scalar` and `in` relation reads.
`check --project` checks them, and `emit-sql --project` emits one selected
table or query for one dialect under an emission contract, within the target
limits and contract premises described below. Single-file commands refuse
these forms with an ERROR: PIE-S2334 for DISTINCT and set operations, and
PIE-S2345 to PIE-S2352 for relation lets, header parameters, VALUES bodies,
relation reads, `capture` lines and table functions. A set-operation input is
PIE-S2334 at its `from` or JOIN.

LEGACY_FLAT project checks keep their existing boundaries: JOIN kinds other
than INNER/LEFT relationship traversal and JOIN-local `on` remain unavailable,
and omitted relationship sources and VIA roles are not inferred. The
single-file JOIN support does not widen LEGACY_FLAT, PACKAGE_ROOT or the
EXPLICIT_MODULES project's target and execution contracts.

Common SQL forms map to these project forms:

| SQL | Pietto |
| --- | --- |
| `WITH x AS (...)` | a relation let `let x:` at the start of the body |
| `FROM (subquery)` | a relation let `let x:`, read with `from x` |
| `EXISTS (subquery)` | `exists x` over a relation or let `x` |
| `value IN (subquery)` | `value in x`, where `x` has one output column |
| `(SELECT c FROM ...)` | `scalar x.c` |
| `UNION`, `INTERSECT`, `EXCEPT` | `union all:`, `intersect distinct:`, `except all:` and so on, with named operands |

A single file that passes `check` can still fail to emit. `check` stops after
semantic analysis. `explain` and `emit-sql` also build IR, which refuses an
authored `qualify:` block with PIE-I1000. `explain` separately refuses JOIN
relations as described above. `emit-sql --dialect X` then asks the X backend,
which refuses with PIE-B1000 forms it does not support, for example `ignore nulls` and `from last` on both backends,
GROUPS and EXCLUDE frames on MySQL, and a source whose connector is not
`X.table`. MySQL refuses every JOIN relation; PostgreSQL refuses the two
FULL JOIN cases described below. PostgreSQL also refuses a table or query
that another relation of the file reads through `from` or as a JOIN target
when one of its outputs is `null` itself, such as `v = null`, a
`let:` name bound to `null` or a `def` call that is `null` once written in, or
a conditional, `coalesce` or `nullif` whose every value is such a `null`, such
as `v = null if b else null` or `c = coalesce(null, null)`, as PostgreSQL
would give the reader a `text` column where Pietto has no type (a project
refuses such an output at check with PIE-S2333). Only `emit-sql
--dialect X` shows that a file emits for X.

## Types and shapes

The builtin scalar names are:

```text
Any Bool Bytes Date Decimal Float Int Json Text Timestamp UUID
```

Enum declarations are nominal definitions rather than builtin scalar names.
Nullability is explicit with `nullable` or `not null`; an omitted modifier
retains the compiler's implicit/unknown posture rather than proving non-null.

```pietto
type Age = Int:
    ensure self between 0 and 130

enum Status:
    active
    suspended

shape User:
    id: UUID not null
    age: Age nullable
    status: Status not null
    email: Text nullable
```

Shape items may include fields, named `check` blocks, `unique` declarations,
and `index` hints. An admitted `unique ... on ...` is a trusted Pietto model
contract whose authored NULL policy defaults to `NULLS_DISTINCT`. On an exact
source row output, all-`NON_NULL` determinants provide strict row uniqueness;
otherwise the evidence remains lax and usable under standard equality.
This does not claim runtime validation, catalog enforcement, DDL, or physical
database UNIQUE behavior.

## Sources and relations

A source optionally names a shape and retains a connector expression without
executing it:

```pietto
source users: User is postgres.table("public.users")
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
inner/left/right/full/cross/semi/anti join (zero or more)
let (optional)
where (optional)
group by (optional)
select
satisfying (optional)
qualify (optional)
order by (optional)
limit (optional)
```

```pietto
table active_users:
    from users
    let:
        normalized = lower(trim(email))
    where email is not null
    select:
        id
        normalized_email = normalized
    order by:
        id asc
    limit 100
```

Single-file checks require a selected `let` binding to take a new output name,
as `normalized_email = normalized` does. Outside a grouped query a single-file
`order by` key reads input fields, `let` bindings and selected window results,
not other SELECT outputs (PIE-S2102). In such a query, a key that is a bare
constant once `let:` names and signs are inlined, such as `label` with `let:
label = "x"` or `-1`, is PIE-S2380, even from a source without a shape,
because SQL reads an integer as a column position and PostgreSQL rejects other
bare constants; a computed constant such
as `1 + 1` sorts nothing and is accepted. In a query with aggregates and no
GROUP BY, a key that reads an input field outside an aggregate is PIE-S2380
too, also from a source without a shape, where any name that no `let:` binds
is an input field. A JOIN relation with an aggregate and no GROUP BY instead
refuses the entire ORDER BY clause with PIE-S2334. A grouped
key stays PIE-S2321. When a SELECT item would capture a bare
input field key (an output of the same name, which MySQL compares
case-insensitively; on PostgreSQL any unaliased computed item, which it
names implicitly; on MySQL an unaliased Text literal, `true`, `false` or
`null`, which it names by the Text value or `TRUE`, `FALSE` or `NULL`), the
emitted SQL qualifies the key with the name FROM already
gives the input, as in `FROM "sales"."orders" ... ORDER BY "orders"."amount"`;
the FROM clause is unchanged. Single-file
lowering inlines a `let` binding wherever a relation expression reads it, so an
expression that reads bindings and would exceed 768 nested levels or 100,000
expression nodes once they are inlined fails `check` with PIE-S2328. A
conditional or `in` list counts two levels, a function call three, and each let
substitution, a plain alias `b = a` included, one more; a `def` call counts as
its expansion, and a binding that nothing reads is not counted. An expression
written inline is bounded only by PIE-S2006 (450 nested levels, see
Expressions), and moving it into one binding read as `y = v` keeps it accepted.
A `let:` name has the type of its value written where it is read, as
emission inlines it: a name whose value is `null`, directly or through other
names, takes its type from where it is read, as `null` does, and over a
source without a shape a name has its binding's type. A binding is typed the
same way with the earlier names it reads, so its errors are reported in the
binding, at their own positions, whether or not anything reads it: with
`k = null` and `j = coalesce(k, 1)`, `j` is `Int not null` as
`coalesce(null, 1)` is, `d = len(j)` is PIE-S2104 in the binding and
`v = lower(j)` is PIE-S2104 at `lower`; over a source without a shape, with
`w = n is null`, `-w` is PIE-S2105. A cast of a name whose binding has an
error of its own reports only that error, as the cast of the value written
by hand does. An EXPLICIT_MODULES project types `let:` names the same way,
with or without JOIN inputs, but a relation there with a binding of unknown
type, such as `k = null`, still fails closed: `check --project` may report
PIE-S2333 at the table or query even when nothing in it is ill-typed, as it
does with JOIN inputs, a GROUP BY or `select distinct`, and
`emit-sql --project` blocks one that passes `check --project` with
PIE-B1003.
Selected project SQL admits the
documented project scalar subset when its physical carrier requirements are
established.

### Single-file JOINs

Each JOIN introduces a distinct input occurrence with an `as` binding, even
when it reads the same relation as another input. The FROM binding is the
relation's name. Bindings must be unique and may not equal the FROM binding
(PIE-S2335 at the `as` name). A written JOIN `from` names an earlier visible
binding. Unknown, forward, duplicate and hidden bindings fail closed.

All seven kinds are available to single-file `check`. A relationship JOIN
uses no `on`, with zero or one `via` step; one `via` may also have an `on`
refinement. An `on` without VIA is a general row predicate and never infers a
relationship. CROSS takes neither `on` nor VIA. A JOIN with `on` and every
CROSS JOIN must write `from` (PIE-S2378). The existing header and block forms
apply, including `: from b`, `: via r` and `: via r: s -> t`.

A relationship JOIN without `from` considers every visible earlier binding
whose relation has a declared relationship to its target, including unusable
relationships; no binding wins by proximity. It needs one source binding and
one usable direction. A VIA step with omitted roles needs one direction
ending at the target, and an omitted source needs one earlier binding of that
direction's source relation. A self relationship needs explicit endpoint
roles. The relationship's `on` must be made only of `==` equalities between
fields of its two endpoints, with types other than `Decimal`, `Json`, `Any`,
`Bytes`, a shape or an unknown type, aliases expanded. Missing, ambiguous or
unusable relationships report PIE-S2335 with candidates or reasons; a
relationship with declaration errors adds no JOIN diagnostic.

The FROM input and JOIN targets may be sources, tables or queries of the same
file, with known row fields. A relationship JOIN requires both endpoint
relations to be sources. To join a table or query, write `from` and `on`
without VIA, or use CROSS. An unshaped source, including one reached through
other relations, is refused with PIE-S2334 at the JOIN that introduces it (the
first JOIN for an unknown FROM row). A JOIN cycle is PIE-S2302 at the closing
read. Output schemas propagate through both FROM and JOIN dependencies.

Use `binding.field` for a qualified field, or a bare field name when exactly
one visible binding has it. Ambiguity is PIE-S2335 and lists qualified
alternatives in input order. A target's relation name is not its binding:
after `join customers as customer`, write `customer.id`; an unknown or hidden
field is PIE-S2102, with a reason for a relation-name qualifier or a SEMI/ANTI
binding. Row `let:` values, inlined `def` arguments, WHERE, SELECT, GROUP BY
and ungrouped ORDER BY use this row scope. A `let:` name cannot equal a visible
field, any binding or a binding's relation name (PIE-S2329). Grouped ORDER BY
and `satisfying` read selected outputs under their existing rules. Selected
column names remain the authored alias or the field's final name.

A JOIN's `on` sees visible earlier inputs and its own target, including a
SEMI/ANTI target, before that JOIN adds any NULLs. It cannot read later or
hidden targets, current row `let:` names or SELECT outputs. Aggregates are
PIE-S2335 there; a non-Bool predicate is PIE-S2202 (`Expected Bool expression
in JOIN ON`), and an otherwise unexplained unknown predicate type is
PIE-S2202 (`JOIN ON expression type is unavailable; the fields it reads need
known types.`). Nullable Bool is allowed: only TRUE matches; FALSE and NULL
do not. Operand errors keep their scalar diagnostic codes.

JOINs operate on the accumulated left row in source order. LEFT makes the
target's fields nullable; RIGHT makes every accumulated-left row input
nullable; FULL does both. CROSS adds every pair without changing nullability.
INNER proves the fields in its relationship equalities non-null, and can
prove direct field leaves of top-level AND conjuncts in `on`: a Bool field,
a comparison's field operand, or `field is not null`. OR gives no such proof.
An earlier outer JOIN's null-extension is retained: a later INNER JOIN never
clears that nullable status, and WHERE does not refine it. These types reach
output schemas and `def` argument checks (PIE-S2395).

SEMI keeps each left occurrence once when some target row matches; ANTI keeps
it once when none matches. Equal-valued left occurrences remain distinct and
repeated target matches do not multiply them. Their target fields are visible
only in their own `on`, never in the output or later JOINs; their bindings
remain reserved. Neither kind adds NULLs or refines the left fields.

PostgreSQL writes one flat SELECT per relation. Every input is aliased by its
binding and every field is qualified. Sources use their `postgres.table`
name; tables and queries use their artifact name. ON writes relationship
equalities in declared order, source side first, then the authored `on` as
one part. A single part is bare; several are parenthesized and joined by AND.
CROSS has no ON. SEMI and ANTI become correlated EXISTS and NOT EXISTS filters
on the left rows. INNER, LEFT, CROSS, SEMI and ANTI keep pending filters in
place; the next RIGHT adds them after its own ON parts and clears them.
Filters still pending at the end precede the authored WHERE, in JOIN order.
GROUP BY, HAVING, ORDER BY and LIMIT then use the existing tail format.

PostgreSQL FULL JOIN requires every condition leaf, after splitting AND, to
be an equality between an earlier input's field and its target's field, both
of builtin Int type after alias expansion. Otherwise it reports PIE-B1000.
A FULL JOIN with a pending SEMI/ANTI filter is also PIE-B1000: there must be a
RIGHT JOIN between that filter and FULL to consume it. These refusals and
MySQL's JOIN refusal are once per relation; other artifacts remain and the
command exits 1. PostgreSQL's existing all-NULL CASE/COALESCE/NULLIF condition
guard applies to JOIN ON and EXISTS conditions too.

Selected windows and named windows over JOIN rows, more than one VIA step,
and ORDER BY after an aggregate without GROUP BY remain PIE-S2334 in every
check mode. Single-file QUALIFY remains untyped and refused at IR with
PIE-I1000. Aggregates over JOIN rows follow the conservative rule in
[Aggregates and grouping](#aggregates-and-grouping). DISTINCT, relation lets,
LATERAL capture, set inputs, VALUES and table functions retain their separate
project-only boundaries.

### JOINs in explicit-module projects

`from` names the base relation. Authored relationship traversal may then add
`inner join` or `left join` clauses with mandatory target bindings:

```pietto
query enriched:
    from orders
    inner join customers as customer:
        from orders
    left join regions as region:
        from customer
        via customer_region: customer -> region
    select:
        order_id = orders.id
```

When all three relations have an `id` field, a bare `id` is ambiguous and the
project check reports `PIE-S2333`; the selection therefore qualifies it as
`orders.id`.

A JOIN that follows a declared relationship needs only its header; its `from`
line and VIA roles are optional. The one-line relationship
`relationship r: a.x == b.y` (one or more `and`-joined equalities between
fields of two different relations) declares the endpoints `a: a` and `b: b`,
so its roles are the relation names; a relationship of a relation to itself
keeps the block form (see [Modules and relationships](#modules-and-relationships)).
The JOIN header may also carry one step after `:` on its line: `: from b`,
`: via r` or `: via r: s -> t`. A JOIN with `on` must name its source with
`from` (PIE-S2378), and a header step takes no lines below it, so the header
step `: on e` is always PIE-S2378; write that JOIN in block form:

```pietto
    inner join customers as customer:
        from orders
        on customer.id == orders.customer_id
```

With

```pietto
relationship order_customer: orders.customer_id == customers.id
relationship customer_region: customers.region_id == regions.id

query enriched:
    from orders
    inner join customers as customer
    left join regions as region: via customer_region
    select:
        order_id = orders.id
```

`enriched` is the explicit query above, written for these one-line
declarations, whose roles are the relation names (its VIA step reads `via
customer_region: customers -> regions`): it has the same semantics and SQL, and
`emit-sql --project` writes the same artifact for both, apart from source
locations and the source size and digest (`byte_count` and `sha256`). In an
EXPLICIT_MODULES project a JOIN without `from` and without VIA considers every
earlier binding it can read, that is the FROM input and earlier JOIN targets
but not SEMI or ANTI targets, and keeps each that has a declared relationship
to its target, including a relationship a JOIN cannot use (no `on`, an `on`
that is not only field equalities, a declaration with errors, or an endpoint a
relationship JOIN cannot read), so such a binding is never passed over for
another one. An earlier binding that a relationship JOIN cannot read (a JOIN
query, set, VALUES body or table function) is a candidate only when a
relationship joins its relation to the target; the JOIN then fails with a
message that names it. Exactly one binding is used, as if it were written with
`from`, and it needs exactly one usable direction. A VIA step without roles
takes the direction of its relationship that ends at the relation the step must
reach (the JOIN target, or the start of the next step), and a JOIN without
`from` but with VIA starts at the one earlier binding of the relation its first
step starts at. No candidate is preferred, neither the FROM input nor the
nearest binding. For a JOIN that omits `from` or the roles of a VIA step, these
are errors: no candidate, several bindings, one binding whose relationships
cannot be used, several directions from one binding (two relationships between
the same relations, or a relationship of a relation to itself without roles), a
VIA step without roles whose relationship does not end at the relation it must
reach, a VIA step that names no relationship of the JOIN's module, a
relationship with declaration errors or one that cannot be used, roles that
name no endpoint of the relationship or one role as both source and target, VIA
steps that do not connect, and a VIA path that does not start at the `from`
binding's relation or end at the JOIN target. Each is PIE-S2333 at the JOIN, of
every JOIN kind, whose message names every candidate with its relationship and
direction, the failing VIA step, or the reason a relationship cannot be used,
or every binding it checked when there is none. A failure of one of its inputs,
such as an unknown target relation or an earlier JOIN that fails, is reported
as for the written form. It offers a `via` line only for a relationship of the
JOIN's own module, because a `via` cannot name a relationship of another
module. After `from employees` and `left join employees as boss: via
reports_to: report -> boss`, with `relationship works_in: employees.dept_id ==
departments.id`, the JOIN `inner join departments as d` reports a message that
ends with:

```text
(JOIN d matches relationships from 2 earlier bindings: employees `via works_in: employees -> departments` and boss `via works_in: employees -> departments`; write `from <binding>`)
```

A RIGHT, FULL, SEMI or ANTI JOIN also keeps its PIE-S2334 and PIE-S2335 at the
JOIN (`JOIN source binding is unknown.` or `is ambiguous.`, or `JOIN pre-match
input or relationship authority is unavailable.` when a binding, the target or
a VIA step blocks the lookup). Such a JOIN message is reported even when
another JOIN of the relation keeps its PIE-S2334, such as a JOIN-local `on`. A
written `from` with zero `via` lines whose source has several relationship
directions to the target keeps its one PIE-S2333 at the table or query, which
is reported only when nothing else explains the relation; its message adds the
candidate list of each such JOIN. A JOIN with `on` and a CROSS JOIN still name
their source with `from` (PIE-S2378). LEGACY_FLAT project checks do not infer
an omitted `from` or omitted VIA roles: they check written parts and skip the
omitted ones and the VIA path those parts would decide. Single-file checks
instead apply the resolution and limits described above.

Zero `via` lines use exact direct-relationship shorthand. One or more lines
name an explicit ordered path as `via relationship: source_role -> target_role`,
or as `via relationship` without roles when the relationship joins two
different relations.
Bindings are relation-local occurrences: duplicates, forward sources,
ambiguous paths, and failed-binding dependencies fail closed without a winner.
Intermediate path relations do not become bindings. INNER/LEFT relationship
traversal retains its existing semantic support. The parser also retains
`cross`, `right`, `full`, `semi`, `anti`, and one optional JOIN-local `on`
expression after VIA steps. ON-only and VIA+ON are distinct AST forms; generic
ON and one-VIA refinement now complete INNER/LEFT project checks in
EXPLICIT_MODULES through available named results and the existing SELECT-body
tail. A generic ON JOIN may read exact completed joined, grouped/global,
window/QUALIFY and ORDER/LIMIT results. A JOIN through a relationship, with or
without `from` and `via`, cannot yet read a FROM input with GROUP BY or a
computed SELECT output, such as a grouped or windowed query: an INNER or LEFT
JOIN without `on` then reports PIE-S2333 at the table or query, a JOIN with
`via` and `on` reports PIE-S2334 at the `on` and PIE-S2335 at the JOIN, and a
RIGHT, FULL, SEMI or ANTI JOIN reports PIE-S2334 and PIE-S2335 at the JOIN.
Changed inputs rebuild their conditions; repeated bindings remain distinct.
Condition analysis accepts the existing row-scalar Bool domain, including
nullable Bool with TRUE-only matching. Project SQL emission does not yet realize
an INNER JOIN whose ON has a nullable `Bool` field as an AND conjunct of its own
(`on o.flag`, `on lhs.id == o.id and o.flag`): `check --project` accepts it, and
`emit-sql --project` and `compile_query` report it BLOCKED with `PIE-B1002`
(`join_output_nullability_drift`) on both targets. Comparing the field with a
literal does not help (`o.flag == true` is `PIE-B1003`
`comparison_type_pair_not_admitted`); write the test in WHERE instead (`on
lhs.id == o.id` with `where o.flag`), which keeps the same rows when no later
RIGHT or FULL JOIN null-extends that side. It uses exact pre-match fields and prior
JOIN nullability, without current-block LET/projection/window capture. Generic
ON does not discover relationships. Exactly one VIA plus ON retains the base
condition and adds a JOIN-local refinement; its upper bound may survive but
coverage does not. Ordered AND conjuncts retain exact reference occurrences;
OR alone supplies no unconditional key non-nullness. Invalid conditions and
combinations add precise diagnostics. CROSS has no ON/VIA, and new kinds are
direct binary only. CROSS, RIGHT and FULL now complete through the same
EXPLICIT_MODULES project-check path as INNER/LEFT. CROSS has no match predicate
and retains every occurrence pair. RIGHT preserves every right occurrence and
null-extends the entire accumulated left input when unmatched; FULL preserves
unmatched occurrences from both sides and null-extends the opposite side.
Fields remain ordered left then right, repeated occurrences remain distinct,
and earlier null-extension provenance is retained. Property transfer uses only
exact directional premises; outer-match facts do not become unconditional
equality, key or FD evidence. Two GLOBAL inputs under a false FULL predicate
retain UNKNOWN intrinsic grain rather than a false GLOBAL proof.
SEMI and ANTI also support direct M1–M4 matching through EXPLICIT_MODULES checks.
For each occurrence of the entire accumulated left input, SEMI retains it once
if any right occurrence matches TRUE; ANTI retains it once if no right occurrence
matches TRUE. FALSE and UNKNOWN are non-matches. Repeated right matches never
multiply output; equal-valued left occurrences remain distinct. Only exact left
fields are output, including prior hidden fields and nulling history. Right
fields are available in this matching predicate only; later JOIN conditions and
SELECT-tail scopes cannot reference them. Their dependencies and binding names
remain reserved. Left keys/FD/grain follow subset transfer, with no new nulling,
fanout, coverage or ordering claim; UNKNOWN right grain alone does not make left
grain UNKNOWN. This retention rule does not prove at-most-one right match.
LEGACY_FLAT and PACKAGE_ROOT retain their existing rejection boundaries;
the single-file path has the separate subset described above. A successful
project check is not SQL capability.
Current JOIN roots are retained in private combined query-block IR and its
VERIFIED-only inspection. Project Explain keeps its separate schema boundary.

A JOIN of any kind above may read a source with fields typed by an enum or a
shape, or by an alias of either, with or without `nullable` or `not null`, and
`check --project` completes it. A project types a field of an enum, or of an
alias of one, as that enum, with or without a JOIN and whatever the JOIN makes
of its nullability: it may be selected (also from the groups), compared, tested
with `is null` or `between`, grouped, ordered, partitioned or ordered in a
window, the value of `lag`, `lead`, `first_value`, `last_value` or `nth_value`,
or matched in a JOIN `on`, and a read is checked as a single file checks it, so
`lower(c.status)` and `coalesce(c.status, "x")` report PIE-S2104,
`c.status in ("active")` and `c.status not like "a%"` report PIE-S2105,
`where c.status` reports PIE-S2202 and a `def` parameter it does not fit
reports PIE-S2395. With JOIN inputs a `let:` name bound to it and another
output of enum type may be selected, and `count(c.status)` reports PIE-S2314.
Without JOIN inputs a project does not complete every such read yet: an
aggregate of an enum field (PIE-S2314 in a single file), a selected `let:` name
bound to an enum value and a computed output of enum type other than a window
value, such as `coalesce(new_status, status)` of two enum fields or a
conditional between them, report PIE-S2333 at the table or query, and a project
check does not type the ungrouped `order by` of a relation without JOIN inputs
that is not `select distinct`, so `order by: lower(status)` passes
`check --project` there. An output such as `status in ("active", null)` reports
PIE-S2333 with or without JOIN inputs, and so does a window value function over
an enum field of a row that also has a field of another enum of the same name,
declared in another module. A single file keeps an alias of an enum as the
alias, so its messages name the alias and its window value functions refuse it
(PIE-S2104).

A table, query or relation `let` that outputs a field typed by a shape, or by
an alias of one, and completes on its own can be the target of a SEMI or ANTI
JOIN with an `on` and no `via`. Other JOINs may read it when it has a GROUP BY
but no ORDER BY, LIMIT or window function, when it is a set operation, or when
it is a table or query that only selects, renames, filters, orders or limits
the fields of such a source, directly or through other tables or queries that
do only that. In other cases, for example a relation `let` with no GROUP BY or
set operation, or a table or query with a `let:` clause or a computed SELECT
output such as `v = id + 1`, those JOINs may report PIE-S2333 at the table or
query, even when the field is never read. After the JOIN, scalar typing reads
such a field as of unknown type, so a `where` test, a SELECT output, a `let:`
value or an ORDER BY key may read it only inside an expression whose own type
stays known: a comparison (`==`, `!=`, `<`, `<=`, `>`, `>=`), `is null`,
`is not null`, and `and`, `or` and `not` over such tests, for example
`c.home is null or c.id > 0`. Any other read there is not supported yet and
reports PIE-S2333 at the table or query: the field itself (selected, bound in
`let:` or used as an ORDER BY key), a call, and every `in`, `not in`,
`between`, `like` or `not like` test of it, in `where` too. GROUP BY may name
the field, but selecting it from the groups reports PIE-S2333 as well. An
aggregate of it reports PIE-S2315 at the call, and a window partitioned or
ordered by it reports PIE-S2103 (`window partition field type must be
concrete` or `window order field type must be concrete`); a JOIN `on` that
reads such a field reports PIE-S2334 and PIE-S2335. A relationship whose `on`
compares fields typed by a shape, or by an alias of one, cannot be used by a
JOIN yet: an INNER or LEFT JOIN that uses it, with or without `via`, reports
PIE-S2333 at the table or query, and a RIGHT, FULL, SEMI or ANTI JOIN that uses
it, or a JOIN that adds an `on` to its `via`, reports PIE-S2334 and PIE-S2335;
over enum fields such a relationship completes. Project SQL emission has no
representation for enum or shape fields: with or without a JOIN,
`emit-sql --project` reports a table or query that passes `check --project` and
reads a source declaring one BLOCKED with PIE-B1003 (for example
`representation_not_in_initial_domain` at the field), or with PIE-B1003 `order`
for an ORDER BY key that reads a shape-typed field inside an expression, such
as `home is null`.

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

```pietto
query combined:
    union all:
        from current_orders
        from archived_orders
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
counts actual predicate-TRUE right BAG matches per exact left occurrence at a
direct boundary, exact relationship hop, or complete path. Equal payloads and
SEMI/ANTI left-output retention do not change this unit. Applicable directional
AT_MOST_ONE/refinement evidence or the exact completed right producer's LIMIT
0/1 (and supported real GLOBAL aggregate/replay roots) may prove the request.
Grain, post-JOIN LIMIT/WHERE, source keys or estimates alone do not prove it.
Legal unproved requests retain a private enforcement obligation and emit
PIE-S2337 WARNING in all three modes; invalid requests emit PIE-S2338 ERROR.
Proved requests emit neither. Successful checks include the exact warning in
existing text/JSON diagnostics. Combined Project IR retains every valid request,
its exact direct/hop/path boundary, input pair and proof roots. LEGAL_UNPROVED
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

Historical Project row facts and single-relation IR retain
`AUTHORED_JOIN_DEFERRED`. The completed EXPLICIT_MODULES path adds combined JOIN
rows, joined scalar lookup, null-extension evidence, final outputs and private
Query-block IR, and project SQL emission (`emit-sql --project`) emits the
JOINs. Single-file Script IR separately retains JOIN input occurrences,
conditions and binding-qualified fields for PostgreSQL emission. Single-file
`explain` keeps its one-input metadata boundary and reports PIE-I1000 at each
JOIN relation. Join-free behavior is unchanged.

## Relation blocks and relation references

The parser accepts the following forms. In an EXPLICIT_MODULES project a closed
relation let, a typed VALUES body, a bounded `generate_series` table-function
input, a closed `exists`/`not exists`, `scalar` or `in`/`not in` read, a let
with `capture` lines read by `exists`, `scalar` or `in`/`not in` or joined
LATERAL by `cross join`, `inner join` or `left join` and the header of an
entry query whose own body reads a relation with `from` are
available, as described after the example; every other form is not available
yet:

```pietto
query vip_report(cutoff: Int not null, label: Text nullable):
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
        values(id: Int not null, label: Text nullable):
            1, "new"
            2, null
    let codes:
        union all:
            from seed
            from archived_codes
    from codes
    select:
        id

query empty_seed:
    values(id: Int not null, label: Text nullable)

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
`generate_series(1, 31, 1) as n`. The row-level `let:` clause after `from` is
unchanged. A typed VALUES body has one row per line; its header without `:` has
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
ON, a row `let:`, the SELECT of a grouped or aggregate query, SATISFYING, a
window call or window specification, QUALIFY, ORDER BY or LIMIT it is reported
at the read with its family's code, PIE-S2349 for `exists`, PIE-S2348 for
`scalar` and PIE-S2350 for `in`. Outside a relation body, for example in a type
rule, a shape `check`, a type argument or a VALUES row, a read keeps that
pre-admission code.

`exists r` is a `Bool not null`: true when `r` has at least one row. Project
SQL renders it as `EXISTS (SELECT 1 FROM <block> AS e<n>)`.

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
`null` value takes the type of that one column, like a NULL in a literal list.
The columns of a set, an authored JOIN or a relation reading one of them, a
typed VALUES body or a table function are not known before completion, so for
such a block `check
--project` reports none of these, and `emit-sql --project` and `compile_query`
refuse the query with PIE-B1003 `relation_membership_width_not_one` when it does
not have exactly one output column, with PIE-B1003
`membership_type_pair_not_admitted` when the type or physical carrier of `value`
does not pair with its column, and with PIE-B1003
`expression_evidence_unavailable` for a bare `null` value, which has no type
there; a literal list whose elements are all null is PIE-S2105 at check. Project
SQL renders the read as `(value [NOT] IN (SELECT e<n>.<column> FROM <block> AS
e<n>))`, so an `order by` and `limit` of the read block stay inside its CTE and
no IN subquery carries a LIMIT.

In an EXPLICIT_MODULES project a typed VALUES body is also the body of a
top-level table or query. It is its own zero-input relation, read by `from`, a
JOIN target or a set operand within the same current limits as a set operation
body (grouping over it, by a field or a computed key, with or without JOIN, is
not available yet: PIE-S2333), and its row schema comes only from its header,
never from a named relation or source. Each column is `name: Type not null` or
`name: Type nullable` with Type one of `Bool`, `Int`, `Float` or `Text`
(PIE-S2361 otherwise; a repeated name is PIE-S2001). Each row has one cell per
column (PIE-S2362). A cell is a fixed literal, a signed number included; a
name, parameter, call or other expression is PIE-S2363. A cell matches its
column's declared type and nullability: an `Int` is within the signed 64-bit
range, an integer literal is not a `Float`, and `null` appears only in a
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
name or a JOIN binding such as `r` in `left join rhs as r`; a SEMI or ANTI JOIN
target never reaches the row and is not a row input, and neither is the binding
of a table function the body reads (the bindings of its JOINs are). Inside the let body
`NAME.field` reads that field of the outer row; bare names and every other
qualified name keep naming the let's own input, so a captured input is never
found by a bare name and adding a field to an outer input never changes what a
bare name inside the let means. Only FROM and JOIN row fields are captured,
never an outer row `let:` value, SELECT output, aggregate or window result. A
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
read the renamed let, for example `let inner: from orders` and then
`capture orders` in a let that reads `from inner`. These forms report:

- PIE-S2366 at a capture line whose name is not exactly one FROM or JOIN row
  input of the declaration body;
- PIE-S2367 at a capture line that repeats an earlier name of the same let;
- PIE-S2368 at a capture line whose name is also an input of the let itself;
- PIE-S2369 at a captured field the captured input does not have, and at each
  field read of a captured input whose columns are not known before completion;
- PIE-S2370 at the let when its body has a JOIN, row `let:`, GROUP BY, an
  aggregate in WHERE or SELECT, a window, QUALIFY, SATISFYING or DISTINCT, is
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
- PIE-S2372 at a RIGHT, FULL, SEMI or ANTI JOIN whose target is a let with
  capture lines.

All but PIE-S2369 are reported with the file's pre-admission diagnostics
(below), in one (path, line, column, code) order with them and before the
file's query header checks; semantic analysis then does not run.

Joining a let with capture lines is LATERAL: no new keyword is needed. Its
capture lines then name the FROM input or the binding of a JOIN written before
the JOIN that reads the let, and every row of those bindings, duplicates
included, gets its own rows of the let:

```pietto
query customers_with_their_orders:
    let their_orders:
        capture customers
        from orders
        where orders.customer_id == customers.id
        select:
            order_id = id
    from customers
    cross join their_orders as o:
        from customers
    select:
        id
        order_id = o.order_id
```

`cross join` pairs each left row with the let's rows for that row; `inner join
... on <condition>` keeps only the pairs for which the condition is true, and a
pure LATERAL INNER JOIN writes `on true`. `left join ... on <condition>` keeps
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
is never a CTE. A RIGHT, FULL, SEMI or ANTI JOIN of such a let is not available
yet (PIE-S2372).

The let body is limited as for an `exists` read, except that a let joined
LATERAL may end in `order by` and `limit`, a top-k per left row:

```pietto
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
    left join last_orders as o:
        from customers
        on true
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
not a field of the let's input, such as one of the let's own SELECT outputs or
an unknown name, is not available either; this alpha reports it only as
PIE-S2333 at the declaration, with no diagnostic at the key. Project SQL
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
`n` names its rows and its only column, `Int not null`, inside that body (`n`
or `n.n`, and a JOIN body reads it with `from n`). The binding is never looked
up as a relation name: another body's `n` or a module relation `n` is a
different thing, and a let of the declaration named like the binding is
PIE-S2001, as for a JOIN binding. A let with capture lines
reads a table function only through another let (PIE-S2370 otherwise), and no
capture line names its binding (PIE-S2366). `generate_series` with exactly three
arguments is the only admitted table function: any other name is PIE-S2373
and another argument count PIE-S2374. Each argument is a fixed integer literal
within the signed 64-bit range, a signed number included; `null`, a Float, a
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
available.

### Query header parameters in explicit-module projects

An EXPLICIT_MODULES project admits the header of an entry query whose own body
reads a relation with `from` (not a table function), with or without relation
lets, as long as no let reads a table function:

```pietto
query orders_since(cutoff: Int not null, label: Text nullable):
    from orders
    let:
        next_day = cutoff + 1
    where order_day >= next_day and note == label
    select:
        id
        first_day = cutoff
```

Each parameter names exactly `Bool`, `Int`, `Float` or `Text` and writes `not
null` or `nullable`; a query declares at most 64 (PIE-S2353), and a repeated
name is PIE-S2001. These declaration checks, the position checks below and the
alias check of an unaliased read run before semantic analysis: each file
reports them after its temporary diagnostics, and semantic analysis then does
not run. In that query's body a bare name equal to a parameter reads
the parameter. A parameter name that is also an input field (a typed VALUES
column of a FROM or JOIN input included), a `let:` name, a relation name of the
module, a JOIN binding, a SELECT output or a named window is an error
(PIE-S2354), so a read never changes meaning; a SELECT item that only reads a
parameter needs its own alias. A read is typed as its declaration: a `Text`
parameter is a `Text` operand that is not a literal, so comparing it with a
`Date`, `Timestamp`, `UUID`, `Bytes`, `Json` or enum field is PIE-S2105 (see
Comparisons), and no parameter can stand for a value of those types.

A read, or a `let:` binding or output whose value reads one, is available
beneath unary, binary, comparison, null-test, BETWEEN, conditional,
literal-list `in` and `cast` operators and the value arguments of `lower`,
`upper`, `trim`, `contains` (both), `starts_with`/`ends_with` (the text, not
the prefix or suffix), `coalesce` (all), `nullif` (both) and `sign`, in these
positions:

- `let:` bindings, `where`, JOIN `on` and the SELECT items of a query without
  GROUP BY, SATISFYING or aggregates;
- `satisfying` comparisons and `qualify`;
- ORDER BY keys that name a `let:` binding or restate a selected expression
  (`order by: id + cutoff` with `s = id + cutoff` selected); a restated key
  reuses that SELECT value, so a read in an ORDER key renders no placeholder
  of its own, and under `select distinct` a read counts as a constant leaf.
  Outside a grouped query a key cannot name a SELECT output;
- in a grouped query, a SELECT item that names a computed group key or applies
  `count`, `avg`, `min` or `max` to one `let:` name, and an ORDER BY key that
  names an output;
- a GROUP BY key that names a computed `let:` binding in a query without JOIN
  inputs (`let: bucket = amount * weight` with `group by: bucket`).

For example:

```pietto
query weighted(weight: Int not null, bonus: Int nullable):
    from orders
    let:
        bucket = amount * weight
        boosted = amount + bonus
    group by:
        bucket
    select:
        bucket
        n = count(boosted)
        mean = avg(boosted)
    satisfying:
        n >= weight
    order by:
        n desc
```

A nullable parameter bound to NULL makes `boosted` NULL in every row, so `n` is
0 and `mean` is NULL. Every other position is refused (PIE-S2355), whether it
reads the parameter or a `let:` binding or output that reads it: LIMIT, window
expressions and named windows (frame offsets included) except the window
arguments below, other call arguments (such as the bounds of `substr`, `len`,
`replace`, `matches` and the prefix of `starts_with`), a GROUP BY key that names
a parameter, an alias or a key of a JOIN query, other grouped SELECT items (a
direct read, `sum`, `count_distinct`, an aggregate of an expression or of a
parameter), a grouped ORDER BY key that is not an output name, and an ORDER BY
key that reads no field, binding or output. An output that reads a parameter
counts only in SATISFYING, QUALIFY, ORDER BY and LIMIT; elsewhere its name reads
the input field it may shadow. A position that a literal cannot use either keeps
the literal's diagnostic. A query with parameters is never the input of another
relation, a relation let or the body of a declaration with lets included, nor
read by `exists`, `scalar` or `in` (PIE-S2356). Headers stay PIE-S2346 in
single-file analysis, in LEGACY_FLAT projects, on a VALUES, set-operation or
table-function FROM body and beside a relation let whose FROM is a table
function, whether or not that let reads a parameter.

In a window call that is a SELECT item of a query without GROUP BY, SATISFYING
or aggregates, a bare read is also available as a window argument: the value
of `lag`, `lead`, `first_value`, `last_value` and `nth_value`, the default of
`lag`/`lead`, and a structural count — the `lag`/`lead` offset, the `ntile`
bucket count and the `nth_value` position:

```pietto
query neighbours(step: Int not null, fill: Int not null):
    from orders
    select:
        id
        previous = lag(amount, step, fill) window:
            order by:
                id
        bucket = ntile(step) window:
            order by:
                id
```

A count parameter must be declared `Int not null` (PIE-S2358). A value
parameter must be `Int` or `Float` and a `lag`/`lead` default parameter `Int`:
`check` accepts the other tags, but `emit-sql` blocks a `Text` or `Bool` value
with PIE-B1003 `window_parameter_value_kind_not_realized_yet` and any other
default with PIE-B1003 `window_default_literal_kind_not_realized_yet`. A
`lag`/`lead` result with a parameter offset may be NULL, as for any nonzero
offset, even if the binding is 0. Any other window argument, window PARTITION BY and ORDER BY
keys, frame offsets and a read nested in an operator inside a window argument
stay refused (PIE-S2355).

The relation lets of an admitted entry query read its header as its own body does:

```pietto
query recent_orders(cutoff: Int not null, label: Text nullable):
    let recent:
        from orders
        let:
            next_day = cutoff + 1
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
query, under the same position rules, and a let's own `let:` bindings and
outputs that read it are refused where the query's would be (PIE-S2355). The
name must also differ from every let name of the query and from every name
visible in each let's body: its input fields, `let:` names, JOIN bindings,
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
0, 1 or NULL, and that of `amount + bonus` only for 0 or NULL. A SATISFYING or
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
`between`, `is null`, `is not null`, `in`/`not in` literal lists, `not`, `and`,
`or`, `cast(value as Type)`, and the conditional `when_true if condition else
when_false`. The conditional binds loosest and nests to the right, so
`"a" if n > 1 else "b" if n > 0 else "c"` reads as `"a" if n > 1 else ("b" if
n > 0 else "c")`. There is no `case when ... end` form and no `||` operator;
both are syntax errors (PIE-P1000), and `+` does not join `Text` values
(PIE-S2105). A single-file expression nests at most 450 levels: each operator,
operand, call, cast or conditional on its deepest path counts one, so a chain
such as `a and b and c` or `x + y + z` nests one level per operand, and a `def`
call counts as its expansion (see [Inline functions](#inline-functions-def)). A
single file with a deeper expression anywhere, a relationship `on` condition, a
type `ensure` condition and a window frame offset included, fails `check`,
`emit-sql` and `explain` alike with PIE-S2006. A project is not held to that
bound (see Diagnostics, IR, SQL, and output).

Arithmetic (`+ - * / %` and unary `+`/`-`), `not`, `and`, `or`, comparisons,
`like`/`not like`, `between`, `in`, the arguments of the scalar functions
listed below, of the aggregates and of `lag`, `lead`, `first_value`,
`last_value` and `nth_value`, and a `where`, `satisfying`, shape `check` or
index `when` condition read a type alias operand, argument or condition, an
alias chain included, as the builtin type it expands to. The result has that
base type, not the alias: with `type Age = Int not null`, `type Money =
Decimal(12, 2) not null` and `type Email = Text not null`, `age + 1`, `-age`
and `first_value(age)` are `Int`, `sum(amount)` and `max(amount)` over an
`amount: Money not null` field are a `Decimal`, `lower(email)` is a `Text` that
`count(lower(email))` accepts, and the SQL is that of the same program with
base-typed fields; with `type Flag = Bool not null`, `where flag` over a `flag:
Flag not null` field filters as a `Bool` field does. A pair the base type
refuses is refused alike, such as `amount * 2` or `-amount` (PIE-S2105),
`count` of an alias of `Any` is PIE-S2314 as `count` of `Any` is, and
`lower(amount)` is PIE-S2104, whose message names the type as written (`got
Money`). An alias of an enum or a shape is not expanded there, but it reads
as that enum or shape where operands need one type or family (a comparison,
`between`, an `in` list, `coalesce`, `nullif` and a conditional's branches),
and an alias of an enum as the enum for an aggregate argument too: with
`type Phase = Status not null`, `count` of a `Phase` field is PIE-S2314 as
`count` of a `Status` field is (`got Phase`), and a `Phase` field compares
with a `Status` field.

`/` follows SQL division. `Int / Int` is an `Int` truncated toward zero (`7 /
2` is `3`, `-7 / 2` is `-3`): PostgreSQL emits `a / b`, and MySQL, whose `/`
would return a DECIMAL, emits `a DIV b`. With a `Float` operand the result is a
`Float`, emitted as a bare `a / b` on both targets; Pietto never inserts a
cast. To keep the fraction of an `Int` division, convert explicitly:

```pietto
query rates:
    from orders
    select:
        whole = amount / quantity
        exact = amount * 1.0 / quantity
        approximate = cast(amount as Float) / quantity
```

`amount * 1.0 / quantity` keeps the decimal digits the target computes
(PostgreSQL `numeric`, MySQL DECIMAL), and `cast(amount as Float) / quantity`
divides binary floating-point values. Any other known operand type, such as
`Text`, `Bytes`, `Json`, `Any` or an enum, is PIE-S2105, as for `+`, `-` and
`*`. Division by zero follows the target: PostgreSQL
raises an error, while MySQL `/` and `DIV` return NULL. Dividing the smallest
`Int` by -1 overflows the signed 64-bit range; what each target does then is
not specified here. Division with a `Decimal` operand is not specified yet: it
has no result type and emits a bare `/`, so each target applies its own
numeric division. The quotient is still a number, as are arithmetic over it
and numbers, `abs` of it and a `coalesce`, `nullif` or conditional of such
numbers, where a `null` takes their type, also through a `let:` name (a
column of another relation that holds one is of unknown type there), so a use
that takes no
number is refused as it is for an operand of each numeric type: with
`amount: Decimal(10, 2) not null` and `label: Text not null`,
`where amount / 2`, `where coalesce(amount / 2, 0)` and
`where coalesce(amount / 2, null)` are PIE-S2202; `amount / 2 + "x"`,
`amount / 2 == "x"`, `amount / 2 like "x%"`, `amount / 2 in ("x", "y")`,
`amount / 2 between "a" and "z"`, `not (amount / 2)` and
`label if amount > 1 else amount / 2` are PIE-S2105, as is
`abs(amount / 2) + "x"`; and `lower(amount / 2)`, `lower(abs(amount / 2))`,
`year(amount / 2)` (`got numeric`) and
`coalesce(label, amount / 2)` are PIE-S2104, in a single file and in an
EXPLICIT_MODULES relation (one with JOIN inputs may fail closed with
PIE-S2333 instead). Where a number fits, it is accepted beside numbers of any
type, so a single file accepts `amount / 2 > 1`, `amount / 2 + 1`,
`(amount / 2) % 2.5`, `amount / 2 in (1, 2.5)` and `abs(amount / 2)`. Beside
another operand of unknown type, other than such a `null`, arithmetic, a
comparison, `like`, `between`, `in`/`not in`, a conditional's branches,
`coalesce` and `nullif` do not check the quotient, as they do not check an
operand of any numeric type there; a parameter that takes no number refuses
it also beside an argument of unknown type. Semantic support is intentionally
narrower than parsing for some type/operator pairs; rejected pairs use diagnostics
rather than implicit conversions. A `null` operand of `+`, `-`, `*`, `/` or
`%`, also a `let:` name bound to it, takes the other operand's type, which the
operator must accept: `n + null` is accepted, while `label + null` with a
`Text` field is PIE-S2105, as `label + label` is. The result, always null, has
the type that the operator gives two operands of that type, as its typed twin
does: with `Int` fields `n` and `f1`, `n + null` is an `Int` (so MySQL
divides `(n + null) / 2` with `DIV`), and `trim(null % f1)`,
`lower(null + n)`, `(null + n) == "x"` and `where null + n` are refused as
`trim(f1 % f1)` and the others are, while with a `Decimal` field `d`,
`null / d` is a number of unknown type, as `d / d` is. PostgreSQL types no
arithmetic whose every operand is `null`, so single-file PostgreSQL emission
refuses `null + null` and `-null`, also as `coalesce(-null, n)` or as
`twice(null)` with `def twice(x: Int nullable) -> Int nullable: return x + x`
(PIE-B1000); MySQL emits them. PostgreSQL types a conditional, `coalesce` or
`nullif` whose every value is `null` as `text`, so single-file PostgreSQL
emission also refuses one (PIE-B1000) as an operand of an arithmetic, `and`,
`or`, `not` or sign operator, as a `where` condition or a conditional's
condition, as the argument of `abs`, `sign`, `year`, `month`, `day`, `hour`
or `minute`, such as `coalesce(null, null) + 1`, and beside an operand of a
known type that is not `Text`, an enum or `Any` in a comparison, `between`, an
`in` list, `coalesce`, `nullif` or a conditional's branches, such as
`coalesce(null, null) == 1` or `coalesce(null if b else null, n)` with an
`Int` field `n`; MySQL emits them too. As a conditional's branch, a
`coalesce` or `nullif` argument or an `in` operand, such a value takes the
type of the values of known type beside it, as `null` does, so the expression
around it is checked: with a `Text` field `t2`,
`(t2 if b else (null if b else null)) + 1` and
`coalesce(t2, coalesce(null, null)) == 1` are PIE-S2105, as
`(t2 if b else null) + 1` is, and so is `v + 1` in a relation that reads
`v = t2 if b else (null if b else null)`.

Comparisons and `between` require operands from one family: numeric (`Int`,
`Float`, `Decimal`), `Text`, `Bool`, temporal (`Date`, `Timestamp`), `UUID`,
`Bytes`, `Json`, one enum or one shape. A type alias operand is checked as the
type it expands to, an alias of an enum or a shape as that enum or shape.
Other known pairs, such as an `Int` field compared with `"x"`, a `Bool` field
compared with `1`, or an enum field compared with `1` or with a field of
another enum, report `PIE-S2105` in every check mode. Operands typed `Any`
are not checked. A `Text` literal, or a `let:` name bound to
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
and `Int` mix as they do in a comparison: with `amount: Decimal(12, 2) not
null` and `n: Int not null`, `amount in (1, 2)` and `n not in (amount, -3)`
check and emit as written (`"amount" IN (1, 2)` on PostgreSQL), and a `null`
option among them takes the `Decimal` type. Every other mix is PIE-S2105
(`expected same canonical membership operands`) even where the comparison is
accepted, such as `amount in (2.5)` or a `Float` field in `(1, 2)`. A `null`
option is typed only when the other operands have such a type. Otherwise the
list is PIE-S2105 when the value does not compare with another option (see
Comparisons), as `id in (1, "x", null)` with an `Int` field `id` is, and is
not refused for its types when it does, as `amount in (2.5, null)` is not. A
list with another operand of unknown type is not refused for its types. An
EXPLICIT_MODULES
project checks lists and `in` reads alike, and `emit-sql --project` and
`compile_query` then refuse a `Decimal` with an `Int` in a query they otherwise
emit with PIE-B1003 `membership_type_pair_not_admitted`, as they refuse
`amount == 1` with `comparison_type_pair_not_admitted`.

A comparison with `null` is never true: SQL evaluates `x = NULL`, `x <> NULL`
and the ordering comparisons to NULL for every `x`. A comparison (`==`, `!=`,
`<`, `<=`, `>`, `>=`) whose operand is the null literal, or a `let:` name bound
to it, is therefore PIE-S2105; write `x is null` for `x == null` and `x is not
null` for `x != null` (with both operands null the message suggests neither).
The same applies to a `between` whose value or both bounds are null and to an
`in`/`not in` list whose value or every option is null. A `between` with one
null bound (never true, but false when the other bound fails), an `in` list
with a null among other options (it can still match), a comparison with an
operand that may be NULL at run time, and calls such as `coalesce(x, null)`
stay accepted. Such a `between` is still a `Bool` whose other bound must be
comparable with the value: `n between null and "z"` is PIE-S2105, and
`n if flag else n between null and 1` is PIE-S2105 for its branches of two
types, and such an `in` list still needs a value that compares with its other
options: `n in (1, "x", null)` is PIE-S2105.
In an EXPLICIT_MODULES project the WHERE of a relation with a
`let:` binding of unknown type, such as `nothing = null`, or with an error in
a binding is checked as well, as in a single file (a read of a binding with
an error of its own is of unknown type), so `where x == nothing` is PIE-S2105
there too, except in a `select distinct` relation or one with QUALIFY, which
reports PIE-S2333 at the relation, or the binding's own error, instead. In
`satisfying:` a comparison
with the null literal is PIE-S2327 (`Unsupported satisfying expression form:
null literal`) in single-file checks and in an EXPLICIT_MODULES relation with
JOIN inputs, at the literal, and a bare PIE-S2333 in an EXPLICIT_MODULES
relation without JOIN inputs; any other `satisfying:` predicate of unknown
type in a project relation with JOIN inputs makes the relation fail closed
with PIE-S2333. Single-file `check` accepts any authored QUALIFY (see QUALIFY
below).

The closed scalar surface has explicit signatures, and no argument is
converted to fit one:

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

`sign` returns -1, 0 or 1 as an `Int`. PostgreSQL `sign` itself returns
`double precision` for an integer argument and `numeric` for a numeric one, so
PostgreSQL SQL casts the result: single-file `emit-sql` renders
`CAST(sign(x) AS bigint)` and project SQL `CAST(sign(x) AS pg_catalog.int8)`.
MySQL `SIGN` already returns an integer; single-file MySQL SQL renders
`SIGN(x)` and project SQL `CAST(SIGN(x) AS SIGNED)`.

`abs` picks its line by the argument's type and keeps the argument's
nullability; a `null` argument is read as a `Decimal`, an argument of unknown
type, such as a field of a source without a shape, makes it a number of
unknown type, as a quotient with a `Decimal` operand is (see above), so
`abs(t) * 2` and `abs(t) % 2` pass `check` there while `lower(abs(t))` is
PIE-S2104 (`got numeric`), and any other type, such as `Text`, is PIE-S2104
(`expected Int, Float or Decimal`). It emits
`abs(x)` on PostgreSQL and `ABS(x)` on MySQL, which return the argument's
type. Project SQL (`emit-sql --project`) proves an `Int` result as it proves
unary `-` (see Aggregates and grouping).

`coalesce` requires at least two same-canonical-type arguments. Beside an
argument of unknown type its arguments of known type must still compare with
each other (see Comparisons), as SQL has no common type for them otherwise:
over a source without a shape `coalesce(t, 1, "x")` is PIE-S2104, while
`coalesce(t, 1, 2.5)` is not refused.
`nullif` requires exactly two. `substr` is one-based and requires a
statically admitted positive start and nonnegative count, each an `Int`
literal written in the call (a `let:` name bound to one is PIE-S2104 too,
also in a `def` argument).
PostgreSQL additionally requires each
static `substr` index to fit its signed `int32` argument range. `cast(value as
Float)` is the only scalar cast: it accepts `Int` and may lose binary64
precision. Its target is the bare name `Float`, with no nullability marker or
type arguments. Every other cast, such as `Float` to `Int`, `Int` to `Text`, a
same-type `cast(n as Int)` or `cast(n as Float not null)`, is PIE-S2105.
`in`/`not in`, `not`,
conditional expressions, `like`/`not like` with `ESCAPE '!'`, and `between`
retain their ordinary SQL NULL behavior. In a pattern `!` escapes the next
character, so `!!` matches a literal `!`; a literal pattern, or a `let:` name
bound to one, that ends in an unpaired `!` is PIE-S2105. `matches` remains
outside the selected
project SQL scalar subset.

A condition must be a `Bool`: a `where`, `satisfying`, shape `check` or index
`when` condition (PIE-S2202), an operand of `and`, `or` or `not`, and the
condition of a conditional (PIE-S2105). An operand of `and` or `or`, or the
condition of a conditional, of a known type that is not `Bool` is refused also
beside an operand or branch of unknown type that reported no error of its own
and reads no `let:` binding with one. A call of one of the functions above but
`coalesce` and `nullif` has the result type its signature gives it (a number
for `abs`) also beside an argument of unknown type, as the call has that type
or fails wherever it runs, and each of its arguments of known type is checked
against the signature. So over a source without a shape `where len(t)`,
`where lower(t)` and `where abs(t)` are PIE-S2202, `not lower(t)`, `t and 5`
(also as the lines `t` and `5` of a `where:` block) and `1 if len(t) else 2`
are PIE-S2105, also through a `let:` name bound to such a call, `lower(t) + 1`
is PIE-S2105, `where len(t) + 1` PIE-S2202 and `matches(t, 1)` PIE-S2104, and
`len(t) / 2` is an `Int` division (MySQL `DIV`), while `where t`,
`where coalesce(t, u)`, `where contains(t, "x")` and `year(t) + 1` pass. A call
whose always-null argument, or `Decimal` quotient, leaves its type unknown has
its result type as well: `where lower(coalesce(null, null))` is PIE-S2202 in a
single file and in an EXPLICIT_MODULES relation, with or without JOIN inputs,
and with a `Decimal` field `d`, `sign(d / 2) / 2` is an `Int` division. Over a
source without a shape a `count()` output, and a `count` or `count_distinct`
output whose argument reads a field, is an `Int` to `satisfying`, so with
`c = count()` or
`c = count(t)`, `satisfying: c` is PIE-S2202 and `satisfying: c and m > 1`
PIE-S2105. These are types that the checks read inside the relation: over
such a row `explain` shows the type of an output of a relation with GROUP BY,
such as `Int` for `c = count(t)` and `len(max(t))`, while every output of a
relation without GROUP BY, also `z = 1`, is of unknown type there, and the
outputs of either are of unknown type to a relation that reads it. An unknown
type that an error of its own explains, or one of a `let:` binding it reads,
reports nothing more, and neither does a call whose
argument reads such a binding or a name whose error is reported where it is
bound, such as a forward reference to a later `let:` binding.

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
untyped NULL, so for a `null` argument, also a `let:` name bound to `null` or
a `def` argument that is `null`, the PostgreSQL SQL is `CAST(NULL AS bigint)`.

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
    id: Int not null
    email: Text nullable
    coupon_code: Text nullable
    ordered_at: Timestamp not null

source orders: Order is postgres.table("shop.orders")

def reachable(email: Text nullable, coupon: Text nullable) -> Bool nullable: return email like "%@%" and coupon is null

def in_2026(ts: Timestamp not null) -> Bool nullable:
    return ts between "2026-01-01 00:00:00" and "2026-12-31 23:59:59"

table reachable_2026:
    from orders
    where:
        in_2026(ordered_at)
        reachable(email, coupon_code)
    select:
        id
```

`emit-sql --dialect postgres` writes the same WHERE as the hand-written
`(ordered_at between "2026-01-01 00:00:00" and "2026-12-31 23:59:59") and
(email like "%@%" and coupon_code is null)`:

```sql
WHERE ("ordered_at" BETWEEN '2026-01-01 00:00:00' AND '2026-12-31 23:59:59') AND (("email" LIKE '%@%' ESCAPE '!') AND ("coupon_code" IS NULL))
```

- Where: single files and EXPLICIT_MODULES projects (schema version 2). A def
  belongs to its module: another module cannot call it (PIE-S2103), export it
  or import it. An `export:` or `import` block item `def f` is PIE-P1000;
  naming the def under another kind, as in an `export:` block with the item
  `table f`, is PIE-S2704 (PIE-S2705 for an `import` item). A LEGACY_FLAT
  project check refuses every def with PIE-S2379. PACKAGE_ROOT
  `explain --project` does not check defs, so a package module with a def can
  be explained; that does not make the def available.
- Signature: each parameter and the result have exactly one of the types
  `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp` or `UUID`,
  without type arguments, and state `nullable` or `not null`. An omitted
  marker is a syntax error (PIE-P1000). A type alias declared in the same
  file is read as the type it expands to, as an operator reads one, when its
  chain of aliases ends at one of these types and no alias in the chain has
  type arguments or an `ensure`; its own nullability is the marker written in
  the signature. Any other alias (such as one imported into a module, or an
  alias of an enum), an enum, `Any`, `Bytes`, `Json`, type arguments or a
  shape (a row type, which is not available yet) is PIE-S2397. Arguments are
  positional only.
- Body: one `return` expression, on the `def` line or in an indented block. It
  reads only its parameters and may use literals, operators, the built-in
  scalar functions and other defs. Every parameter must be used (PIE-S2397).
  An aggregate or a qualified name is PIE-S2397, and a `window` call cannot be
  written there (PIE-P1000). An `exists`, `scalar` or relation `in` read is
  PIE-S2348 to PIE-S2350. Any other name is PIE-S2102. A parameter may share
  the name of a function: `def f(upper: Text not null) -> Text not null:
  return upper(upper)` calls `upper` on its argument. A `constraint` or
  `derive` cannot be called from a body or anywhere else (PIE-S2103).
- Result: the body is typed with the declared parameter types, so a `Text`
  parameter is a `Text` operand that is not a literal: a body that compares
  it with a `Date`, `Timestamp` or `UUID` parameter, such as `return d > s`
  with `d: Date nullable` and `s: Text nullable`, is PIE-S2105 at the def,
  also when no call passes it a value or every call passes a literal, and a
  `Date`, `Timestamp` or `UUID` parameter takes no `Text` literal argument
  (PIE-S2395), so no def parameter stands for a constant of those types; the
  body can compare with one written as a literal (`return d > "2020-01-01"`).
  Its type must be the declared result type, and a `not null` result needs a
  body that the checker proves non-null (PIE-S2402). A body is proven
  non-null when every value it reads is non-null, except through `/`, `%`,
  `and`, `or`, `nullif` or `matches`: in a body a comparison, `between` or
  `+`, `-` or `*` of non-null
  operands is non-null, so `def lt(a: Int not null, b: Int not null) -> Bool
  not null: return a < b` is accepted, and so are bodies such as `not lt(x,
  1)` and `abs(a - b)` over non-null parameters, while MySQL `/` and `%` give
  NULL for a zero divisor. `is null`, `coalesce` with a non-null argument and
  a conditional with non-null branches are non-null whatever else they read.
  An argument of a def call fits its parameter as it does outside a body,
  every part of it typed as there, where a comparison, `between` or
  arithmetic keeps its unknown nullability: neither `y + 1` nor `abs(y + 1)`
  fits a `not null` parameter, also in a body, so `return lt(y + 1, 2)` and
  `return lt(abs(y + 1), 2)` are PIE-S2395 (see Calls below). An argument
  that fits is then read as any other value: with `def idn(x: Int nullable)
  -> Int nullable: return x`, `return idn(a + b)` over non-null `a` and `b`
  is non-null. A body that is always null
  (the same forms as for arguments below, such as `x + null`) fits only a
  `nullable` result, of its type where it has one (`x + null` with an `Int`
  parameter `x` is an `Int`), and a body whose type the checker cannot
  determine, such as `-null if x > 0 else x`, fits none (PIE-S2402), while
  `coalesce(null, null) if x > 0 else x` has the type of `x`, as
  `null if x > 0 else x` does.
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
  conversion (an `Int` value does not fit a `Decimal` parameter). An argument
  that is nullable, or whose nullability is unknown, does not fit a `not null`
  parameter; `id + 1` is such an argument even when `id` is `not null`. An
  argument that is always null (`null`; a sign, `not`, arithmetic or
  comparison with an always-null operand, such as `id + null`; or a
  `coalesce` or conditional of such values) fits only a `nullable`
  parameter, and its type is still checked when it has one: `id + null` is
  an `Int` and a comparison such as `id == (id + null)` is `Bool`. A def
  argument is checked as it is
  written into SQL, with each `let:` name replaced by its value: the type,
  nullability and errors of the value written there by hand decide whether
  it fits. With `k = null`, `j = coalesce(k, n)` and `m = id + null`, the
  arguments `k`, `k + 1` and `m` are null, and `lower(k)` and `j` are
  `Text nullable` and `Int nullable`, as `lower(null)` and
  `coalesce(null, n)` are. Over a source without a shape a `let:` value has
  the type it has written there: with `u = true` or `u = a is null`, the
  argument `u` is `Bool not null`, while `u = coalesce(a, 1)` stays unknown,
  as the field `a` is. A `let:` name whose binding has an error of its own is
  not replaced, so that its error stands alone; nor is one that is an
  unknown field where it is read, as in a grouped select item (PIE-S2102);
  and one that an aggregate argument reads is checked with its binding's
  type, and is null where its value written in is null. These are
  PIE-S2395 at the call, also when the call is in a def
  body, reported once however many times the body uses the argument and
  only for the innermost call that does not fit: an argument that does not
  fit is unknown to every expression around it, also through a built-in call
  such as `len`, and to an aggregate whose argument it is or is part of, also
  as the value of a `let:` name the aggregate reads, which adds no
  PIE-S2315 beside it when it accepts the argument's form for some argument
  type, as for a field of unknown type: `count(nn(n + 1))` is PIE-S2395
  alone, also through a `let:` name the aggregate reads, with `w = n + 1` or
  `j = n` and `w = j + 1`, and so are `count(nn(n + 1) + 1)` and `count(w)`
  with `w = nn(n + 1)`. A form the aggregate accepts for no argument type
  is PIE-S2315 too: `count(nn(upper(text)))` is PIE-S2395 and PIE-S2315, as
  `count(upper(text))` is PIE-S2315, also through a `let:` name the
  aggregate reads, with `w = upper(text)` or a constant such as `w = 1.5`,
  and `min(nn(n) + 1)` is both, as `min(n + 1)` is PIE-S2315.
  A null argument is no exception: `sum(nn(null))` is PIE-S2395 and
  PIE-S2315, as `nn(null)` outside an aggregate is PIE-S2395, and so is
  `sum(nn(k))` with `k = null`, while `count(nn(n + null))` is PIE-S2395
  alone, also as `count(nn(w))` with `w = n + null`. A
  select output that is a field or `let:` name passed to a def it does not
  fit, a group key included, has no type, as a computed output with an
  error has; in a project its relation then has no known columns, so a
  relation that reads it reports what it reports then, such as PIE-S2333.
  An argument with an
  error of its own that leaves its type unknown, such as a comparison with
  the null literal (`text == null`, PIE-S2105) or `k + zz` with an unknown
  field `zz`, is not checked against its parameter. A `let:` value is typed
  as it is written wherever it is read (see Relations), so a value that is
  ill-typed once the null it reads takes its type reports its errors in its
  binding, at their own positions, whether a def argument, another
  expression or nothing reads it, and an argument that reads it is checked
  against its parameter when the value still has a type: with
  `i = upper(k) + 1`, the binding `i` is PIE-S2105, as `upper(null) + 1`
  is, and with `d = len(j) + len(j)`, the binding `d` is two PIE-S2104, one
  at each `len`, as the value written by hand is. The argument `lower(j)` is
  PIE-S2104 at `lower`; `lower(j) == "a"` passed to a `Bool not null`
  parameter is that PIE-S2104 and PIE-S2395, as the comparison is still
  `Bool` of unknown nullability; and with `w = lower(j) is null`, the
  binding `w` is PIE-S2104 and, in a single file, `w` passed to an
  `Int not null` parameter is PIE-S2395, as `w` is `Bool not null` (a project
  check does not check an argument that reads a binding with an error of its
  own). An argument whose type is unknown for another reason is not checked
  either, as the same expression written
  by hand is not: a field of a source without a shape; `null` inside `and` or
  `or`, such as `null and true`; or an always-null value other than `null`
  that has no type, such as `-null` or `null + null` (while `id + null` is
  an `Int`), inside `coalesce`, `nullif`, a conditional or an `in` list, as
  in `coalesce(-null, n)`, except a conditional, `coalesce` or `nullif` whose
  every value is `null`, which takes the type beside it there as `null` does
  (see Expressions): `coalesce(null if b else null, n)` is checked as
  `coalesce(null, n)` is. A built-in call whose signature fixes its result type
  has that type whatever the types of its arguments are, unless an
  argument's own error, or a `let:` binding's, explains them (see
  Expressions), so its type is
  checked: over a source without a shape `len(t)` passed to a
  `Text nullable` parameter is PIE-S2395. Its nullability then follows from
  an argument of unknown type and is not checked, as that argument's is not:
  `lower(t)` and `year(null)` pass a `not null` parameter as `t` does, also
  through an operator, a conditional or a `let:` name, as in `len(t) + 1` or
  `k` with `k = lower(t)`. A comparison with null is never true
  wherever the expansion puts it:
  `low(null)` with `def low(x: Int nullable) -> Bool nullable: return x < 3`
  is PIE-S2105 at the call, as `null < 3` is by hand, unless the null
  argument (also a `let:` name bound to `null`) does not fit its parameter,
  which is then the one error. An argument cannot read a relation (`exists`,
  `scalar` or `in`) yet (PIE-S2395), because a body that repeats or reorders
  its parameters would change the SQL names of those reads.
- Positions: a call is refused (PIE-S2397), in a def body as anywhere else,
  where the written form must be a literal, a field or a window call that
  Pietto checks by a rule of its own: inside a window computation (a window
  function's arguments, PARTITION BY, ORDER BY, frame or a named window), as
  a table function or in its input, LIMIT, a VALUES row, a relationship
  condition, a source connector, a type argument, and the ORDER BY of a
  grouped relation; the message names the innermost such position. A window
  call may itself be an argument, as in a
  QUALIFY `top(row_number() window: ...)`. Anywhere else the argument's type
  and nullability are checked wherever the expansion is typed. These
  positions are not typed today, so the type and nullability of an argument
  there are checked no more than the same expression written by hand (the
  argument count, relation-read and position rules above still apply): a type
  or field `ensure`; in a project, a `constraint` or `derive` body and a shape
  `check`, `index` predicate or field `derive` (a single file checks them); a
  single-file `qualify:` (which `explain` and `emit-sql` refuse); in a
  project check, the ungrouped `order by` of a relation without JOIN inputs
  that is not `select distinct` (`emit-sql --project` blocks a mismatched
  argument there with PIE-B1003 without naming it; with JOIN inputs or
  `select distinct` the argument is checked).
  In a project, a mismatch is reported where the same error written by hand
  would be: where a project reports the errors of a position as PIE-S2333 at
  the relation, such as a grouped `satisfying` or an aggregate argument
  without JOIN inputs, a select over a VALUES let, the ORDER BY of a
  global-aggregate query or the WHERE of a `select distinct` relation or one
  with QUALIFY that has a `let:` binding of unknown type, such as `k = null`,
  the mismatch is PIE-S2333 there too, also for a `let:` name that an
  aggregate reads, which is checked with its binding's type.
- Expansion: each call becomes one parenthesized expression. An argument that
  the body uses n times is written n times in the SQL, as it would be by hand:
  with `def twice(x: Int nullable) -> Int nullable: return x + x`, the item
  `d = twice(id + 1)` emits `("id" + 1) + ("id" + 1) AS "d"`. No Pietto
  function is volatile (there is no `now`, `random` or UUID generator; such
  calls are PIE-S2103), and an aggregate argument gives one value per group,
  so the results do not change. Every inlined node keeps a real location:
  the body is at the call, and each use of an argument is at the argument's
  own text. An error inside an argument (other than a PIE-S2395 mismatch,
  which is at the call) is therefore reported at the argument, and an error
  that the body makes with its arguments at the call. A call is written once,
  so each such error is reported once, however many times the body uses the
  argument and however many body nodes make it: `low(null)` with
  `def low(x: Int nullable) -> Bool nullable: return x < 3 or x < 4` is one
  PIE-S2105 at the call, also when the call is itself an argument. This holds
  in a single-file check and in a project check, a JOIN ON condition
  included, except for a query header parameter read in a position that
  refuses it (PIE-S2355), which a project check currently reports at each use
  of the argument. A def body is checked at the def
  before any call, and there an error in a call is reported as often as its
  expansion makes it, in both checks, except an argument mismatch
  (PIE-S2395), which is reported once as at any call: with
  `def dup(x: Int not null) -> Int not null: return coalesce(x, x)`, a body
  `dup(true)` is one PIE-S2395. With its arguments, one expansion has
  at most 1000 expression nodes and 64 levels of nesting (PIE-S2399); every
  expression counts, also those in a window call's arguments and
  specification and in a cast's type arguments. A single file counts the
  450 levels of an expression (PIE-S2006, see Expressions) with every call
  in it replaced by its expansion, so a call nested 400 levels deep whose
  body nests 60 levels makes the expression 459 levels deep.
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
  of a call can cause, such as a form that `satisfying` does not support, is
  reported at the call.
- `explain` does not list defs. Their effect is part of the expressions they
  were inlined into, and lineage locates each use of an argument at the
  argument.

## Aggregates and grouping

The current aggregate family is:

```text
count count_distinct sum avg min max
```

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
file `min` and `max` accept no `let:` name. Over an input row of known shape,
the argument of a `min` or `max` that is a whole aliased SELECT item and reads
a `let:` name is never accepted, even where the argument with each name's
value written in place is: `max(w)` is PIE-S2315 with `w = 3`, as `max(3)`
is, and also with `w = n` for a field `n`, `w = f(n)` for a `def` that returns
its argument, or `w = z` for a field `z` of unknown type (such as `z = null`
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
a source without a shape or a relation that reads one, a local `let:` name is
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
never takes, such as `min(x + 1)`. A `null` operand has no type and is not
checked, as the database types it from the other operand: `count(x + null)`
passes; with a known numeric `x`, `count(x + null)` still reports PIE-S2315
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
the following conservative rule; a failure is PIE-S2381 at the aggregate
call in every check mode.

Start with the input occurrences the argument reads, following `let:` values,
and each source input whose declared unique key is entirely in GROUP BY and
whose key fields are all `not null` in the source shape. Field-renaming
`let:` keys count; computed keys do not. Close that set using only these
relationship dependencies:

- An INNER or LEFT relationship JOIN adds its target when its source is in
  the set and its matched target fields contain a declared unique key of the
  target source. The key may have nullable fields; one VIA plus ON retains this
  forward dependency.
- An INNER relationship JOIN without ON also adds its source when its target
  is in the set and its matched source fields contain a declared source key.
  A VIA plus ON has no reverse dependency.

The set must then contain the FROM input and every row-producing JOIN target;
SEMI and ANTI targets are excluded. RIGHT, FULL, CROSS and ON-only JOINs add
no dependencies, even when the ON equates a declared key. Keys are taken only
from source shapes, never inferred through tables or queries. Outer NULL
extension does not justify a RIGHT/FULL dependency: one NULL left part may
match several preserved target rows. Group protection uses the source's
non-null key so a NULL-extended part remains one fixed value within a group;
later INNER refinement does not turn a nullable source key into a strict key.

PIE-S2381 names repeated JOINs in source order and offers a unique-key or
grouping remedy only when that remedy closes the rule. For example:

```text
An aggregate may read rows repeated by JOIN customer; declare a unique key on customers.id (matched by JOIN customer), or group by a unique key of customer whose fields are all not null
```

GROUP BY accepts fields and `let:` names that rename fields. Self-join keys
such as `customers.id` and `peer.id` remain distinct; a bare and qualified
read of the same field remain one key. SELECT aggregates must be directly
aliased. `satisfying` and grouped ORDER BY read their selected outputs.
ORDER BY after an ungrouped aggregate is PIE-S2334 even when fan-out is safe.
This rule does not widen the existing aggregate argument/type domain or
admit selected windows over JOIN rows.

In an explicit-module project a JOIN must not let an aggregate see one input
row several times. A JOIN repeats the rows of one side when the other side may
match a row more than once, and in a chain of JOINs a later JOIN can repeat
them again. An aggregate whose argument reads the fields of one JOIN input is
refused, with PIE-S2333 at the table or query, unless every JOIN that could
repeat those rows is covered by one of these proofs about the other side of that
JOIN:

- a group key that is a unique key of the other side, declared with
  `unique ... on` over fields that are all `not null`, such as
  `group by: orders.id` with `unique order_key on id` and `id: Int not null`
  when the aggregates read customer fields. This proof works for every JOIN
  kind, a JOIN `on` condition and CROSS JOIN included;
- for a relationship JOIN, a `unique ... on` declaration that covers the other
  side's matched field, declared on the shape of the source that field comes
  from; the field may be `nullable`. With `from orders` and
  `on order.customer_id == customer.id`, `unique customer_key on id` on the
  customers shape proves an aggregate over order fields for an INNER or LEFT
  JOIN. A RIGHT or FULL JOIN also keeps each customer that matches no order,
  with every input before the JOIN NULL, so there the key proves such an
  aggregate only if it never reads one of these rows, or reads one only with
  a row of a later JOIN from customers whose relationship or `on` equality
  matches a key of customers; the argument or a group key must then fix that
  JOIN's input too, as `count(o2.id)` with `group by: orders.id` does after
  `left join orders as o2: from c`. For this unmatched-row proof, grouping by
  a nullable unique key of that later input also fixes it if every key field
  is proved non-null in the final joined rows. An INNER relationship equality
  can establish this even with an additional `on`; a later outer JOIN that
  NULL-extends the input removes that proof. This does not give nullable keys
  general group protection for unrelated or unbounded JOINs.
  An aggregate never reads such a row when
  its argument is NULL there, such as `count(orders.id)` or a `coalesce`,
  `and` or `or` over fields of those inputs, but not
  `count(orders.rush or true)` or `max(v)` with
  `v = orders.amount if orders.rush else 0`; when WHERE is never TRUE there,
  such as `orders.id is not null`, `not (orders.id is null)`,
  `orders.id in (1, 2)` or `orders.amount between 1 and 10`, also through a
  `let` name; or when a later INNER, SEMI or RIGHT JOIN whose condition is
  never TRUE there drops the row. For an initial RIGHT or FULL JOIN between
  direct sources with no extra `on`, a later SEMI or INNER traversal of the
  complete reverse match into the same source also removes every unmatched
  row; the paired equalities may be written in a different order. A different source declaration or a filtered relation does not supply
  this proof, even with the same physical table name. A later LEFT or FULL JOIN
  with such a
  condition NULL-extends its own input there, so `count(p.id)` after
  `left join payments as p: from orders` never reads such a row either. A
  condition that is false there only because of its values, such as
  `(orders.amount if orders.rush else 0) > 0`, does not count.
  `unique order_customer on customer_id` on the orders shape proves an
  aggregate over customer fields for an INNER or RIGHT JOIN only. An INNER or
  LEFT JOIN along several `via` lines takes such a key for every hop, each
  under the same rule. A JOIN `on` condition without `via` and a CROSS JOIN
  get no such proof for themselves.

A unique key of the aggregated side itself does not help, neither declared nor
as a group key. `count()` without an argument counts the joined rows and needs
no proof; `min`, `max` and `count_distinct` get no exemption. In this example
the aggregates read order fields, and each order matches at most one customer:

```pietto
shape Customer:
    id: Int not null
    name: Text not null
    unique customer_key on id

shape Order:
    id: Int not null
    customer_id: Int not null
    amount: Int not null

source customers: Customer is postgres.table("customers")
source orders: Order is postgres.table("orders")

relationship order_customer:
    endpoint order: orders
    endpoint customer: customers
    on order.customer_id == customer.id

query orders_per_customer:
    from orders
    inner join customers as customer:
        from orders
        via order_customer: order -> customer
    group by:
        customer.name
    select:
        customer_name = customer.name
        order_count = count(orders.id)
        largest = max(orders.amount)
```

`check --project` accepts it, and `emit-sql --project` emits the INNER JOIN
before the GROUP BY. Without the `unique` line `count(orders.id)` and
`max(orders.amount)` could see an order once per matching customer, and the
query is PIE-S2333:

```text
main.pietto:18:1 PIE-S2333 error: Project relation semantic completion is unavailable: orders_per_customer (an aggregate may read rows repeated by JOIN customer; declare a unique key on customers.id (matched by JOIN customer), or group by a unique key of customer whose fields are all not null)
```

The message names, in source order, the JOINs where the aggregated rows
repeat, which in a chain of JOINs may be later ones; when the aggregate reads
no JOIN input, for example `max(level)` over `let: level = 3`, it says
`rows that a JOIN repeats` instead. It then gives up to two remedies, either of
which removes the fan-out cause on its own: declaring every listed unique key,
or grouping by a unique key, whose fields are all not null, of each listed
binding. Each unique key is named by the source's own field and listed once
with every JOIN it serves, such as `customers.id (matched by JOIN customer)` or
`customers.id (matched by JOINs c1 and c2)`; a key over two fields reads
`customers (a, b)`. A key that is already proven is not listed. The message
names a unique key only on a source matched by a relationship JOIN with at
most one `via` line and no `on`: the target field for an INNER or LEFT JOIN,
and the FROM field for an INNER JOIN. It names the group key only for a
binding that is a source or an input that already has such a key. A remedy it
cannot confirm is left out, so it may name only the group key, even where a
declared unique key would be accepted (for example on a RIGHT JOIN), or no
remedy at all, for example for a JOIN along several `via` lines, a JOIN of a
query or a UNION input. An ungrouped aggregate followed by ORDER BY, a window
or QUALIFY stays refused after the key remedy, with a bare PIE-S2333. A
relation that only reads the refused one, such as a query
`from orders_per_customer`, reports a bare PIE-S2333. With
`total = sum(orders.amount)` added, the check still passes and the emission is
BLOCKED by the `sum(Int)` rule above.

Grouped relations preserve group-key order and selected aggregate output
identity. `satisfying` and grouped result ordering use the current selected
output rules; they are not general post-aggregate expression languages.

In EXPLICIT_MODULES projects, a group key may also name one row `let` binding
whose value is computed, such as `bucket = amount * 2` with `group by: bucket`;
the key is selected by that `let` name. Emitted SQL establishes the value once
in its LET stage and groups by that qualified column, never by a repeated
expression, an ordinal, or an output alias. Such a key is not assumed injective
and never supplies source-row grain. It passes the same comparison-domain check
as a field key: Int keys use the LET site's proven range, Decimal keys keep the
value's exact precision and scale, Bool and Text keys keep their comparison
domains, and Float keys stay refused. Grouped result ordering may name the
key's selected output; without JOIN inputs a `satisfying` reference to that
output keeps its existing rejection. With JOIN inputs the key records every JOIN
side its value reads, including both sides of `agg.rid > r.rid`, but it never
proves that a side is unique per group, so it never removes a fan-out refusal;
only direct field keys that form a strict unique key, as described above, can
do that. There, `satisfying` and grouped
result ordering may name the key's selected output. With or without JOIN
inputs, a QUALIFY reference to the key or a window argument that names it
keeps the unknown-name rejection (`PIE-S2332`, `PIE-S2102`), and a window
PARTITION BY or ORDER BY that names it is PIE-S2103 at the window call (see
Windows).
With JOIN inputs a `let` binding that only renames a field, such as
`g = r.n` with `group by: g`, groups by that field, and selecting the name
selects that field's key, as selecting the field does. A `let` alias of a
computed binding, single-file checks, and LEGACY_FLAT projects keep their
existing rejection; with JOIN inputs a selected `let` name that names no group
key, such an alias included, is PIE-S2333 at the table or query rather than an
unknown field.

## Windows

A single-file relation with JOINs currently refuses each selected window call
and each named window declaration with PIE-S2334. The following single-file
window forms apply to relations without JOINs; projects keep their own
completion and target limits.

Direct selected window expressions use an indented `window` specification:

```pietto
query ranked:
    from users
    select:
        position = row_number() window:
            order by:
                id asc
```

The bounded window identities are `row_number`, `rank`, `dense_rank`,
`percent_rank`, `cume_dist`, `ntile`, `lag`, `lead`, `first_value`,
`last_value`, and `nth_value`. Aggregates are not window functions yet:
`sum(n) window:` and the other aggregates over a window report PIE-S2103.
Partition and resolved order items preserve source order, duplicates,
qualification, and direction. Each item names a field: an expression reports
PIE-S2103 (`window partition expression must be a direct field` or `window
order expression must be a direct field`) at the window call. A `let:` name
there stands for its value once its `let:` names and `def` calls are
expanded: a field, such as with `k = t`, is read as that field, and a value
that is no name, such as with `k = lower(t)` or `k = 3`, is PIE-S2103 at the
window call, as that value written there is (a `def` call written there is
PIE-S2397 instead). In a single file over a known input row a binding's own
errors do not change this, except that a read of a name that PIE-S2329
refused reports nothing more and, otherwise, a binding with an error of its
own whose value is a name, such as `k = nosuch` or `k = j` with `j = k`, makes
the item an unknown field (PIE-S2102 `Unknown field: k`) beside that error. An
EXPLICIT_MODULES relation over a known input row checks no window that reads
a `let:` binding of unknown type, such as `k = null` or
`k = coalesce(null, null)`, or with an error of its own: the relation fails closed
with that binding's error or with PIE-S2333 at the table or query, and one
with a relationship JOIN (one without `on`, written with `via` or found)
reports PIE-S2103 at the window call instead,
`relation context requires canonical window input scope facts`, beside the
binding's error when it has one. Over
an unknown input row a selected window that reads a `let:` name is instead
PIE-S2103 at the window call, whatever the name's value: in a single file over
the row of a source without a shape, read with `from` directly or through a
chain of `from` inputs, and in an EXPLICIT_MODULES relation without JOIN
inputs also over the row of a table or query one of whose SELECT outputs has
an unknown type or an error.
(Single-file `check` accepts any authored QUALIFY, its windows included; see
QUALIFY.)
Window specifications recognize authored ROWS, RANGE, and GROUPS forms with
optional EXCLUDE:

```pietto
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
effective frame even when source omits one. In a selected window, named
windows included, single-file checks require each ROWS, GROUPS or RANGE
offset to be, once `let:` names are inlined, a nonnegative `Int` literal up to
9223372036854775807, and refuse a literal `ntile` count, `lag`/`lead` offset or
`nth_value` position above that value (PIE-S2104); PostgreSQL emission also
requires those three to fit signed `int32` (PIE-B1000). An EXPLICIT_MODULES
project check requires the same of each RANGE offset of any window, a QUALIFY
window included (PIE-S2104), since no target emits another RANGE offset. The
result of `lag`, `lead`, `first_value`, `last_value` and `nth_value` has the
type of its value,
or of the `lag`/`lead` default when the value is `null`, an enum's included,
so in a single file a later relation may combine the column with a field of
that enum, as in `coalesce(previous, status)`. The value or default may have
an unknown nullability, as an earlier relation's computed column such as
`v = m + 1` has, where the result's nullability does not depend on it:
always for `first_value`, `last_value` and `nth_value`, whose result may be
null; for a `lag` or `lead` value at an offset other than the literal 0
without a default or with a nullable or `null` one; and for a default when the
value is nullable or `null`, or at offset 0. Otherwise, as in `lag(v, 0)` or
`lag(v, 1, 0)`, the call reports PIE-S2104 (`value type must be concrete`, or
`default type must be concrete` for the default). PostgreSQL types a string
literal value, such as `lag("b")`, only from a default, so without one
PostgreSQL emission writes it as `CAST('b' AS text)`. Single-file `check`
does not analyze QUALIFY windows (see QUALIFY below). RANGE offsets retain
unresolved Phase 64 type/arithmetic requirements. GROUPS uses canonical peer
groups; EXCLUDE is a removal-only membership filter after base-frame clipping.

Value/navigation modifiers occur between the call and `window`:

```pietto
previous = lag(value) ignore nulls window ordered
first = first_value(value) respect nulls window:
    order by:
        id
nth = nth_value(value, 2) from last ignore nulls window:
    order by:
        id
```

Omitted NULL treatment means `RESPECT NULLS`; omitted `nth_value` direction
means `FROM FIRST`. Modifiers belong only to the concrete function use and are
never inherited from a named-window template. `check` accepts these forms, but
unsupported backend combinations such as PostgreSQL/MySQL `IGNORE NULLS`,
`FROM LAST`, or MySQL GROUPS/EXCLUDE fail closed when SQL is emitted:
single-file `emit-sql` reports `PIE-B1000`, and project SQL emission reports
the table or query BLOCKED with `PIE-B1003`.

Each table or query body may declare query-local named-window templates after
`select:`:

```pietto
window ordered:
    order by:
        id

window per_account = ordered:
    partition by:
        account_id
```

Calls use a template directly or add missing local components monotonically:

```pietto
result = row_number() window ordered
result = row_number() window ordered:
    partition by:
        account_id
```

Empty roots and pure aliases use `window name` and `window alias = base`.
References are query-block-local, forward/backward capable, and single-base;
duplicates, dangling references, cycles, and repeated inherited components
fail closed. Named declarations and uses preserve relation-local occurrence
identity in private IR, Project semantic provenance, and package inspection.
MySQL may preserve reachable source order; PostgreSQL uses stable base-first
ordering; exact inline fallback is used when native inheritance is not
representable. Unsupported target shapes fail closed without erasing semantic
provenance. Named windows do not cross relation blocks. Arbitrary nesting and
window expressions in unsupported clauses remain rejected.

Query blocks may add one `qualify:` block after named-window declarations
and optional `satisfying`, but before relation `order by` and `limit`:

```pietto
query top_items:
    from items
    select:
        item
    qualify:
        row_number() window:
            order by:
                item
        <= 3
```

QUALIFY has its own expression grammar with the existing scalar precedence and
AST forms plus an inline-only hidden `WindowExpr`. Hidden named-window uses are
not accepted, and adding QUALIFY does not make window expressions legal in
WHERE, LET, GROUP BY, or the global scalar grammar.

Outer QUALIFY names resolve across the complete pre-window input bucket followed
by exact selected window-result bindings. Selected aliases are bare-only;
qualified lookup remains input-only. A collision is ambiguous with no selected
or input winner. Ordinary projection aliases never become backward QUALIFY
bindings. Every hidden window uses the same pre-window namespace as selected
windows and therefore cannot consume a selected result.

An authored QUALIFY requires at least one selected or hidden window computation.
Its predicate reuses the existing scalar and Bool kernels; a known nullable Bool
is legal. SQL truth retains only TRUE and drops FALSE or UNKNOWN. Completed
EXPLICIT_MODULES semantics and private Query-block IR retain QUALIFY, final
relation ordering and output, and project SQL emission (`emit-sql --project`)
renders QUALIFY as a filter over the window stage. The single-file legacy
Script IR has no QUALIFY lowering: single-file `check` accepts an authored
QUALIFY, but single-file `explain` and `emit-sql` reject every one with
`PIE-I1000`, including a constant-true predicate.

## Modules and relationships

Module statements use explicit declaration kinds and source order:

```pietto
import "shared/types.pietto":
    type UserId
    shape User as SharedUser

export:
    type UserId
    shape SharedUser
```

Project module semantics preserve exact module/declaration identity, explicit
visibility, aliases, every collision, graph evidence, provenance, and lineage.
They never choose a first or last winner.

An import cycle between modules is PIE-S2703. While any cycle exists, project
checks, project `emit-sql` and `compile_query` stop before relation completion
in every module, not only in the modules of the cycle. They report the parse
diagnostics, the diagnostics of semantic analysis (for example an unknown
relation, PIE-S2301, or an unknown SELECT field, PIE-S2102) and the source
connector diagnostics, but none of the checks made while completing relations,
for example the typing of a WHERE condition, the checks at a `scalar` or `in`
read, and query header parameter collisions and parameterized inputs
(PIE-S2354, PIE-S2356). Those appear once every cycle is fixed.

Relationship declarations store two named endpoints and may add one authored
base-match expression after them:

```pietto
relationship order_customer:
    endpoint order: orders
    endpoint customer: customers
    on order.customer_id == customer.id
```

The one-line form `relationship order_customer: orders.customer_id ==
customers.id` declares the endpoints `orders: orders` and `customers:
customers` with the same `on` condition, and is checked by PIE-S2601 to
PIE-S2604 like the block form. Its condition is one or more `and`-joined
equalities `a.x == b.y` between fields of two different relations; any other
condition, an equality of a relation with itself included, is PIE-P1000 and
needs the block form.

Endpoint-only declarations remain valid and carry no inferred field match.
`check FILE` and an EXPLICIT_MODULES or LEGACY_FLAT `check --project` check
every relationship declaration, whether or not a query uses it, except that a
pre-admission diagnostic (PIE-S2345 to PIE-S2352, and PIE-S2379 for a `def` in
a LEGACY_FLAT check) stops `check FILE` and a LEGACY_FLAT check before
relationships are checked:

- each endpoint names a `source`, `table` or `query` (PIE-S2601, at the
  endpoint);
- a relationship name is declared only once in a file or module (PIE-S2602, at
  the later declaration);
- the two endpoint names differ (PIE-S2603, at the later endpoint);
- in each `and`-joined equality `role.field == role.field` of `on`, the role is
  one of the two endpoint names and the field is a field of that endpoint's
  relation; and when the equality compares the two endpoints and neither
  field's type is `Decimal`, `Json`, `Any`, `Bytes`, a shape or unknown, the
  two fields have the same type after alias expansion (`Int` and `Float` are
  different types; enums compare by declaration, so same-named enums of two
  modules differ and the message names each module, for example
  `Status from a.pietto`). Otherwise the check
  reports PIE-S2604 at the operand, or at the equality when the types differ,
  for example `Unknown relationship condition endpoint role: custx`,
  `Unknown relationship condition field: customer.region_id` or
  `Incompatible relationship condition operands: customer.name (Text) == region.id (Int)`.
  An equality within one endpoint and a `Decimal`, `Json`, `Any`, `Bytes`,
  shape or unknown-typed equality are not type-checked, and other condition
  forms such as `<`, `or` or a literal are not checked at all.

A JOIN `via` a relationship needs an `on` made only of such equalities over
field types other than `Decimal`, `Json`, `Any`, `Bytes`, a shape or an
unknown type. With no `on`, with another condition form such as `<`, `or`, a
literal or an equality within one endpoint, with a `Decimal`, `Json`, `Any`,
`Bytes`, shape or unknown-typed equality, or with one of the errors above, an
EXPLICIT_MODULES project check reports an INNER or LEFT JOIN through the
relationship as PIE-S2333 at the table or query when the JOIN writes `from`
and the roles of each VIA step, and at the JOIN, naming the relationship and
why it cannot be used, when it omits `from` or VIA roles. A
RIGHT, FULL, SEMI or ANTI JOIN through it reports PIE-S2334 and PIE-S2335 at
the JOIN, and that PIE-S2333 at the JOIN as well when it omits `from` or VIA
roles. Single-file checks also verify relationship usability: the JOIN
reports PIE-S2335 for an unusable match, and PIE-S2334 when a table or query
would be a relationship endpoint. A declaration with its own PIE-S2601 to
PIE-S2604 adds no JOIN diagnostic. Forms that are not declaration errors still
pass `check` while no query uses the relationship. A declaration alone infers
no same-name fields, keys or cardinality and adds no JOIN or SQL.
A LEGACY_FLAT project (`schema_version = 1`) keeps its prior declaration
checks and JOIN admission: it does not infer omitted sources or VIA roles
or check relationship usability as the single-file JOIN path now does; JOIN
kinds other than INNER/LEFT and JOIN-local ON remain unavailable (see
[Projects and packages](project-package.md#schema-compatibility)).

In an EXPLICIT_MODULES project, a JOIN through a relationship cannot yet read
the rows of a `from` input that
has `let:` bindings, GROUP BY, `satisfying` or a computed SELECT output, such as
a grouped or windowed query, or that reads such a relation or a relation let
through a chain of `from` inputs. When the FROM input of a table or query is
such an input and every JOIN of it is an INNER or LEFT JOIN through a
relationship, with or without `from` and `via` and without `on`, the check
reports PIE-S2333 at the table or query with a clause that names the JOINs
reading the input, by a written `from` or the one their lookup infers, and
why, for example
`Project relation semantic completion is unavailable: q (JOIN x reads per_user, whose rows are not available to a relationship JOIN yet: it has GROUP BY and a computed SELECT output)`.
A RIGHT, FULL, SEMI or ANTI JOIN through a relationship reading such an input
reports PIE-S2334 and PIE-S2335 at the JOIN, and an INNER or LEFT JOIN with
both `via` and `on` reports PIE-S2334 at the `on` and PIE-S2335 at the JOIN.
An INNER or LEFT JOIN with a JOIN-local `on` and no `via` reads such an input.

Relationship declarations have a separate namespace. In an EXPLICIT_MODULES
project a relationship traversal of any JOIN kind (`inner`, `left`, `right`,
`full`, `semi` or `anti`) resolves through them, and project SQL emission
(`emit-sql --project`) writes the relationship's field match as the JOIN
condition, inside `EXISTS` or `NOT EXISTS` for SEMI and ANTI. Single-file
PostgreSQL emission also writes the admitted one-step relationship match,
under the single-file JOIN limits above. MySQL refuses its JOIN relations
with PIE-B1000; single-file `explain` refuses them with PIE-I1000.

## Diagnostics, IR, SQL, and output

Parser, semantic, IR, backend, and runtime diagnostic families remain
separate. Diagnostic codes, ordering, and source locations are stable public
behavior as described in [diagnostics](spec/diagnostics.md).

A single-file expression that nests more than 450 levels (see Expressions), in
a relationship `on` or a type `ensure` condition too, fails closed with
PIE-S2006 over that whole file. In a project, an expression nested deeper than
the compiler's recursion limit allows, such as a WHERE of several hundred `and`
conditions, fails closed with PIE-S2006 over one whole file. A project reports
it from `check --project` and, BLOCKED, from `emit-sql --project`: for the
module whose own syntax checks exceed the limit, or, once the modules are
analyzed together, for the module whose syntax, each `def` call counted as its
expansion, nests deepest, where a relationship `on` adds no depth: a project
reads each of its conjuncts one at a time and only at its top. Project emission uses more of the limit than project
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
