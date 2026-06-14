# Single-Input Qualified Field Binding v1

## Status

Phase 17 Slice 1 is complete as a narrow compiler implementation slice. It
adds semantic, Semantic IR, and SQL backend handling for already-parsed dotted
field references in existing single-input relation contexts.

This contract introduces no new Pietto source syntax. The latest grammar and
the Phase 16 syntax-surface audit remain authoritative for accepted syntax.
`docs/spec/pietto-v0.9.md` remains a high-level language philosophy document:
Pietto is a gradual semantic SQL authoring DSL with readable indentation
blocks, common things implicit, dangerous things explicit, and ambiguous
things checked. Older forward-looking notes in that document do not authorize
syntax or behavior beyond the latest Phase 16 contracts and this Phase 17
slice.

## Scope

The implemented scope is limited to expression binding inside a relation that
has exactly one existing `from` input:

- `where` expressions;
- `select` expressions;
- input-scope `order by` expressions.

In those contexts, an existing dotted expression with exactly two parts is a
qualified field reference when:

1. the first part equals the current relation input name from the `from`
   clause; and
2. the second part names a field on that input's known row schema.

For example:

```pietto
source users: User is postgres.table("public.users")

table selected:
    from users
    where users.active == true
    select:
        users.email
    order by:
        users.email desc
```

The qualifier is the existing relation input name `users`; there is no new
relation alias syntax.

## Semantic Rules

Qualified field binding is semantic-only. It uses the completed relation
symbol table and row schemas that already support unqualified field lookup.

Valid qualified references receive the same value type as the corresponding
unqualified input field. Invalid qualified references fail closed with the
existing semantic diagnostic `PIE-S2102` and source span for the complete
dotted expression. No new diagnostic code is introduced or reserved.

When a qualified field appears in `select`, the output schema preserves the
input field's type and nullability. An unaliased projection such as
`users.email` exposes the output field name `email`; an aliased projection
such as `email = users.email` exposes the alias name and keeps the same field
facts.

The following are invalid in the implemented scope:

- a qualifier that does not equal the current `from` input name;
- a field that does not exist on the input schema;
- a dotted expression with more or fewer than two parts when used as a field
  reference.

Connector calls such as `postgres.table("public.users")` and
`mysql.table("app_users")` remain connector metadata, not field references.
Projection aliases remain visible only inside `select` output naming and do
not enter input-scope `order by` lookup.

Relationship metadata remains secondary read-only metadata. It does not
participate in qualified field lookup, does not create endpoint-qualified
lookup, and does not authorize relationship-aware querying.

## Semantic IR

Lowering preserves the existing `FieldRefIR` shape. A valid qualified field
reference lowers to a `FieldRefIR` whose:

- `qualifier` contains the source qualifier from the source expression;
- `field` points at the existing relation input `FieldId`;
- value type matches the bound field.

Unqualified field lowering remains unchanged.

## SQL Lowering

PostgreSQL and MySQL emitters may introduce a SQL input alias only when a
relation's emitted expressions actually use a qualified field reference. The
alias is the current logical input name from the `from` clause and is rendered
with backend identifier quoting.

This backend `AS` is emitted SQL, not accepted Pietto source syntax. Pietto
source still does not accept `as` relation aliases.

Relations that use only unqualified fields preserve the existing `FROM` bytes.
This keeps existing SQL output stable except for fixtures that already contain
qualified field references and therefore require a legal SQL alias.

## Boundaries

This slice does not implement:

- grammar changes or generated ANTLR changes;
- `source name: Shape = connector`;
- Pietto source `as` syntax;
- relation alias declarations;
- multi-input relations;
- JOIN;
- relation composition;
- endpoint-qualified lookup;
- relationship-aware querying;
- relationship SQL lowering;
- runtime authorization or database security;
- database connections, connector execution, or SQL execution;
- JSON version 2;
- public MySQL API changes;
- a generic SQL emitter API;
- new dependencies.
