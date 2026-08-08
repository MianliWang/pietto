# Semantic convergence reference

Supporting material for `SKILL.md`. The normative contract is
`docs/spec/pietto-semantic-slice-convergence-governance-v1.md`.

## Causal-root families observed in Phase 54 Slices 9 through 12

| Family | Violated invariant |
| --- | --- |
| authority root and canonical projection | a derived fact must name the exact canonical authority object that produced it, never a re-searched or differently scoped substitute |
| foreign or value-equal graft acceptance | provenance is decided by object identity; structural equality never selects a fact |
| mixed-root and coordinated replacement | the whole carrier plus its complete ordered child tuple is anchored, so a simultaneous replacement of every child is still rejected |
| first match, early return, winner selection, incomplete bucket | the complete candidate bucket is built and analyzed before any reduction, block, or winner selection |
| identity, ordering, multiplicity, cardinality collapse | every occurrence appears once, in exact source order, with exact owner identity; deduplication keys only on the exact object |
| availability, status, reason atomicity | status, reason, availability, analysis, and derived product form one atomic tuple |
| semantic owner or prerequisite ambiguity | a private path consumes exactly the prerequisite inputs and stage state the core path used |
| reader, hash, digest closure | the executing closure, the byte-modified set, and the frozen allowlist are three different sets |
| publication and synthetic topology mismatch | topology readers accept exactly the projections publication produces and re-read volatile references |
| interpreter-version compatibility | assert the behavior contract, never a standard-library exception class |
| evidence and documentary recovery | immutable evidence is never rewritten; a numbered append-only correction precedes any contradicting operation |
| false-positive review findings | a frozen contract clause outranks a review claim; a recorded disposition is reused, not re-argued |
| correctly retained later-scope findings | a deferred finding is recorded with its exact owner and re-entered as declared scope at the next Gate 0 |

## Worked example: one root, one projection, many views

A preservation carrier derives from three roots: the module set, the per-module
catalogs, and the relation resolutions. It builds one canonical source-ordered
tuple of relation facts. Everything else — a per-owner index, a per-role bucket,
a per-output-name lookup — is computed from that tuple at construction and is
never accepted as a constructor argument.

Consequences that follow automatically:

- a replacement operation can substitute a root and the projection rebuilds;
- a supplied index cannot smuggle in a fact the roots do not contain;
- a duplicate output name yields two retained occurrences and an ambiguous
  status rather than a silent overwrite;
- a lookup on an absent name returns an empty complete tuple, distinguishable
  from an unknown or blocked state.

## Anti-patterns with their exact failure

| Anti-pattern | Failure |
| --- | --- |
| `candidates[0]` after filtering | multiplicity collapse; ambiguity becomes undetectable |
| `return` on the first failing item | later items are never analyzed; mixed outcomes are misreported |
| `mapping.setdefault(name, fact)` | first writer wins; a later identity-distinct fact is dropped |
| keying a bucket on a display name | two modules with the same spelling merge |
| comparing rendered diagnostic text | text changes silently rebind provenance |
| `dataclasses.replace` on a derived field | a derived product is grafted without its roots |
| upgrading unknown to concrete when children look complete | availability atomicity is broken |
| adding a guard for the child a reviewer named | the next adjacent child fails in the next generation |

## Generation accounting worked through

Fourteen accepted review generations in one slice reduced to six causal roots,
one of which was purely iatrogenic — an over-broad repair invariant that broke
an established contract and had to be undone. Seven pushed heads carried those
fourteen generations, and only three of the seven carried product semantics.

The reading is not "fourteen architecture failures". It is: two roots
(non-concrete state handling and exact-identity binding) accounted for fifteen
of the accepted findings, and they were found one child at a time because each
review pass ran against a fresh tree instead of closing the carrier once.

## Freeze checklist

- [ ] every reproduced finding repaired and its owning clause recorded
- [ ] every property dimension exercised
- [ ] every compatibility suite green
- [ ] no pending finding on the current exact tree
- [ ] disposition register updated for every false positive
- [ ] negative-compatibility matrix recorded for every new invariant
- [ ] semantic freeze declared before any reader or hash refresh begins
