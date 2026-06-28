# Phase 35 Developer Experience And Delivery Pipeline MVP

## 1. Status And Trusted Handoff

Phase 35 Slice 1 Candidate Decision, Inventory, And Safe Simplification Scope
is the current docs/spec/static-audit-only slice.

Trusted handoff:

- baseline HEAD: `10f882ad66f94523e05368b34aea9c5f845a9e62`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 34 relationship readiness audit`;
- Phase 34 is complete, pushed, and CI green;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation occurred.

Phase 34 completion statement:

```text
Phase 34 Relationship Grain And Narrow JOIN readiness foundation is complete as docs/spec/static-audit/status-only work. The original behavior MVP remains future implementation deferred.
```

Phase 34 completed as a conservative relationship grain and narrow JOIN
readiness/contracts foundation only. Phase 35 must preserve that handoff:
unsupported join-like syntax remains unsupported, relationship metadata remains
metadata-only, current single-input relation behavior remains unchanged,
`RelationIR` remains single-source, PostgreSQL/MySQL render one `FROM` input,
and Phase 33 project/JSON boundaries remain locked.

## 2. Candidate Decision

The selected Phase 35 direction is:

**Developer Experience And Delivery Pipeline MVP**

Proceed with Phase 35 as Developer Experience And Delivery Pipeline MVP. Slice
1 adds Safe Simplification as a scoped developer-experience discipline, not as a
roadmap title change and not as authorization for source refactors. Slice 1 is
docs/spec/static-audit-only and implements no behavior change.

Safe Simplification is a Slice 1 scope and future-slice discipline. It is not a
Phase 35 title change, not a compiler behavior change, not a cleanup mandate,
not a roadmap title change, and not authorization for large rewrites.

Slice 1 adds only:

- this Phase 35 plan;
- `docs/spec/phase-35-safe-simplification-contract-v1.md`;
- `tests/test_phase35_safe_simplification_candidate_decision.py`.

Slice 1 does not update `README.md`, `AGENTS.md`, or
`docs/spec/pietto-v0.9.md`. Those global status-housekeeping files are stale
after Phase 34 and remain a later dedicated slice candidate.

## 3. Slice 1 Objective

Slice 1 records the Phase 35 candidate decision, Phase 34 handoff, Safe
Simplification inventory, no-behavior-change standard, stale
status-housekeeping needs, validation strategy, and forbidden surfaces.

Safe Simplification means reducing duplication, clarifying local control flow,
improving helper boundaries, and aligning developer guidance only when public
behavior remains unchanged.

## 4. Safe Simplification Categories

Every Phase 35 simplification candidate must be classified into one of these
categories:

- `safe docs/status housekeeping`;
- `safe test-helper simplification`;
- `safe internal helper simplification with proof`;
- `behavior-risky refactor`;
- `defer / do not touch`.

Current Slice 1 inventory:

- `safe docs/status housekeeping`: later update `AGENTS.md`, `README.md`, and
  `docs/spec/pietto-v0.9.md` to record Phase 34 complete and Phase 35 active.
- `safe test-helper simplification`: repeated Phase 34 static-audit helpers such
  as `_read`, `_normalized`, `_phase34_docs`, `_git_diff_name_only`,
  release-claim constants, and forbidden path lists are later candidates.
- `safe internal helper simplification with proof`: CLI parse/analyze/IR flow
  and project/metadata serializers have helper opportunities but touch public
  CLI, JSON v1, Project JSON v2, or Semantic Metadata Artifact v1 behavior.
- `behavior-risky refactor`: PostgreSQL/MySQL expression and relation renderer
  de-duplication can change SQL bytes or backend fail-closed errors.
- `defer / do not touch`: grammar, generated parser, fixtures, goldens, package
  metadata, workflows, JOIN/grain implementation, project source selection, and
  runtime/database behavior.

## 5. No-behavior-change Standard

A simplification is allowed only if it preserves accepted/rejected programs,
diagnostics code/message/order/span where applicable, SQL bytes, JSON v1,
Project JSON v2, Semantic Metadata Artifact v1, generated inventory, goldens,
package version, dependencies, workflows, and public CLI behavior.

Shorter code is not success unless the exact public surface remains unchanged.
Fail-closed branches and explicit diagnostics must be preserved over compact
ambiguous control flow.

## 6. Validation Strategy

Every implementation slice must run focused tests for the changed surface and
the standard repository validation stack appropriate to its risk.

Slice 1 validation commands:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest tests/test_phase35_safe_simplification_candidate_decision.py
uv run pytest tests/test_phase34_completion_audit.py
uv run pytest tests/test_phase33_completion_audit.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run python scripts/validate.py
git diff --check
git diff --cached --check
```

Future refactor slices also require pre-check evidence, full diff, focused
diff, full changed-file contents, replacement table, forbidden-surface checks,
validation raw output, package/tag proof, and final integrity checks.

## 7. Forbidden Surfaces

Slice 1 must not modify:

- `README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md`;
- grammar or generated ANTLR artifacts;
- parser, AST, semantic model, Semantic IR, SQL backends, CLI behavior, JSON
  v1, Project JSON v2, or Semantic Metadata Artifact v1 behavior;
- source code under `src/pietto/`;
- fixtures, goldens, scripts, dependencies, package metadata, lockfiles, or
  workflows;
- package version, tags, releases, publishing, uploads, signing, or
  attestation.

Slice 1 also must not implement JOIN, JOIN syntax, relationship grain syntax,
project source selection, multi-file semantic behavior, runtime/database
behavior, schema introspection, graph/ERD/AI metadata export, or any deferred
feature.

## 8. Tentative Later Slices

Tentative future slices, subject to separate approval:

1. Candidate Decision, Inventory, And Safe Simplification Scope.
2. Status-housekeeping for `README.md`, `AGENTS.md`, and
   `docs/spec/pietto-v0.9.md`, if explicitly approved.
3. Shared test helper simplification, if focused static-audit helper proof is
   approved.
4. Validation/delivery workflow polish, if it does not mutate package metadata,
   dependencies, lockfiles, or workflows without separate approval.
5. Internal helper simplification candidates only with explicit approval and
   full public-surface proof.
6. Completion Audit And Status Lock.

This breakdown authorizes no implementation beyond Slice 1.

## 9. Slice 1 Status

Slice 1 is docs/spec/static-audit-only. It adds a Phase 35 plan, a Safe
Simplification contract, and focused static audit coverage. Slice 1 implements
no source refactor, no test-helper refactor, no behavior change, no grammar or
generated change, no fixture or golden change, no package/dependency/workflow
change, and no release operation.

Package version remains `0.1.0`. No tag/release/publish/upload/signing/
attestation is performed by Slice 1.
