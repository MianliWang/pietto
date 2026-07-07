# Phase 47 - Direct Row Schema MVP

## Status

Phase 47 Slice 1 is Candidate Decision And Scope Lock for:

**Direct Row Schema MVP candidate/scope lock only**

Slice 1 is docs/spec/static-audit work only. It implements no source behavior,
no private row schema carrier scaffold, no source row schema propagation, no
table/query output schema propagation, no projection/body validation, no CLI
behavior, no Project JSON v2 behavior, no IR, no SQL, no project `emit-sql`,
no project `explain`, and no release behavior.

Phase 47 Slice 2 is Route Expansion And Downstream Readiness Lock.
Slice 2 is docs/spec/static-audit work only. It is an additive route update
after the committed Slice 1 scope lock. It implements no source behavior, no
private row schema carrier scaffold, no source row schema propagation, no
table/query output schema propagation, no unknown field diagnostics
implementation, no query-to-query propagation, no computed aliases, no `let`
schema, no aggregate output schema, no CLI behavior, no Project JSON v2
behavior, no IR, no SQL, no project `emit-sql`, no project `explain`, and no
release behavior.

Phase 47 follows the completed Phase 46 `Project Semantic Continuation`.
Phase 46 explicitly deferred direct row schema propagation to Phase 47 and
closed with the entry direction "direct row schema MVP candidate work only".
That Phase 46 closeout is the authoritative next-phase source for this work.

Package version remains `0.1.0`.

## Slice 1 Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `2d06552789b3fac1db604f6da3552fd73040956f`.
- Baseline subject: `Complete Phase 46 project semantic continuation audit`.
- Baseline package version: `0.1.0`.
- Baseline worktree status: clean and equivalent to `## main...origin/main`.
- Baseline HEAD tag: none.
- Baseline exact-match tag: none.

## Slice 2 Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `36ec7d25142387ef0ee48a46e68849d2647da1f5`.
- Baseline subject: `Add Phase 47 direct row schema scope lock`.
- Baseline package version: `0.1.0`.
- Baseline worktree status: clean and equivalent to `## main...origin/main`.
- Baseline HEAD tag: none.
- Baseline exact-match tag: none.
- Natural CI: `CI` run `28841671010`, event `push`, headSha
  `36ec7d25142387ef0ee48a46e68849d2647da1f5`, completed with success.

## Selected Candidate

Phase 47 Slice 1 selects:

```text
A. Phase 47 Slice 1 candidate/scope lock only
```

Slice 1 rejects implementation in this gate. It does not include the private
row schema carrier scaffold, and it does not implement direct row schema MVP
behavior.

The rejected Slice 1 alternatives are:

```text
B. Phase 47 Slice 1 candidate/scope lock
   + private row schema carrier scaffold
C. Phase 47 Slice 1 direct row schema MVP implementation
```

The implementation direction is still Phase 47 `Direct Row Schema MVP`, but
behavior begins only in later separately approved slices.

## Slice 2 Route Expansion

Phase 47 Slice 2 selects:

```text
B. Add Phase 47 Slice 2 Gate 2 route expansion/static-audit update
```

The committed six-slice route compressed too many direct row schema behavior
decisions into one behavior slice and did not lock downstream readiness for
Phase 48 through Phase 50. Slice 2 expands Phase 47 to an eleven-slice route
without implementing behavior and without amending, rebasing, resetting, or
rewriting Slice 1 history.

## Scope Evidence

Phase 46 delivered private relation dependency graph and cycle diagnostics
while leaving row schema out of scope. The relevant locked boundary is:

- Phase 46 does not compute row schemas.
- Row schema propagation is deferred to Phase 47.
- Phase 47 entry direction is direct row schema MVP candidate work only.
- Private project semantic facts remain private and un-serialized.
- Project JSON v2 semantic diagnostics flow only through top-level
  `diagnostics[]`.

The older `docs/spec/pietto-roadmap-phase45-60-v1.md` row labels Phase 47 as
`Project Semantic Metadata Artifact`. For this Gate 2, that older roadmap row
is superseded by the phase-specific Phase 46 closeout and the current Phase 47
direct-row-schema planning lock. This Slice 1 does not edit the old roadmap.

## Future Direct Row Schema Boundary

The future Phase 47 MVP should add project-private row schema facts only. The
minimal future carrier should be private to `src/pietto/_project/model.py`,
frozen, slots-based, and independent from the single-file `pietto.semantic`
row schema classes. Likely private carrier names are:

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

