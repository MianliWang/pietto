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

Top-level declarations are `type`, `enum`, `constraint`, `derive`, `shape`,
`source`, `table`, and `query`. Relationship metadata and module `import` /
`export` statements are also accepted at top level.

## Single files and projects

`check FILE`, `explain FILE` and `emit-sql FILE --dialect ...` read one file. A
table or query there reads one relation with `from` and may add a row `let:`
block, `where`, grouping and aggregates, `satisfying`, window calls, `order by`
and `limit`.

The following forms need an explicit-module project (`schema_version = 2`, see
[Projects and packages](project-package.md#schema-compatibility)): JOIN kinds
other than an `inner` or `left` relationship traversal, a JOIN `on` condition,
`select distinct:`, set operations (`union`, `intersect`, `except`), relation
lets (`let NAME:`), query header parameters, typed VALUES bodies,
`generate_series`, and `exists`, `scalar` and `in` relation reads.
`check --project` checks them, and `emit-sql --project` emits one selected
table or query for one dialect under an emission contract, within the target
limits and contract premises described below. Single-file commands
refuse them with an ERROR: PIE-S2334 for the JOIN forms, DISTINCT and set
operations, and PIE-S2345 to PIE-S2352 for relation lets, header parameters,
VALUES bodies, relation reads, `capture` lines and table functions. Each of
these messages says that the form is available in EXPLICIT_MODULES projects
(schema version 2), except the DISTINCT one, which says that DISTINCT requires
explicit-module semantics. An `inner` or `left` relationship traversal passes
single-file `check` only while its target, `from` binding and `via` steps
resolve (PIE-S2301, PIE-S2335) and nothing reads its joined binding (a read
such as `customer.id` is PIE-S2102, whose message says that JOIN binding fields
are not available in single-file mode), and single-file `explain` and
`emit-sql` then refuse it with PIE-I1000; JOIN SQL needs `emit-sql --project`.

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
authored `qualify:` block and a relationship JOIN with PIE-I1000. `emit-sql
--dialect X` then asks the X backend, which refuses with PIE-B1000 forms it
does not support, for example `ignore nulls` and `from last` on both backends,
GROUPS and EXCLUDE frames on MySQL, and a source whose connector is not
`X.table`. Only `emit-sql --dialect X` shows that a file emits for X.

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
has an error of its own. Project mode does not split or
interpret the name, although its check still rejects an empty `mysql.table`
string; project SQL emission takes the physical relation from its emission
contract.

Tables and queries share this ordered clause shape:

```text
from
inner/left join (zero or more)
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
too. A grouped key stays PIE-S2321. When a SELECT item would capture a bare
input field key (an output of the same name, which MySQL compares
case-insensitively, or on PostgreSQL any unaliased computed item, which it
names implicitly), the emitted SQL qualifies the key with the name FROM already
gives the input, as in `FROM "sales"."orders" ... ORDER BY "orders"."amount"`;
the FROM clause is unchanged. Single-file
lowering inlines a `let` binding wherever a relation expression reads it, so an
expression that reads bindings and would exceed 768 nested levels or 100,000
expression nodes once they are inlined fails `check` with PIE-S2328. A
conditional or `in` list counts two levels, a function call three, and each let
substitution, a plain alias `b = a` included, one more; a binding that nothing
reads is not counted. An expression written inline is bounded only by
PIE-S2006, and moving it into one binding read as `y = v` keeps it accepted.
Selected project SQL admits the
documented project scalar subset when its physical carrier requirements are
established.

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

Zero `via` lines use exact direct-relationship shorthand. One or more lines
name an explicit ordered path as `via relationship: source_role -> target_role`.
Bindings are relation-local occurrences: duplicates, forward sources,
ambiguous paths, and failed-binding dependencies fail closed without a winner.
Intermediate path relations do not become bindings. INNER/LEFT relationship
traversal retains its existing semantic support. The parser also retains
`cross`, `right`, `full`, `semi`, `anti`, and one optional JOIN-local `on`
expression after VIA steps. ON-only and VIA+ON are distinct AST forms; generic
ON and one-VIA refinement now complete INNER/LEFT project checks in
EXPLICIT_MODULES through available named results and the existing SELECT-body
tail. Inputs may be exact completed joined, grouped/global, window/QUALIFY and
ORDER/LIMIT results. Changed inputs rebuild their conditions; repeated bindings
remain distinct. Condition analysis accepts the existing row-scalar Bool domain, including
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
Single-file/LEGACY_FLAT/PACKAGE_ROOT and legacy IR/SQL retain their existing
rejection boundaries; a successful project check is not SQL capability.
Current JOIN roots are retained in private combined query-block IR and its
VERIFIED-only inspection. Project Explain keeps its separate schema boundary.

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
JOINs. The single-file legacy Script IR has no JOIN lowering: single-file
`explain` and `emit-sql` reject an authored JOIN that passes `check` with
`PIE-I1000`. Join-free behavior is unchanged.

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
a let, so LATERAL needs no new keyword. Parentheses still cannot span lines.

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
there, like an all-NULL literal list. Project SQL renders the read as `(value
[NOT] IN (SELECT e<n>.<column> FROM <block> AS e<n>))`, so an `order by` and
`limit` of the read block stay inside its CTE and no IN subquery carries a
LIMIT.

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
parameter needs its own alias.

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
(PIE-S2105).

`/` follows SQL division. `Int / Int` is an `Int` truncated toward zero (`7 /
2` is `3`, `-7 / 2` is `-3`): PostgreSQL emits `a / b`, and MySQL, whose `/`
would return a DECIMAL, emits `a DIV b`. With a `Float` operand the result is a
`Float`, emitted as a bare `a / b` on both targets; Pietto never inserts a
cast. A type alias operand counts as the type it expands to. To keep the
fraction of an `Int` division, convert explicitly:

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
divides binary floating-point values. A `Text`, `Bool`, `Date`, `Timestamp` or
`UUID` operand is PIE-S2105. Division by zero follows the target: PostgreSQL
raises an error, while MySQL `/` and `DIV` return NULL. Dividing the smallest
`Int` by -1 overflows the signed 64-bit range; what each target does then is
not specified here. Division with a `Decimal` operand is not specified yet: it
has no result type and emits a bare `/`, so each target applies its own
numeric division. Semantic support is intentionally narrower
than parsing for some type/operator pairs; rejected pairs use diagnostics
rather than implicit conversions.

Comparisons and `between` require operands from one family: numeric (`Int`,
`Float`, `Decimal`), `Text`, `Bool`, temporal (`Date`, `Timestamp`), or
`UUID`. A type alias operand is checked as the type it expands to. Other known
pairs, such as an `Int` field compared with `"x"` or a `Bool` field compared
with `1`, report `PIE-S2105` in every check mode. `Text` against `Date`,
`Timestamp` or `UUID` stays accepted until typed constants are decided, because
a text literal is the only constant form for those types; non-literal `Text`
operands such as fields, calls and `let` values are not yet checked against
those types either. Operands typed `Any`, `Bytes`, `Json`, an enum, or a shape
are not checked.

The closed scalar surface has explicit signatures; it has no overload search:

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
abs(Decimal) -> Decimal
sign(Int | Decimal) -> Int
year(Date | Timestamp) -> Int
month(Date | Timestamp) -> Int
day(Date | Timestamp) -> Int
hour(Timestamp) -> Int
minute(Timestamp) -> Int
date_of(Timestamp) -> Date
```

`coalesce` requires at least two same-canonical-type arguments. `nullif`
requires exactly two. `substr` is one-based and requires a statically admitted
positive start and nonnegative count. PostgreSQL additionally requires each
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

## Aggregates and grouping

The current aggregate family is:

```text
count count_distinct sum avg min max
```

`count()` lowers to `COUNT(*)`; supported `count(field)` forms count non-null
field values. The selected project numeric boundary admits Int unary `+`/`-`
and binary `+`, `-`, `*` only when the compiler can propagate a signed range
that fits the selected physical carrier. It also admits `avg(Int)` for a direct
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
links no JOIN side, so the group keys alone must fix every side.
`count_distinct` includes direct fields and the bounded Text lower/trim chain.
Literal-only and arbitrary expression widening remain fail closed unless a
current retained contract says otherwise.

In an explicit-module project a JOIN must not let an aggregate see one input
row several times. A JOIN repeats the rows of one side when the other side may
match a row more than once, and in a chain of JOINs a later JOIN can repeat
them again. An aggregate whose argument reads the fields of one JOIN input is
refused, with PIE-S2333 at the query, unless every JOIN that could repeat
those rows is covered by one of these proofs about the other side of that
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
  customers shape proves an aggregate over order fields for an INNER, LEFT,
  RIGHT or FULL JOIN, and `unique order_customer on customer_id` on the orders
  shape proves an aggregate over customer fields for an INNER or RIGHT JOIN
  only. An INNER or LEFT JOIN along several `via` lines takes such a key for
  every hop, each under the same rule. A JOIN `on` condition without `via` and
  a CROSS JOIN get no such proof.

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
result ordering may name the key's selected output, while a window or QUALIFY
reference to it keeps the unknown-name rejection (`PIE-S2102`, `PIE-S2332`). A
`let` alias of a computed binding, window references to the key, single-file
checks, and LEGACY_FLAT projects keep their existing rejection.

## Windows

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
qualification, and direction.
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
windows included, single-file checks require each ROWS or GROUPS offset to be,
once `let:` names are inlined, a nonnegative `Int` literal up to
9223372036854775807, and refuse a literal `ntile` count, `lag`/`lead` offset or
`nth_value` position above that value (PIE-S2104); PostgreSQL emission also
requires those three to fit signed `int32` (PIE-B1000). Single-file `check`
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

Endpoint-only declarations remain valid and carry no inferred field match.
`check FILE` and an EXPLICIT_MODULES `check --project` check every relationship
declaration, whether or not a query uses it, except that in `check FILE` a
pre-admission diagnostic (PIE-S2345 to PIE-S2352) stops the file before
relationships are checked:

- each endpoint names a `source`, `table` or `query` (PIE-S2601, at the
  endpoint);
- a relationship name is declared only once in a file or module (PIE-S2602, at
  the later declaration);
- the two endpoint names differ (PIE-S2603, at the later endpoint);
- in each `and`-joined equality `role.field == role.field` of `on`, the role is
  one of the two endpoint names and the field is a field of that endpoint's
  relation; and when the equality compares the two endpoints and neither field
  is `Decimal`, `Json`, `Any` or `Bytes`, the two fields have the same type
  after alias expansion (`Int` and `Float` are different types; enums compare
  by declaration, so same-named enums of two modules differ and the message
  names each module, for example `Status from a.pietto`). Otherwise the check
  reports PIE-S2604 at the operand, or at the equality when the types differ,
  for example `Unknown relationship condition endpoint role: custx`,
  `Unknown relationship condition field: customer.region_id` or
  `Incompatible relationship condition operands: customer.name (Text) == region.id (Int)`.
  An equality within one endpoint and a `Decimal`, `Json`, `Any` or `Bytes`
  equality are not type-checked, and other condition forms such as `<`, `or`
  or a literal are not checked at all.

A JOIN `via` a relationship needs an `on` made only of such equalities over
field types other than `Decimal`, `Json`, `Any` and `Bytes`. With no `on`, with
another condition form such as `<`, `or`, a literal or an equality within one
endpoint, with a `Decimal`, `Json`, `Any` or `Bytes` equality, or with one of
the errors above, an INNER or LEFT JOIN through the relationship reports
PIE-S2333 at the query, and a RIGHT, FULL, SEMI or ANTI JOIN through it
reports PIE-S2334 and PIE-S2335 at the JOIN; the forms that are not errors
still pass `check` while no query uses the relationship. A declaration alone
infers no same-name fields, keys or cardinality and adds no JOIN or SQL. A
project with `schema_version = 1` does not check relationship declarations
yet.

Relationship declarations have a separate namespace. In an EXPLICIT_MODULES
project a relationship traversal of any JOIN kind (`inner`, `left`, `right`,
`full`, `semi` or `anti`) resolves through them, and project SQL emission
(`emit-sql --project`) writes the relationship's field match as the JOIN
condition, inside `EXISTS` or `NOT EXISTS` for SEMI and ANTI. The single-file
legacy Script IR has no relationship JOIN lowering: single-file `explain` and
`emit-sql` refuse a relationship JOIN with `PIE-I1000`.

## Diagnostics, IR, SQL, and output

Parser, semantic, IR, backend, and runtime diagnostic families remain
separate. Diagnostic codes, ordering, and source locations are stable public
behavior as described in [diagnostics](spec/diagnostics.md).

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
windows, range/as-of behavior, timezone conversion, parsing, and other casts
remain unavailable.
