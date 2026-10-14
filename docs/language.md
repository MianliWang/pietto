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

A file may still begin with the older header lines `pietto`, `mode`,
`dialect`, and `encoding`, in that order. They are accepted for now and will
be retired later. Only `mode` has an effect, and only in single-file commands,
where `--check-mode` overrides it.

Top-level declarations are `type`, `enum`, `constraint`, `derive`, `shape`,
`source`, `table`, and `query`. Relationship metadata and module `import` /
`export` statements are also accepted at top level.

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
each part separately, so the source above emits `FROM "public"."users"`. A
string with more than one dot or an empty part fails `check` with `PIE-S2306`
at the string, except that an empty `mysql.table("")` keeps its existing
`PIE-S2306` on the whole connector call. Project mode does not split or
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
as `normalized_email = normalized` does. Selected project SQL admits the
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
nullable Bool with TRUE-only matching. It uses exact pre-match fields and prior
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
for independent verification and inspection; no DISTINCT SQL is emitted here.

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
Query-block IR. Legacy Script IR rejects authored JOIN with `PIE-I1000`;
multi-relation SQL lowering remains unavailable. Join-free behavior is unchanged.

## Relation blocks and relation references

The parser accepts the following forms. In an EXPLICIT_MODULES project a closed
relation let and the header of an entry query whose FROM reads a relation and
that declares no relation let are available, as described after the example;
every other form is not available yet:

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
            id
            order_day
    from orders
    where id in big_vip_orders and order_day >= cutoff
    select:
        id
        latest_day = scalar big_vip_orders.order_day
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
is a FROM-based or set operation body, without `capture`, is its own query
block. It is not a module declaration: it cannot be exported or imported, read
from another declaration, or selected by `emit-sql --project` or
`compile_query`, and project SQL emits it as one named CTE like a module-level
table or query. A table or query declares at most 64 lets; each let after the
64th is PIE-S2357 at the let, reported like the temporary diagnostics below. A
let name shares one scope with the module's relation names, including every
relation import binding whether or not it resolves, the other lets of its
declaration and that declaration's JOIN bindings; a let named like any of them
is PIE-S2001 at the let, and inside the declaration a `from`, JOIN target or
set operand with that name then resolves to no relation. A let never hides
another name. Until reuse and forward reads are available, each let is read
exactly once, by `from`, a JOIN target or a set operand of a later let or of
the declaration body; a let that is never read, read more than once, or read by
itself or an earlier let is PIE-S2345 at the let. A source read only inside a
let is a source of the query like any other: the emission contract describes
it, and the compiled query, source qualification and R2 source requirements
include it.

In EXPLICIT_MODULES the `let NAME:` line itself is admitted, so a let there
never receives the temporary PIE-S2345; a VALUES body, `capture` line or other
form inside it still receives its own code. Every other occurrence of these
forms receives its temporary ERROR diagnostic in every check mode before any
semantic reader runs: PIE-S2345 relation let,
PIE-S2346 query header parameter, PIE-S2347 VALUES body, PIE-S2348 scalar read,
PIE-S2349 EXISTS reference, PIE-S2350 IN reference, PIE-S2351 capture line and
PIE-S2352 table-function FROM input. The one exception is a query header that
an EXPLICIT_MODULES project admits (see below). That run then reports no other
semantic diagnostic. Single-file `check`, `explain` and `emit-sql` report them
from semantic analysis; LEGACY_FLAT and EXPLICIT_MODULES project checks,
project `emit-sql` and `compile_query` report them with the owning file's parse
diagnostics, alongside other files' parse errors.
Single-file/LEGACY_FLAT/PACKAGE_ROOT retain their existing availability
boundaries: relation lets and every later family become available only for
EXPLICIT_MODULES.
PACKAGE_ROOT `explain --project` does not read relation bodies, so a package
module using these forms can be explained; that does not make its relations
available.

### Query header parameters in explicit-module projects

An EXPLICIT_MODULES project admits the header of an entry query whose body
reads a relation with `from` (not a table function) and declares no relation
let:

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
name is PIE-S2001. In that query's body a bare name equal to a parameter reads
the parameter. A parameter name that is also an input field, a `let:` name, a
relation name of the module, a JOIN binding, a SELECT output or a named window
is an error (PIE-S2354), so a read never changes meaning; a SELECT item that
only reads a parameter needs its own alias.

A read is available in `let:` bindings, `where`, JOIN `on` and the SELECT items
of a query without GROUP BY, SATISFYING or aggregates, beneath unary, binary,
comparison, null-test, BETWEEN, conditional, literal-list `in` and `cast`
operators. Every other position is refused (PIE-S2355), whether it reads the
parameter or a `let:` binding or output that reads it: call arguments, window
expressions and named windows (frame offsets included), GROUP BY keys,
SATISFYING, QUALIFY, ORDER BY, LIMIT and grouped SELECT items. An output that
reads a parameter counts only in SATISFYING, QUALIFY, ORDER BY and LIMIT;
elsewhere its name reads the input field it may shadow. A query with parameters
is never the input of another relation, a relation let or the body of a
declaration with lets included (PIE-S2356). Headers stay PIE-S2346 in
single-file analysis, in LEGACY_FLAT projects and beside relation lets, VALUES,
set-operation or table-function FROM bodies.