These are planned private carrier concepts, not Slice 2 implementation. The
row field carrier may reserve private provenance or origin structure for future
expression-derived fields, but Slice 2 does not add the carrier and does not
authorize expression type inference.

Source definitions should get row schemas from resolved source shape fields.
The row schema should preserve source field order, resolved project type facts,
field nullability, and the original `FieldDef` owner where available.

Table/query output schema should initially support only direct projections over
direct source inputs:

- bare `field`;
- `source.field` when the qualifier matches the table/query `from` source
  name, in a separate bounded behavior slice.

Unknown direct field references should use existing semantic diagnostics flow,
with `PIE-S2102` as the preferred existing diagnostic candidate. The final
diagnostic code, message, and location policy must be confirmed in the
behavior slice Gate 1 before implementation. Project text / Project JSON v2
should receive those diagnostics through `ProjectSemanticResult.diagnostics`
and the already established semantic diagnostics path. Project JSON v2 shape
must not change.

`alias = field` is a direct field rename, for example:

```pietto
select:
    user_id = id
```

It preserves the input field type, nullability, and provenance while changing
the output name. It differs from bare `field` because the output name is
explicit. It differs from a computed alias such as `total = price + tax`
because no expression typing or computed value propagation is required.
`alias = field` belongs in Phase 47 only as a late bounded slice after bare
and qualified direct fields. `alias = source.field` may be considered in that
direct field rename slice only after qualified direct fields are complete.
The boundary is that computed aliases remain deferred to Phase 49.

## Downstream Readiness Lock

Phase 47 may include readiness for Phase 48 query-to-query row schema
propagation, but Phase 47 must not implement query-to-query propagation
behavior. Private carriers should be shaped so future downstream relation
schemas can be stored without refactor, relation row schema mappings should be
deterministic, and Phase 48 remains the behavior phase for table/query to
table/query row schema propagation.

Phase 47 may include readiness for Phase 49 computed alias schema and
let-bound expression schema, but Phase 47 must not implement computed aliases
or `let` schema behavior. Row field carrier vocabulary may reserve private
provenance or origin structure for future expression-derived fields. Computed
aliases and `let` remain deferred. No expression type inference is authorized
in Phase 47 unless a later Gate 1 explicitly widens scope.

Phase 47 may include readiness for Phase 50 aggregate output schema and
grouped result schema, but Phase 47 must not implement aggregate or grouped
output schema behavior. Row schema, nullability, and type vocabulary should
not block future aggregate result fields. Aggregate output schema remains
Phase 50 or later. No aggregate schema behavior is authorized in Phase 47
unless a later Gate 1 explicitly widens scope.

## Explicit Deferrals

The following work is deferred from Slice 1 and from the first direct behavior
slice unless a later Gate 1 explicitly widens scope:

- private row schema carrier scaffold in Slice 1;
- source row schema propagation in Slice 1;
- table/query output schema propagation in Slice 1;
- `alias = field` before its late bounded Phase 47 direct rename slice;
- computed aliases;
- expression typing for project relation bodies;
- `let` schema;
- aggregate output schema;
- query-to-query row schema propagation;
- projection/body validation beyond direct field references;
- project IR;
- project SQL;
- project `emit-sql`;
- project `explain`;
- public project semantic API;
- private semantic facts serialized into JSON;
- Project JSON v2 shape change;
- parser/grammar/generated changes;
- single-file behavior changes;
- JOIN behavior;
- relationship-driven query behavior;
- runtime/database execution behavior;
- package version changes.

Query-to-query row schema propagation behavior should be Phase 48 or a later
separately approved phase, not Phase 47.

## Final Phase 47 Slice Route

The final Phase 47 route is complete:

1. Candidate/scope lock only - complete
2. Route expansion and downstream readiness lock - complete
3. Private row schema carrier scaffold - complete
4. Source shape fields to source row schema - complete
5. Direct bare field projections from direct source inputs - complete
6. Qualified direct field projections: `source.field` - complete
7. Direct field rename projections: `alias = field` - complete
8. Unknown direct field diagnostics and deterministic ordering - complete
9. Downstream readiness hardening for Phase 48-50 - complete
10. Project JSON/private-fact privacy and compatibility hardening - complete
11. Completion audit/status lock - complete

