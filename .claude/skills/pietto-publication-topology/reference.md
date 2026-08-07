# Publication topology reference

Supporting material for `SKILL.md`. Deterministic fixtures live in
`tests/_pietto_publication_topology.py`.

## Fixture surface

| Name | Purpose |
| --- | --- |
| `TOPOLOGY_KINDS` | the seven standardized projection identifiers, sorted |
| `build_topology(kind, root)` | build one projection inside an empty temporary root |
| `build_all(root)` | build every projection under one temporary root |
| `observe(...)` | read branch, head, tree, parents, merge base, shallow flag, event metadata, and dirty sets |
| `TopologyExpectation` | the exact state a reader may accept |
| `verify(observation, expectation)` | exact mismatch reasons; empty accepts |
| `assert_topology(fixture)` | fail closed unless a built projection matches its own expectation |
| `rejected_variants(expectation)` | named corruptions that must all be rejected |
| `sequence_is_complete(kinds)` | whether a sweep covered every projection |

Commit identity and timestamps are pinned, so a fixture built twice produces
the same commits and the same trees.

## Observed field semantics

| Field | Meaning |
| --- | --- |
| `branch` | current branch name, or `HEAD` when detached |
| `head` | current commit |
| `head_tree` | tree of the current commit; equality with the reviewed tree is the merge gate |
| `head_parents` | ordered parents; empty on a shallow boundary, two on a merge |
| `merge_base` | merge base with the declared base reference; empty when unavailable |
| `shallow` | whether the checkout is depth limited |
| `event_name` | integration event: pull request, push, or local |
| `event_head_ref`, `event_base_ref` | event-declared head and base branch names |
| `added_paths`, `modified_paths`, `deleted_paths` | untracked, modified, and deleted working-tree paths |
| `staged_paths` | paths whose index entry differs from the head commit |

## Why each projection exists

- **dirty gate candidate** — the only projection in which a gate manifest sees
  a non-empty dirty set. Readers gated on the dirty set take a different branch
  here than anywhere else.
- **clean topic candidate** — the first projection where the dirty branch stops
  applying and the clean branch begins asserting inventories.
- **non-amend repair child** — proves a repair chains from the previous head
  rather than replacing it, and that the previous head's guards still hold.
- **pull-request merge** — two parents in a fixed order and a detached head.
  Guards that assume a named branch or a single parent break here.
- **shallow pull-request checkout** — the depth-limited *merge* commit, detached,
  with no parents and no merge base. Integration checks out the synthetic merge,
  not the named topic branch; a fixture built from the branch would describe the
  pull-request head instead of the checkout and would pass locally while the real
  run still failed.
- **squashed main** — a single parent and a tree equal to the topic tree. This
  is where tree equality is proven.
- **natural main push** — the squashed result observed under a push event, so
  event-scoped guards are exercised on the merged head.

## Failure modes this harness models

| Historical failure | Modeled by |
| --- | --- |
| a guard written for the local topic applied unconditionally to the merge and main projections | building the merge and main projections separately and requiring each guard to state its scope |
| a bypass commit with the expected parent and subject but a different tree was accepted | the wrong-tree rejection variant |
| moving references read once and reasoned about later | re-reading every reference inside its observation window |
| a projection sweep that ran the reader set but omitted the focused module | including the focused module in the sweep |
| a shallow checkout treated as if history were present | the shallow projection with no parents and no merge base |
| a staged-only change observed as a clean tree | index and worktree status bits are both read, and renames, copies, and unmerged records fail closed |
| an obsolete generation predicate conflated with the latest clean state | one expectation per projection, compared field by field |

## Sweep checklist

- [ ] all seven projections built
- [ ] each projection accepted by its own expectation
- [ ] every corruption variant rejected for every projection
- [ ] topology-sensitive readers run under every projection
- [ ] the focused module of the current work included in every projection
- [ ] `sequence_is_complete` confirms full coverage
