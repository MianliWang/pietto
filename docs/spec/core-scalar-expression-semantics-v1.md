# Core Scalar Expression Semantics v1

## Status

Phase 17 Slice 2 is complete as a narrow semantic typing slice for existing
parsed scalar expression nodes. It adds no grammar, generated ANTLR, AST,
parser API, Semantic IR shape, SQL renderer, SQL golden, CLI, JSON, dependency,
package, version, or CI change.

This contract introduces no new Pietto source syntax. The latest grammar and
the Phase 16 syntax-surface audit remain authoritative for accepted syntax.

## Scope

The implemented scope covers semantic value typing for expression forms that
were already parsed before Phase 17 Slice 2:

- unary `+x` and `-x`;
- arithmetic binary `+`, `-`, `*`, and `%`;
- Boolean binary `and` and `or`;
- `between` predicates.

The slice reuses existing recursive expression typing, row schemas, field
lookup, built-in function typing, predicate checks, Semantic IR lowering, and
SQL renderer behavior.

## Semantic Rules

Unary `+` and `-` require a known numeric operand, `Int` or `Float`. The result
type and nullability are exactly the operand type and nullability. If the
operand is unknown, the expression remains unknown and no invalid-operator
diagnostic is emitted.

Binary `+`, `-`, and `*` require known numeric operands, `Int` or `Float`. The
result type is `Float` if either operand is `Float`; otherwise the result type
is `Int`. Result nullability follows the project's current conservative
expression convention and is `unknown`.

Binary `%` requires known `Int` operands and returns `Int` with conservative
unknown nullability. Phase 17 Slice 2 implements `%` typing because both the
PostgreSQL and MySQL renderers already supported `%` before this slice.

Binary `/` remains semantically deferred for this slice because portable
PostgreSQL/MySQL integer division behavior is not yet specified. A `/`
expression remains unknown and does not emit the invalid-operator diagnostic.

Binary `and` and `or` require known `Bool` operands. The result type is `Bool`
with conservative unknown nullability.

`between` recursively types its value, lower bound, and upper bound. If all
three children are known, the result is `Bool` with conservative unknown
nullability. If any child is unknown, the `between` expression remains unknown.
This slice does not add operand compatibility checks for `between`.

## Diagnostics

Phase 17 Slice 2 adds one semantic diagnostic:

| Code | Severity | Meaning |
|---|---|---|
| `PIE-S2105` | `ERROR` | Invalid operator operands |

The diagnostic is emitted only when all relevant operands are semantically
known and incompatible with the operator. It is located at the complete unary
or binary expression span.

The stable message form is:

```text
Invalid operands for operator <op>: expected <expected>
```

Unknown children suppress `PIE-S2105` cascades. For example, `missing + 1`,
`missing and true`, and `missing between 1 and 5` preserve only the existing
unknown-field diagnostics.

## IR And SQL

Semantic IR lowering consumes the newly known expression value types through
the existing expression-lowering path. No IR dataclass or SQL renderer changes
are part of this slice.

Existing PostgreSQL and MySQL SQL bytes remain stable. `%` does not require SQL
renderer changes because both backends already rendered the operator.

## Boundaries

This slice does not implement:

- grammar changes or generated ANTLR changes;
- AST or parser API changes;
- SQL renderer changes;
- SQL golden changes;
- source `=` connector syntax;
- Pietto source `as` syntax;
- aggregate functions;
- `GROUP BY` or `HAVING`;
- JOIN or relation composition expansion;
- relationship query behavior;
- projection row-schema propagation for computed aliases beyond existing
  behavior;
- runtime or database execution;
- strict-mode safety policy;
- security or policy DSL;
- new dependencies.