Phase 47 Direct Row Schema MVP is complete after Slice 11. Slice 11 is
docs/tests/static-audit/status-lock work only. It adds no source/compiler
behavior and does not pre-claim the final Gate 3 natural CI proof; that proof
belongs in the Gate 3 report.

## Slice 11 Completion Audit And Status Lock

Phase 47 delivered project-private direct row schema facts only. The private
carrier inventory is:

- `ProjectRowFieldNullability`;
- `ProjectRowFieldProvenanceKind`;
- `ProjectRowFieldProvenance`;
- `ProjectRowField`;
- `ProjectRowSchema`;
- `ProjectSemanticModel.source_row_schemas`;
- `ProjectSemanticModel.relation_row_schemas`.

Source row schema propagation is complete for resolved source shape fields,
preserving source field order, resolved project type facts, project-private
nullability, and the original `FieldDef`.

Direct-source ungrouped relation row schemas are complete for:

- bare direct fields such as `id`;
- qualified direct fields such as `users.id`;
- renamed bare fields such as `user_id = id`;
- renamed qualified fields such as `user_id = users.id`.

Mixed direct field select order is preserved. Relation row fields preserve
type, nullability, and `FieldDef` facts from the source schema and use private
`SOURCE_FIELD` and `DIRECT_PROJECTION` provenance.

Unknown direct field references use existing semantic diagnostics flow through
`PIE-S2102`. Duplicate output names remain private unknown schemas without
diagnostics. Grouped relations skip direct relation row schema population to
preserve Phase 50 aggregate/grouped output-schema deferral.

Project JSON v2 privacy and compatibility are locked: Project JSON v2 key
order and shape remain unchanged, private row schema facts remain
un-serialized, private relation graph and cycle facts remain un-serialized,
and diagnostics flow only through the existing top-level `diagnostics[]`.

Package version remains `0.1.0`. Slice 11 performs no tag, release, publish,
upload, signing, or attestation. Final natural CI evidence belongs in the
Gate 3 report and must not be pre-claimed in docs.

The following remain deferred after Phase 47:

- Phase 48 query-to-query row schema propagation;
- Phase 49 computed alias schema;
- Phase 49 `let` schema;
- Phase 50 aggregate/grouped output schema;
- project IR;
- project SQL emit;
- project `emit-sql`;
- project `explain`;
- public project semantic API;
- parser/grammar/generated changes;
- single-file behavior changes;
- JOIN/relationship behavior;
- runtime/database execution;
- package version, tag, release, publish, upload, signing, or attestation.

## Gate 2 Allowlist

Phase 47 Slice 11 Gate 2 is limited to:

- `docs/plan/phase-47-direct-row-schema-mvp.md`
- `docs/spec/phase47-direct-row-schema-scope-lock-v1.md`
- `tests/test_phase47_completion_audit.py`
- `tests/test_phase47_direct_row_schema_scope_lock.py`

No other file is approved in this Gate 2. Slice 11 must remain
docs/tests/static-audit/status-lock only.

## Forbidden Surfaces

Gate 2 must not modify:

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

Gate 2 must not implement any source/compiler behavior.

## Validation Expectations

The focused Gate 2 validation commands are:

```bash
git diff --check
git diff --no-index --check -- /dev/null tests/test_phase47_completion_audit.py || true
uv run ruff format --check tests/test_phase47_completion_audit.py tests/test_phase47_direct_row_schema_scope_lock.py
uv run ruff check tests/test_phase47_completion_audit.py tests/test_phase47_direct_row_schema_scope_lock.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase47_completion_audit.py tests/test_phase47_direct_row_schema_scope_lock.py
```

Gate 2 must not run the broad test suite, `scripts/validate.py`, parser
generation, or formatters that modify files outside the Slice 11 allowlist.

## Stop Conditions

Stop immediately if:

- the branch is not `main`;
- the worktree or index is dirty before edits;
- the local branch is ahead, behind, or diverged unexpectedly;
- package version is not exactly `0.1.0`;
- any required change appears to require files outside the allowlist;
- implementation pressure appears for `src/**`;
- implementation pressure appears for parser/grammar/generated files;
- implementation pressure appears for CLI or Project JSON v2;
- new private row schema behavior becomes necessary in Slice 11;
- direct row schema behavior expansion becomes necessary in Slice 11;
- broad validation appears necessary;
- any focused validation command fails.

Gate 2 must not stage, commit, push, trigger CI, rerun CI, cancel CI, create a
tag, create a release, publish, upload, sign, or attest artifacts.
