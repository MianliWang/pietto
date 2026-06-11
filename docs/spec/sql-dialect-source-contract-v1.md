# SQL Dialect Capability And Source Contract v1

## Status

**This contract is planning/specification-only and is not implemented.**

It defines the responsibility boundaries required before Pietto adds another
SQL backend, a dialect abstraction, SQLGlot, or another source connector.
Current PostgreSQL behavior remains authoritative and byte-exact.

The only implemented source connector is:

```pietto
postgres.table("public.users")
```

The only implemented CLI SQL dialect is:

```bash
pietto emit-sql file.pie --dialect postgres
```

`mysql.table`, `--dialect mysql`, backend capability declarations, generic
connector syntax, and the contracts described below are not runtime features.

## Goals

This contract defines:

- how connector names relate to SQL dialects;
- semantic, IR, CLI, and backend responsibility boundaries;
- the capabilities every future SQL backend must declare;
- source connector and relation-source compatibility rules;
- function, expression, operator, identifier, and literal policies;
- deterministic unsupported-case diagnostics;
- qualified physical-name compatibility requirements;
- fail-closed behavior that prohibits best-effort SQL generation.

This contract covers SQL generation only. A connector is static compiler
metadata; it is not executable and carries no database session, credentials,
network endpoint, schema lookup, or runtime behavior.

## Terms

**CLI dialect**
: The explicitly selected, implemented SQL output backend, currently only
  `postgres`.

**Source connector**
: A statically named source-level call that identifies physical source
  metadata, currently `postgres.table(Text)`.

**Connector signature catalog**
: The future semantic-stage catalog of recognized connector names, arity,
  argument types, and static-value requirements.

**Backend capability declaration**
: The future backend-owned declaration of which connectors, IR definitions,
  expression nodes, calls, operators, and rendering policies one SQL backend
  supports.

**Physical table name**
: The connector-provided static value used as a backend relation input. The
  current `postgres.table(Text)` argument is one opaque identifier.

## Decision Summary

1. Initial physical connectors are dialect-specific.
2. `postgres.table(Text)` remains unchanged.
3. A future MySQL MVP should use the distinct connector
   `mysql.table(Text)`.
4. No generic `table(...)` connector is planned for the initial
   multi-dialect implementation.
5. Semantic analysis owns connector recognition and static signature
   validation.
6. The selected backend owns connector compatibility and SQL-generation
   capability validation.
7. `SourceIR` preserves connector identity and static arguments without
   executing or interpreting them as SQL.
8. Unsupported combinations fail with deterministic diagnostics and never
   fall back to another connector, function, operator, or dialect.
9. Existing dotted PostgreSQL table strings remain one quoted identifier.
10. Structured qualified names require a future explicit, versioned source
    representation and must never be inferred by splitting existing strings.

## Connector Naming

Physical connector names are dialect-specific for the initial
multi-dialect model:

| Connector | Status | Intended backend |
|---|---|---|
| `postgres.table(Text)` | Implemented | PostgreSQL |
| `mysql.table(Text)` | Future candidate only | MySQL 8.0+ |

The namespace prefix is a physical-source contract, not an instruction to
open a database connection. It identifies the static metadata semantics a
backend must understand.

A generic connector such as `table(Text)` is rejected for the initial model.
It would incorrectly imply that identifier qualification, case rules, string
interpretation, and physical source semantics are portable across dialects.

A generic connector layer may be reconsidered only in a later version after:

- at least two implemented dialects demonstrate identical source semantics;
- a portable physical-name model is accepted;
- compatibility and migration behavior are specified;
- the generic form does not silently reinterpret existing connector data.

Connector names never select the CLI backend. The CLI dialect, a future
project default, a source header dialect, and a connector name are distinct
concepts. No compiler stage may infer an output dialect by scanning connector
names.

## Current Compatibility Baseline

Current behavior remains unchanged:

- semantic analysis recognizes only `postgres.table`;
- `mysql.table("users")` receives `PIE-S2306` as an unknown connector;
- `postgres.table` requires one argument typed as `Text`;
- IR lowering preserves the name `postgres.table`, its static argument, and
  source span in `ConnectorIR`;
- PostgreSQL relation emission accepts only `postgres.table(Text)`;
- `postgres.table("public.users")` renders `FROM "public.users"`;
- the string is not split into `public` and `users`;
- unused `SourceIR` metadata emits no SQL artifact;
- the CLI accepts only `--dialect postgres`;
- unsupported CLI dialects stop before parsing and use the existing usage
  error and JSON `unsupported_dialect` behavior.

This specification does not change those behaviors or their diagnostic text,
locations, ordering, exit codes, or JSON representation.

## Stage Responsibilities

### Parser

The parser owns only source syntax:

