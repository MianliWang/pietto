# Development

## Working rules

Use the smallest change that preserves current compiler behavior. Reuse an
existing owner before adding a helper or framework. Keep focused regression
tests for parser/AST, semantic/IR, SQL, diagnostics, CLI/JSON, package behavior,
generated artifacts, and real trust boundaries. Do not preserve historical
repository shape, completed-phase prose, path counts, or self-authored hashes.

Ponytail is an installed runtime layer: use `FULL` for ordinary work, `ULTRA`
for minimization, `ponytail-review` for candidates, and periodic
`ponytail-audit` or `ponytail-debt` only when useful. Pietto overrides its
deletion-first default only for semantic identity/completeness, ordering,
multiplicity, availability, stable diagnostics/output, generated
reproducibility, and genuine content/trust identity.

Escalate user decisions only for product behavior, durable architecture,
public compatibility, or high-risk trust/algorithm assumptions. Exact file
layout, straightforward behavior-equivalent implementation, formatting, and
derived cleanup are implementation freedom.

## Lean Gate v2

**Gate 0 — sync.** Fetch, require clean worktree/index, no active Git
operation, and a synchronized fast-forward `main`; freeze the baseline.

**Gate 1 — decisions.** Record only substantive product, durable architecture,
public compatibility, or high-risk trust/algorithm decisions. Do not make a
decision record for mechanical implementation detail.

**Gate 2 — build.** Implement the minimum solution, run focused checks, review
the complete candidate, group real findings by root cause, make one repair
batch when needed, run proportionate final validation, and seal the candidate
by its Git tree OID. Stop for unresolved material findings, trust/data-loss or
security regressions, unreproducible candidate content, validation failure, or
out-of-scope behavior.

**Gate 3 — publish.** Rebind the baseline, stage exactly the sealed tree, make
one ordinary fast-forward commit and push, then require natural exact-head CI.
If CI fails, preserve that head and repair in a child commit; never rerun the
failed head as a substitute for a repair.

Git is the publication mechanism. The conceptual states are
`DIRTY_LOCAL_CANDIDATE`, `CLEAN_PRE_PUSH`, and `SHALLOW_PUSHED_HEAD`; no
repository simulator is required. `origin/HEAD` is not publication authority.

## SHA policy v2

For ordinary work, baseline identity is the Git parent, candidate content is
the Git tree OID, and changed paths are derived from Git diff. Do not add
patch, manifest, evidence-file, historical repository, path, count, or
reader-of-reader digests. Keep hashes only when they bind a real cross-boundary
artifact: dependency/lock integrity, pinned GitHub Actions, generated artifact
or vendored-tool reproducibility, trusted opened bytes, or package/dependency
product identity. Product `sha256` semantics are unchanged.

## Validation tiers

Use the layered policy in
[Workflow Lifecycle Reader And Validation Efficiency v1](spec/workflow-lifecycle-reader-validation-efficiency-v1.md):
keep dirty-stage checks focused, run one complete review, then run the
authoritative Python 3.13 validator exactly once. Run generated, golden, and
package-smoke audits locally only when their owned risk surfaces change.
Natural CI remains the final independent Python 3.12 and 3.13 full-validation
owner.


## Explicit target conformance

After the Phase66 Slice2 infrastructure publication, applicable acceptance needs
both the existing compiler gates and successful PostgreSQL/MySQL conformance.
Default pytest remains offline; it runs the fixture/observer/config/receipt unit
checks without Docker or database discovery. Real execution is explicit:

```text
UV_PYTHON=3.13 uv run python tests/_pietto_target_conformance.py run --target postgres --pins tests/phase66_target_pins.json --evidence-dir /tmp/pietto-target-postgres-new --run-id local-check --run-attempt 1
UV_PYTHON=3.13 uv run python tests/_pietto_target_conformance.py run --target mysql --pins tests/phase66_target_pins.json --evidence-dir /tmp/pietto-target-mysql-new --run-id local-check --run-attempt 1
```

Use new owned evidence directories outside the repository. The fixed pins,
local Docker endpoint, linux/amd64 platform, finite cases, deadlines and exact
resource cleanup are specified by the [facility contract](spec/phase66-isolated-target-conformance-facility-v1.md).
No arbitrary DSN/image/SQL input, missing-environment skip, automatic retry of a
failed target, host administration or shared-image cleanup is provided.
`verify-receipts` is data-only; CI verifies both same-run receipts, transferred
bytes and successful compiler/target prerequisites through its strict aggregate.
Local compiler, local target, CI compiler and CI target results are separate.
This facility preserves its six Slice2 legacy/control cases and also consumes
the installed Slice3 scan/projection pipeline: production public artifact bytes,
independent data-only decoding, unchanged submission and complete typed BAG
observations. Slice3 added twelve cases and thirteen public artifact variants;
the [Slice4 contract](spec/phase66-slice4-named-shared-producer-scopes-terminal-output-emission-v1.md)
extended its publication manifest to fifteen cases and twenty-six public documents per
target, including six successful named-chain variants and seven structural-only
BLOCKED variants. Compiler failures have independent no-submission evidence.
The decoder checks actual immediate CTE terminals while retaining final physical
source provenance. Environment observations include identifier limits/case; pins,
acquisition limits and workflow commands remain unchanged. R03 joint JOIN/ORDER/SET
execution remains assigned to Slices7/10/11.


The [Slice5 fixed-value/native contract](spec/phase66-slice5-fixed-values-physical-type-anchors-server-parameter-use-mapping-v1.md)
sets the current exact A–S19-case/46-public-document denominator:30 VERIFIED,
3 INPUT_REJECTED and13 BLOCKED per target. Private receipts require v2 native
prepare/execute/session/argument/terminal/close-send evidence and exact harness inputs;
historical v1 is not new transport proof. MySQL query submissions use pinned low-level
native methods, including zero parameters. Fixed BEGIN/rollback and identified manager
operations retain their ordinary purpose. A native failure never falls back to a cursor.
Part A focused prerequisite and final whole-candidate target manifests are separate.
