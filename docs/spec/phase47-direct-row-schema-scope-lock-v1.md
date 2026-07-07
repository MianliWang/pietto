# Phase 47 Direct Row Schema Scope Lock v1

## Status

Phase 47 Slice 1 locks the scope for:

**Direct Row Schema MVP candidate/scope lock only**

Slice 1 is docs/spec/static-audit only. It adds no source behavior, no private
row schema carrier scaffold, no source row schema propagation, no table/query
output schema propagation, no projection/body validation, no CLI behavior, no
Project JSON v2 behavior, no IR, no SQL, no project `emit-sql`, no project
`explain`, and no release behavior.

Phase 47 Slice 2 is Route Expansion And Downstream Readiness Lock.
Slice 2 is docs/spec/static-audit only and is additive to the committed Slice
1 scope lock. It adds no source behavior, no private row schema carrier
scaffold, no source row schema propagation, no table/query output schema
propagation, no direct field diagnostics implementation, no query-to-query row
schema propagation, no computed aliases, no `let` schema, no aggregate output
schema, no CLI behavior, no Project JSON v2 behavior, no IR, no SQL, no
project `emit-sql`, no project `explain`, and no release behavior.

Package version remains `0.1.0`.

## Selected Candidate

Phase 47 Slice 1 selects:

```text
A. Phase 47 Slice 1 candidate/scope lock only
```

The Slice 1 gate intentionally excludes:

- private row schema carrier scaffold;
- direct row schema implementation;
- direct field diagnostics implementation.

The direct row schema MVP remains the Phase 47 direction, but behavior belongs
to later bounded slices after this scope lock.

## Slice 2 Route Expansion Selection

Phase 47 Slice 2 selects:

```text
B. Add Phase 47 Slice 2 Gate 2 route expansion/static-audit update
```

Slice 2 expands the tentative Phase 47 route from six slices to eleven slices
because the six-slice route compressed too many behavior decisions into one
direct projection slice and did not lock downstream readiness for Phase 48
through Phase 50. Slice 2 is route expansion only and does not amend, rebase,
reset, or rewrite Slice 1 history.

## Authoritative Roadmap Source

Phase 46 is the authoritative current predecessor for Phase 47. Phase 46
states that row schema propagation is deferred to Phase 47 and that the Phase
47 entry direction is direct row schema MVP candidate work only.

The older `docs/spec/pietto-roadmap-phase45-60-v1.md` row that labels Phase 47
as `Project Semantic Metadata Artifact` is superseded for this Gate 2 by the
Phase 46 phase-specific closeout and this Direct Row Schema scope lock. This
Slice 1 does not edit that older roadmap document.

## Private Row Schema Vocabulary

Future Phase 47 row schema facts should use project-private vocabulary:

- a project row schema is ordered private semantic state for one project
  relation definition;
- a project row field records an output field name plus resolved project type
  and nullability facts;
- planned field-level concepts include `ProjectRowField.name`,
  `ProjectRowField.resolved_type`, `ProjectRowField.nullability`,
  `ProjectRowField.field_def`, and `ProjectRowField.provenance` or an
  equivalent private origin slot;
- planned schema-level concepts include `ProjectRowSchema.fields` and
  `ProjectRowSchema.is_unknown`;
- source row schemas come from source shape fields;
- relation row schemas come from approved table/query direct projections;
- unknown project row schemas are conservative private facts and do not imply
  successful projection/body validation.

The future carriers must be private frozen slots dataclasses and must not reuse
single-file `pietto.semantic.RowSchema` or related single-file semantic model
classes. The project semantic builder must preserve the existing boundary that
project checks do not call the single-file semantic analyzer.

The likely private carrier vocabulary is:

- `ProjectEffectiveNullability`;
- `ProjectRowField.name`;
- `ProjectRowField.resolved_type`;
- `ProjectRowField.nullability`;
- `ProjectRowField.field_def`;
- `ProjectRowField.provenance` or an equivalent private origin slot;
- `ProjectRowSchema.fields`;
- `ProjectRowSchema.is_unknown`;
- `ProjectSemanticModel.source_row_schemas`;
- `ProjectSemanticModel.relation_row_schemas`.

These are planned private carrier concepts, not Slice 2 implementation.

## Source Row Schema Boundary

Source row schema propagation belongs to a later Phase 47 behavior slice.

When implemented, source row schemas should be built only for sources whose
shape binding has already resolved through the existing project type namespace
facts. Source fields should preserve:

- source order from the referenced `ShapeDef.fields`;
- field name;
- resolved project type fact;
- explicit nullability as project-private nullability;
- original `FieldDef` owner where available.

Unresolved source shapes or non-shape source shape bindings should continue to
use existing project semantic diagnostics and should not require a new Project
JSON v2 field.

## Direct Relation Projection Boundary

The first table/query output schema behavior should be limited to direct source
input projections:

- bare `field`;
- `source.field` when the qualifier matches the table/query `from` source
  name, in a separate bounded behavior slice.

The first behavior slice should not support table/query inputs whose `from`
target resolves to another table/query. Query-to-query row schema propagation
is deferred to Phase 48 or later separate approval.