- parse a source connector as an ordinary call-shaped expression;
- preserve its callee, arguments, and source span;
- report syntax and indentation failures.

The parser does not recognize connector catalogs, select dialects, validate
signatures, construct SQL, or execute connectors.

### Semantic Analysis

Semantic analysis owns source-language validity independent of the selected
output backend:

- require a call-shaped connector expression;
- resolve the exact connector name against the connector signature catalog;
- reject unknown connector names;
- type connector arguments;
- validate connector arity and declared argument types;
- require connector arguments designated as static to be compile-time literal
  values;
- preserve existing cascade suppression when an argument already has an
  unknown type;
- validate source shape binding and row-schema semantics;
- report connector-name, signature, and static-value failures as semantic
  diagnostics.

`PIE-S2306` remains the connector semantic diagnostic category.

The current implementation already validates call shape, connector name,
arity, and argument type. Static literal enforcement is a required future
semantic responsibility; the current IR builder still performs a defensive
check. Slice 3 does not move or change that behavior.

When a future implementation adds `mysql.table(Text)`, it must first add that
exact signature to the semantic connector catalog. Until then,
`mysql.table` remains unknown and must continue to receive `PIE-S2306`.

Semantic analysis does not:

- choose the output backend;
- decide whether the selected backend accepts a semantically known connector;
- render identifiers or literals;
- map Pietto calls or operators to SQL;
- approximate an unsupported capability;
- connect to, inspect, or execute the referenced source.

### Semantic IR

`ConnectorIR` remains parser-independent static metadata:

```text
ConnectorIR
    name
    arguments
    span
```

IR lowering owns:

- copying the semantically validated connector name;
- copying ordered static scalar arguments;
- retaining the connector source span;
- rejecting missing or inconsistent semantic prerequisites through existing
  IR diagnostics.

IR lowering does not select a backend, normalize one dialect into another,
split physical names, create SQL AST nodes, or execute connectors.

The initial multi-dialect MVP does not require a dialect field on `SourceIR`
or a new public IR model. Connector identity is carried by
`ConnectorIR.name`.

### CLI

The CLI owns output-dialect selection:

- require an explicit supported dialect under the current single-file
  contract;
- reject an unimplemented dialect before parsing;
- preserve the supplied dialect in JSON errors;
- dispatch to exactly one implemented backend only after parser, semantic,
  and IR stages succeed.

An unknown CLI dialect is a usage error with exit code `2`. It is not a
compiler diagnostic.

After a future `mysql` backend is implemented, `--dialect mysql` may pass the
CLI gate. A connector/backend mismatch discovered later is then a backend
diagnostic with exit code `1`, not an `unsupported_dialect` usage error.

### SQL Backend

The selected SQL backend owns SQL-generation capability:

- accept `ScriptIR` without rerunning earlier stages;
- declare supported source connector names;
- declare supported emitting and non-emitting definition kinds;
- declare supported expression IR node kinds;
- declare supported call names and exact arities;
- declare supported comparison, unary, and binary operators;
- own physical source-name validation;
- own identifier quoting and case-preservation policy;
- own literal spelling, escaping, range, and rejection policy;
- own relation formatting and artifact construction;
- diagnose unsupported or invalid backend cases deterministically.

A backend may defensively validate IR invariants, but defensive checks do not
replace semantic validation and must not mutate IR.

Backend capability validation is demand-driven. A source connector is checked
when an emitted relation resolves to that `SourceIR`. Unused source metadata
remains non-emitting and does not independently produce a backend diagnostic.
This preserves current PostgreSQL behavior.

## Capability Declaration Requirements

Every future backend must have one reviewable capability declaration. Slice 3
specifies its required content; Slice 5 will specify the implementation
interface.

The declaration must cover:

| Capability area | Required declaration |
|---|---|
| Identity | Stable CLI/backend dialect identifier |
| Connectors | Exact semantic catalog connector names accepted by the backend |
| Definitions | Emitting, non-emitting, and unsupported `DefinitionIR` kinds |
| Expressions | Supported `ExpressionIR` node kinds |
| Calls | Source-level callee, arity, SQL mapping, and semantic caveats |
| Comparisons | Supported Pietto comparison operators and SQL mapping |
| Unary operators | Supported operators and SQL mapping |
| Binary operators | Supported operators and SQL mapping |
| Identifiers | Quote character, escaping, qualification, case policy, empty/NUL rejection |
| Literals | Supported static types, spelling, escaping, finite-number rules, NUL rejection |
| Sources | Physical-name interpretation and connector argument constraints |
| Relations | Projection, alias, input-reference, filter, ordering, and formatting policy |
| Diagnostics | Failure code category, message requirements, span ownership, and ordering |

The semantic connector signature catalog is the source of truth for connector
name, arity, argument type, and static-value requirements. Backend capability
declarations reference catalog connector identities and must not redefine a
conflicting signature.

