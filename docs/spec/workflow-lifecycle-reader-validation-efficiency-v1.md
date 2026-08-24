# Workflow Lifecycle Reader And Validation Efficiency v1

## Answer And Scope

This maintenance policy separates mutable repository lifecycle presentation
from immutable historical product contracts and defines Pietto's layered local
validation workflow. It changes no Phase 58 product semantics or 12-Slice
route. Phase 58 Slice 5 remains unstarted and unauthorized.

## Lifecycle Reader Ownership

`tests/test_active_phase_lifecycle.py` is the sole test owner for the mutable
current state in `docs/status.md` and the current/next owner sentence in the
`Phase 58 route` section of `docs/roadmap.md`.

Git plus successful natural exact-head CI remains completion authority.
Documentation presents the next authorized working state and may intentionally
lag published completion by one transition.

## Historical Immutable Readers

Completed Phase 56/57 and Phase 58 product-Slice tests retain their own product,
compatibility, completion, route, non-scope, and handoff assertions from
immutable specifications and exact product authorities. They do not read the
mutable status table, current/next roadmap sentence, or current
`PHASE58_SLICE*_END_TO_END` identifier.

Removing mutable presentation assertions is not permission to remove product
semantics, compatibility boundaries, historical completion evidence, or
handoff direction.

## Lifecycle Transition Edit Set

The normal lifecycle presentation edit set for Phase 58 Slice 5 and later is:

```text
docs/roadmap.md
docs/status.md
tests/test_active_phase_lifecycle.py
```

Only the current task's genuinely affected source, specification, product test,
and direct semantic/compatibility readers are added. Completed Phase/Slice
tests are not mechanical lifecycle readers.

## Dirty Focused Validation

Before review, run only current task tests, changed historical tests, exact
direct semantic or compatibility readers affected by the changed contract,
changed-file Ruff format/check/lint, `git diff --check`, and a targeted type
check only when a repository-supported targeted command is materially useful.

Do not automatically run every test that opens a shared document, broad
historical compatibility bundles, unrelated whole-source scanners, full
pytest, `scripts/validate.py`, full production Pyright plus full test Pyright,
generated audit, golden audit, or package smoke during the dirty focused stage.

Opening the same file does not by itself make a test a focused reader. Its
assertion must consume the changed semantic region.

## Review

Run one complete foreground Ponytail FULL review. Discover the complete finding
set, group it by causal root, apply at most one causal repair generation, rerun
only affected focused checks, and perform a fresh complete rereview.

## Authoritative Local Validation

After a clean rereview, run exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

This is the comprehensive local release gate. Do not place a redundant broad
pseudo-full validation immediately before it. A failure after the validator
starts is terminal for that candidate.

## Risk-gated Auxiliary Audits

Run an auxiliary audit locally after review only when the task changes its
owned risk surface:

- generated audit when generator inputs or the generated surface changed;
- golden audit when golden-producing behavior, schema, or fixtures changed;
- package smoke when packaging inventory, installed import surface, package
  metadata, or the packaged module set changed.

The mere presence of these gates in CI does not require a redundant local run.

## Natural CI

Natural exact-head CI remains an independent full matrix on Python 3.12 and
3.13. Its authoritative validation, generated verification, golden audit, and
installed-package smoke must not be weakened by the layered local policy.

## Regression Lock

`tests/test_workflow_lifecycle_validation_efficiency.py` structurally enforces:

- exactly one mutable status reader;
- no mutable lifecycle or roadmap dependency in completed product tests;
- no historical `LIFECYCLE_READERS` or changing-path inventory;
- separation between product tests and lifecycle/workflow tests; and
- the authoritative full local gate plus unchanged natural CI ownership.

## Steady-state Efficiency

At adoption, 18 historical tests read the mutable status/current-owner state;
15 test paths appeared in all four Phase 58 Slice changed-path sets. The steady
state has one active mutable lifecycle reader and zero historical tests that
require per-Slice lifecycle edits.

## Compatibility And Non-scope

This policy changes tests and documentation only. It changes no production
source, public output, CLI, JSON, parser, AST, semantics, IR, SQL, package
behavior, generated artifact, golden fixture, workflow, version, tag, Release,
publication, signing, or attestation behavior.

