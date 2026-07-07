# Phase 47 - Direct Row Schema MVP

## Status

Phase 47 Slice 1 is Candidate Decision And Scope Lock for:

**Direct Row Schema MVP candidate/scope lock only**

Slice 1 is docs/spec/static-audit work only. It implements no source behavior,
no private row schema carrier scaffold, no source row schema propagation, no
table/query output schema propagation, no projection/body validation, no CLI
behavior, no Project JSON v2 behavior, no IR, no SQL, no project `emit-sql`,
no project `explain`, and no release behavior.

Phase 47 follows the completed Phase 46 `Project Semantic Continuation`.
Phase 46 explicitly deferred direct row schema propagation to Phase 47 and
closed with the entry direction "direct row schema MVP candidate work only".
That Phase 46 closeout is the authoritative next-phase source for this work.

Package version remains `0.1.0`.

## Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `2d06552789b3fac1db604f6da3552fd73040956f`.
- Baseline subject: `Complete Phase 46 project semantic continuation audit`.
- Baseline package version: `0.1.0`.
- Baseline worktree status: clean and equivalent to `## main...origin/main`.
- Baseline HEAD tag: none.
- Baseline exact-match tag: none.

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
- `ProjectRowField`;
- `ProjectRowSchema`;
- `ProjectSemanticModel.source_row_schemas`;
- `ProjectSemanticModel.relation_row_schemas`.

Source definitions should get row schemas from resolved source shape fields.
The row schema should preserve source field order, resolved project type facts,
field nullability, and the original `FieldDef` owner where available.

Table/query output schema should initially support only direct projections over
direct source inputs:

- bare `field`;
- optionally `source.field` when the qualifier matches the table/query
  `from` source name.

Unknown direct field references should use existing semantic diagnostics flow,
preferably existing `PIE-S2102`, and project text / Project JSON v2 should
receive those diagnostics through the already established semantic diagnostics
path. Project JSON v2 shape must not change.

## Explicit Deferrals

The following work is deferred from Slice 1 and from the first direct behavior
slice unless a later Gate 1 explicitly widens scope:

- private row schema carrier scaffold in Slice 1;
- source row schema propagation in Slice 1;
- table/query output schema propagation in Slice 1;
- `alias = field`;
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

Query-to-query row schema propagation should be Phase 48 or a later separately
approved phase, not Phase 47.

## Tentative Phase 47 Slice Route

The tentative Phase 47 route is:

1. Candidate/scope lock only
2. Private row schema carrier scaffold
3. Source shape fields to source row schema
4. Source-input table/query direct field projections to output schema and
   unknown-field diagnostics
5. Compatibility hardening
6. Completion audit/status lock

Any change to this route requires a later Gate 1 revision.

## Gate 2 Allowlist

Phase 47 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-47-direct-row-schema-mvp.md`
- `docs/spec/phase47-direct-row-schema-scope-lock-v1.md`
- `tests/test_phase47_direct_row_schema_scope_lock.py`

No other file is approved in this Gate 2.

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
uv run ruff format --check tests/test_phase47_direct_row_schema_scope_lock.py
uv run ruff check tests/test_phase47_direct_row_schema_scope_lock.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase47_direct_row_schema_scope_lock.py
```

Gate 2 must not run the broad test suite, `scripts/validate.py`, parser
generation, or formatters that modify files.

## Stop Conditions

Stop immediately if:

- the branch is not `main`;
- the worktree or index is dirty before edits;
- the local branch is ahead, behind, or diverged unexpectedly;
- HEAD is not `2d06552789b3fac1db604f6da3552fd73040956f`;
- package version is not exactly `0.1.0`;
- any required change appears to require files outside the allowlist;
- implementation pressure appears for `src/**`;
- implementation pressure appears for parser/grammar/generated files;
- implementation pressure appears for CLI or Project JSON v2;
- private row schema carrier implementation becomes necessary in Slice 1;
- direct row schema behavior implementation becomes necessary in Slice 1;
- broad validation appears necessary;
- any focused validation command fails.

Gate 2 must not stage, commit, push, trigger CI, rerun CI, cancel CI, create a
tag, create a release, publish, upload, sign, or attest artifacts.