A capability declaration is closed: absence means unsupported. There is no
implicit standard SQL fallback.

## Current PostgreSQL Capability

The handwritten PostgreSQL backend remains authoritative. Its current
capability is:

| Area | Supported behavior |
|---|---|
| Connector | `postgres.table(Text)` |
| Emitting definition | `RelationIR` |
| Non-emitting definitions | Type, enum, shape, source, constraint, derive |
| Expressions | Literal, field reference, call, comparison, null predicate, between, unary, binary |
| Calls | `lower/1`, `trim/1`, `len/1`, `matches/2` |
| Comparisons | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| Unary | `+`, `-` |
| Binary | `and`, `or`, `+`, `-`, `*`, `/`, `%` |
| Identifiers | Always double quoted; embedded quotes doubled |
| Literals | `NULL`, Boolean, integer, finite float, and escaped text |
| Relations | Ordered projections, explicit aliases, `FROM`, optional `WHERE` |
| Relation inputs | Static PostgreSQL source or quoted relation name |
| Diagnostics | Ordered `PIE-B1000` for unsupported or invalid emission |

The backend does not support `LIKE` even though the parser recognizes it.
An unsupported `ComparisonIR` operator remains a backend capability failure.

Phase 9 must not refactor this implementation or alter its output.

## Future MySQL Candidate Capability

The initial MySQL 8.0+ candidate may declare:

- `mysql.table(Text)`;
- the same minimal relation forms as PostgreSQL;
- literals and field references;
- comparisons, null predicates, between, unary, arithmetic, and Boolean
  operators accepted by the MySQL MVP contract;
- `lower/1`, `trim/1`, and `len/1`, with `len` mapped to character-length
  semantics;
- MySQL-specific identifier and literal policies.

`matches/2` must be absent from the initial MySQL capability declaration until
regex function/operator choice, collation, case sensitivity, Unicode, and
escaping semantics are accepted.

Consequently:

- `matches` remains a semantically known Pietto function;
- a relation using `matches` may pass semantic analysis;
- the MySQL backend must produce a deterministic backend diagnostic;
- it must not substitute `LIKE`, `REGEXP`, `REGEXP_LIKE`, or another
  approximation;
- no partial SQL artifact is produced for the failed relation.

This is a future contract only. Slice 3 does not add the connector, backend,
CLI dialect, or diagnostic behavior.

## Connector And Backend Compatibility

Once both connectors and backends exist, the initial compatibility matrix is:

| Selected backend | `postgres.table` | `mysql.table` |
|---|---|---|
| PostgreSQL | Supported | Backend diagnostic |
| MySQL | Backend diagnostic | Candidate supported |

The matrix is exact. Backends do not reinterpret another dialect's connector.

A relation-to-relation input is backend-local logical metadata rather than a
physical connector. It continues to use the quoted upstream relation name
under the current minimal artifact model.

## Functions, Expression Nodes, And Operators

Semantic and backend support are intentionally separate:

- semantic support means a Pietto expression is a valid, typed language
  construct;
- backend support means one selected SQL dialect has an approved rendering
  with accepted semantics.

Semantic analysis owns function existence, arity, argument types, predicate
typing, field resolution, and other language-level checks.

The backend owns:

- whether the expression IR node is supported;
- whether a semantically valid call has a dialect mapping;
- whether an operator has accepted dialect semantics;
- rendering, precedence, and parentheses;
- deterministic rejection when no mapping exists.

The backend must match calls by stable Pietto callee identity and arity. It
must not derive support from similarly named SQL functions.

An unknown Pietto function is semantic `PIE-S2103`. A known function with
invalid Pietto arguments is semantic `PIE-S2104`. A valid Pietto function
without a selected-backend mapping is backend `PIE-B1000`.

## Identifier And Literal Policies

Identifier and literal rendering are backend-owned policies, not shared
string helpers with assumed portability.

Each backend must explicitly define:

- identifier delimiters and delimiter escaping;
- empty and NUL rejection;
- qualified-name component handling;
- spelling and case preservation;
- reserved-word behavior;
- text delimiter and escape rules;
- backslash behavior and relevant SQL-mode assumptions;
- Boolean and `NULL` spelling;
- integer and finite-float representation;
- unsupported static-value rejection.

The PostgreSQL policy remains byte-exact. A future backend may share
well-tested policy helpers only when their semantics are identical; shared
code must not erase dialect ownership.

## Physical Table Names

The argument of current `postgres.table(Text)` is one opaque physical table
identifier. The backend quotes the complete string once:

```pietto
postgres.table("public.users")
```

```sql
FROM "public.users"
```

This behavior is a compatibility contract. Neither semantic analysis, IR
lowering, nor a future backend abstraction may reinterpret the value. They
must not split on `.`.

