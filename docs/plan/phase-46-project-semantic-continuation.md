# Phase 46 — Project Semantic Continuation

## Status

Phase 46 Slice 1 is Candidate Decision And Scope Lock for:

**Candidate/scope lock + private relation dependency graph scaffold + very narrow relation cycle detection MVP**

Slice 1 is docs/spec/static-audit work only. It implements no source behavior,
no dependency graph implementation, no relation cycle detection implementation,
no row schema implementation, no CLI behavior, no JSON behavior, no IR, no SQL,
no project `emit-sql`, no project `explain`, and no release behavior.

Phase 46 Slice 8 is `Completion audit and status lock`. Slice 8 is
docs/tests/static-audit/status-lock only. It locks the Phase 46 completion
boundary after Slices 1 through 7 without changing production source behavior,
parser behavior, Project JSON v2 behavior, single-file behavior, package
metadata, workflow/dependency files, or release surfaces.

Phase 46 is complete after Slice 8 as `Project Semantic Continuation`, with
the final Gate 3 commit, push, and natural CI proof handled outside this Gate 2
document.

Phase 46 continues after the completed Phase 45
`Project-wide Semantic Model Design And MVP`. It preserves Phase 45's private
project semantic model boundary and advances only toward private relation
dependency graph readiness and a narrow relation cycle diagnostic MVP in later
slices.

Package version remains `0.1.0`.

## Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `13a870f06c10747ac19c6255f7e68205de954558`.
- Baseline subject: `Update uv-build requirement from <0.12.0,>=0.11.19 to >=0.11.26,<0.12.0 (#8)`.
- Baseline package version: `0.1.0`.
- Baseline worktree status: clean and equivalent to `## main...origin/main`.
- Baseline HEAD tag: none.
- Baseline exact-match tag: none.

## Approved Phase 46 Direction

Phase 46 is approved as:

```text
Candidate/scope lock
    + private relation dependency graph scaffold
    + very narrow relation cycle detection MVP
```

The equivalent candidate option is:

```text
C. Candidate/scope lock + dependency graph scaffold
   + narrow A. Cycle detection MVP
```

The Phase 46 MVP is private-first and conservative. It may add private project
semantic state in later slices, but that state must remain outside public
project JSON, public CLI schemas, SQL lowering, project `emit-sql`, project
`explain`, and single-file behavior.

## Rejected And Deferred Alternatives

Phase 46 does not select a direct row schema MVP. Direct row schema propagation
is deferred to Phase 47.

The following alternatives are explicitly deferred:

- direct row schema MVP deferred to Phase 47;
- query-to-query schema propagation deferred;
- computed aliases deferred;
- `let` schema deferred;
- aggregate output schema deferred;
- project explain/metadata deferred;
- relationship/JOIN deferred;
- project IR and project SQL deferred;
- runtime/database execution deferred.

## Slice 1 Scope

Slice 1 is docs/spec/static-audit only.

Slice 1 creates the Phase 46 plan, the Phase 46 scope-lock specification, and a
focused static audit test. It does not implement the dependency graph scaffold,
does not collect relation dependency edges, does not select a cycle diagnostic
code, and does not detect cycles.

Slice 1 also does not change parser behavior, grammar, generated parser
artifacts, AST, semantic analysis, private project model source, CLI routing,
Project JSON v2 serialization, fixtures, goldens, scripts, workflows,
dependency files, package metadata, package version, tag, release, publish,
upload, signing, or attestation behavior.

## Tentative Phase 46 Slice Route

The tentative Phase 46 route is:

1. Candidate decision and scope lock
2. Private relation dependency graph scaffold
3. Relation edge collection from existing table/query `from` dependencies
4. Deterministic cycle detection MVP
5. Text-mode project semantic diagnostics
6. JSON v2 diagnostics through existing `diagnostics[]`
7. Compatibility hardening
8. Completion audit/status lock

Any change to this route requires a later Gate 1 revision.

## Gate 2 Allowlist

