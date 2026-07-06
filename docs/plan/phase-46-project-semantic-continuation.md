# Phase 46 — Project Semantic Continuation

## Status

Phase 46 Slice 1 is Candidate Decision And Scope Lock for:

**Candidate/scope lock + private relation dependency graph scaffold + very narrow relation cycle detection MVP**

Slice 1 is docs/spec/static-audit work only. It implements no source behavior,
no dependency graph implementation, no relation cycle detection implementation,
no row schema implementation, no CLI behavior, no JSON behavior, no IR, no SQL,
no project `emit-sql`, no project `explain`, and no release behavior.

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
