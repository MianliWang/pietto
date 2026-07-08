# Phase 49 Selected Let-derived Output Schema v1

## Purpose

This specification locks Phase 49 Slice 7: Selected let-derived output schema.
Slice 7 lets private project row schema construction record selected
`let`-derived output fields when the current relation has concrete private
`let` value facts and a selected bare name resolves to a known `let` binding.

These facts remain private project semantic state. They are not Project JSON v2
output, public semantic API, project explain output, IR, SQL, runtime behavior,
or database behavior.

Package version remains `0.1.0`.

## Scope

Slice 7 supports selected row-level `NameExpr` outputs that resolve to concrete
relation-local `let` facts after direct input field lookup fails. Both forms
are eligible:

```pietto
query projected:
    from users
    let:
        total = score + 1
    select:
        total
```

```pietto
query projected:
    from users
    let:
        total = score + 1
    select:
        exported_total = total
```

Direct input fields keep priority. If a selected bare name is an input field,
the field remains a source-native direct projection and preserves its original
`FieldDef`. Slice 7 does not add syntax, expression forms, qualification rules,
or new `let` visibility rules.

## Source Of Facts

Slice 7 uses `ProjectSemanticModel.relation_let_scope_facts` behavior and
concrete `ProjectRelationLetScopeFacts.value_types` as the private source of
selected `let` output type and nullability. These facts are built from the
existing semantic `analyze_relation_let_bindings` helper and a project-private
input row schema converted to semantic row-schema facts.

Project row schema construction may reuse
`adapt_project_row_expression_schema(..., let_value_types=...)` to adapt the
known semantic `ValueType(resolved_type, nullability)` into project-private row
field facts.

Slice 7 must not call full `semantic_api.analyze`. It must not add Project JSON
v2 serialization, public diagnostics, or public project semantic API behavior.

## Output Field Contract

For a concrete selected let-derived output field, project row schema
construction records a private `ProjectRowField` with:

- the resolved type converted from the selected let `ValueType`;
- the nullability converted from the selected let `ValueType`;
- `field_def=None`;
- private `ProjectRowFieldProvenanceKind.LET_DERIVED`;
- the immediate upstream project symbol as private provenance symbol;
- the selected expression or adapter-result location.

Let-derived fields must not synthesize derived `FieldDef` values. Derived
fields must not look source-native.

Downstream direct projection of a let-derived field may project the field, but
it must preserve `field_def=None` rather than making the field source-native.

Computed aliases remain `DERIVED_EXPRESSION`. Direct and renamed direct input
fields remain direct projections and preserve source-native `field_def`.

## Semantic Let Conflict Exemption

Existing public single-file semantic behavior remains unchanged by default.
The semantic let helper may expose a default-off internal parameter for project
semantic construction. That project-only parameter may permit exactly this
case:

- a let binding name matches an unaliased selected bare `NameExpr` output in
  the same relation.

The exemption does not permit alias-output conflicts such as `total = id` when
`total` is a let binding. It does not permit duplicate let names, input-field
shadowing, source-name shadowing, self references, later references,
aggregate-in-let, qualified let references, grouped/result-scope `let` use, or
any broader visibility, ordering, or shadowing behavior.

Default public calls to the semantic helper must preserve existing diagnostic
wording and diagnostic ordering.

## Invalid And Non-concrete Behavior

Selected let output stays non-concrete when relation-local let facts are
absent, unknown, deferred, blocked, or missing the selected value type.

The following remain non-concrete or diagnostics-preserving under existing
rules:

- duplicate let names;
- input-field shadowing;
- source-name shadowing;
- alias-output conflicts other than the exact unaliased selected-let case;
- self references and later references;
- aggregate calls inside `let:`;
- qualified let references;
- grouped/result-scope `let` uses;
- missing, unknown, deferred, or blocked upstream row schemas;
- aggregate and grouped output schema.

Slice 7 adds no public diagnostics. Existing project diagnostic ordering is
preserved.

## Privacy

Project JSON v2 remains unchanged. It serializes no private row schema facts,
let facts, value types, provenance, origin, dependency, lineage, status, or
reason facts. This privacy boundary also applies to CLI text, CLI JSON v1,
Semantic Metadata Artifact v1, IR, SQL, and future public APIs unless a later
phase explicitly changes it.

## Future Relationship

Slice 7 prepares only private selected let-derived output schema:

- broader let visibility, ordering, and shadowing hardening remains Slice 8;
- private row-level dependency graph remains Slice 9;
- full lineage carrier remains Slices 10 and 11;
- aggregate and grouped output schema remain Phase 50 or later;
- project explain, project IR, project SQL, project `emit-sql`, JOIN,
  relationship behavior, bridge/export/RAG/Arrow, import/export, runtime, and
  database behavior remain deferred.
