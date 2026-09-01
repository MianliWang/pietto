# Phase 62 Slice 9 Explicit Relationship Paths, Fanout/Survival/Null Effects, And Join-Shape Analysis v1

## Exact owner and authority

Slice 9 adds private `src/pietto/_project/project_relationship_paths.py` over
the exact Slice-8 guarantee set. Starting authority is commit
`6dd7dec031bb23d4d675ecf03542186b6df5f371`, tree
`ec3c885527968f4fad65b619bc4fccd5253392dd`, natural CI `33502717286`.

```text
relationship declaration != relationship direction != path step
path step != relationship path != traversal use != JOIN occurrence
```

## Frozen closure

The exact closure is `A3/M5/D0`: roadmap, this contract, status, the private
owner, active lifecycle, Slice-1 live-source reader, Slice-9 focused test, and
validator inventory. A ninth path is `READER_CLOSURE_DRIFT`.

## Direct index and explicit path law

The immutable index retains every concrete direction in Slice-8 order, every
non-concrete subject, exact source/target output-ref buckets, and exact
declaration buckets. Direct shorthand returns ABSENT for zero candidates,
CONCRETE for one, and AMBIGUOUS with all candidates for more than one. Parallel
and self directions never choose a first/name/declaration winner.

A path is a non-empty caller-supplied tuple of exact retained directions.
Path-step positions are contiguous and path-local. Adjacent target/source
properties must be exact-object identical. Repeated directions and finite self
loops remain valid occurrences. No BFS, DFS, shortest-path, all-path, best-path,
or multi-hop cache creates authority.

## Fanout and future INNER survival

AT_MOST_ONE maps to PRESERVES_SOURCE_MULTIPLICITY; UNBOUNDED_BY_ONE maps to
MAY_MULTIPLY. `MAY_MULTIPLY != proof that multiplication occurs`. Path fanout
preserves only when all hops preserve and retains every multiplying-risk hop.

AT_LEAST_ONE maps to GUARANTEES_SOURCE_SURVIVAL; ZERO_ALLOWED maps to
MAY_DROP_SOURCE_ROWS. `ZERO_ALLOWED != proof that a row is actually unmatched`.
Path survival retains every risky hop and is conditional readiness for future
INNER realization, not an executed JOIN effect.

## Future LEFT nulling potential

AT_LEAST_ONE means no local missing-match nulling; ZERO_ALLOWED means
MAY_NULL_EXTEND. Linear all-LEFT folding starts with a non-null-extended source
and propagates null potential downstream once any local root is reached. It
retains every local ZERO_ALLOWED root separately from every propagated target
position. This is analysis readiness only: no actual JOIN/nulling provenance,
optional grain factor, or Project IR property is constructed.

## Independent axes and boundaries

Fanout, future INNER survival, and future LEFT nulling remain independent and
retain per-hop evidence. They are not replaced by ONE_TO_ONE/ONE_TO_MANY labels
and are distinct from grain and cardinality bounds.

There is no grammar/AST/generated, traversal/JOIN syntax, binary JOIN IR,
actual null extension, optional factor, SQL, CLI/JSON/Project Explain, public
schema, chasm/fan-trap/multi-fact/aggregate-safety, optimizer, package/workflow,
dependency, or version delta.

Focused assurance covers absent/unique/ambiguous direct buckets, parallel/self
directions, explicit contiguous and invalid paths, finite repeated steps,
preserving/multiplying hops, guaranteed/may-drop survival, early/late/all-safe
null propagation, complete risk-step evidence, and no automatic path API.

## Review, publication, and handoff

Slice 9 allows one bounded repair batch (`1/1` after review), one authoritative
validator, one ordinary commit/push, and natural exact-head attempt-1 CI.

The single repair root is
`PATH_ANALYSIS_CARRIER_DOES_NOT_CLOSE_AGGREGATE_EFFECT_AND_COMPLETE_RISK_EVIDENCE`.
The repair makes the path-analysis carrier independently recompute and validate
all three aggregate axes, every risky hop, every local nulling root, and every
propagated-null position.

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
Add Phase 62 relationship path and fanout analysis
PASS — PHASE62_SLICE9_EXPLICIT_RELATIONSHIP_PATHS_FANOUT_SURVIVAL_NULL_EFFECTS_JOIN_SHAPE_ANALYSIS_END_TO_END
```

After PASS, `Phase 62 Slice 10 = NEXT / NOT IMPLEMENTED`. Do not begin Slice 10.
