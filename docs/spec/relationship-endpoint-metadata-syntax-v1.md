# Relationship Endpoint Metadata Syntax Version 1

## Status

This contract is implemented by Phase 14 Slice 3 as a parse-only and AST-only
language surface.

Relationship declarations are accepted only as source metadata. Successful
parsing does not establish that referenced relations exist, endpoint names
are unique, a relationship is valid, relations can be composed, or any query
is authorized or executable.

This slice adds no semantic validation, Semantic IR representation, SQL
output, CLI or JSON behavior, runtime behavior, connector behavior, database
connection, database execution, or schema introspection.

## Accepted Syntax

A relationship metadata declaration is a top-level indentation block:

```pietto
relationship membership:
    endpoint member: users
    endpoint group: groups
```

The declaration has:

- the contextual word `relationship`;
- one declaration name;
- a colon followed by a newline and one indented block;
- exactly two endpoint lines.

Each endpoint line has:

- the contextual word `endpoint`;
- one local endpoint metadata name;
- a colon;
- one referenced relation name;
- a newline.

Blank lines are allowed before, between, and after the two endpoint lines
inside the declaration block. The endpoints remain ordered by source
position. Multiple top-level relationship declarations are accepted and
preserved in source order.

The declaration and endpoint names use the existing identifier grammar.
Quoted names, dotted names, expressions, calls, aliases, annotations, and
additional endpoint attributes are not accepted in this syntax version.

## Contextual Words

`relationship` and `endpoint` receive dedicated lexer tokens so the parser can
recognize the metadata structure. They remain accepted by the existing
identifier and dotted-name rules.

They are therefore contextual language words rather than globally reserved
identifiers. Existing declarations, fields, relation names, expressions, and
connector name parts may continue to use either spelling where an identifier
is accepted.

At top level, `relationship` followed by the declaration shape begins
relationship metadata. Inside a relationship block, `endpoint` followed by
the endpoint shape begins one endpoint line.

## Indentation And Block Structure

Relationship metadata follows Pietto's existing block rules:

- a colon terminates the declaration header;
- a physical newline follows the header;
- endpoint lines share one indentation level deeper than the declaration;
- tabs remain subject to the existing indentation diagnostics;
- brace-delimited forms are not accepted;
- the block ends on dedent or end of file.

No nested block is introduced. Endpoint lines cannot contain child clauses.

## Malformed Forms

Existing parser behavior rejects malformed relationship metadata. Rejected
forms include:

- a declaration with no endpoint;
- a declaration with only one endpoint;
- a declaration with three or more endpoints;
- an endpoint outside a relationship block;
- a missing declaration name;
- a missing endpoint local name;
- a missing referenced relation name;
- a missing colon after the declaration name or endpoint local name;
- an unindented endpoint line;
- inconsistent indentation;
- a brace-delimited declaration;
- extra tokens after a referenced relation name.

Slice 3 reserves no diagnostic code and adds no relationship-specific
diagnostic. Malformed forms use the existing parser diagnostic behavior and
the existing parser diagnostic family.

## AST Mapping

The parser maps each accepted endpoint to an immutable
`RelationshipEndpoint` AST node with:

| Field | Meaning |
|---|---|
| `local_name` | The endpoint's source-level local metadata name. |
| `relation_name` | The source-level referenced relation name. |
| `span` | The endpoint line's one-based, half-open source span. |

The parser maps each accepted declaration to an immutable
`RelationshipMetadata` AST node with:

| Field | Meaning |
|---|---|
| `name` | The declaration name. |
| `endpoints` | Exactly two `RelationshipEndpoint` nodes in source order. |
| `span` | The full declaration's one-based, half-open source span. |

`Script.relationships` is an immutable tuple containing relationship metadata
declarations in source order. Its default is the empty tuple, so scripts with
no relationship metadata retain their existing definitions and behavior.

Relationship metadata is intentionally not part of `Script.definitions`.

## Stage Boundary

| Stage or surface | Slice 3 behavior |
|---|---|
| Lexer and parser | Accept only the syntax defined by this contract. |
| AST builder | Preserve declaration names, endpoint names, source order, and spans. |
| Parser API | Unchanged; existing entry points return the extended `Script`. |
| Semantic analysis | Unchanged and unaware of `Script.relationships`. |
| Semantic IR | Unchanged; relationship metadata is not lowered. |
| PostgreSQL and MySQL SQL | Unchanged; no relationship SQL is emitted. |
| CLI | Unchanged; no command, option, exit-code, or presentation change. |
| JSON | Unchanged; JSON schema version 1 remains the only implemented schema. |
| Runtime and database | No behavior is added. |

Existing programs without relationship metadata parse to the same ordered
`Script.definitions`. Their semantic model, Semantic IR, PostgreSQL and MySQL
SQL, CLI text, and JSON version 1 behavior remain unchanged.

## Non-Goals

This contract does not implement or authorize:

- JOIN or relation composition;
- multiple query inputs, composition predicates, CTEs, or subqueries;
- SQL shape or relationship SQL lowering;
- relationship semantic validation;
- relation-role semantics or endpoint-role enforcement;
- cardinality or fanout behavior;
- measures, dimensions, aggregates, grouping, or HAVING;
- nested table semantics;
- ambiguity or name-ownership resolution;
- permission gates, runtime authorization, or runtime security;
- access control, privacy enforcement, row-level security, masking, policy
  isolation, or safe data sharing;
- a threat model or security guarantee;
- a new diagnostic code or diagnostic-code reservation;
- SQL or connector execution, database connection, or schema introspection;
- JSON version 2, project mode, multi-file compilation, watch mode, LSP, Web
  UI, or a playground;
- SQLGlot or another dependency;
- a public MySQL emitter or generic public SQL emitter;
- release, publish, deployment, signing, upload, or attestation behavior.
