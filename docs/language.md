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
and `index` hints. Accepted syntax does not imply runtime validation, DDL, or
database metadata behavior.

## Sources and relations

A source optionally names a shape and retains a connector expression without
executing it:

```pietto
source users: User is postgres.table("public.users")
```

Tables and queries share this ordered clause shape:

```text
from
let (optional)
where (optional)
group by (optional)
select
satisfying (optional)
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

`from` currently names one relation. Qualification, let visibility, grouped
scope, selected-output scope, and relation-to-relation schemas are checked by
the semantic layer. No JOIN or relationship-aware relation composition is
currently accepted.

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

The current bounded window identities are `row_number`, `rank`, `dense_rank`,
`percent_rank`, `cume_dist`, `ntile`, `lag`, and `lead`. Partition and local
order items preserve source order, duplicates, qualification, and direction.
Window specifications also recognize the authored ROWS forms:

```pietto
rows 2 preceding
rows between 2 preceding and current row
```

Bounds may use `unbounded preceding`, an expression plus `preceding`, `current
row`, an expression plus `following`, or `unbounded following`. The current
eight window identities are frame-insensitive, so any explicit ROWS frame is
rejected by function/frame policy until Slice 9 introduces a legal
frame-sensitive caller. RANGE, GROUPS, EXCLUDE, named windows, `QUALIFY`,
arbitrary nesting, and window expressions in unsupported clauses remain
rejected.

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

Relationship declarations store two named endpoints as metadata. They have a
separate namespace and remain outside Semantic IR, SQL JOIN lowering, and
relationship-aware query resolution.

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
