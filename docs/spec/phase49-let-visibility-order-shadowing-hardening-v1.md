# Phase 49 Let Visibility/Order/Shadowing Hardening v1

## Purpose

This specification locks Phase 49 Slice 8: Let visibility/order/shadowing
hardening. Slice 8 is docs/spec/tests-only hardening for the project-private
selected `let` behavior introduced by Slice 7.

The goal is to prove that selected `let`-derived output schema remains narrow:
legal selected `let` outputs may become private project row fields, while
existing public `let` visibility, source-order, shadowing, and fail-closed
rules remain unchanged.

Package version remains `0.1.0`.

## Public Default Behavior

Public single-file `let` semantics remain unchanged by Slice 8. Default calls
to the semantic `let` helper continue to fail closed when a `let` binding name
conflicts with a projection output name, including an unaliased selected bare
`NameExpr` output.

The following cases remain invalid, diagnostics-preserving, or non-concrete
under existing public rules:

- duplicate `let` names;
- `let` names shadowing input fields;
- `let` names shadowing the input qualifier or relation name;
- projection-output conflicts with `let` names;
- self references;
- later or forward references;
- aggregate calls inside `let:`;
- qualified `let` references such as `users.total`;
- grouped output, grouped result ordering, and result-scope uses that are not
  row-level `let` consumers.

Slice 8 adds no public diagnostics and preserves existing diagnostic wording
and ordering.

## Project-private Selected Let Behavior

The project-private selected `let` exemption remains exact and default-off.
Only this shape may pass through the project-private path:

```pietto
query projected:
    from users
    let:
        total = score + bonus
    select:
        total
```

The selected output must be an unaliased bare `NameExpr` whose output name is
the same concrete relation-local `let` binding name. The exemption exists only
inside private project semantic construction.

Direct input field lookup keeps priority. If a selected bare name is an input
field, the output remains a source-native direct projection even when a local
`let` binding attempts to use the same name and the local `let` facts become
non-concrete.

Aliased selected `let` references remain supported when the alias does not
conflict with a `let` output name:

```pietto
query projected:
    from users
    let:
        total = score + bonus
    select:
        exported_total = total
```

When the relation has concrete private `let` facts, this output remains a
private `LET_DERIVED` field with `field_def=None`.

Alias-output conflicts remain invalid or non-concrete. For example, if
`total` is a `let` binding, `total = id` is a projection output conflict and
must not turn the `let` binding into concrete private selected-let schema.

Downstream propagation of a let-derived output may project the propagated
field, but it must preserve `field_def=None`. It must not make the field
source-native and must not synthesize a private derived `FieldDef`.

## Existing Behavior Preservation

Slice 8 preserves Slice 4 through Slice 7 project row schema behavior:

- direct and renamed direct projections preserve source-native `field_def`;
- computed aliases remain private `DERIVED_EXPRESSION` fields with
  `field_def=None`;
- selected legal `let` outputs remain private `LET_DERIVED` fields with
  `field_def=None`;
- invalid `let` facts do not produce selected let-derived output fields;
- aggregate and grouped output schema remains deferred to Phase 50 or later.

Slice 8 does not change parser behavior, grammar, generated files, public
semantic APIs, CLI behavior, IR, SQL, project explain, project IR, project SQL,
project `emit-sql`, JOIN/relationship behavior, bridge/export/RAG/Arrow
behavior, import/export behavior, multi-file behavior, runtime/database
execution, package metadata, lockfiles, workflows, fixtures, goldens, tags, or
release operations.

## Privacy

Project JSON v2 remains unchanged. It serializes no private row schema facts,
let facts, value types, provenance, origin, dependency, lineage, status, or
reason facts.

This privacy boundary also applies to CLI text, CLI JSON v1, Semantic Metadata
Artifact v1, IR, SQL, and future public APIs unless a later phase explicitly
changes it.

## Future Relationship

Slice 8 is boundary hardening only:

- private row-level dependency graph remains Slice 9;
- lineage carriers remain Slices 10 and 11;
- aggregate and grouped output schema remains Phase 50 or later;
- project explain, project IR, project SQL, project `emit-sql`, JOIN,
  relationship behavior, bridge/export/RAG/Arrow, import/export, runtime, and
  database behavior remain deferred.
