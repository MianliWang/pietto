# Phase 40 Let Binding Syntax And Scope Contract v1

## Status And Non-Behavior-Change Guardrail

Phase 40 Slice 2 is Let Binding Syntax And Scope Contract. Slice 2 is
docs/spec/static-audit/tests-only and authorizes no behavior change.

This document defines the future syntax and scope contract for explicit
row-level `let:` bindings. It does not implement `let:`, does not change
source/compiler behavior, and does not change grammar, generated ANTLR files,
parser behavior, AST behavior, semantic behavior, IR behavior, SQL lowering,
CLI behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1,
diagnostic envelope shape, SQL golden bytes, fixtures/goldens, examples,
scripts, workflows, package metadata, lockfiles, package version, public
status docs, release operations, tags, publish/upload, signing, or
attestation.

Trusted Slice 1 baseline:

- baseline HEAD: `475e3a17978b51d8670db042e66ef7b80672c27e`;
- baseline branch: `main`;
- baseline commit: `Add Phase 40 let binding model candidate`;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation is authorized by Slice 2.

Slice 1 completed the Phase 40 Let Binding Model Candidate Decision, selected
explicit `let:` binding over projection-alias expression reuse, and kept the
first behavior MVP row-level only. Slice 2 records the precise syntax and
scope contract that later parser, semantic, IR, and SQL slices must follow if
they are separately approved.

## Current Repo-Derived Facts

The current repository has no accepted `let:` behavior.

| Area | Current fact |
|---|---|
| Relation syntax | `grammar/Pietto.g4` uses one shared `tableBody` for both `table` and `query` definitions. |
| Relation body order | The current relation body order is `from`, optional `where`, optional `group by`, required `select`, optional `satisfying`, optional `order by`, optional `limit`. |
| AST shape | `TableDef` and `QueryDef` store the current relation clauses. There is no current `LetClause` or `LetBinding`. |
| Projection aliases | Projection aliases are output names. They are not reusable expression leaves and must not become row-level variables by accident. |
| Row-level scope | Current `where`, no-GROUP `select`, and no-GROUP input-scope `order by` expressions use the input row-level scope. |
| Result scope | Current `satisfying:` and grouped `order by:` use selected-output/result scope, not input row-level scope. |
| IR shape | Current `RelationIR` is a single-layer relation model. There is no `RelationLayerIR`. |
| SQL rendering | PostgreSQL and private MySQL relation renderers currently emit one SELECT and do not insert hidden CTE or hidden subquery layers. |

These facts make an explicit row-level binding contract possible, but they do
not authorize implementation in Slice 2.

## Future Syntax Contract

If a later slice separately approves parser work, future `let:` is one
optional relation-body section shared by `table` and `query` definitions.

The MVP placement is after `from` and before `where`:

```pietto
table order_totals:
    from orders
    let:
        gross = amount + tax
        normalized_status = lower(status)
    where gross > 0
    select:
        gross_total = gross
```

This example is illustrative only. Slice 2 does not make it parse, type, lower,
or render SQL.

The future MVP rejects `let:` after any of these sections:

- `where`;
- `group by`;
- `select`;
- `satisfying`;
- `order by`;
- `limit`.

A later parser slice may add `LET: 'let'`, but Slice 2 does not implement
grammar. Keyword compatibility must be considered so existing identifier
behavior is not casually broken; Pietto currently keeps new language keywords
valid in identifier positions for compatibility.

## Binding Item Syntax

Each future binding item uses `name = expression`.

Binding names follow existing Pietto identifier rules. In current grammar
terms, identifiers are ASCII letter or underscore followed by ASCII letters,
digits, or underscores, with the existing keyword-compatibility policy for
identifier positions.

The following remain rejected or deferred:

- SQL-style `expression AS name` remains rejected;
- destructuring is deferred;
- tuple binding is deferred;
- multiple assignment is deferred;
- binding type annotations are deferred.

Assignment remains a relation binding item form only. It is not a general
expression form.

## Scope And Visibility Contract

The first behavior MVP is row-level only.

| Clause or surface | First-MVP `let:` visibility |
|---|---|
| `where` | May see let names. |
| no-GROUP `select` | May see let names. |
| no-GROUP input-scope `order by` | May see let names. |
| `group by` | Does not see let names in the first behavior MVP. |
| aggregate arguments | Do not see let names in the first behavior MVP. |
| `satisfying:` | Does not see let names directly and remains selected-output/result scope. |
| grouped `order by` | Does not see let names directly and remains selected-output/result scope. |
| `limit` | Does not see let names. |

