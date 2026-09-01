# Phase 62 Slice 8 Referential Coverage, MATCH SIMPLE/FULL, And Directional Match Guarantees v1

## Exact owner and authority

Slice 8 adds private
`src/pietto/_project/project_relationship_match_guarantees.py` over exact
Slice-3 conditions and Slice-7 final-output key/value-class authority. Starting
authority is commit `01e3c910ec29f85a4b31e4d1a9dcfa6571d19af1`, tree
`35f040a8c12d2244d8007dd3b367be67a81344bf`, natural CI `33498869865`.

```text
relationship declaration != direction != traversal != path != JOIN occurrence
```

## Frozen closure

The exact closure is `A3/M5/D0`: roadmap, this contract, status, the private
owner, active lifecycle, Slice-1 live-source reader, Slice-8 focused test, and
validator inventory. A ninth path is `READER_CLOSURE_DRIFT`.

## Direction and independent bounds

Each retained concrete relationship has two exact directions in relationship
source order then endpoint `0->1`, `1->0`. Direction identity retains the exact
declaration and both endpoint occurrences, so self relationships and repeated
endpoint pairs do not collapse.

Minimum is independently `ZERO_ALLOWED` or `AT_LEAST_ONE`. Maximum is
`AT_MOST_ZERO`, `AT_MOST_ONE`, or `UNBOUNDED_BY_ONE`.

```text
UNBOUNDED_BY_ONE != proof that multiple matches exist
ZERO_ALLOWED != proof that an unmatched row exists
```

Display values such as `0..1` are derived views only.

## Target at-most-one theorem

Endpoint-normalized exact correspondences map by exact `ProjectRowField` object
membership to target final-output value classes. `AT_MOST_ONE` holds when all
determinant classes of at least one target output key are included in the
matched target classes. Extra correspondence fields are allowed; partial keys
are not.

Both STRICT and LAX target keys prove at-most-one under standard-equality
TRUE-only matching. Source uniqueness, FD closure, grain equality, LIMIT,
names, and estimates never substitute for a target key. Every qualifying key
and every correspondence remain in the upper-bound evidence.

## Referential coverage boundary

```text
target key / FD != referential coverage != existence proof
```

Coverage has a distinct typed direction, correspondence tuple, source/target
scope, policy, origin, trust, and exact explicit authority. Policies are exactly
`MATCH_SIMPLE` and `MATCH_FULL`; there is no MATCH PARTIAL.

Current Pietto source has no authored coverage/MATCH producer. The canonical
builder therefore creates only
`NOT_CONSTRUCTIBLE_FROM_CURRENT_AUTHORED_SOURCE`, never fabricated positive
coverage or `AUTHORED_CONTRACT`. Positive coverage laws are exercised only at
the pure typed boundary with an opaque explicit authority. Catalog evidence
remains Phase 69.

## MATCH NULL applicability

MATCH SIMPLE: any source determinant NULL makes coverage inapplicable to that
row; all non-NULL requires a match. MATCH FULL: all NULL is an accepted null
reference, all non-NULL requires a match, and mixed NULL/non-NULL is a FULL
violation. These rules do not change standard equality, where NULL prevents
TRUE.

## At-least-one theorem

`AT_LEAST_ONE` requires trusted applicable coverage, exact source matched
classes whose every occurrence is NON_NULL, exact source/target scopes, target
visibility, and no weakening JOIN/policy boundary. Coverage or relationship
existence alone is insufficient. Nullable/UNKNOWN source fields retain
`ZERO_ALLOWED` with an explicit epistemic reason.

## Completeness and non-concrete isolation

The canonical set preserves every relationship. Proof-capable conditions yield
exactly two directions. Non-concrete relationships and absent/failed conditions
retain typed causal subjects and no partial correspondence/key/coverage proof.
No relationship/name winner or path scan exists.

## Zero delta and assurance

There is no grammar/AST/generated, authored syntax, JOIN/traversal, path,
fanout/survival/null-extension, Project IR binary node, multi-fact, SQL,
CLI/JSON/Project Explain, public schema, package/workflow/dependency/version,
catalog, or runtime-discovery delta.

Focused assurance covers distinct directions/self/repeated declarations,
STRICT/LAX/composite/superset/partial target keys, source-side non-proof,
coverage absence, SIMPLE/FULL truth tables, explicit coverage plus NON_NULL,
nullable fallback, deterministic order, non-concrete isolation, and public
boundaries.

## Review, publication, and handoff

Slice 8 allows one bounded repair batch (`1/1` after review), one authoritative
validator, one ordinary commit/push, and natural exact-head attempt-1 CI.

The single repair root is
`MATCH_GUARANTEE_CARRIERS_DO_NOT_CLOSE_DIRECTION_CONDITION_BOUND_AND_COMPLETE_LEDGER_AUTHORITY`.
The repair makes coverage, independent bounds, direction attachments, and the
complete relationship/direction subject ledger reject detached or incomplete
authority.

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
Add Phase 62 directional relationship match guarantees
PASS — PHASE62_SLICE8_REFERENTIAL_COVERAGE_MATCH_SIMPLE_FULL_DIRECTIONAL_MATCH_GUARANTEES_END_TO_END
```

After PASS, `Phase 62 Slice 9 = NEXT / NOT IMPLEMENTED`. Do not begin Slice 9.