Phase 46 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-46-project-semantic-continuation.md`
- `docs/spec/phase46-project-semantic-continuation-scope-lock-v1.md`
- `tests/test_phase46_project_semantic_continuation_scope_lock.py`

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
- `src/pietto/cli.py`
- `src/pietto/_project/json_v2.py`
- `src/pietto/_project/model.py`
- `src/pietto/_project/check.py`

Gate 2 must not implement:

- relation cycle detection implementation;
- dependency graph implementation;
- row schema implementation;
- projection/body field validation;
- query-to-query schema propagation;
- computed alias schema;
- `let` schema;
- aggregate output schema;
- project IR;
- project SQL emit;
- project explain;
- public project semantic API;
- private semantic facts serialized into JSON;
- Project JSON v2 shape change;
- parser/grammar/generated changes;
- single-file behavior changes;
- JOIN behavior;
- relationship-driven query behavior;
- runtime/database execution behavior;
- package version changes.

## Validation Expectations

The focused Gate 2 validation commands are:

```bash
git diff --check
uv run ruff format --check tests/test_phase46_project_semantic_continuation_scope_lock.py
uv run ruff check tests/test_phase46_project_semantic_continuation_scope_lock.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase46_project_semantic_continuation_scope_lock.py
```

Gate 2 must not run the broad test suite, `scripts/validate.py`, parser
generation, or formatters that modify files.

## Stop Conditions

Stop immediately if:

- the branch is not `main`;
- the worktree or index is dirty before edits;
- the local branch is ahead, behind, or diverged unexpectedly;
- HEAD is not `13a870f06c10747ac19c6255f7e68205de954558`;
- package version is not exactly `0.1.0`;
- any required change appears to require files outside the allowlist;
- implementation pressure appears for `src/**`;
- implementation pressure appears for parser/grammar/generated files;
- implementation pressure appears for CLI or Project JSON v2;
- cycle diagnostic code selection becomes necessary;
- row schema implementation becomes necessary;
- broad validation appears necessary;
- any focused validation command fails.

Gate 2 must not stage, commit, push, trigger CI, rerun CI, cancel CI, create a
tag, create a release, publish, upload, sign, or attest artifacts.

## Slice 8 Completion Audit And Status Lock

Slice 8 is docs/tests/static-audit/status-lock only. It adds the final Phase
46 completion audit and updates the Phase 46 plan/spec status lock. Slice 8
does not change production source behavior.

The Phase 46 completion boundary is locked by Slice 8. Phase 46 is complete
after Slice 8 as `Project Semantic Continuation`, with the final Gate 3 commit,
push, and natural CI proof handled outside this Gate 2 document.

The final delivered Phase 46 boundary includes:

- candidate decision and scope lock;
- private relation dependency graph scaffold;
- relation edge collection from existing table/query `from` dependencies;
- deterministic private relation cycle facts;
- project relation cycle diagnostics through `PIE-S2302`;
- Project JSON v2 relation cycle diagnostics compatibility through existing
  `diagnostics[]`;
- project compatibility hardening;
- completion audit and status lock.

Private graph and cycle facts remain private and un-serialized. Project JSON
v2 does not expose `ProjectRelationDependencyGraph`,
`ProjectRelationDependencyCycle`, `relation_dependency_graph`, `cycles`,
graph nodes, graph edges, dependency sources, or private semantic model
internals. Semantic diagnostics remain top-level `diagnostics[]`;
`cli_errors[]` remains project/config/source-selection/source-read only;
`inputs[]` and `result.check` remain read/parse based; no semantic input
statuses or semantic file counters are introduced.

Single-file `check`, CLI JSON v1, `emit-sql`, and `explain` remain separate and
unchanged. Project `emit-sql` and project `explain` remain unsupported or
absent. Slice 8 has no IR, SQL, project `emit-sql`, or project `explain` path.

Slice 8 changes no row schema behavior, projection/body validation,
query-to-query schema propagation, computed alias schema, `let` schema,
aggregate output schema, project IR, project SQL, project `emit-sql`, project
`explain`, public project semantic API, private semantic fact serialization,
Project JSON v2 shape, parser public API, grammar, generated parser artifact,
single-file behavior, JOIN behavior, relationship-driven query behavior,
runtime/database behavior, fixture, golden, package version, workflow,
dependency file, package metadata, tag, release, publish, upload, signing, or
attestation behavior.

Phase 47 entry direction is direct row schema MVP candidate work only. Slice 8
does not implement row schema propagation. Phase 48 through Phase 50 and later
project IR, project SQL, and import/module/export work remain future Gate 1
planning topics and are not authorized by this Phase 46 closeout.