`emit-sql --project` renders every read as a typed placeholder under both
literal policies (`CAST($n AS pg_catalog.int8)`, `CAST(? AS SIGNED)`, with the
Text collation): PostgreSQL reuses one `$n` for every read of a parameter,
MySQL writes one `?` per read, and bind-safe literal slots share the same
numbering in rendering order. The SQL never depends on a value. The unbound
template keeps each parameter's declared carrier; a check that needs the value,
such as the range of `cutoff + 1` or of a later `next_day + 1`, is listed as a
binding obligation naming every parameter it depends on and runs at every
binding. A query whose parameters are all unread still emits this template;
like any statement that renders no placeholder, it needs no `parameter_protocol`
premise.
Compiling a parameterized query for execution is refused with PIE-R1004 until
compiled records carry parameter reads.

## Expressions

Expressions include literals, names and dotted names, calls, parentheses,
unary `+`/`-`, arithmetic `+ - * / %`, comparisons, `between`, `is null`,
`is not null`, `and`, and `or`. Semantic support is intentionally narrower
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
precision. `in`/`not in`, `not`,
conditional expressions, `like`/`not like` with `ESCAPE '!'`, and `between`
retain their ordinary SQL NULL behavior. `matches` remains outside the selected
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
carrier before aggregation. Empty and all-NULL inputs remain NULL. `sum(Int)`
is rejected until an aggregate-range proof exists; Decimal `sum`/`avg` require
an exact aggregate range/scale and division proof, and Float `sum`/`avg`
require a finite-result proof. A source range, free JSON declaration, renderer
spelling, or database default rounding rule is not such proof. `min` and `max`
retain their bounded direct-field surface; in EXPLICIT_MODULES projects without
JOIN inputs they also accept one row `let` name, and the result keeps that
value's proven range while admitting NULL.
`count_distinct` includes direct fields and the bounded Text lower/trim chain.
Literal-only and arbitrary expression widening remain fail closed unless a
current retained contract says otherwise.

Grouped relations preserve group-key order and selected aggregate output
identity. `satisfying` and grouped result ordering use the current selected
output rules; they are not general post-aggregate expression languages.

In EXPLICIT_MODULES projects without JOIN inputs, a group key may also name one
row `let` binding whose value is computed, such as `bucket = amount * 2` with
`group by: bucket`; the key is selected by that `let` name. Emitted SQL
establishes the value once in its LET stage and groups by that qualified
column, never by a repeated expression, an ordinal, or an output alias. Such a
key is not assumed injective and never supplies source-row grain. It passes the
same comparison-domain check as a field key: Int keys use the LET site's proven
range, Decimal keys keep the value's exact precision and scale, Bool and Text
keys keep their comparison domains, and Float keys stay refused. Grouped result
ordering may name the key's selected output. A `satisfying` reference to that
output, a `let` alias of a computed binding, window references to the key, JOIN
inputs, single-file checks, and LEGACY_FLAT projects keep their existing
rejection.

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
`last_value`, and `nth_value`. Partition and resolved order items preserve
source order, duplicates, qualification, and direction.
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
distribution, `lag`, and `lead` remain frame-insensitive. `first_value`,
`last_value`, and `nth_value` are frame-sensitive and use a concrete Pietto
effective frame even when source omits one. RANGE offsets retain unresolved
Phase 64 type/arithmetic requirements. GROUPS uses canonical peer groups;
EXCLUDE is a removal-only membership filter after base-frame clipping.

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
never inherited from a named-window template. Unsupported backend combinations
such as PostgreSQL/MySQL `IGNORE NULLS`, `FROM LAST`, or MySQL GROUPS/EXCLUDE
fail closed.

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

Joined query blocks may add one `qualify:` block after named-window declarations
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
relation ordering and output. Legacy Script IR rejects every authored QUALIFY
with `PIE-I1000`; SQL lowering remains unavailable, including for a constant-true
predicate. This corrects the former silent omission without changing parsing.

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

Relationship declarations store two named endpoints and may add one authored
base-match expression after them:

```pietto
relationship order_customer:
    endpoint order: orders
    endpoint customer: customers
    on order.customer_id == customer.id
```

Endpoint-only declarations remain valid and carry no inferred field match. A
private Project-side analysis recognizes only ordered non-empty conjunctions
of exact cross-endpoint field equality as proof-capable correspondence. It does
not infer same-name fields, keys, cardinality, JOIN use, or SQL. Relationship
declarations have a separate namespace and remain outside Semantic IR, SQL
JOIN lowering, and relationship-aware query resolution.

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
