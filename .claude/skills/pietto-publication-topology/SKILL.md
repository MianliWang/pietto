---
name: pietto-publication-topology
description: Build and verify the seven temporary, non-primary-repository publication projections - dirty gate candidate, clean topic, non-amend repair child, pull-request merge, shallow pull-request checkout, squashed main, and natural main push - before running any topology-sensitive Pietto reader. Invoke explicitly before a push and before a merge.
disable-model-invocation: true
---

# Pietto Publication Topology

Normative contract: `docs/spec/pietto-semantic-slice-convergence-governance-v1.md`.
Deterministic fixtures: `tests/_pietto_publication_topology.py`. Worked material:
`reference.md` next to this file.

Every fixture is temporary and lives outside the primary repository. Nothing
here mutates the working repository, reads the network, or touches a tracked
file.

## 1. The seven projections

| Projection | Shape |
| --- | --- |
| dirty gate candidate | on the base branch, uncommitted added and modified paths |
| clean topic candidate | topic branch, one commit whose parent is the base |
| non-amend repair child | topic branch, a further commit whose parent is the previous head |
| pull-request merge | detached merge commit with two parents, base first, head second |
| shallow pull-request checkout | depth-limited checkout, no parents, no merge base |
| squashed main | base branch, single parent, tree equal to the real merge of the base and the topic |
| natural main push | the squashed head checked out at depth one under a push event |

## 2. Establish before observing

A fixture must establish, and a reader must be told, all of: refs, parents,
merge base, shallow boundary, event metadata, head and base identity, and the
expected tree. A projection that is observed without a declared expectation
proves nothing.

## 3. Verify fail closed

Accept only when every declared field matches exactly. Each of these must be
rejected: wrong parent, wrong ref, wrong tree, wrong shallow boundary, wrong
event metadata, wrong head, wrong dirty set.

Tree equality is load bearing on its own. A commit with the expected parent and
the expected subject but a different tree must be rejected.

## 4. Re-read volatile references

Read every moving reference inside the same observation window that uses it. A
predicate that samples a reference once and reasons about it later can accept a
state that no longer exists.

## 5. Scope each guard explicitly

State for every guard which projections it applies to. Applying a
local-topic-only condition unconditionally to a merge or main projection is a
recurring and expensive defect.

## 6. Sweep before every push and before merge

Run the complete topology-sensitive reader set under every projection, and
include the focused module of the current work. A green local run with an
omitted projection is the most common cause of a failed integration attempt.

## 7. Consumed history

A failed integration run is consumed history. Repair the cause in a new
non-amend commit; never re-run, dispatch, or cancel to obtain a different
result.
