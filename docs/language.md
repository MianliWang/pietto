# Pietto language

Pietto is a gradual semantic SQL authoring DSL. Its compiler pipeline is:

```text
source -> parse -> analyze -> immutable IR -> selected SQL dialect -> CLI text/JSON
```

Pietto compiles SQL; it does not connect to a database or execute SQL. Syntax
may be broader than the currently supported semantic and backend subsets.
Unsupported combinations fail closed with deterministic diagnostics.

## Source structure

Blocks use a trailing colon and spaces-only indentation. Braces are not block
delimiters, and tabs must not be mixed with spaces.

An optional header may declare, in order:

```pietto
pietto 0.9
mode checked
dialect postgres
encoding utf8
```

`mode` accepts `loose`, `checked`, or `strict`. A dialect is always selected
explicitly for SQL emission; PostgreSQL and MySQL are the current backends.

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
        normalized = lower(trim(status))
    where status is not null
    select:
        id
        normalized
    order by:
        id asc
    limit 100
```

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
        id
```

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
Current JOIN roots also remain unavailable to combined query-block IR and its
inspection until Slice 10. Project Explain keeps its separate schema boundary.

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
single-match obligations. Combined IR/verification/inspection remains Slice 10;
legacy IR/SQL/Explain retain their negative boundaries.

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
keep their existing availability boundaries. Combined DISTINCT Project IR,
verification and inspection remain Slice 10; no DISTINCT SQL is emitted here.

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
existing text/JSON diagnostics. Nonempty private requests remain unavailable to
combined Project IR/inspection until Slice 10; no execution or data repair occurs.

Historical Project row facts and single-relation IR retain
`AUTHORED_JOIN_DEFERRED`. The completed EXPLICIT_MODULES path adds combined JOIN
rows, joined scalar lookup, null-extension evidence, final outputs and private
Query-block IR. Legacy Script IR rejects authored JOIN with `PIE-I1000`;
multi-relation SQL lowering remains unavailable. Join-free behavior is unchanged.

## Expressions

Expressions include literals, names and dotted names, calls, parentheses,
unary `+`/`-`, arithmetic `+ - * / %`, comparisons, `between`, `is null`,
`is not null`, `and`, and `or`. Semantic support is intentionally narrower
than parsing for some type/operator pairs; rejected pairs use diagnostics
rather than implicit conversions.

Current scalar builtins have one explicit signature each:

```text
lower(Text) -> Text
trim(Text) -> Text
len(Text) -> Int
matches(Text, Text) -> Bool
```

There is no arbitrary Python evaluation, implicit overload search, user code
execution, or general cast language.

## Aggregates and grouping

The current aggregate family is:

```text
count count_distinct sum avg min max
```

`count()` lowers to `COUNT(*)`; supported `count(field)` forms count non-null
field values. `sum` and `avg` accept their bounded numeric field/expression
subset. `min` and `max` retain their bounded direct-field surface.
`count_distinct` includes direct fields and the bounded Text lower/trim chain.
Literal-only and arbitrary expression widening remain fail closed unless a
current retained contract says otherwise.

Grouped relations preserve group-key order and selected aggregate output
identity. `satisfying` and grouped result ordering use the current selected
output rules; they are not general post-aggregate expression languages.

## Windows

Direct selected window expressions use an indented `window` specification:

```pietto
query ranked:
    from users
    select:
        position = row_number():
            window:
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