Aggregate arguments referencing let names, such as `sum(gross)`, are deferred
to a later Phase 40 slice, not permanently rejected by the whole phase.
Group-by interaction is deferred to a later contract or behavior slice.

This contract intentionally keeps input row-level scope distinct from
selected-output/result scope. A row-level `let:` name must not leak into
`satisfying:` or grouped result ordering merely because those surfaces can see
selected output names.

## Binding Dependency Contract

Bindings are source-ordered and deterministic.

For the future MVP:

- earlier let references are allowed;
- later references fail closed;
- self-reference fails closed;
- cycles fail closed;
- unresolved input field references inside binding expressions fail closed;
- unresolved let references fail closed.

Later semantic implementation must preserve deterministic diagnostic ordering
and source-span ownership. Slice 2 introduces no diagnostics and does not
choose final diagnostic codes for let-specific dependency failures.

## Naming And Shadowing Contract

The future MVP uses a no-shadowing policy:

- duplicate let names fail closed;
- let names cannot shadow input fields;
- let names cannot shadow the input qualifier or relation name;
- let names cannot shadow projection aliases;
- projection aliases cannot shadow let names;
- projection aliases must not become expression leaves.

Projection aliases remain output names after the projection boundary. They do
not become row-level reusable scalar expressions, aggregate argument leaves, or
hidden input variables.

## Qualification Contract

Let references are bare-only. A future let binding named `gross` is referenced
as `gross`, not as `orders.gross`.

Source-qualified field leaves such as `orders.amount` remain valid inside let
expressions under existing single-input qualifier rules.

Qualified let references such as `orders.gross` are rejected. A dotted name in
the first behavior MVP remains a field reference governed by the existing
single-input qualifier contract, not a let-binding qualifier mechanism.

## Aggregate And Result-Scope Boundary

Aggregate calls inside `let:` are forbidden for the first behavior MVP.

The following remain deferred:

- aggregate-level let binding;
- aggregate arguments referencing let names;
- aggregate binding in `satisfying:`;
- post-aggregate expression composition;
- `RelationLayerIR`;
- hidden CTE insertion;
- hidden subquery insertion;
- relationship-driven lookup or JOIN behavior.

`satisfying:` continues to expose Pietto result predicates, not SQL `HAVING`
source syntax. Direct SQL `HAVING` syntax remains unavailable.

## SQL Lowering Posture

Later behavior slices should prefer explicit inline expression expansion first.
For example, a future valid row-level let expression referenced from `where`,
no-GROUP `select`, or no-GROUP input-scope `order by` should lower by rendering
the approved expression at the reference site after semantic validation and IR
lowering have proved it safe.

Hidden CTE insertion remains forbidden unless separately approved. Hidden
subquery insertion remains forbidden unless separately approved.

Stable SQL output must be protected. Any later behavior slice must provide
PostgreSQL and private MySQL parity evidence, fixture/golden policy if bytes
change, and explicit proof that current projection aliases, `satisfying:`,
grouped ordering, and aggregate boundaries remain stable.

## Diagnostic Posture

Slice 2 introduces no new diagnostics and changes no diagnostic wording.

Later slices may reuse existing diagnostics where appropriate, including:

- existing unknown field diagnostics for unresolved input fields;
- existing duplicate-name or duplicate-output families where a future contract
  explicitly assigns ownership;
- existing aggregate invalid-context, aggregate composition, nested aggregate,
  and deferred aggregate argument diagnostics;
- existing `satisfying:` selected-output diagnostics for result-scope misuse.

Let-specific duplicate, shadowing, forward-reference, self-reference, and cycle
cases may require new semantic codes later. Slice 2 only documents that likely
need; it does not reserve or introduce those codes.

## Public Surface And Release Guardrails

Slice 2 keeps public surfaces unchanged:

- grammar/generated inventory unchanged;
- parser and AST behavior unchanged;
- source/compiler behavior unchanged;
- semantic behavior unchanged;
- IR behavior unchanged;
- SQL behavior unchanged;
- CLI text output unchanged;
- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- examples/fixtures/goldens unchanged;
- scripts/workflows unchanged;
- package metadata unchanged;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation.

Any later behavior slice must separately name its implementation files,
validation commands, SQL portability proof, compatibility proof, diagnostic
policy, and release non-authorization.
