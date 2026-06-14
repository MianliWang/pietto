# Pietto Language Direction Version 1

## Status

Phase 16 Slice 1 is complete as design, specification, and audit work only.
This document records language direction and evaluation principles. It
defines no new accepted Pietto syntax and authorizes no compiler, runtime, or
database implementation.

## Language Identity

Pietto is a typed SQL authoring DSL. It is intended to make ordinary SQL
logic easier to write, read, check, document, and compile while preserving a
clear path to the SQL that a selected backend emits.

The language identity has these commitments:

- readable, indentation-based source with colon-delimited blocks;
- a small core language whose behavior can be checked deterministically by
  the compiler;
- diagnostic-first failure reporting with precise, structured errors;
- explicit syntax at dangerous or ambiguous boundaries;
- a familiar and concise path for normal single-relation queries;
- an honest distinction between compile-time guarantees and
  runtime/database security.

Compiler-safe means that accepted language features should have bounded,
deterministic compiler behavior, explicit ownership between stages, and
fail-closed diagnostics for unsupported or ambiguous cases. It does not mean
that generated SQL is authorized, private, transactionally safe, or safe to
execute in an arbitrary database environment.

The language-direction slogan is:

> Simple by default, explicit when dangerous, fail closed on ambiguity.

## Syntax Style

Pietto syntax should follow these principles:

1. Use colon plus indentation for blocks. Do not introduce braces as block
   delimiters.
2. Keep the keyword and punctuation vocabulary small. A new keyword needs a
   concrete readability or safety benefit.
3. Make common SQL authoring tasks direct and recognizable. Normal queries
   should not require graph, metric-layer, or policy-model ceremony.
4. Prefer explicit names and clauses when an operation changes relation
   scope, introduces fanout, crosses a trust boundary, or has multiple
   plausible interpretations.
5. Reject ambiguity with source-located diagnostics instead of guessing,
   silently selecting a candidate, or relying on backend behavior.
6. Keep parser, semantic, IR, and backend responsibilities distinct. Syntax
   should not imply a guarantee that its owning compiler stage cannot
   enforce.
7. Add syntax only through a separately reviewed contract and explicitly
   authorized implementation slice.

This slice does not add syntax, keywords, parser rules, AST nodes, semantic
rules, IR definitions, or SQL forms.

## Relationship Metadata Position

Relationship metadata is secondary descriptive metadata for possible future
language work. It is not the center of ordinary Pietto query authoring, and
Pietto is not a relationship-graph language first.

The currently implemented relationship metadata:

- records and validates names and endpoints;
- remains outside relation, type, and callable namespaces;
- remains outside Semantic IR and SQL generation;
- does not create a JOIN or relation-composition operation;
- does not authorize endpoint-qualified lookup or multi-input queries;
- does not perform SQL lowering;
- does not enforce runtime authorization, access control, privacy, or
  database security.

Any future relationship-aware query capability requires a separate syntax,
semantic, ambiguity, SQL-shape, and security review. Existing metadata must
not be treated as implicit query behavior.

## Compile-Time And Runtime Boundary

Pietto's compiler may provide parse checks, type checks, name resolution,
static connector validation, deterministic diagnostics, immutable Semantic
IR, and conservative SQL generation for implemented features.

Those compile-time properties do not provide:

- database authentication or authorization;
- row-level security, masking, privacy, or policy isolation;
- transaction, lock, concurrency, or execution guarantees;
- connector or database execution;
- schema introspection or validation against a live database;
- protection from every data-dependent cost or backend behavior.

The selected database and its operators remain responsible for execution,
credentials, privileges, transactions, physical planning, resource
governance, and runtime enforcement. Pietto must not claim runtime security
or privacy guarantees unless separately implemented, threat-modeled, tested,
and documented.

## Future Direction Candidates

The following are equal candidates for later planning. Their order does not
express priority, and none is an automatic next step or implementation
authorization:

- core SQL authoring improvements;
- aggregates and measures planning;
- relationship-aware querying;
- strict mode design;
- project workflow.

Each candidate requires a separately authorized phase or slice with explicit
syntax, compiler-stage, compatibility, diagnostic, and security boundaries.

## Explicit Non-Goals

Pietto is:

- not a runtime database framework;
- not an access-control system;
- not a relationship graph language first;
- not a Malloy clone;
- not a security-policy DSL.

This specification makes no runtime authorization, access-control, privacy,
isolation, database-execution, or safe-sharing guarantee. It introduces no
diagnostic code and reserves no diagnostic code.
