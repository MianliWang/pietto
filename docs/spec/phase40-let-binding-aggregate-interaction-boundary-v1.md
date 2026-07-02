# Phase 40 Let Binding Aggregate Interaction Boundary v1

## Status

Phase 40 Slice 8 is docs/spec and tests/static-audit boundary hardening only.
It does not implement aggregate-level `let:` support, change diagnostics, change
semantic implementation, change IR or SQL lowering, change CLI/JSON behavior,
or change metadata schemas.

## Trusted Baseline

- Phase 40 Slice 7 is complete, pushed, and CI green.
- Latest trusted commit:
  `d26e619e96d7e19777ee778dc79e9c1ab09250e4`.
- Latest trusted subject: `Harden Phase 40 let binding CLI JSON metadata`.
- Package version remains `0.1.0`.
- No tag, release, publish, upload, signing, or attestation is authorized by
  Slice 8.

## Supported Row-Level Let Scopes

The current public `let:` MVP is row-level inline expansion only. Let names may
be referenced from these input-row scopes:

- row-level `where`, including pre-aggregate `where gross > 0` in grouped
  queries;
- no-GROUP non-aggregate `select`, such as `gross_value = gross`;
- no-GROUP input-scope `order by`, such as `order by: gross`.

These supported scopes inline the let expression at the reference site. They do
not create a relation layer, a SQL alias-reuse layer, hidden CTEs, hidden
subqueries, or public metadata keys.

## Deferred Aggregate Interaction Boundary

Aggregate arguments do not see let names in Slice 8. The following forms remain
fail-closed and deferred when `gross` is a let binding:

- `sum(gross)`
- `avg(gross)`
- `count(gross)`
- `count_distinct(gross)`

This is a deferred boundary, not a permanent language rejection. Future
aggregate-let work may choose to support these forms, but only in a separately
approved slice with an explicit contract.

Future aggregate-let support requires:

- explicit semantic aggregate-argument scope design;
- IR aggregate-argument inline expansion design;
- SQL stability proof for PostgreSQL and the private MySQL path;
- diagnostics policy for unsupported aggregate-let cases;
- proof that aggregate arguments do not inherit projection aliases as
  expression leaves.

## Result-Scope And Clause Boundaries

Let names remain unavailable in non-row-level or result-scope positions:

- `group by gross` remains fail-closed/deferred;
- `satisfying: gross > 0` remains fail-closed/deferred;
- grouped `order by gross` remains fail-closed/deferred;
- `limit gross` remains fail-closed/deferred;
- qualified let references such as `orders.gross` remain rejected.

`where gross > 0` in a grouped query remains supported because `where` is
pre-aggregate input-row scope. `satisfying:` remains Pietto result-predicate
syntax over selected outputs, not SQL `HAVING` syntax over arbitrary row-level
let names.

Projection aliases remain output names only. They do not become aggregate
argument leaves, scalar expression leaves, or reusable aliases inside the same
relation body.

## IR, SQL, JSON, And Metadata Guardrails

Slice 8 authorizes no new IR node type and no public schema change:

- no `LetBindingIR`;
- no `RelationLayerIR`;
- no hidden CTE insertion;
- no hidden subquery insertion;
- no SQL renderer changes;
- no CLI/JSON schema changes;
- no public `let_scopes` metadata key.

Unsupported aggregate-let programs must fail before SQL artifacts are produced.
Supported row-level let programs must continue to emit inline expression SQL
without hidden relation layers.

## Validation Posture

Slice 8 validation should prove both sides of the boundary:

- supported row-level `let:` still passes semantic, IR, SQL, CLI, and metadata
  paths;
- aggregate arguments and result-scope consumers do not see let names;
- unsupported aggregate-let programs produce diagnostics and no SQL artifacts;
- package version remains `0.1.0`;
- no release, tag, publish, upload, signing, or attestation is authorized.
