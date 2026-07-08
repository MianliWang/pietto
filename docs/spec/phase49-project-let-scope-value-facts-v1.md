# Phase 49 Project Let Scope/Value Facts v1

## Purpose

This specification locks Phase 49 Slice 6: Project let scope/value facts.
Slice 6 adds private per-relation project facts for relation-local `let:`
bindings. These facts record the parse clause, source-ordered binding names,
binding expressions, and known `ValueType(resolved_type, nullability)` facts
when existing legal row-level let semantics can type them safely.

The facts are private project semantic state. They are readiness plumbing for
later selected `let` output schema, dependency graph, and lineage slices. They
are not public behavior.

Package version remains `0.1.0`.

## Non-goals

Slice 6 does not implement:

- selected `let`-derived output schema;
- Project JSON v2 let fact, value type, binding expression, status, or reason
  output;
- public project semantic API;
- new public diagnostics or diagnostic wording changes;
- parser, grammar, or generated ANTLR changes;
- project explain;
- project IR;
- project SQL;
- project `emit-sql`;
- JOIN or relationship behavior;
- bridge, export, RAG, Arrow, import, or export behavior;
- multi-file language behavior beyond existing private project semantic state;
- private row-level dependency graph;
- full lineage carrier;
- aggregate or grouped output schema;
- runtime or database execution;
- package version, tag, release, publish, upload, signing, or attestation.

Slice 6 also does not expand `let` syntax, row expression syntax, or expression
typing semantics.

## Source Of Truth

Project let facts reuse existing legal single-file row-level `let` semantics as
much as possible. The preferred private source is
`analyze_relation_let_bindings` from the semantic let helpers, supplied with a
project-private input row schema converted to semantic `RowSchema` facts.

Slice 6 must not call full `semantic_api.analyze`. It does not run full
single-file analysis for a project relation, and it does not replace existing
project diagnostics or diagnostic ordering.

The project helper may import semantic let helper and `ValueType` model types.
It must not emit diagnostics, mutate `ProjectSemanticModel`, resolve select
items through let facts, build output row schema fields, or expand the
expression language.

## Carrier Shape

The private carrier is stored from `ProjectSemanticModel` by relation
definition key (`TableDef` or `QueryDef`). The carrier records:

- private status: concrete, unknown, deferred, blocked, or absent;
- deterministic private reason;
- the `LetClause` reference when present;
- source-ordered `LetBinding` references;
- a mapping from let binding name to binding expression reference;
- a mapping from let binding name to known semantic `ValueType` for concrete
  facts.

Relations without a `let:` clause use a deterministic absent fact instead of
being omitted. This keeps project semantic consumers from guessing whether a
missing map entry means absence or an unavailable build path.

Concrete facts require all source-ordered binding names to have known value
types. Non-concrete and absent facts carry no concrete `value_types`.

## Upstream Behavior

For an upstream concrete row schema, Slice 6 attempts to infer private let value
types using existing semantic let helper behavior. If the helper reports local
let diagnostics, the project fact becomes non-concrete with a suppressed-local
diagnostics reason. Those local helper diagnostics are not emitted by project
semantics in Slice 6.

For upstream unknown, deferred, or blocked row schema state, Slice 6 stores a
matching deterministic non-concrete private let fact and no concrete
`value_types`.

If required type facts are missing or current semantic behavior returns
`ValueTypeKind.UNKNOWN`, the project fact stays non-concrete with a
missing-or-unknown value type reason.

## Diagnostics

Slice 6 adds no public diagnostics and preserves existing diagnostic ordering.
Project diagnostics continue to come from the existing project semantic paths.
Local diagnostics produced by the reused semantic let helper are suppressed into
private status/reason facts only.

## Selected Let Output

Private let facts may exist for a relation while selecting a let binding remains
out of scope for project row schema. Current behavior for examples such as:

```pietto
query projected:
    from users
    let:
        total = score + 1
    select:
        total
```

remains unchanged until Slice 7. Slice 6 must not use private let facts to make
`total` a concrete output field. Future let-derived output fields must use
`field_def=None`, but Slice 6 creates no such output fields.

## Privacy

Project JSON v2 serializes no private let facts. It must not expose
`relation_let_scope_facts`, `ProjectRelationLetScopeFacts`, let binding
expression references, `ValueType` values, private let statuses, private let
reasons, or helper implementation names.

This privacy boundary also applies to CLI text, CLI JSON v1, Semantic Metadata
Artifact v1, IR, SQL, and any future public API unless a later phase explicitly
changes it.

## Future Relationship

Slice 6 prepares only private fact storage:

- selected `let`-derived output schema remains Slice 7;
- let visibility, ordering, and shadowing hardening remains Slice 8;
- private row-level dependency graph remains Slice 9;
- full lineage carrier remains Slices 10 and 11;
- aggregate and grouped output schema remain Phase 50 or later;
- project explain, project IR, project SQL, project `emit-sql`, JOIN,
  relationship behavior, bridge/export/RAG/Arrow, import/export, runtime, and
  database behavior remain deferred.