The initial future `mysql.table(Text)` candidate must use the same
one-argument, one-opaque-identifier contract. This defines source metadata
shape, not shared quoting behavior.

Structured catalog/schema/table qualification is deferred. It must be added
through an explicit new or versioned connector signature that supplies
separate static components. It must not reinterpret existing `Text` values,
and it must define component count, empty values, case rules, diagnostics,
and IR representation before implementation.

No specific qualified connector spelling is approved by this contract.

## Unsupported-Case Diagnostics

Failures are owned by the earliest stage with sufficient responsibility:

| Failure | Owner | Current/future result |
|---|---|---|
| Unsupported CLI dialect | CLI | Usage error, exit `2`, JSON `unsupported_dialect` |
| Non-call connector expression | Semantic | `PIE-S2306` |
| Unknown connector catalog name | Semantic | `PIE-S2306` |
| Invalid connector arity/type/static value | Semantic | `PIE-S2306` |
| Missing semantic prerequisite during lowering | IR | `PIE-I1000` |
| Known connector unsupported by selected backend | Backend | `PIE-B1000` |
| Valid function unsupported by selected backend | Backend | `PIE-B1000` |
| Unsupported expression node or operator | Backend | `PIE-B1000` |
| Invalid identifier/literal for selected backend | Backend | `PIE-B1000` |

`PIE-B1000` means the selected SQL backend cannot emit one requested case.
The current implementation and messages remain PostgreSQL-specific; future
backend work may make messages dialect-specific without changing the code
category.

Backend messages must identify:

- the selected backend;
- the affected definition;
- the unsupported connector, function, node, operator, or policy reason.

Backend diagnostics must retain deterministic definition order. New backends
should use the narrowest stable IR span available. Existing PostgreSQL
diagnostic locations and text remain unchanged unless a separate compatibility
change is approved.

A failed relation produces no artifact for that relation. Processing may
continue in definition order so supported artifacts and ordered diagnostics
can coexist, matching the current result model. Output-write behavior remains
owned by the existing CLI contract.

## No Best-Effort Generation

Future backends must fail closed.

They must not:

- transpile emitted PostgreSQL SQL into another dialect;
- silently replace one connector with another;
- select a dialect from connector names;
- split opaque physical names;
- substitute `LIKE` for regex matching;
- choose a dialect function based only on a similar name;
- drop unsupported predicates or projections;
- omit unsupported definitions without a diagnostic;
- invoke optimizer rewrites to make unsupported IR appear supported;
- emit partially rendered SQL for one failed relation.

Adding a SQL library does not relax this rule. Library warnings, fallback
generation, or best-effort transpilation must be converted into deterministic
Pietto rejection before an artifact is accepted.

## Security And Runtime Boundary

Connector validation and SQL generation are pure compiler operations.

This contract adds no:

- database driver;
- credentials or secret references;
- network access;
- DNS or endpoint handling;
- connector execution;
- schema introspection;
- SQL execution;
- transaction, migration, or DML behavior;
- plugin or dynamic module loading.

Any runtime or database proposal requires a separate threat model and phase.

## Compatibility Requirements

Later implementation must preserve:

- `emit_postgres_sql(ScriptIR) -> SqlResult`;
- current PostgreSQL byte-exact golden output;
- current PostgreSQL connector behavior;
- current CLI PostgreSQL invocation and exit codes;
- JSON schema version 1;
- parser, semantic, IR, and backend stage isolation;
- ordered artifacts and diagnostics;
- metadata non-emitting behavior;
- no execution or database access.

Adding a future connector or backend requires dedicated semantic, IR,
backend, CLI, diagnostic, and golden tests in its approved implementation
phase.

## Explicit Non-Goals

This contract does not implement or approve:

- `mysql.table`;
- `--dialect mysql`;
- SQLGlot or another SQL library;
- a dialect registry, protocol, class, or dispatch implementation;
- generic `table(...)` syntax;
- structured qualified-name syntax;
- grammar or generated parser changes;
- semantic catalog or IR lowering changes;
- PostgreSQL backend changes;
- JSON changes;
- richer SQL features;
- SQL execution, database connections, connector execution, or schema
  introspection;
- project/multi-file behavior, watch mode, LSP, Web UI, or compiler
  convenience wrappers.

## Acceptance Criteria

The contract is complete when:

- dialect-specific connector naming is explicit;
- semantic and backend responsibilities do not overlap ambiguously;
- required backend capability categories are enumerated;
- connector/backend compatibility is deterministic;
- the MySQL `matches` rejection policy is explicit;
- current dotted PostgreSQL names cannot be reinterpreted;
- unsupported combinations fail closed with stage-owned diagnostics;
- current PostgreSQL, CLI, JSON, grammar, semantic, IR, dependency, and
  runtime behavior remain unchanged.
