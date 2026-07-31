# Pietto End-to-end Resilience And Recovery Standard v1

## Status

This is the repository-owned recovery contract for every future Pietto
end-to-end Goal. It governs workflow recovery only. It does not authorize a
product, dependency, CI, release, or publication-scope change.

## Logical gates and continuation

Every end-to-end Goal has three logical gates:

1. Gate 0 / Gate 1 discovers authority, audits the live baseline, freezes
   product scope, converges the mechanical reader/topology closure, and creates
   immutable planning evidence.
2. Gate 2 implements the reviewed scope, validates the exact reviewed tree,
   and creates immutable evidence sidecars plus a concise main authority.
3. Gate 3 publishes exactly that tree, observes natural exact-head CI,
   reconciles `main` with ff-only semantics, cleans up the publication branch,
   and creates immutable publication evidence.

A successful gate continues automatically to the next gate when the Goal says
to proceed end to end. A pause is not a recovery mechanism. Return only for a
substantive STOP or when external state must be observed.

## Evidence creation

Every evidence target is a flat, predeclared path and is created once with
`O_CREAT | O_EXCL | O_NOFOLLOW`, mode `0644`. It must be a regular non-symlink
with one link. Never overwrite, truncate, replace, or repurpose an evidence
target. Reopen every created artifact and verify byte identity, mode, link
count, size, line count when textual, SHA-256, schema, and terminal.

The persistent operation ledger records whether every state-changing operation
was unconsumed, attempted with ambiguous outcome, or consumed with a verified
outcome. Process failure does not prove operation failure.

## Gate 0 corrections

After a valid original Gate 0 authority, at most three mechanical corrections
may add only:

- executing tests or test infrastructure;
- script, hash, Git-blob, directory-digest, inventory, formatter, or topology
  readers;
- exact formatter check-only paths;
- directly implied counts.

Correction 3 is final. Mechanical corrections cannot add product behavior,
dependencies, workflow changes, or weaker assertions. One separate
transcription-only correction may fix documentary copying without changing
scope, commands, counts, identities, or conclusions.

## Gate 2 and Gate 3 documentary recovery

Gate 2 evidence Recovery 1 and Recovery 2 and Gate 3 evidence Recovery 1 and
Recovery 2 are available only when the underlying operations and validation
already succeeded but the canonical evidence is documentary-defective. A
recovery references the invalid predecessor, records why it is superseded, and
reconstructs facts from immutable sidecars or read-only state. It never reruns
validation, changes the reviewed tree, or repeats publication.

## CI repair

Never manually dispatch, rerun, or cancel CI. One mechanical PR CI Repair 1 is
permitted only for a demonstrated CI-only defect. It uses a new commit, a new
natural `pull_request` attempt 1, and a new exact-head authority. One mechanical
Main CI Repair 1 is permitted only for a demonstrated main-CI-only defect. It
uses a new branch, commit, PR, squash, and new natural `push` attempt 1.

No repair may amend, rebase, force-push, directly push `main`, broaden product
scope, or hide a failing assertion. Each repair has its own Gate 0/1 and Gate 2
evidence; Main CI Repair 1 also has its own Gate 3 evidence.

## Ambiguous operations and retry

When a command reports failure after an operation may have reached a remote or
filesystem target, first reconcile read-only state. If the requested final
state exists exactly, mark the operation consumed and continue. If no state
changed, exactly one no-state-change retry is allowed when the controlling
Goal authorizes it. Conflicting, partial, or unprovable state is STOP.

## Publication invariants

Gate 3 requires all of the following:

- one exact allowlist and an empty index before staging;
- one candidate commit whose parent is the frozen base and whose tree equals
  the Gate 2 reviewed tree;
- one normal push of the declared branch;
- one ready PR with the exact base, head, title, and candidate SHA;
- one unique natural PR-CI attempt 1 for that exact head;
- expected-head squash protection;
- squash-tree equality with the reviewed and candidate trees;
- one unique natural main-CI attempt 1 for the exact squash SHA;
- one fetch and ff-only local reconciliation;
- exact local, tracking, and remote publication-branch cleanup.

Force push, amend, rebase, direct-main push, tag, Release, publish, upload,
signing, and attestation remain forbidden unless a separate Goal explicitly
authorizes them.

## Hard STOP conditions

STOP for ambiguous authority, baseline drift, allowlist escape, product or
architecture expansion, weakened security or supply-chain controls, unresolved
dynamic readers, incomplete topology coverage, tree inequality, conflicting
publication state, non-natural or wrong-head CI, dependency/lock/workflow
mutation outside scope, evidence overwrite, or an operation whose consumption
cannot be proven. These conditions are not mechanical recovery candidates.