Unknown direct field references should use existing semantic diagnostics flow,
with `PIE-S2102` as the preferred existing diagnostic candidate. The final
diagnostic code, message, and location policy must be confirmed in the
behavior slice Gate 1 before implementation. Direct field diagnostics should
appear in project text and Project JSON v2 through
`ProjectSemanticResult.diagnostics` and the existing top-level semantic
diagnostics path. Project JSON v2 shape must remain unchanged.

## Alias And Expression Boundary

`alias = field` is a direct field rename, for example:

```pietto
select:
    user_id = id
```

It preserves input field type, nullability, and provenance while changing the
output name. It differs from bare `field` because the output name is explicit.
It differs from computed alias syntax such as `total = price + tax` because no
expression typing or computed value propagation is required. `alias = field`
is deferred from the first direct row schema behavior slice and belongs in
Phase 47 only as a late bounded slice after bare and qualified direct fields.
`alias = source.field` may be considered in that direct field rename slice
only after qualified direct fields are complete.

The following remain out of scope:

- computed aliases;
- expression typing for project relation bodies;
- same-`select` alias reuse;
- projection aliases as reusable bindings;
- `let` schema;
- aggregate output schema;
- grouped result schema;
- `where`, `order by`, `limit`, or `satisfying` body validation;
- any SQL lowering behavior.

## Downstream Readiness Boundary

Phase 47 may include readiness for Phase 48 query-to-query row schema
propagation, but Phase 47 must not implement query-to-query propagation
behavior. Private carriers should be shaped so future downstream relation
schemas can be stored without refactor, relation row schema mappings should be
deterministic, and Phase 48 remains the behavior phase for table/query to
table/query row schema propagation.

Phase 47 may include readiness for Phase 49 computed alias schema and
let-bound expression schema, but Phase 47 must not implement computed aliases
or `let` schema behavior. The row field carrier may reserve private
provenance or origin structure for future expression-derived fields. Computed
aliases and `let` remain deferred. No expression type inference is authorized
in Phase 47 unless a later Gate 1 explicitly widens scope.

Phase 47 may include readiness for Phase 50 aggregate output schema and
grouped result schema, but Phase 47 must not implement aggregate or grouped
output schema behavior. Row schema, nullability, and type vocabulary should
not block future aggregate result fields. Aggregate output schema remains
Phase 50 or later. No aggregate schema behavior is authorized in Phase 47
unless a later Gate 1 explicitly widens scope.

## Public Surface Rule

Phase 47 Slice 1 changes no public surface.

Future private row schema facts must not be serialized into Project JSON v2,
CLI JSON v1, Semantic Metadata Artifact v1, fixtures, goldens, public Python
APIs, generated artifacts, or SQL output unless a later Gate 1 explicitly
authorizes a public surface.

Project JSON v2 shape must remain unchanged. Semantic diagnostics may flow
only through the existing top-level `diagnostics[]` field. `cli_errors[]`
remains project/config/source-selection/source-read only. `inputs[]` and
`result.check` remain read/parse based.

## Explicit Deferrals

The following work is out of scope for Phase 47 Slice 1:

- private row schema carrier scaffold;
- source row schema propagation;
- table/query output schema propagation;
- direct field diagnostics implementation;
- `alias = field` before its late bounded Phase 47 direct rename slice;
- query-to-query row schema propagation;
- computed aliases;
- `let` schema;
- aggregate output schema;
- project IR;
- project SQL;
- project `emit-sql`;
- project `explain`;
- public project semantic API;
- private semantic fact serialization;
- Project JSON v2 shape change;
- parser/grammar/generated changes;
- single-file behavior changes;
- JOIN behavior;
- relationship-driven query behavior;
- runtime/database execution behavior;
- package version changes.

## Tentative Slice Roadmap

The tentative Phase 47 route is:

1. Candidate/scope lock only
2. Route expansion and downstream readiness lock
3. Private row schema carrier scaffold
4. Source shape fields to source row schema
5. Direct bare field projections from direct source inputs
6. Qualified direct field projections: `source.field`
7. Direct field rename projections: `alias = field`
8. Unknown direct field diagnostics and deterministic ordering
9. Downstream readiness hardening for Phase 48-50
10. Project JSON/private-fact privacy and compatibility hardening
11. Completion audit/status lock

Any change to this route requires a later Gate 1 revision.

## Forbidden Surfaces

Slice 1 changes no production source, generated parser artifacts, grammar, CLI
behavior, Project JSON v2 serializer behavior, CLI JSON v1 behavior, Semantic
Metadata Artifact v1 behavior, fixtures, goldens, scripts, workflows,
dependency files, package metadata, package version, tag, release, publish,
upload, signing, or attestation behavior.

Slice 1 does not add or change:

- `src/**`
- `grammar/**`
- generated parser files
- `fixtures/**`
- `goldens/**`
- `scripts/**`
- `.github/**`
- `pyproject.toml`
- `uv.lock`
- `README*`
- `AGENTS*`
- `docs/spec/pietto-v0.9.md`
- `docs/spec/pietto-roadmap-phase45-60-v1.md`
- `src/pietto/cli.py`
- `src/pietto/_project/json_v2.py`
- `src/pietto/_project/model.py`
- `src/pietto/_project/check.py`
